from fastapi.testclient import TestClient

import web.app as appmod
from web import auth


def _cliente_autenticado(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    c = TestClient(appmod.app)
    c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    return c


def test_api_catalogo_sin_sesion_devuelve_401(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    c = TestClient(appmod.app)
    r = c.get("/api/catalogo")
    assert r.status_code == 401


def test_pagina_catalogo_sin_sesion_redirige_a_login(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    c = TestClient(appmod.app, follow_redirects=False)
    r = c.get("/catalogo")
    assert r.status_code in (302, 307)
    assert "login" in r.headers["location"]


def test_api_catalogo_con_sesion_y_sin_productos(tmp_path, monkeypatch):
    c = _cliente_autenticado(tmp_path, monkeypatch)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [])
    r = c.get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["mensaje"] == "Estamos actualizando los precios"


def test_api_catalogo_con_sesion_y_productos(tmp_path, monkeypatch):
    c = _cliente_autenticado(tmp_path, monkeypatch)
    monkeypatch.setattr(
        appmod, "_cargar_productos",
        lambda: [{"nombre": "iPhone 15", "categoria": "Apple - iPhone"}],
    )
    r = c.get("/api/catalogo")
    assert r.status_code == 200
    secciones = r.json()["secciones"]
    assert secciones["Celulares"][0]["nombre"] == "iPhone 15"
    assert secciones["Gaming"] == []
