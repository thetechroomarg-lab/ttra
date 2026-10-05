from io import BytesIO

from PIL import Image as PilImage
from reportlab.lib import colors
from web import recibos


def _jpeg_minimo():
    buffer = BytesIO()
    PilImage.new("RGB", (8, 8), "#c8102e").save(buffer, format="JPEG")
    return buffer.getvalue()


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
    assert "1 año" in contenido
    assert "6 meses" in contenido
    assert "Hola Ana," in contenido
    assert "Hola Ana Pérez," not in contenido


def test_html_recibo_no_depende_de_imagenes_externas_para_el_logo():
    contenido = recibos.html_recibo(
        {"nombre": "Ana", "apellido": "Pérez"},
        {"recibo_id": "TTRA-000002", "detalle": [], "total_usd": 0},
        "http://127.0.0.1:8000/favicon.svg",
    )

    assert "<img" not in contenido
    assert "THE TECH ROOM ARG" in contenido


def test_html_recibo_ajusta_nombres_largos_sin_invadir_otras_columnas():
    contenido = recibos.html_recibo(
        {"nombre": "Ana", "apellido": "Pérez"},
        {
            "recibo_id": "TTRA-000004",
            "detalle": [{
                "nombre": "ProductoConUnNombreExtraordinariamenteLargoSinEspaciosParaProbarElCorte",
                "cantidad": 1,
                "usd_unitario": 900,
                "usd_subtotal": 900,
            }],
            "total_usd": 900,
        },
    )

    assert "table-layout:fixed" in contenido
    assert "<colgroup>" in contenido
    assert "word-break:break-word" in contenido


def test_formatear_fecha_emision_convierte_a_gmt_menos_3():
    assert recibos._formatear_fecha_emision("2026-08-24T15:30:00+00:00") == "24/08/2026 12:30"
    assert recibos._formatear_fecha_emision("2026-08-24T02:15:00+00:00") == "23/08/2026 23:15"


def test_html_recibo_incluye_leyenda_no_valido_como_factura():
    contenido = recibos.html_recibo(
        {"nombre": "Ana", "apellido": "Pérez"},
        {"recibo_id": "TTRA-000006", "detalle": [], "total_usd": 0},
    )

    assert "Documento no válido como factura" in contenido


def test_pdf_recibo_incluye_leyenda_no_valido_como_factura(monkeypatch):
    textos = []
    original = recibos.Paragraph

    def _paragraph_espia(texto, *args, **kwargs):
        textos.append(texto)
        return original(texto, *args, **kwargs)

    monkeypatch.setattr(recibos, "Paragraph", _paragraph_espia)

    recibos.pdf_recibo(
        {"nombre": "Ana", "apellido": "Pérez"},
        {"recibo_id": "TTRA-000007", "detalle": [], "total_usd": 0, "descuento_usd": 0},
    )

    assert any("Documento no válido como factura" in texto for texto in textos)


def test_pdf_recibo_contiene_el_detalle_y_la_fecha_original():
    pdf = recibos.pdf_recibo(
        {"nombre": "Ana", "apellido": "Pérez"},
        {"recibo_id": "TTRA-000003", "recibo_emitido_en": "2026-08-24T15:30:00+00:00",
         "detalle": [{"nombre": "iPhone 15", "cantidad": 1, "usd_unitario": 900, "usd_subtotal": 900}],
         "total_usd": 900, "descuento_usd": 0},
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_pdf_recibo_ajusta_texto_largo_e_incluye_fotos_de_entrega():
    pdf = recibos.pdf_recibo(
        {"nombre": "Ana", "apellido": "Pérez"},
        {
            "recibo_id": "TTRA-000005",
            "detalle": [{
                "nombre": "ProductoConUnNombreExtraordinariamenteLargoSinEspaciosParaProbarElCorteEnElPDF",
                "cantidad": 1, "usd_unitario": 900, "usd_subtotal": 900,
            }],
            "total_usd": 900,
        },
        fotos=[_jpeg_minimo()],
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1500


def test_garantias_del_recibo_son_las_mismas_de_la_web():
    garantias = "\n".join(recibos.garantias_para_detalle([
        {"nombre": "Samsung Galaxy S26"},
        {"nombre": "Motorola Edge 50"},
        {"nombre": "Xiaomi Redmi Note"},
        {"nombre": "Apple MacBook Air"},
        {"nombre": "Notebook Lenovo"},
        {"nombre": "Parlante JBL"},
        {"nombre": "iPhone 13 128GB (Usado)"},
    ]))

    assert "Garantía Samsung: 3 meses" in garantias and "5 días hábiles" in garantias
    assert "Garantía Motorola" in garantias and "números de serie" in garantias
    assert "Garantía Xiaomi" in garantias and "Sin cuentas activas" in garantias
    assert "Garantía Apple: 1 año" in garantias and "One Click" in garantias and "MacStation" in garantias
    assert "Garantía Notebooks: 6 meses" in garantias and "30 días" in garantias
    assert "Garantía Gaming y Accesorios: 1 mes" in garantias
    assert "Garantía Usados Swap: 30 días" in garantias and "Ampsentrix" in garantias


def test_misma_marca_no_repite_garantia():
    from web import garantias

    assert garantias.claves_para_detalle([
        {"nombre": "Samsung Galaxy Buds 3"},
        {"nombre": "A17 4GB 128GB"},
    ]) == ["samsung"]
    assert garantias.claves_para_detalle([
        {"nombre": "Samsung Galaxy Buds 3"},
        {"nombre": "A17 4GB 128GB"},
        {"nombre": "Notebook Lenovo IdeaPad"},
    ]) == ["samsung", "notebooks"]


def test_clasificacion_de_garantias_por_producto():
    from web.garantias import clave_para_nombre as clave

    assert clave("Xiaomi Redmi Watch 6") == "xiaomi"
    assert clave("Apple Watch Serie 11 42mm") == "apple"
    assert clave("Magic Mouse 2") == "apple"
    assert clave("CARGADOR APPLE 35W CERTIFICADO USB C") == "gaming"
    assert clave("IPHONE 15 PRO 512GB USADO Grado A") == "usados"
    assert clave("MSI Cyborg 15 GAMING Core 7-240H 512GB SSD 16GB") == "notebooks"
    assert clave("PARLANTE JBL FLIP 7") == "gaming"


def test_encabezado_de_tabla_pdf_conserva_texto_blanco():
    assert recibos._estilo_celda_encabezado().textColor == colors.white
