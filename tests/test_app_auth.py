from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    return TestClient(appmod.app)


def test_registro_exitoso_crea_sesion(monkeypatch):
    c = _cliente(monkeypatch)
    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_registro_celular_duplicado_devuelve_400(monkeypatch):
    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/registro", json={
        "nombre": "Otro", "apellido": "Nombre", "celular": "3511234567",
        "email": "otro@x.com", "password": "clave1234",
    })
    assert r.status_code == 400
    assert "error" in r.json()


def test_login_correcto(monkeypatch):
    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/login", json={"email": "juan@x.com", "password": "clave1234"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_login_incorrecto_devuelve_mensaje_generico(monkeypatch):
    c = _cliente(monkeypatch)
    r = c.post("/login", json={"email": "nadie@x.com", "password": "loquesea"})
    assert r.status_code == 401
    assert r.json()["error"] == "Usuario o contraseña incorrectos"


def test_logout_limpia_sesion(monkeypatch):
    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert c.get("/api/catalogo").status_code == 200  # pública, no requiere sesión


def test_registro_con_supabase_caido_da_mensaje_claro(monkeypatch):
    def _client_roto():
        raise Exception("connection refused")

    monkeypatch.setattr(appmod, "get_client", _client_roto)
    c = TestClient(appmod.app)
    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    assert r.status_code == 503
    assert "error" in r.json()
