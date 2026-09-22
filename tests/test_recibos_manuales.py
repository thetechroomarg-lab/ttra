import pytest

from web import recibos_manuales


def test_construir_items_normaliza_precio_a_float():
    items = recibos_manuales.construir_items([
        {"nombre": "iPhone 11 128GB", "precio_usd": "425"},
        {"nombre": "Funda", "precio_usd": 10},
    ])
    assert items == [
        {"nombre": "iPhone 11 128GB", "precio_usd": 425.0},
        {"nombre": "Funda", "precio_usd": 10.0},
    ]


def test_construir_items_rechaza_lista_vacia():
    with pytest.raises(ValueError):
        recibos_manuales.construir_items([])


def test_construir_items_rechaza_nombre_vacio_o_precio_invalido():
    with pytest.raises(ValueError):
        recibos_manuales.construir_items([{"nombre": "  ", "precio_usd": 10}])
    with pytest.raises(ValueError):
        recibos_manuales.construir_items([{"nombre": "Funda", "precio_usd": -5}])
    with pytest.raises(ValueError):
        recibos_manuales.construir_items([{"nombre": "Funda", "precio_usd": "no-es-numero"}])


def test_calcular_total_suma_precios():
    items = [{"nombre": "A", "precio_usd": 10.5}, {"nombre": "B", "precio_usd": 4.5}]
    assert recibos_manuales.calcular_total(items) == 15.0


def test_armar_pedido_like_tiene_la_forma_que_espera_recibos_py():
    items = [{"nombre": "iPhone 11 128GB", "precio_usd": 425.0}]
    pedido = recibos_manuales.armar_pedido_like(
        nombre_cliente="Ana Lopez",
        items=items,
        total_usd=425.0,
        recibo_id="0001-1993",
        emitido_en="2026-09-19T12:00:00+00:00",
        creado_por="alejo",
    )
    assert pedido["detalle"] == [{
        "nombre": "iPhone 11 128GB", "color": None, "cantidad": 1,
        "usd_unitario": 425.0, "usd_subtotal": 425.0,
    }]
    assert pedido["total_usd"] == 425.0
    assert pedido["descuento_usd"] == 0
    assert pedido["recibo_id"] == "0001-1993"
    assert pedido["recibo_emitido_en"] == "2026-09-19T12:00:00+00:00"
    assert pedido["entregado_por_cadete"] is True
