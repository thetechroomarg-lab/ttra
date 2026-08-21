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
        "email": "juan@x.com", "password": "clave1234", "username": "juanperez",
    })
    c.post("/api/pedidos", json={"productos": ["iPhone 13"]})
    c.post("/logout")
    c.post("/admin/clientes/login", json={"password": "clave-admin"})
    return c


def test_admin_clientes_lista_nombre_y_pedidos(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    r = c.get("/admin/clientes")
    assert r.status_code == 200
    assert "Juan" in r.text
    assert "iPhone 13" in r.text
