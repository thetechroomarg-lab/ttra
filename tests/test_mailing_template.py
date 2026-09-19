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


def test_cada_franja_de_la_card_tiene_altura_fija_e_igual_en_ambas():
    corto = _producto(nombre="A", colores=[])
    largo = _producto(
        nombre="Xiaomi Redmi Note 17 PRO MAX 5G 8GB 512GB NFC (8GB+8GB)",
        colores=["Black", "Cloud Blush", "Green", "Purple"],
    )

    html = template.armar_html([corto, largo], nota=None, cliente_id=None)

    # 5 franjas (nombre, colores, usd, pesos, boton) x 2 cards = 10 alturas fijas
    assert html.count('height="58"') == 2
    assert html.count('height="34"') == 4  # colores + pesos, x2 cards
    assert html.count('height="22"') == 2
    assert html.count('height="46"') == 2


def test_footer_incluye_los_cuatro_datos_de_contacto_como_links():
    html = template.armar_html([_producto()], nota=None, cliente_id=None)

    assert 'href="https://wa.me/543512145217"' in html
    assert 'href="mailto:thetechroomarg@gmail.com"' in html
    assert 'href="https://instagram.com/thetechroomarg"' in html
    assert 'href="https://tiktok.com/@thetechroomarg"' in html


def test_card_sin_colores_igual_reserva_la_franja_de_color():
    sin_colores = {"nombre": "Producto sin color", "usd": 100, "pesos": 100, "transferencia": 100, "colores": []}

    html = template.armar_html([sin_colores], nota=None, cliente_id=None)

    assert "&nbsp;" in html
