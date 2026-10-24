from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient
from web import zona_envio

CENTRO = (-31.4167, -64.1833)
CARLOS_PAZ = (-31.4241, -64.4978)
RIO_CUARTO = (-33.1232, -64.3493)


def test_adentro_de_la_circunvalacion_es_gratis():
    assert zona_envio.cotizar(*CENTRO, 1580) == {"zona": "gratis", "envio_usd": 0, "distancia_km": 0.0, "desglose": None}


def test_franja_de_5_km_pasando_la_circunvalacion_es_gratis():
    # ~3 km al oeste del borde oeste del anillo.
    envio = zona_envio.cotizar(-31.4300, -64.2900, 1580)
    assert envio["zona"] == "gratis"
    assert 0 < envio["distancia_km"] <= 5


def test_entre_5_y_60_km_cobra_nafta_ida_y_vuelta_mas_desgaste(monkeypatch):
    monkeypatch.setattr(zona_envio, "distancia_km", lambda lat, lng: 25.0)
    envio = zona_envio.cotizar(*CARLOS_PAZ, 1000)
    d = envio["desglose"]
    assert envio["zona"] == "con_cargo"
    assert d["km_excedentes"] == 20.0
    assert d["km_recorridos"] == 52.0  # 20 km x 2 (ida y vuelta) x 1,3 (ruta)
    assert d["litros"] == 5.2
    assert d["combustible_usd"] == round(5.2 * zona_envio.NAFTA_ARS_LITRO / 1000, 2)
    assert d["desgaste_tiempo_usd"] == d["combustible_usd"]
    assert envio["envio_usd"] == round(d["combustible_usd"] * 2, 2)


def test_mas_de_60_km_hay_que_consultar():
    assert zona_envio.cotizar(*RIO_CUARTO, 1580)["zona"] == "consultar"


def test_sin_coordenadas_no_se_puede_ubicar():
    assert zona_envio.cotizar(None, None, 1580)["zona"] == "sin_ubicacion"


def _cliente(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [{"nombre": "iPhone 13", "usd": 500}])
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    return c, fake


def _pedido(coords, **extra):
    return {
        "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Calle 1",
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
        "lat": coords[0],
        "lng": coords[1],
        **extra,
    }


def test_api_cotizar_envio(monkeypatch):
    c, _ = _cliente(monkeypatch)
    r = c.post("/api/envio/cotizar", json={"lat": CARLOS_PAZ[0], "lng": CARLOS_PAZ[1]})
    assert r.status_code == 200
    assert r.json()["envio_usd"] == zona_envio.cotizar(*CARLOS_PAZ, appmod.COTIZACION_DOLAR)["envio_usd"] > 0
    assert r.json()["desglose"]["km_por_litro"] == 10


def test_pedido_fuera_de_zona_suma_el_envio_al_total(monkeypatch):
    c, fake = _cliente(monkeypatch)
    envio = c.post("/api/envio/cotizar", json={"lat": CARLOS_PAZ[0], "lng": CARLOS_PAZ[1]}).json()["envio_usd"]
    r = c.post("/api/pedidos", json=_pedido(CARLOS_PAZ, envio_usd=envio))
    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["total_usd"] == pytest.approx(500 + envio)
    assert pedido["detalle"][-1]["nombre"] == "Envío fuera de zona"
    assert pedido["detalle"][-1]["usd_subtotal"] == pytest.approx(envio)
    assert pedido["detalle"][-1]["proveedor"] == "envío"


def test_pedido_fuera_de_zona_sin_aceptar_el_envio_se_rechaza(monkeypatch):
    c, fake = _cliente(monkeypatch)
    r = c.post("/api/pedidos", json=_pedido(CARLOS_PAZ))
    assert r.status_code == 409
    assert r.json()["conflicto"] == "envio"
    assert fake.table("pedidos").select("*").execute().data == []


def test_pedido_a_mas_de_60_km_pide_consultar(monkeypatch):
    c, fake = _cliente(monkeypatch)
    r = c.post("/api/pedidos", json=_pedido(RIO_CUARTO))
    assert r.status_code == 400
    assert r.json()["conflicto"] == "envio_consultar"
    assert fake.table("pedidos").select("*").execute().data == []


def test_pedido_en_zona_gratis_no_agrega_envio(monkeypatch):
    c, fake = _cliente(monkeypatch)
    r = c.post("/api/pedidos", json=_pedido(CENTRO))
    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["total_usd"] == 500
    assert len(pedido["detalle"]) == 1


def test_checkout_avisa_el_costo_de_envio_antes_de_confirmar():
    from pathlib import Path
    js = (Path(appmod.__file__).parent / "static" / "landing.js").read_text()
    assert "/api/envio/cotizar" in js
    assert "envio_usd" in js
    assert "actualizarDetalleEnvio" in js
    assert "Desgaste del vehículo y tiempo" in js
