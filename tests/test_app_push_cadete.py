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
