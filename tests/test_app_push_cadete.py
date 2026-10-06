from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _admin_logueado(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/admin/clientes/login", json={"password": "clave-admin"})
    return c, fake


def _cadete_logueado(fake, monkeypatch):
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    return c


def test_vapid_public_key_requiere_sesion_de_cadete():
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/admin/cadete/push/vapid-public-key")
    assert r.status_code == 401


def test_vapid_public_key_devuelve_503_sin_configurar(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod.push_cadete, "PUSH_CONFIGURADO", False)
    cadete = _cadete_logueado(fake, monkeypatch)
    r = cadete.get("/admin/cadete/push/vapid-public-key")
    assert r.status_code == 503


def test_suscribir_push_requiere_sesion_de_cadete():
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/admin/cadete/push/suscribir", json={
        "endpoint": "https://ejemplo.com/x", "keys": {"p256dh": "a", "auth": "b"},
    })
    assert r.status_code == 401


def test_suscribir_push_guarda_la_suscripcion(monkeypatch):
    fake = FakeSupabaseClient()
    cadete = _cadete_logueado(fake, monkeypatch)
    r = cadete.post("/admin/cadete/push/suscribir", json={
        "endpoint": "https://ejemplo.com/x", "keys": {"p256dh": "a", "auth": "b"},
    })
    assert r.status_code == 200
    filas = fake.table("cadete_push_suscripciones").select("*").execute().data
    assert len(filas) == 1
    assert filas[0]["endpoint"] == "https://ejemplo.com/x"


def test_suscribir_push_actualiza_en_vez_de_duplicar(monkeypatch):
    fake = FakeSupabaseClient()
    cadete = _cadete_logueado(fake, monkeypatch)
    body = {"endpoint": "https://ejemplo.com/x", "keys": {"p256dh": "a", "auth": "b"}}
    cadete.post("/admin/cadete/push/suscribir", json=body)
    body["keys"]["auth"] = "otra-clave"
    cadete.post("/admin/cadete/push/suscribir", json=body)
    filas = fake.table("cadete_push_suscripciones").select("*").execute().data
    assert len(filas) == 1
    assert filas[0]["auth"] == "otra-clave"


def test_derivar_pedido_al_cadete_dispara_push(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Juan", "apellido": "Perez",
    }).execute()
    fake.table("pedidos").insert({
        "id": "pedido-1", "cliente_id": "cliente-1", "fecha_entrega": "2026-09-25",
        "productos": ["iPhone 13"], "detalle": [{"nombre": "iPhone 13", "cantidad": 1}],
        "total_usd": 500,
    }).execute()

    llamadas = []
    monkeypatch.setattr(
        appmod.push_cadete, "enviar_push_cadete",
        lambda client, titulo, cuerpo, **kw: llamadas.append((titulo, cuerpo)),
    )

    r = admin.put("/admin/pedidos/pedido-1/derivar", json={"derivado": True})
    assert r.status_code == 200
    assert len(llamadas) == 1
    assert "Juan Perez" in llamadas[0][1]


def test_derivar_pedido_al_admin_no_dispara_push(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fake.table("pedidos").insert({
        "id": "pedido-1", "fecha_entrega": "2026-09-25",
        "productos": ["iPhone 13"], "detalle": [{"nombre": "iPhone 13", "cantidad": 1}],
        "total_usd": 500, "asignado_a": appmod.CADETE_SLUG,
    }).execute()

    llamadas = []
    monkeypatch.setattr(
        appmod.push_cadete, "enviar_push_cadete",
        lambda client, titulo, cuerpo, **kw: llamadas.append((titulo, cuerpo)),
    )

    r = admin.put("/admin/pedidos/pedido-1/derivar", json={"derivado": False})
    assert r.status_code == 200
    assert llamadas == []


def test_crear_nota_asignada_al_cadete_dispara_push(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    llamadas = []
    monkeypatch.setattr(
        appmod.push_cadete, "enviar_push_cadete",
        lambda client, titulo, cuerpo, **kw: llamadas.append((titulo, cuerpo)),
    )
    r = admin.post("/admin/tareas-entrega", json={
        "fecha_entrega": "2026-09-25", "titulo": "Retirar equipo", "enviar_a_alejo": True,
    })
    assert r.status_code == 200
    assert len(llamadas) == 1
    assert "Retirar equipo" in llamadas[0][1]


def test_crear_nota_sin_asignar_no_dispara_push(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    llamadas = []
    monkeypatch.setattr(
        appmod.push_cadete, "enviar_push_cadete",
        lambda client, titulo, cuerpo, **kw: llamadas.append((titulo, cuerpo)),
    )
    r = admin.post("/admin/tareas-entrega", json={
        "fecha_entrega": "2026-09-25", "titulo": "Nota interna", "enviar_a_alejo": False,
    })
    assert r.status_code == 200
    assert llamadas == []


def test_suscribir_push_admin_requiere_sesion_de_admin(monkeypatch):
    fake = FakeSupabaseClient()
    cadete = _cadete_logueado(fake, monkeypatch)
    r = cadete.post("/admin/clientes/push/suscribir", json={
        "endpoint": "https://ejemplo.com/a", "keys": {"p256dh": "a", "auth": "b"},
    })
    assert r.status_code == 401


def test_suscribir_push_admin_guarda_en_su_propia_tabla(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    r = admin.post("/admin/clientes/push/suscribir", json={
        "endpoint": "https://ejemplo.com/a", "keys": {"p256dh": "a", "auth": "b"},
    })
    assert r.status_code == 200
    assert [f["endpoint"] for f in fake.table("admin_push_suscripciones").select("*").execute().data] == ["https://ejemplo.com/a"]
    assert fake.table("cadete_push_suscripciones").select("*").execute().data == []


def test_panel_admin_tiene_boton_de_notificaciones(monkeypatch):
    admin, _ = _admin_logueado(monkeypatch)
    html = admin.get("/admin/clientes").text
    assert 'id="btn-notificaciones-admin"' in html
    assert "/admin/clientes/push/suscribir" in html


def test_pedido_nuevo_de_la_web_avisa_al_admin(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    fake.table("clientes").insert({"id": "c1", "nombre": "Ana", "apellido": "Pérez"}).execute()
    enviados = []
    monkeypatch.setattr(appmod.push_cadete, "enviar_push_admin", lambda client, titulo, cuerpo, url="/admin/clientes": enviados.append((titulo, cuerpo)))

    appmod._avisar_pedido_nuevo("c1", ["iPhone 17 256GB x1"], 1020)

    assert enviados == [("🛒 Nuevo pedido · Ana Pérez", "iPhone 17 256GB x1 · U$D 1.020")]


def test_envio_push_carga_la_clave_vapid_desde_pem(monkeypatch):
    """pywebpush no acepta el PEM como string: hay que pasarle la clave cargada."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    import pywebpush
    from py_vapid import Vapid01
    from web import push_cadete

    pem = ec.generate_private_key(ec.SECP256R1()).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption(),
    ).decode()
    monkeypatch.setattr(push_cadete, "PUSH_CONFIGURADO", True)
    monkeypatch.setattr(push_cadete, "VAPID_PRIVATE_KEY_PEM", pem)
    claves = []
    monkeypatch.setattr(pywebpush, "webpush", lambda **kw: claves.append(kw["vapid_private_key"]))
    fake = FakeSupabaseClient()
    fake.table("admin_push_suscripciones").insert({"endpoint": "https://e/x", "p256dh": "a", "auth": "b"}).execute()

    push_cadete.enviar_push_admin(fake, "t", "c")

    assert len(claves) == 1 and isinstance(claves[0], Vapid01)
