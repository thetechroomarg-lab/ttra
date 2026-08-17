from fastapi.testclient import TestClient

import web.app as appmod
from web import auth


def _cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    return TestClient(appmod.app)


def test_registro_exitoso_crea_sesion(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    r = c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_registro_email_duplicado_devuelve_400(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    r = c.post("/registro", json={"nombre": "Otro", "email": "juan@x.com", "password": "otraclave"})
    assert r.status_code == 400
    assert "error" in r.json()


def test_login_correcto(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    r = c.post("/login", json={"email": "juan@x.com", "password": "clave123"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_login_incorrecto_devuelve_mensaje_generico(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    r = c.post("/login", json={"email": "nadie@x.com", "password": "loquesea"})
    assert r.status_code == 401
    assert r.json()["error"] == "Usuario o contraseña incorrectos"


def test_logout_limpia_sesion(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    r = c.post("/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert c.get("/api/catalogo").status_code == 401
