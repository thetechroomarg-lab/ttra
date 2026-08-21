from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_landing_sin_sesion_muestra_login(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app)
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Ingresar" in r.text


def test_landing_con_sesion_muestra_index(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text
