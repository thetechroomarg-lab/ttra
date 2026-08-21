from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_autenticado(tmp_path, monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave123",
    })
    return c


def test_api_catalogo_es_publica_sin_sesion(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [])
    c = TestClient(appmod.app)
    r = c.get("/api/catalogo")
    assert r.status_code == 200


def test_pagina_catalogo_sin_sesion_redirige_a_login(tmp_path, monkeypatch):
    c = TestClient(appmod.app, follow_redirects=False)
    r = c.get("/catalogo")
    assert r.status_code in (302, 307)
    assert "login" in r.headers["location"]


def test_api_catalogo_sin_productos(tmp_path, monkeypatch):
    c = _cliente_autenticado(tmp_path, monkeypatch)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [])
    r = c.get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["mensaje"] == "Estamos actualizando los precios"


def test_api_catalogo_con_productos(tmp_path, monkeypatch):
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


def test_flujo_completo_registro_logout_login_catalogo(tmp_path, monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod, "_cargar_productos",
        lambda: [{"nombre": "iPhone 15", "categoria": "Apple - iPhone"}],
    )
    c = TestClient(appmod.app)

    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave123",
    })
    assert r.status_code == 200

    r = c.post("/logout")
    assert r.status_code == 200

    r = c.post("/login", json={"email": "juan@x.com", "password": "clave123"})
    assert r.status_code == 200

    r = c.get("/catalogo")
    assert r.status_code == 200

    r = c.get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["secciones"]["Celulares"][0]["nombre"] == "iPhone 15"

    r = c.post("/logout")
    assert r.status_code == 200

    # /api/catalogo ahora es pública: sigue respondiendo 200 incluso sin sesión.
    r = c.get("/api/catalogo")
    assert r.status_code == 200
