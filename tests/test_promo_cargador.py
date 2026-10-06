from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient
from web import promo_cargador

APPLE = promo_cargador.PROMOS["apple"]["nombre"]
SAMSUNG = promo_cargador.PROMOS["samsung"]["nombre"]


@pytest.mark.parametrize("producto, esperado", [
    ({"nombre": "IPHONE 15 128GB", "categoria": "Apple - iPhone", "usd": 685}, "apple"),
    ({"nombre": "IPHONE 13 128GB usado", "categoria": "Apple - iPhone Usado", "usd": 380}, "apple"),
    ({"nombre": "iPhone 17 256GB", "categoria": "Apple - iPhone", "usd": 900}, None),
    ({"nombre": "IPHONE 11 PRO 64GB CPO (Caja con cargador)", "categoria": "Apple - iPhone", "usd": 405}, None),
    ({"nombre": "SAMSUNG A06 4GB 128GB", "categoria": "Samsung", "usd": 185}, "samsung"),
    ({"nombre": "SAMSUNG A07 4GB 128GB con cargador", "categoria": "Samsung", "usd": 205}, None),
    ({"nombre": "XIAOMI 15 5G 12GB 512GB (s/ cargador)", "categoria": "Xiaomi", "usd": 800}, "samsung"),
    ({"nombre": "MOTO G86 5G 8GB 256GB (s/ cargador)", "categoria": "Motorola", "usd": 295}, "samsung"),
    ({"nombre": "Xiaomi Redmi Note 14 8GB 256GB", "categoria": "Xiaomi", "usd": 260}, None),
    ({"nombre": "Cargador Original SAMSUNG 45W USB C (con cable)", "categoria": "Samsung", "usd": 60}, None),
    ({"nombre": "Galaxy Tab S9 8GB 128GB", "categoria": "Samsung", "usd": 700}, None),
])
def test_que_telefono_recibe_que_cargador(producto, esperado):
    assert promo_cargador.promo_para_producto(producto) == esperado


def test_item_promo_tiene_pesos_y_transferencia_como_el_catalogo():
    assert promo_cargador.item_promo("apple", 1565) == {
        "nombre": APPLE, "usd": 30, "pesos": 46950, "transferencia": 48402,
    }


PRODUCTOS = [
    {"nombre": "IPHONE 15 128GB", "categoria": "Apple - iPhone", "usd": 685},
    {"nombre": "SAMSUNG A06 4GB 128GB", "categoria": "Samsung", "usd": 185},
    {"nombre": "AirPods 4", "categoria": "Apple - AirPods", "usd": 150},
]


def _cliente(monkeypatch, *, mayorista=False):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: PRODUCTOS)
    monkeypatch.setattr(
        appmod, "_cargar_snapshot_mayorista",
        lambda: (PRODUCTOS, {p["nombre"]: p["usd"] - 50 for p in PRODUCTOS}),
    )
    monkeypatch.setattr(
        appmod.entregas, "ahora_argentina",
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
        fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq("id", cliente["id"]).execute()
    return c, fake


def _linea(nombre, usd, cantidad=1):
    return {"nombre": nombre, "color": None, "cantidad": cantidad, "usd_unitario": usd, "usd_subtotal": usd * cantidad}


def _pedido(c, detalle, total_usd):
    return c.post("/api/pedidos", json={
        "productos": [d["nombre"] for d in detalle],
        "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": detalle,
        "total_usd": total_usd,
    })


def test_catalogo_minorista_marca_los_telefonos_con_oferta(monkeypatch):
    c, _ = _cliente(monkeypatch)
    celulares = {p["nombre"]: p for p in c.get("/api/catalogo").json()["secciones"]["Celulares"]}
    assert celulares["IPHONE 15 128GB"]["oferta_cargador"]["nombre"] == APPLE
    assert celulares["IPHONE 15 128GB"]["oferta_cargador"]["usd"] == 30
    assert celulares["SAMSUNG A06 4GB 128GB"]["oferta_cargador"]["nombre"] == SAMSUNG
    assert celulares["SAMSUNG A06 4GB 128GB"]["oferta_cargador"]["usd"] == 35


def test_catalogo_mayorista_no_ofrece_cargador(monkeypatch):
    c, _ = _cliente(monkeypatch, mayorista=True)
    celulares = c.get("/api/catalogo").json()["secciones"]["Celulares"]
    assert celulares and all("oferta_cargador" not in p for p in celulares)


def test_pedido_con_cargador_promo_no_suma_al_descuento_por_cantidad(monkeypatch):
    c, fake = _cliente(monkeypatch)
    r = _pedido(c, [_linea("IPHONE 15 128GB", 685), _linea(APPLE, 30)], 715)
    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["total_usd"] == 715
    assert pedido["descuento_usd"] == 0
    assert pedido["detalle"][1] == {
        "nombre": APPLE, "color": None, "cantidad": 1,
        "usd_unitario": 30, "usd_subtotal": 30, "proveedor": "stock propio",
    }


def test_pedido_rechaza_cargador_promo_sin_telefono_que_lo_habilite(monkeypatch):
    c, _ = _cliente(monkeypatch)
    assert _pedido(c, [_linea("AirPods 4", 150), _linea(APPLE, 30)], 180).status_code == 409
    # El de Samsung no lo habilita un iPhone.
    assert _pedido(c, [_linea("IPHONE 15 128GB", 685), _linea(SAMSUNG, 35)], 720).status_code == 409


def test_pedido_rechaza_mas_cargadores_promo_que_telefonos(monkeypatch):
    c, _ = _cliente(monkeypatch)
    r = _pedido(c, [_linea("SAMSUNG A06 4GB 128GB", 185), _linea(SAMSUNG, 35, cantidad=2)], 255)
    assert r.status_code == 409


def test_pedido_rechaza_cargador_promo_con_otro_precio(monkeypatch):
    c, _ = _cliente(monkeypatch)
    assert _pedido(c, [_linea("IPHONE 15 128GB", 685), _linea(APPLE, 1)], 686).status_code == 409


def test_pedido_mayorista_rechaza_cargador_promo(monkeypatch):
    c, _ = _cliente(monkeypatch, mayorista=True)
    celulares = c.get("/api/catalogo").json()["secciones"]["Celulares"]
    usd = next(p["usd"] for p in celulares if p["nombre"] == "IPHONE 15 128GB")
    assert _pedido(c, [_linea("IPHONE 15 128GB", usd)], usd).status_code == 200
    r = _pedido(c, [_linea("IPHONE 15 128GB", usd), _linea(APPLE, 30)], usd + 30)
    assert r.status_code == 409
