from web.ui_helpers import descuentos_pedido


def _pedido(**extra):
    base = {
        "modo_precio": "minorista",
        "detalle": [
            {"nombre": "iPhone 15", "color": "Negro", "cantidad": 1,
             "usd_unitario": 500, "usd_subtotal": 500, "proveedor": "az"},
        ],
        "descuento_usd": 20,
        "total_usd": 480,
    }
    base.update(extra)
    return base


def test_un_equipo_con_cupon_es_todo_cupon():
    assert descuentos_pedido(_pedido()) == [
        ("Descuento por cupón (sellos, referidos o mailing)", 20.0),
    ]


def test_cantidad_y_cupon_se_separan():
    detalle = [{"nombre": "A", "cantidad": 2, "usd_unitario": 100, "usd_subtotal": 200, "proveedor": "az"}]
    assert descuentos_pedido(_pedido(detalle=detalle, descuento_usd=30)) == [
        ("Descuento por cantidad (2 unidades)", 10.0),
        ("Descuento por cupón (sellos, referidos o mailing)", 20.0),
    ]


def test_seis_o_mas_unidades_descuentan_siete_y_medio_cada_una():
    detalle = [{"nombre": "A", "cantidad": 6, "usd_unitario": 100, "usd_subtotal": 600, "proveedor": "az"}]
    assert descuentos_pedido(_pedido(detalle=detalle, descuento_usd=45)) == [
        ("Descuento por cantidad (6 unidades)", 45.0),
    ]


def test_envio_y_regalo_no_cuentan_como_unidades():
    detalle = _pedido()["detalle"] + [
        {"nombre": "Auriculares", "cantidad": 1, "usd_unitario": 0, "usd_subtotal": 0, "tipo": "regalo_promocional"},
        {"nombre": "Envío", "cantidad": 1, "usd_unitario": 5, "usd_subtotal": 5, "proveedor": "envío"},
    ]
    assert descuentos_pedido(_pedido(detalle=detalle)) == [
        ("Descuento por cupón (sellos, referidos o mailing)", 20.0),
    ]


def test_mayorista_no_tiene_descuento_por_cantidad():
    detalle = [{"nombre": "A", "cantidad": 3, "usd_unitario": 100, "usd_subtotal": 300, "proveedor": "az"}]
    assert descuentos_pedido(_pedido(detalle=detalle, modo_precio="mayorista", descuento_usd=20)) == [
        ("Descuento por cupón (sellos, referidos o mailing)", 20.0),
    ]


def test_sin_descuento_o_sin_detalle_no_hay_renglones():
    assert descuentos_pedido(_pedido(descuento_usd=0)) == []
    assert descuentos_pedido({"detalle": None, "descuento_usd": 20}) == []
