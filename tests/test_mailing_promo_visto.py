from datetime import datetime, timezone

from web.mailing import promo_visto

PROD = {
    "nombre": "IPHONE 17 PRO 512GB", "usd": 1465, "pesos": 2549100,
    "transferencia": 2627938, "colores": ["Silver", "Deep Blue"],
}
VENCE = datetime(2026, 11, 28, 18, 40, tzinfo=timezone.utc)


def test_vencimiento_en_hora_argentina():
    assert promo_visto.texto_vencimiento(VENCE) == "sábado 28 de noviembre a las 15:40"


def test_mail_menciona_producto_codigo_descuento_y_vencimiento():
    asunto, cuerpo = promo_visto.armar_mail("Tomás", [PROD], "TTRA-ABC12345", VENCE, "11111111-1111-1111-1111-111111111111")
    assert "U$D 10" in asunto
    assert "IPHONE 17 PRO 512GB" in cuerpo
    assert "TTRA-ABC12345" in cuerpo
    assert "sábado 28 de noviembre a las 15:40" in cuerpo
    assert "U$D 1.455" in cuerpo  # 1465 - 10
    assert "codigo=TTRA-ABC12345" in cuerpo and "agregar=1" in cuerpo
    assert "/mailing/baja/11111111-1111-1111-1111-111111111111" in cuerpo
    assert "nosotros" not in cuerpo.lower()


def test_mail_escapa_el_nombre_y_limita_productos():
    prods = [dict(PROD, nombre=f"P{i}<b>") for i in range(7)]
    _, cuerpo = promo_visto.armar_mail("<script>", prods, "TTRA-X", VENCE, "c")
    assert "<script>" not in cuerpo
    assert cuerpo.count("Lo quiero") == promo_visto.MAX_PRODUCTOS
