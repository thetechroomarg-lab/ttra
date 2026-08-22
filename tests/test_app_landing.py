from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_landing_sin_sesion_muestra_index(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


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


def test_index_html_directo_sin_sesion_sirve_la_landing(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/index.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


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


def test_doble_barra_sin_sesion_no_sirve_la_landing(monkeypatch):
    """StaticFiles resuelve "//" igual que "/" y serviría index.html directo,
    evitando la ruta explícita GET "/" que sí chequea sesión."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    # httpx colapsa "//" si se pasa como path relativo — hay que mandar la
    # URL absoluta para que el "//" llegue tal cual al servidor.
    r = c.get("https://testserver//")
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/"


def test_triple_barra_sin_sesion_no_sirve_la_landing(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    r = c.get("https://testserver///")
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/"


def test_index_html_con_barra_final_sin_sesion_sirve_la_landing(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/index.html/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_catalogo_html_mayusculas_sin_sesion_no_sirve_la_landing(monkeypatch):
    """En un filesystem case-insensitive (macOS/Windows) StaticFiles serviría
    igual /CATALOGO.HTML — el chequeo tiene que ser case-insensitive."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    r = c.get("/CATALOGO.HTML")
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/"


def test_segmentos_punto_percent_encoded_sin_sesion_no_sirven_la_landing(monkeypatch):
    """uvicorn decodifica %2e/%2f antes de que la app vea el path, así que
    "/%2e/", "/foo/%2e%2e/" etc. llegan como "/./" y "/foo/../" — que
    posixpath.normpath resuelve a "/". Sin resolver esos segmentos, StaticFiles
    los serviría igual que "/" (index.html) sin pasar por ninguna gate."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    for ruta in ["/%2e/", "/%2E/", "/%2e%2f", "/%2e/%2e/", "/static/%2e%2e/", "/foo/%2e%2e/", "/x/%2e%2e/%2e/"]:
        r = c.get(ruta)
        assert r.status_code in (302, 307), f"{ruta} devolvió {r.status_code}"
        assert r.headers["location"] == "/"


def test_index_html_via_segmentos_punto_sin_sesion_sirve_la_landing(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/foo/%2e%2e/index.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_login_html_con_barra_final_sigue_siendo_publico(monkeypatch):
    """La normalización no debe convertir /login.html/ en algo distinto de
    /login.html y bloquearlo por error."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/login.html/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Ingresar" in r.text


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
