import pytest
from fastapi.testclient import TestClient

import web.app as appmod
from web import cadetes
from tests.fakes_supabase import FakeSupabaseClient


@pytest.fixture
def fake(monkeypatch):
    f = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: f)
    cadetes._cache.clear()
    f.table("cadetes").insert({"id": "c1", "nombre": "Alejo", "email": "alejo@example.com", "rol": "cadete",
                               "activo": True, "password_hash": cadetes.hashear_password("clave-larga-123")}).execute()
    return f


def _c():
    return TestClient(appmod.app, base_url="https://testserver")


def test_hash_no_guarda_texto_plano_y_verifica():
    h = cadetes.hashear_password("abc12345")
    assert "abc12345" not in h and cadetes.verificar_password("abc12345", h)
    assert not cadetes.verificar_password("otra", h) and not cadetes.verificar_password("x", "basura")


def test_login_con_cuenta_da_acceso_al_panel(fake):
    c = _c()
    assert c.post("/admin/cadete/login", json={"email": "ALEJO@example.com", "password": "clave-larga-123"}).status_code == 200
    assert "Ingresar" not in c.get("/admin/cadete").text


def test_login_con_cuenta_rechaza_clave_o_email_malos(fake):
    c = _c()
    assert c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "mala"}).status_code == 401
    assert c.post("/admin/cadete/login", json={"email": "nadie@example.com", "password": "clave-larga-123"}).status_code == 401
    assert "Ingresar" in c.get("/admin/cadete").text


def test_dar_de_baja_la_cuenta_corta_la_sesion(fake):
    c = _c()
    c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"})
    fake.table("cadetes").update({"activo": False}).eq("id", "c1").execute()
    cadetes._cache.clear()
    assert "Ingresar" in c.get("/admin/cadete").text
    assert c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"}).status_code == 401


def test_cambiar_la_clave_invalida_sesiones_viejas(fake):
    c = _c()
    c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"})
    fake.table("cadetes").update({"password_hash": cadetes.hashear_password("nueva-clave-456")}).eq("id", "c1").execute()
    cadetes._cache.clear()
    assert "Ingresar" in c.get("/admin/cadete").text


def test_contrasena_unica_sigue_andando_y_se_puede_apagar(fake, monkeypatch):
    c = _c()
    assert c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD}).status_code == 200
    monkeypatch.setattr(appmod, "_CADETE_CONTRASENA_UNICA", False)
    assert "Ingresar" in c.get("/admin/cadete").text
    assert _c().post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD}).status_code == 401


def test_sesion_de_cuenta_falla_cerrado_si_la_base_cae(fake, monkeypatch):
    c = _c()
    c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"})
    cadetes._cache.clear()
    def roto(): raise RuntimeError("db caida")
    monkeypatch.setattr(appmod, "get_client", roto)
    assert "Ingresar" in c.get("/admin/cadete").text
