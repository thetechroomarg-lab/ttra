from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_con_catalogo(monkeypatch, *, precio_publico=180, costo=100, mayorista=False):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [{"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": precio_publico}],
    )
    monkeypatch.setattr(appmod, "_cargar_costos", lambda: {"Elegible": costo})
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
        "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",
    })
    if mayorista:
        cliente = fake.table("clientes").select("*").execute().data[0]
        fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq(
            "id", cliente["id"]
        ).execute()
    return c, fake


def _cliente_mayorista_con_catalogo(monkeypatch, *, precio_publico=180, costo=100):
    return _cliente_con_catalogo(
        monkeypatch,
        precio_publico=precio_publico,
        costo=costo,
        mayorista=True,
    )


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
    "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
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
        appmod, "_cargar_productos", lambda: [{"nombre": "iPhone 13", "usd": 500}]
    )
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})

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
    monkeypatch.setattr(
        appmod, "_cargar_productos", lambda: [{"nombre": "iPhone 13", "usd": 500}]
    )
    monkeypatch.setattr(appmod, "_cargar_proveedores", lambda: {"iPhone 13": "az"})
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})

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
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [{"nombre": "Xiaomi Redmi Note 14 8GB 256GB slim", "usd": 300}],
    )
    monkeypatch.setattr(appmod, "_cargar_proveedores", lambda: {"Xiaomi Redmi Note 14 8GB 256GB": "az"})
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})

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
        appmod, "_cargar_productos", lambda: [{"nombre": "iPhone 13", "usd": 500}]
    )
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
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
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})

    r = c.post("/api/pedidos", json={"productos": ["iPhone 13"], "fecha_entrega": "2026-08-29"})

    assert r.status_code == 400


def test_pedido_mayorista_recalcula_y_guarda_auditoria(monkeypatch):
    c, fake = _cliente_mayorista_con_catalogo(monkeypatch, precio_publico=180, costo=100)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 2,
            "usd_unitario": 130, "usd_subtotal": 260,
        }],
        "total_usd": 260, "descuento_usd": 0,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["modo_precio"] == "mayorista"
    assert pedido["descuento_mayorista_usd"] == 100
    assert pedido["total_usd"] == 260


def test_pedido_rechaza_precio_manipulado(monkeypatch):
    c, _fake = _cliente_mayorista_con_catalogo(monkeypatch, precio_publico=180, costo=100)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 1, "usd_subtotal": 1,
        }],
        "total_usd": 1,
    })

    assert r.status_code == 409
    assert "precios" in r.json()["error"].lower()


def test_pedido_minorista_guarda_precios_autorizados(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 2,
            "usd_unitario": 180, "usd_subtotal": 360,
        }],
        "total_usd": 360,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["modo_precio"] == "minorista"
    assert pedido["descuento_mayorista_usd"] == 0
    assert pedido["total_usd"] == 360


def test_pedido_rechaza_subtotal_o_total_manipulado(monkeypatch):
    c, _fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    base = {
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 2,
            "usd_unitario": 180, "usd_subtotal": 1,
        }],
        "total_usd": 360,
    }

    assert c.post("/api/pedidos", json=base).status_code == 409
    base["detalle"][0]["usd_subtotal"] = 360
    base["total_usd"] = 1
    assert c.post("/api/pedidos", json=base).status_code == 409


def test_pedido_mayorista_sin_detalle_se_rechaza(monkeypatch):
    c, fake = _cliente_mayorista_con_catalogo(monkeypatch)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
    })

    assert r.status_code == 409
    assert fake.table("pedidos").select("*").execute().data == []
