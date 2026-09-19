from web.mailing import template


def _producto(nombre="IPHONE 11 128GB", usd=425, colores=None):
    return {
        "nombre": nombre, "usd": usd, "pesos": 667250, "transferencia": 687887,
        "colores": colores or ["Black"],
    }


def test_incluye_nombre_precio_y_link_del_producto():
    html = template.armar_html([_producto()], nota=None, cliente_id=None)

    assert "IPHONE 11 128GB" in html
    assert "U$D 425" in html
    assert "/p/iphone-11-128gb" in html


def test_incluye_nota_cuando_se_pasa():
    html = template.armar_html([_producto()], nota="20% off en fundas", cliente_id=None)

    assert "20% off en fundas" in html


def test_no_incluye_banner_de_nota_si_no_hay_nota():
    html = template.armar_html([_producto()], nota=None, cliente_id=None)

    assert "20% off" not in html


def test_link_de_baja_usa_el_cliente_id():
    html = template.armar_html([_producto()], nota=None, cliente_id="cliente-123")

    assert "/mailing/baja/cliente-123" in html


def test_sin_cliente_id_el_link_de_baja_es_un_placeholder():
    html = template.armar_html([_producto()], nota=None, cliente_id=None)

    assert 'href="#"' in html


def test_todas_las_cards_tienen_la_misma_altura_fija():
    corto = _producto(nombre="A", colores=[])
    largo = _producto(
        nombre="Xiaomi Redmi Note 17 PRO MAX 5G 8GB 512GB NFC (8GB+8GB)",
        colores=["Black", "Cloud Blush", "Green", "Purple"],
    )

    html = template.armar_html([corto, largo], nota=None, cliente_id=None)

    assert html.count('height="260"') == 4  # table + td, por cada una de las 2 cards
