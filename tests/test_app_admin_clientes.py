from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_logueado(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    c.post("/api/pedidos", json={"productos": ["iPhone 13"]})
    c.post("/logout")
    c.post("/admin/clientes/login", json={"password": "clave-admin"})
    return c


def test_admin_clientes_lista_nombre_y_link_a_historial(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    r = c.get("/admin/clientes")
    assert r.status_code == 200
    assert "Juan" in r.text
    assert "/historial" in r.text
    assert "Productos consultados" not in r.text


def test_admin_clientes_historial_muestra_pedidos_del_cliente(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    fake.table("interacciones_cliente").insert({
        "id": "inter-1",
        "cliente_id": cliente_id,
        "anon_id": "anon-juan",
        "session_id": "anon-juan",
        "tipo_evento": "search",
        "metadata": {"termino": "iphone"},
        "fecha": "2026-08-22T18:35:00+00:00",
    }).execute()

    r = c.get(f"/admin/clientes/{cliente_id}/historial")
    assert r.status_code == 200
    assert "Juan" in r.text
    assert "iPhone 13" in r.text
    assert "Buscó" in r.text
    assert "iphone" in r.text


def test_admin_clientes_historial_requiere_sesion_admin():
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/admin/clientes/algun-id/historial", follow_redirects=False)
    assert r.status_code in (302, 307)


def test_admin_clientes_historial_cliente_inexistente(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    r = c.get("/admin/clientes/id-que-no-existe/historial")
    assert r.status_code == 404


def test_admin_resetea_password_y_manda_mail(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]

    mails_enviados = []
    monkeypatch.setattr(
        appmod, "enviar_email",
        lambda destinatario, asunto, html: mails_enviados.append((destinatario, asunto, html)),
    )

    r = c.post(f"/admin/clientes/{cliente_id}/resetear-password")

    assert r.status_code == 200
    assert len(mails_enviados) == 1
    assert mails_enviados[0][0] == "juan@x.com"


def test_admin_resetea_password_requiere_sesion_admin():
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/admin/clientes/algun-id/resetear-password")
    assert r.status_code == 401


def test_admin_resetea_password_cliente_inexistente(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    r = c.post("/admin/clientes/id-que-no-existe/resetear-password")
    assert r.status_code == 400
