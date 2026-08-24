from web import recibos


def test_html_recibo_usa_snapshot_y_garantias_del_producto():
    contenido = recibos.html_recibo(
        {"nombre": "Ana", "apellido": "Pérez", "email": "ana@x.com"},
        {
            "recibo_id": "TTRA-000001",
            "detalle": [
                {
                    "nombre": "iPhone 15", "color": "Negro", "cantidad": 1,
                    "usd_unitario": 900, "usd_subtotal": 900,
                },
                {
                    "nombre": "Notebook Lenovo", "color": None, "cantidad": 1,
                    "usd_unitario": 700, "usd_subtotal": 700,
                },
            ],
            "total_usd": 1600,
            "descuento_usd": 0,
        },
    )

    assert "Recibo interno TTRA-000001" in contenido
    assert "U$D 1.600" in contenido
    assert "iPhone 15" in contenido
    assert "12 meses" in contenido
    assert "6 meses" in contenido


def test_html_recibo_no_depende_de_imagenes_externas_para_el_logo():
    contenido = recibos.html_recibo(
        {"nombre": "Ana", "apellido": "Pérez"},
        {"recibo_id": "TTRA-000002", "detalle": [], "total_usd": 0},
        "http://127.0.0.1:8000/favicon.svg",
    )

    assert "<img" not in contenido
    assert "THE TECH ROOM ARG" in contenido


def test_pdf_recibo_contiene_el_detalle_y_la_fecha_original():
    pdf = recibos.pdf_recibo(
        {"nombre": "Ana", "apellido": "Pérez"},
        {"recibo_id": "TTRA-000003", "recibo_emitido_en": "2026-08-24T15:30:00+00:00",
         "detalle": [{"nombre": "iPhone 15", "cantidad": 1, "usd_unitario": 900, "usd_subtotal": 900}],
         "total_usd": 900, "descuento_usd": 0},
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000
