from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_admin(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/admin/clientes/login", json={"password": "clave-admin"})
    return c, fake


def test_nombre_cliente_con_cierre_de_script_no_rompe_el_html(monkeypatch):
    c, fake = _cliente_admin(monkeypatch)
    payload = "</script><script>alert(1)</script>"
    fake.table("clientes").insert({
        "id": "cliente-xss", "nombre": payload, "apellido": "Prueba",
        "celular": "3511234567", "email": "xss@x.com", "provincia": "Córdoba",
    }).execute()

    r = c.get("/admin/clientes")
    assert r.status_code == 200
    assert "</script><script>alert(1)</script>" not in r.text
    assert "\\u003c/script\\u003e" in r.text


def test_json_para_script_escapa_tags_y_ampersand():
    resultado = appmod._json_para_script("</script><b>x</b> & co")
    assert "</script>" not in resultado
    assert "<b>" not in resultado
    assert "&" not in resultado.replace("\\u0026", "")


def test_login_admin_clientes_se_bloquea_tras_repetidos_intentos_fallidos(monkeypatch):
    monkeypatch.setattr(appmod, "get_client", lambda: FakeSupabaseClient())
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    appmod._intentos_login_fallidos.clear()
    c = TestClient(appmod.app, base_url="https://testserver")

    for _ in range(appmod._LOGIN_MAX_INTENTOS):
        r = c.post("/admin/clientes/login", json={"password": "incorrecta"})
        assert r.status_code == 401

    r_bloqueado = c.post("/admin/clientes/login", json={"password": "incorrecta"})
    assert r_bloqueado.status_code == 429

    r_bloqueado_con_clave_correcta = c.post("/admin/clientes/login", json={"password": "clave-admin"})
    assert r_bloqueado_con_clave_correcta.status_code == 429


def test_login_cadete_exitoso_limpia_el_contador_de_intentos_fallidos(monkeypatch):
    monkeypatch.setattr(appmod, "get_client", lambda: FakeSupabaseClient())
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    appmod._intentos_login_fallidos.clear()
    c = TestClient(appmod.app, base_url="https://testserver")

    c.post("/admin/cadete/login", json={"password": "incorrecta"})
    r = c.post("/admin/cadete/login", json={"password": "clave-cadete"})
    assert r.status_code == 200
    assert appmod._intentos_login_fallidos.get(("testclient", "cadete"), []) == []
