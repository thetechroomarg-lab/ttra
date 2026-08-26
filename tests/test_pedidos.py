from datetime import date

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
