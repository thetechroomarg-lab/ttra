import json
import sqlite3

from tests.fakes_supabase import FakeSupabaseClient
from scripts.migrar_a_supabase import migrar


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


def test_migrar_crea_mayoristas_invitados_y_leads(tmp_path):
    client = FakeSupabaseClient()
    db_path = _usuarios_db(tmp_path)
    json_path = _clientes_json(tmp_path)

    conteos = migrar(client, db_path, json_path)

    assert conteos == {"mayoristas": 1, "leads": 1}
    filas = client.table("clientes").select("*").execute().data
    assert len(filas) == 2
    mayorista = next(f for f in filas if f["email"] == "mayorista@x.com")
    assert mayorista["tipo_cliente"] == "mayorista"
    lead = next(f for f in filas if f["celular"] == "3511234567")
    assert lead["auth_id"] is None  # invitado: sin cuenta todavía
    assert lead["nombre"] == "Ana"


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
