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


@pytest.fixture(autouse=True)
def _sin_google(monkeypatch):
    monkeypatch.setattr(zona_envio, "km_por_ruta", lambda origen, destino: None)


def test_franja_de_5_km_de_ruta_pasando_la_circunvalacion_es_gratis(monkeypatch):
    monkeypatch.setattr(zona_envio, "km_por_ruta", lambda origen, destino: 4.0)
    envio = zona_envio.cotizar(-31.4300, -64.2900, 1580)
    assert envio["zona"] == "gratis"
    assert envio["distancia_km"] == 4.0


def test_entre_5_y_60_km_de_ruta_cobra_nafta_ida_y_vuelta_mas_desgaste(monkeypatch):
    monkeypatch.setattr(zona_envio, "km_por_ruta", lambda origen, destino: 25.0)
    envio = zona_envio.cotizar(*CARLOS_PAZ, 1000)
    d = envio["desglose"]
    assert envio["zona"] == "con_cargo"
    assert d["estimado"] is False
    assert d["km_excedentes"] == 20.0
    assert d["km_recorridos"] == 40.0  # ida y vuelta
    assert d["litros"] == 4.0
    assert d["combustible_usd"] == round(4.0 * zona_envio.NAFTA_ARS_LITRO / 1000, 2)
    assert d["desgaste_tiempo_usd"] == d["combustible_usd"]
    assert envio["envio_usd"] == round(d["combustible_usd"] * 2, 2)


def test_la_ruta_sale_del_punto_de_la_circunvalacion_mas_cercano(monkeypatch):
    llamadas = []
    monkeypatch.setattr(zona_envio, "km_por_ruta", lambda o, d: llamadas.append((o, d)) or 30.0)
    zona_envio.cotizar(*CARLOS_PAZ, 1580)
    (origen, destino), = llamadas
    assert destino == CARLOS_PAZ
    assert zona_envio.distancia_km(*origen) < 0.1


def test_sin_google_se_estima_con_la_linea_recta():
    envio = zona_envio.cotizar(*CARLOS_PAZ, 1580)
    assert envio["desglose"]["estimado"] is True
    assert envio["distancia_km"] == round(zona_envio.distancia_km(*CARLOS_PAZ) * zona_envio.FACTOR_RUTA, 1)


def test_adentro_no_consulta_a_google(monkeypatch):
    monkeypatch.setattr(zona_envio, "km_por_ruta", lambda o, d: pytest.fail("no debería consultar"))
    assert zona_envio.cotizar(*CENTRO, 1580)["zona"] == "gratis"


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


def test_pedido_con_codigo_promo_suma_el_envio_sin_contarlo_como_producto(monkeypatch):
    c, fake = _cliente(monkeypatch)
    fake.table("codigos_promo").insert({
        "id": "promo-R", "code": "REGALO", "producto_regalo": "Funda",
        "usos_maximos": 5, "usos_actuales": 0, "activo": True,
    }).execute()
    envio = c.post("/api/envio/cotizar", json={"lat": CARLOS_PAZ[0], "lng": CARLOS_PAZ[1]}).json()["envio_usd"]
    r = c.post("/api/pedidos", json=_pedido(CARLOS_PAZ, envio_usd=envio, codigo_promo="REGALO"))
    assert r.status_code == 200, r.json()
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["total_usd"] == pytest.approx(500 + envio)
    assert pedido["descuento_usd"] == 0
    assert [i["nombre"] for i in pedido["detalle"]].count("Envío fuera de zona") == 1
    assert pedido["detalle"][-1]["nombre"] == "Envío fuera de zona"
