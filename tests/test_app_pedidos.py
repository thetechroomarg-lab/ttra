from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_pedido_sin_sesion_devuelve_401(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app)
    r = c.post("/api/pedidos", json={"productos": ["iPhone 13"]})
    assert r.status_code == 401


def test_pedido_con_sesion_se_guarda(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/api/pedidos", json={"productos": ["iPhone 13", "AirPods"]})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
