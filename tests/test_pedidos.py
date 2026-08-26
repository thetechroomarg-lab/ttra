from datetime import date
from decimal import Decimal

from tests.fakes_supabase import FakeSupabaseClient
from web import pedidos


def test_guardar_pedido_inserta_asociado_al_cliente():
    client = FakeSupabaseClient()
    resultado = pedidos.guardar_pedido(client, "cliente-1", ["iPhone 13", "AirPods"])
    assert resultado["cliente_id"] == "cliente-1"
    assert resultado["productos"] == ["iPhone 13", "AirPods"]
    assert resultado["origen"] == "whatsapp"
    assert resultado["modo_precio"] == "minorista"
    assert resultado["descuento_mayorista_usd"] == 0
    filas = client.table("pedidos").select("*").eq("cliente_id", "cliente-1").execute().data
    assert len(filas) == 1


def test_guardar_pedido_persiste_modo_y_descuento_mayorista():
    client = FakeSupabaseClient()

    resultado = pedidos.guardar_pedido(
        client,
        "cliente-1",
        ["Elegible"],
        modo_precio="mayorista",
        descuento_mayorista_usd=50,
    )

    assert resultado["modo_precio"] == "mayorista"
    assert resultado["descuento_mayorista_usd"] == 50


def test_guardar_pedido_no_consolida_modos_de_precio_distintos():
    client = FakeSupabaseClient()
    detalle_minorista = [{
        "nombre": "Elegible", "cantidad": 1,
        "usd_unitario": 180, "usd_subtotal": 180,
    }]
    detalle_mayorista = [{
        "nombre": "Elegible", "cantidad": 1,
        "usd_unitario": 130, "usd_subtotal": 130,
    }]

    pedidos.guardar_pedido(
        client, "cliente-1", ["Elegible"], date(2026, 8, 24),
        detalle=detalle_minorista, total_usd=180, modo_precio="minorista",
    )
    pedidos.guardar_pedido(
        client, "cliente-1", ["Elegible"], date(2026, 8, 24),
        detalle=detalle_mayorista, total_usd=130, modo_precio="mayorista",
        descuento_mayorista_usd=50,
    )

    filas = client.table("pedidos").select("*").execute().data
    assert len(filas) == 2
    assert {fila["modo_precio"] for fila in filas} == {"minorista", "mayorista"}


def test_editar_fecha_no_consolida_modos_de_precio_distintos():
    client = FakeSupabaseClient()
    minorista = pedidos.guardar_pedido(
        client, "cliente-1", ["Elegible"], date(2026, 8, 24),
        detalle=[{"nombre": "Elegible", "cantidad": 1, "usd_unitario": 180, "usd_subtotal": 180}],
        total_usd=180, modo_precio="minorista",
    )
    mayorista = pedidos.guardar_pedido(
        client, "cliente-1", ["Elegible"], date(2026, 8, 25),
        detalle=[{"nombre": "Elegible", "cantidad": 1, "usd_unitario": 130, "usd_subtotal": 130}],
        total_usd=130, modo_precio="mayorista", descuento_mayorista_usd=50,
    )

    pedidos.editar_fecha_entrega(client, mayorista["id"], date(2026, 8, 24))

    filas = client.table("pedidos").select("*").execute().data
    assert len(filas) == 2
    assert next(f for f in filas if f["id"] == minorista["id"])["total_usd"] == 180
    assert next(f for f in filas if f["id"] == mayorista["id"])["fecha_entrega"] == "2026-08-24"


def test_guardar_pedido_no_consolida_direcciones_distintas():
    client = FakeSupabaseClient()
    detalle = [{"nombre": "Elegible", "cantidad": 1, "usd_unitario": 180, "usd_subtotal": 180}]

    pedidos.guardar_pedido(
        client, "cliente-1", ["Elegible"], date(2026, 8, 24),
        direccion_entrega="Av. Colón 123", detalle=detalle, total_usd=180,
    )
    pedidos.guardar_pedido(
        client, "cliente-1", ["Elegible"], date(2026, 8, 24),
        direccion_entrega="San Martín 456", detalle=detalle, total_usd=180,
    )

    filas = client.table("pedidos").select("*").execute().data
    assert len(filas) == 2
    assert {fila["direccion_entrega"] for fila in filas} == {"Av. Colón 123", "San Martín 456"}


def test_editar_fecha_no_consolida_direcciones_distintas():
    client = FakeSupabaseClient()
    detalle = [{"nombre": "Elegible", "cantidad": 1, "usd_unitario": 180, "usd_subtotal": 180}]
    destino = pedidos.guardar_pedido(
        client, "cliente-1", ["Elegible"], date(2026, 8, 24),
        direccion_entrega="Av. Colón 123", detalle=detalle, total_usd=180,
    )
    movido = pedidos.guardar_pedido(
        client, "cliente-1", ["Elegible"], date(2026, 8, 25),
        direccion_entrega="San Martín 456", detalle=detalle, total_usd=180,
    )

    pedidos.editar_fecha_entrega(client, movido["id"], date(2026, 8, 24))

    filas = client.table("pedidos").select("*").execute().data
    assert len(filas) == 2
    assert next(f for f in filas if f["id"] == destino["id"])["total_usd"] == 180
    assert next(f for f in filas if f["id"] == movido["id"])["fecha_entrega"] == "2026-08-24"


def test_consolidacion_preserva_decimales_sin_truncar():
    client = FakeSupabaseClient()
    detalle = [{"nombre": "Decimal", "cantidad": 3, "usd_unitario": 0.1, "usd_subtotal": 0.3}]

    pedidos.guardar_pedido(
        client, "cliente-1", ["Decimal"], date(2026, 8, 24),
        direccion_entrega="Av. Colón 123", detalle=detalle,
        total_usd=130.5, descuento_usd=0.1,
    )
    pedidos.guardar_pedido(
        client, "cliente-1", ["Decimal"], date(2026, 8, 24),
        direccion_entrega="Av. Colón 123", detalle=detalle,
        total_usd=130.5, descuento_usd=0.1,
    )

    pedido = client.table("pedidos").select("*").execute().data[0]
    assert pedido["total_usd"] == 261
    assert pedido["descuento_usd"] == 0.2
    assert pedido["detalle"][0]["usd_subtotal"] == 0.6


def test_guardar_pedido_serializa_decimal_a_numero_db():
    client = FakeSupabaseClient()

    pedido = pedidos.guardar_pedido(
        client, "cliente-1", ["Decimal"], date(2026, 8, 24),
        direccion_entrega="Av. Colón 123",
        detalle=[{
            "nombre": "Decimal", "cantidad": 3,
            "usd_unitario": Decimal("0.1"),
            "usd_subtotal": Decimal("0.3"),
        }],
        total_usd=Decimal("130.50"),
        descuento_usd=Decimal("0.1"),
    )

    assert pedido["total_usd"] == 130.5
    assert isinstance(pedido["total_usd"], float)
    assert pedido["descuento_usd"] == 0.1
    assert pedido["detalle"][0]["usd_unitario"] == 0.1
    assert pedido["detalle"][0]["usd_subtotal"] == 0.3
