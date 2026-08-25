from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_interaccion_anonima_se_guarda_solo_si_ve_producto(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.post(
        "/api/interacciones",
        json={"tipo_evento": "view_item", "producto_nombre": "iPhone 15", "categoria": "Celulares"},
        headers={"X-TTRA-ANON-ID": "anon-1"},
    )

    assert r.status_code == 200
    filas = fake.table("interacciones_cliente").select("*").eq("anon_id", "anon-1").execute().data
    assert len(filas) == 1
    assert filas[0]["tipo_evento"] == "view_item"
    assert filas[0]["producto_nombre"] == "iPhone 15"
    assert filas[0]["categoria"] is None
    assert filas[0]["marca"] is None
    assert filas[0]["metadata"] == {}


def test_evento_no_permitido_se_ignora(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.post(
        "/api/interacciones",
        json={"tipo_evento": "view_category", "categoria": "Celulares"},
        headers={"X-TTRA-ANON-ID": "anon-ignorado"},
    )

    assert r.status_code == 200
    filas = fake.table("interacciones_cliente").select("*").eq("anon_id", "anon-ignorado").execute().data
    assert filas == []


def test_select_product_viejo_se_normaliza_a_view_item(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.post(
        "/api/interacciones",
        json={"tipo_evento": "select_product", "producto_nombre": "iPhone 15"},
        headers={"X-TTRA-ANON-ID": "anon-legacy"},
    )

    assert r.status_code == 200
    filas = fake.table("interacciones_cliente").select("*").eq("anon_id", "anon-legacy").execute().data
    assert len(filas) == 1
    assert filas[0]["tipo_evento"] == "view_item"
    assert filas[0]["producto_nombre"] == "iPhone 15"


def test_view_product_viejo_se_normaliza_a_view_item(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.post(
        "/api/interacciones",
        json={"tipo_evento": "view_product", "producto_nombre": "Galaxy A56"},
        headers={"X-TTRA-ANON-ID": "anon-older"},
    )

    assert r.status_code == 200
    filas = fake.table("interacciones_cliente").select("*").eq("anon_id", "anon-older").execute().data
    assert len(filas) == 1
    assert filas[0]["tipo_evento"] == "view_item"
    assert filas[0]["producto_nombre"] == "Galaxy A56"


def test_login_vincula_interacciones_anonimas_de_producto_al_cliente(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")

    c.post(
        "/api/interacciones",
        json={"tipo_evento": "view_item", "producto_nombre": "MacBook Air"},
        headers={"X-TTRA-ANON-ID": "anon-2"},
    )
    c.post(
        "/registro",
        json={
            "nombre": "Ana", "apellido": "Gómez", "celular": "3511234567",
            "email": "ana@x.com", "password": "clave1234",
        "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",
        },
        headers={"X-TTRA-ANON-ID": "anon-2"},
    )
    c.post("/logout")

    r = c.post(
        "/login",
        json={"email": "ana@x.com", "password": "clave1234"},
        headers={"X-TTRA-ANON-ID": "anon-2"},
    )

    assert r.status_code == 200
    cliente_id = fake.table("clientes").select("*").eq("email", "ana@x.com").execute().data[0]["id"]
    filas = fake.table("interacciones_cliente").select("*").eq("anon_id", "anon-2").execute().data
    assert len(filas) == 1
    assert all(f["cliente_id"] == cliente_id for f in filas)
    assert filas[0]["tipo_evento"] == "view_item"
