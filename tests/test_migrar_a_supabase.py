import json
import sqlite3

from tests.fakes_supabase import FakeSupabaseClient
from scripts.migrar_a_supabase import migrar, resolver_clientes_json_path
from web import cuentas


def _usuarios_db(tmp_path):
    db_path = tmp_path / "usuarios.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nombre TEXT, email TEXT UNIQUE, "
        "password_hash TEXT, creado TEXT)"
    )
    conn.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, creado) VALUES (?, ?, ?, ?)",
        ("Mayorista Uno", "mayorista@x.com", "hash-no-migrable", "2026-01-01 10:00"),
    )
    conn.commit()
    conn.close()
    return db_path


def _clientes_json(tmp_path):
    json_path = tmp_path / "clientes.json"
    json_path.write_text(json.dumps({
        "s1": {"nombre": "Ana", "celular": "351 123-4567", "productos": ["iPhone 13"], "fecha": "2026-01-02 11:00"},
    }), encoding="utf-8")
    return json_path


def test_migrar_fusiona_leads_que_normalizan_al_mismo_celular(tmp_path):
    """En clientes.json real aparecen entradas de la misma persona guardadas
    con y sin código de país (ej. "+543513017015" y "3513017015") en
    sesiones distintas, con productos distintos en cada una. Antes de este
    fix, la segunda entrada se descartaba entera por "celular ya existe",
    perdiendo sus productos. Ahora se fusionan en un solo cliente."""
    client = FakeSupabaseClient()
    json_path = tmp_path / "clientes.json"
    json_path.write_text(json.dumps({
        "s1": {"nombre": "Marina", "celular": "+543513017015", "productos": [], "fecha": "2026-01-01 10:00"},
        "s2": {"nombre": "Marina", "celular": "3513017015", "productos": ["iPhone 13", "AirPods"], "fecha": "2026-01-02 11:00"},
    }), encoding="utf-8")

    conteos = migrar(client, tmp_path / "no-existe.db", json_path)

    assert conteos["leads"] == 1  # una sola persona, no dos
    filas = client.table("clientes").select("*").execute().data
    assert len(filas) == 1
    assert filas[0]["celular"] == "3513017015"
    pedidos = client.table("pedidos").select("*").eq("cliente_id", filas[0]["id"]).execute().data
    assert len(pedidos) == 1
    assert pedidos[0]["productos"] == ["iPhone 13", "AirPods"]  # no se perdieron


def test_migrar_crea_mayoristas_con_cuenta_real_y_leads_invitados(tmp_path):
    client = FakeSupabaseClient()
    db_path = _usuarios_db(tmp_path)
    json_path = _clientes_json(tmp_path)

    conteos = migrar(client, db_path, json_path)

    assert conteos == {"mayoristas": 1, "leads": 1}
    filas = client.table("clientes").select("*").execute().data
    assert len(filas) == 2
    mayorista = next(f for f in filas if f["email"] == "mayorista@x.com")
    assert mayorista["tipo_cliente"] == "mayorista"
    # El mayorista NO queda "invitado": tiene una cuenta real de Supabase
    # Auth desde el día uno, así que nadie puede reclamar su fila
    # registrándose con su email (ver web/cuentas.py).
    assert mayorista["auth_id"] is not None
    assert mayorista["auth_id"] == client.auth._usuarios_por_email["mayorista@x.com"].id
    assert "mayorista@x.com" in client.auth.emails_con_reset_pedido
    lead = next(f for f in filas if f["celular"] == "3511234567")
    assert lead["auth_id"] is None  # el lead sí queda invitado: se vincula por celular
    assert lead["nombre"] == "Ana"

    # El historial de productos consultados del lead debe migrar a "pedidos",
    # asociado al cliente_id nuevo (no quedarse pisado en clientes.json).
    filas_pedidos = client.table("pedidos").select("*").execute().data
    assert len(filas_pedidos) == 1
    assert filas_pedidos[0]["cliente_id"] == lead["id"]
    assert filas_pedidos[0]["productos"] == ["iPhone 13"]


def test_migrar_cierra_el_robo_de_cuenta_por_email(tmp_path):
    """Regresión del hallazgo de seguridad: antes de este fix, un mayorista
    migrado quedaba "invitado" (auth_id=None) y cualquiera que supiera su
    email podía registrarse con ese email y apropiarse de su fila. Tras la
    migración, la fila del mayorista ya tiene una cuenta real — un impostor
    que intente registrarse con ese mismo email tiene que chocar contra
    EmailDuplicadoError, no apropiarse de nada."""
    client = FakeSupabaseClient()
    db_path = _usuarios_db(tmp_path)
    json_path = _clientes_json(tmp_path)
    migrar(client, db_path, json_path)

    import pytest
    with pytest.raises(cuentas.EmailDuplicadoError):
        cuentas.registrar_cliente(
            client, "Impostor", "Impostor", "3510000001", "mayorista@x.com", "clave-robada", "impostor",
        )

    filas = client.table("clientes").select("*").eq("email", "mayorista@x.com").execute().data
    assert len(filas) == 1
    assert filas[0]["nombre"] == "Mayorista Uno"  # la fila real no fue tocada


def test_migrar_no_duplica_si_se_corre_dos_veces(tmp_path):
    client = FakeSupabaseClient()
    db_path = _usuarios_db(tmp_path)
    json_path = _clientes_json(tmp_path)

    migrar(client, db_path, json_path)
    migrar(client, db_path, json_path)

    filas = client.table("clientes").select("*").execute().data
    celulares = [f["celular"] for f in filas if f.get("celular")]
    emails = [f["email"] for f in filas if f.get("email")]
    assert len(celulares) == len(set(celulares))
    assert len(emails) == len(set(emails))


def test_resolver_clientes_json_path_usa_clientes_path_si_esta_seteada(tmp_path, monkeypatch):
    """En producción (Railway), clientes.json vive en un volumen persistente
    apuntado por CLIENTES_PATH, no en web/ — si el script no respeta esa
    variable, corre contra un archivo que no existe y migra "0 leads"
    silenciosamente."""
    monkeypatch.setenv("CLIENTES_PATH", str(tmp_path))
    monkeypatch.delenv("PRODUCTOS_PATH", raising=False)
    assert resolver_clientes_json_path() == tmp_path / "clientes.json"


def test_resolver_clientes_json_path_cae_al_directorio_de_productos_path(tmp_path, monkeypatch):
    monkeypatch.delenv("CLIENTES_PATH", raising=False)
    monkeypatch.setenv("PRODUCTOS_PATH", str(tmp_path / "productos.json"))
    assert resolver_clientes_json_path() == tmp_path / "clientes.json"
