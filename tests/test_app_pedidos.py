from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_pedido_sin_sesion_devuelve_401(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/api/pedidos", json={"productos": ["iPhone 13"], "fecha_entrega": "2026-08-24"})
    assert r.status_code == 401


def test_pedido_con_sesion_guarda_fecha_entrega_valida(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    "provincia": "Córdoba",
    })
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    r = c.post("/api/pedidos", json={"productos": ["iPhone 13", "AirPods"], "fecha_entrega": "2026-08-24"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["fecha_entrega"] == "2026-08-24"


def test_pedido_guarda_el_detalle_y_total_usd_del_checkout(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba",
    })

    r = c.post("/api/pedidos", json={
        "productos": ["iPhone 13 (Negro)"],
        "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{
            "nombre": "iPhone 13", "color": "Negro", "cantidad": 2,
            "usd_unitario": 500, "usd_subtotal": 1000,
        }],
        "total_usd": 1000,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["detalle"] == [{
        "nombre": "iPhone 13", "color": "Negro", "cantidad": 2,
        "usd_unitario": 500, "usd_subtotal": 1000,
        "proveedor": "Proveedor no identificado",
    }]
    assert pedido["total_usd"] == 1000
    assert pedido["direccion_entrega"] == "Av. Colón 123, Córdoba"


def test_pedido_guarda_el_proveedor_solo_resuelto_en_el_servidor(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_proveedores", lambda: {"iPhone 13": "az"})
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba",
    })

    r = c.post("/api/pedidos", json={
        "productos": ["iPhone 13"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
    })

    assert r.status_code == 200
    detalle = fake.table("pedidos").select("*").execute().data[0]["detalle"]
    assert detalle[0]["proveedor"] == "az"


def test_pedido_normaliza_el_nombre_antes_de_resolver_proveedor(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_proveedores", lambda: {"Xiaomi Redmi Note 14 8GB 256GB": "az"})
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba",
    })

    r = c.post("/api/pedidos", json={
        "productos": ["Xiaomi Redmi Note 14 8GB 256GB slim"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{"nombre": "Xiaomi Redmi Note 14 8GB 256GB slim", "cantidad": 1, "usd_unitario": 300, "usd_subtotal": 300}],
        "total_usd": 300,
    })

    assert r.status_code == 200
    detalle = fake.table("pedidos").select("*").execute().data[0]["detalle"]
    assert detalle[0]["proveedor"] == "az"


def test_pedido_del_mismo_cliente_y_entrega_se_consolida(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba",
    })
    pedido = {
        "productos": ["iPhone 13 (Negro)"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{"nombre": "iPhone 13", "color": "Negro", "cantidad": 1,
                     "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
    }

    assert c.post("/api/pedidos", json=pedido).status_code == 200
    pedido["detalle"][0]["cantidad"] = 2
    pedido["detalle"][0]["usd_subtotal"] = 1000
    pedido["total_usd"] = 1000
    assert c.post("/api/pedidos", json=pedido).status_code == 200

    filas = fake.table("pedidos").select("*").execute().data
    assert len(filas) == 1
    assert filas[0]["detalle"][0]["cantidad"] == 3
    assert filas[0]["detalle"][0]["usd_subtotal"] == 1500
    assert filas[0]["total_usd"] == 1500


def test_pedido_rechaza_fecha_fuera_de_las_opciones(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 28, 17, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba",
    })

    r = c.post("/api/pedidos", json={"productos": ["iPhone 13"], "fecha_entrega": "2026-08-29"})

    assert r.status_code == 400
