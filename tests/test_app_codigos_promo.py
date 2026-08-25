from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_logueado(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
        "provincia": "Córdoba",
    })
    return c, fake


def _insertar_codigo_promo(fake, usos_maximos=20, usos_actuales=0, activo=True):
    fake.table("codigos_promo").insert({
        "code": "QUIEROMISPLAY6",
        "producto_regalo": "Auriculares Redmi 6 Play",
        "usos_maximos": usos_maximos,
        "usos_actuales": usos_actuales,
        "activo": activo,
    }).execute()


def test_validar_codigo_promo_devuelve_el_producto_regalo(monkeypatch):
    c, fake = _cliente_logueado(monkeypatch)
    _insertar_codigo_promo(fake)

    r = c.post("/api/codigos-promo/validar", json={"codigo": "quieromisplay6"})

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["codigo"] == "QUIEROMISPLAY6"
    assert body["producto_regalo"] == "Auriculares Redmi 6 Play"


def test_validar_codigo_promo_falla_si_no_existe(monkeypatch):
    c, _fake = _cliente_logueado(monkeypatch)

    r = c.post("/api/codigos-promo/validar", json={"codigo": "NOEXISTE"})

    assert r.status_code == 400
    assert "inválido" in r.json()["error"].lower()


def test_validar_codigo_promo_falla_si_ya_agoto_los_usos(monkeypatch):
    c, fake = _cliente_logueado(monkeypatch)
    _insertar_codigo_promo(fake, usos_maximos=20, usos_actuales=20)

    r = c.post("/api/codigos-promo/validar", json={"codigo": "QUIEROMISPLAY6"})

    assert r.status_code == 400


def test_validar_codigo_promo_falla_si_esta_inactivo(monkeypatch):
    c, fake = _cliente_logueado(monkeypatch)
    _insertar_codigo_promo(fake, activo=False)

    r = c.post("/api/codigos-promo/validar", json={"codigo": "QUIEROMISPLAY6"})

    assert r.status_code == 400


def test_consumir_codigo_promo_incrementa_el_contador_de_usos(monkeypatch):
    c, fake = _cliente_logueado(monkeypatch)
    _insertar_codigo_promo(fake, usos_maximos=20, usos_actuales=5)

    r = c.post("/api/codigos-promo/consumir", json={"codigo": "QUIEROMISPLAY6"})

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["producto_regalo"] == "Auriculares Redmi 6 Play"
    filas = fake.table("codigos_promo").select("*").eq("code", "QUIEROMISPLAY6").execute().data
    assert filas[0]["usos_actuales"] == 6


def test_consumir_codigo_promo_falla_cuando_ya_no_quedan_usos(monkeypatch):
    c, fake = _cliente_logueado(monkeypatch)
    _insertar_codigo_promo(fake, usos_maximos=20, usos_actuales=20)

    r = c.post("/api/codigos-promo/consumir", json={"codigo": "QUIEROMISPLAY6"})

    assert r.status_code == 400
    filas = fake.table("codigos_promo").select("*").eq("code", "QUIEROMISPLAY6").execute().data
    assert filas[0]["usos_actuales"] == 20


def test_codigos_promo_requiere_sesion(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    _insertar_codigo_promo(fake)

    r = c.post("/api/codigos-promo/validar", json={"codigo": "QUIEROMISPLAY6"})

    assert r.status_code == 401
