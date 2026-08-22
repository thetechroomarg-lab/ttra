from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_interaccion_anonima_se_guarda(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.post(
        "/api/interacciones",
        json={"tipo_evento": "view_category", "categoria": "Celulares"},
        headers={"X-TTRA-ANON-ID": "anon-1"},
    )

    assert r.status_code == 200
    filas = fake.table("interacciones_cliente").select("*").eq("anon_id", "anon-1").execute().data
    assert len(filas) == 1
    assert filas[0]["tipo_evento"] == "view_category"
    assert filas[0]["categoria"] == "Celulares"


def test_login_vincula_interacciones_anonimas_al_cliente(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")

    c.post(
        "/api/interacciones",
        json={"tipo_evento": "search", "metadata": {"termino": "macbook"}},
        headers={"X-TTRA-ANON-ID": "anon-2"},
    )
    c.post(
        "/registro",
        json={
            "nombre": "Ana", "apellido": "Gómez", "celular": "3511234567",
            "email": "ana@x.com", "password": "clave1234",
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
    assert len(filas) >= 2
    assert all(f["cliente_id"] == cliente_id for f in filas)
    assert any(f["tipo_evento"] == "login" for f in filas)
