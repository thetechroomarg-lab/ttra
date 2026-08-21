from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_landing_sin_sesion_muestra_login(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Ingresar" in r.text


def test_landing_con_sesion_muestra_index(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_index_html_directo_sin_sesion_no_sirve_la_landing(monkeypatch):
    """El StaticFiles mount serviría /index.html tal cual, sin pasar por el
    chequeo de sesión de GET "/" — hay que bloquear ese atajo."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    r = c.get("/index.html")
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/"


def test_index_html_directo_con_sesion_sigue_funcionando(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.get("/index.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_login_html_es_publico_sin_sesion(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/login.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Ingresar" in r.text


def test_chat_sin_sesion_devuelve_401(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/chat", json={"mensaje": "hola", "sesion": "s1"})
    assert r.status_code == 401


def test_chat_con_sesion_sigue_funcionando(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_productos",
                         lambda: [{"nombre": "x", "usd": 1, "pesos": 1, "transferencia": 1}])
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/chat", json={"mensaje": "hola", "sesion": "s1"})
    assert r.status_code == 200
    assert "respuesta" in r.json()
