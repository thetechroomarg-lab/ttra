from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_con_codigo(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    fake.table("codigos_descuento").insert({
        "cliente_id": cliente_id,
        "code": "TTRA-TEST1234",
        "productos": ["iPhone 13", "Galaxy A56"],
        "descuento_usd": 5,
        "activo": True,
    }).execute()
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [
            {"nombre": "iPhone 13", "categoria": "Apple - iPhone", "usd": 560, "pesos": 873600, "transferencia": 900619},
            {"nombre": "Galaxy A56", "categoria": "Samsung", "usd": 300, "pesos": 468000, "transferencia": 482474},
            {"nombre": "MacBook Air", "categoria": "Apple - Mac", "usd": 1000, "pesos": 1560000, "transferencia": 1608248},
        ],
    )
    return c, fake, cliente_id


def test_validar_descuento_mail_aplica_solo_a_items_elegibles(monkeypatch):
    c, _fake, _cliente_id = _cliente_con_codigo(monkeypatch)

    r = c.post("/api/descuentos/validar", json={
        "codigo": "TTRA-TEST1234",
        "items": [
            {"nombre": "iPhone 13", "cantidad": 2},
            {"nombre": "MacBook Air", "cantidad": 1},
        ],
    })

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["codigo"] == "TTRA-TEST1234"
    assert body["productos"] == ["iPhone 13"]
    assert body["cantidad"] == 2
    assert body["descuento_usd_por_item"] == 5
    assert body["descuento"]["usd"] == 10
    assert body["descuento"]["pesos"] == 15600
    assert body["descuento"]["transferencia"] == 16082


def test_validar_descuento_mail_falla_si_no_aplica(monkeypatch):
    c, _fake, _cliente_id = _cliente_con_codigo(monkeypatch)

    r = c.post("/api/descuentos/validar", json={
        "codigo": "TTRA-TEST1234",
        "items": [{"nombre": "MacBook Air", "cantidad": 1}],
    })

    assert r.status_code == 400
    assert "sin productos aplicables" in r.json()["error"].lower()


def test_consumir_descuento_mail_lo_marca_como_usado(monkeypatch):
    c, fake, _cliente_id = _cliente_con_codigo(monkeypatch)

    r = c.post("/api/descuentos/consumir", json={
        "codigo": "TTRA-TEST1234",
        "items": [{"nombre": "Galaxy A56", "cantidad": 3}],
    })

    assert r.status_code == 200
    body = r.json()
    assert body["ok"] is True
    assert body["productos"] == ["Galaxy A56"]
    filas = fake.table("codigos_descuento").select("*").eq("code", "TTRA-TEST1234").execute().data
    assert len(filas) == 1
    assert filas[0]["usado_en"]

    r2 = c.post("/api/descuentos/validar", json={
        "codigo": "TTRA-TEST1234",
        "items": [{"nombre": "Galaxy A56", "cantidad": 1}],
    })
    assert r2.status_code == 400
