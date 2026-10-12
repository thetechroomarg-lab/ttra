from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient
from web import mail_pedido


PEDIDO = {
    "id": "df6a0e4d-1234-5678-9abc-def012345678",
    "detalle": [
        {"nombre": "iPhone 16 128GB", "color": "Negro", "cantidad": 2, "usd_unitario": 800, "usd_subtotal": 1600},
        {"nombre": "Moto Edge 50 5G 12GB 512GB", "cantidad": 1, "usd_unitario": 380, "usd_subtotal": 380},
    ],
    "total_usd": 1950,
    "descuento_usd": 30,
    "fecha_entrega": "2026-10-13",
    "direccion_entrega": "Av. Colón 123, Córdoba",
    "piso_entrega": "4",
    "depto_entrega": "B",
}


def test_el_mail_trae_el_detalle_la_entrega_y_el_total():
    html = mail_pedido.html_pedido_confirmado({"nombre": "juan carlos"}, PEDIDO)

    assert "¡Gracias, Juan!" in html
    assert "#DF6A0E4D" in html
    assert "iPhone 16 128GB" in html and "Negro" in html and "U$D 800 c/u" in html
    assert "Moto Edge 50 5G 12GB 512GB" in html
    assert "martes 13 de octubre" in html
    assert "Av. Colón 123, Córdoba" in html and "Piso 4 · Depto B" in html
    assert "U$D 1.980" in html and "-U$D 30" in html and "U$D 1.950" in html


def test_el_mail_resume_la_garantia_de_cada_producto_sin_repetir():
    html = mail_pedido.html_pedido_confirmado({"nombre": "Juan"}, PEDIDO, "https://thetechroomarg.com")

    assert html.count("Garantía Apple") == 1
    assert html.count("Garantía Motorola") == 1
    assert "Garantía Samsung" not in html
    assert "Fallas de fábrica o de funcionamiento interno." in html
    assert "https://thetechroomarg.com/#ttra-garantias" in html


def test_el_mail_firma_con_el_sticker_de_la_web():
    html = mail_pedido.html_pedido_confirmado({"nombre": "Juan"}, PEDIDO)

    assert ">HOLA<" in html and ">Vlad<" in html
    assert "vendo tecnología desde el año 2009." in html


def test_el_mail_escapa_lo_que_carga_el_cliente():
    pedido = {**PEDIDO, "direccion_entrega": "<script>x</script>"}
    html = mail_pedido.html_pedido_confirmado({"nombre": "<b>Ana</b>"}, pedido)

    assert "<script>x</script>" not in html
    assert "<b>Ana</b>" not in html


def test_un_pedido_sin_detalle_igual_lista_los_productos():
    html = mail_pedido.html_pedido_confirmado({}, {"id": "abc", "productos": ["AirPods Pro 2"], "total_usd": None})

    assert "AirPods Pro 2" in html
    assert "¡Gracias por tu compra!" in html
    assert "Total · Dólares" not in html


def test_notificar_no_rompe_si_el_mail_falla(monkeypatch):
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({"id": "c1", "nombre": "Juan", "email": "juan@x.com"}).execute()

    def falla(*args, **kwargs):
        raise RuntimeError("Resend caído")

    monkeypatch.setattr(mail_pedido, "enviar_email", falla)
    assert mail_pedido.notificar_pedido(fake, "c1", PEDIDO) is False


def test_notificar_sin_email_no_manda(monkeypatch):
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({"id": "c1", "nombre": "Juan"}).execute()
    enviados = []
    monkeypatch.setattr(mail_pedido, "enviar_email", lambda *a, **k: enviados.append(a))

    assert mail_pedido.notificar_pedido(fake, "c1", PEDIDO) is False
    assert enviados == []


def test_confirmar_un_pedido_en_la_web_le_manda_el_mail_al_cliente(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [{"nombre": "iPhone 13", "usd": 500, "colores": ["Negro"]}])
    monkeypatch.setattr(
        appmod.entregas, "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    enviados = []
    monkeypatch.setattr(mail_pedido, "enviar_email", lambda destino, asunto, html, **k: enviados.append((destino, asunto, html)))
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba"})

    r = c.post("/api/pedidos", json={
        "productos": ["iPhone 13 (Negro)"],
        "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{"nombre": "iPhone 13", "color": "Negro", "cantidad": 2, "usd_unitario": 500, "usd_subtotal": 1000}],
        "total_usd": 990,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert len(enviados) == 1
    destino, asunto, html = enviados[0]
    assert destino == "juan@x.com"
    assert asunto == f"Pedido confirmado #{mail_pedido.numero_pedido(pedido)} — The Tech Room Arg"
    assert "iPhone 13" in html and "U$D 990" in html and "Garantía Apple" in html
    assert "proveedor" not in html.lower()


def test_los_cinco_precios_salen_con_las_mismas_cuentas_que_la_web():
    # Moto Edge 50 en productos.json: usd 380, pesos 594.700, transferencia 613.093.
    assert mail_pedido.precios(380, 1565) == [
        ("U$D contado", "U$D 380"),
        ("Transf. USA", "U$D 390"),
        ("USDT", "USDT 384"),
        ("Pesos contado", "$ 594.700"),
        ("Pesos transf.", "$ 613.093"),
    ]


def test_el_detalle_muestra_los_cinco_precios_de_cada_producto_y_del_total():
    html = mail_pedido.html_pedido_confirmado({"nombre": "Juan"}, PEDIDO, cotizacion=1565)

    for etiqueta in ("U$D contado<", "Transf. USA<", "USDT<", "Pesos contado<", "Pesos transf.<"):
        assert html.count(etiqueta) == 3  # dos productos + el total
    assert "$ 594.700" in html and "$ 613.093" in html
    assert "$ 3.051.750" in html  # total U$D 1.950 en pesos
    assert "dólar a $ 1.565" in html


def test_agregar_al_pedido_del_mismo_dia_manda_correccion_de_pedido(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [
        {"nombre": "iPhone 13", "usd": 500, "colores": ["Negro"]},
        {"nombre": "AirPods 4", "usd": 150},
    ])
    monkeypatch.setattr(
        appmod.entregas, "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    enviados = []
    monkeypatch.setattr(mail_pedido, "enviar_email", lambda destino, asunto, html, **k: enviados.append((asunto, html)))
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba"})
    base = {"fecha_entrega": "2026-08-24", "direccion_entrega": "Av. Colón 123, Córdoba"}

    c.post("/api/pedidos", json={**base, "productos": ["iPhone 13 (Negro)"], "total_usd": 500, "detalle": [
        {"nombre": "iPhone 13", "color": "Negro", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500}]})
    c.post("/api/pedidos", json={**base, "productos": ["AirPods 4"], "total_usd": 150, "detalle": [
        {"nombre": "AirPods 4", "cantidad": 1, "usd_unitario": 150, "usd_subtotal": 150}]})

    pedidos = fake.table("pedidos").select("*").execute().data
    assert len(pedidos) == 1
    numero = mail_pedido.numero_pedido(pedidos[0])
    assert [asunto for asunto, _ in enviados] == [
        f"Pedido confirmado #{numero} — The Tech Room Arg",
        f"Corrección de Pedido #{numero} — The Tech Room Arg",
    ]
    correccion = enviados[1][1]
    assert "iPhone 13" in correccion and "AirPods 4" in correccion
    assert correccion.count("+ Agregado") == 1
    assert correccion.index("+ Agregado") > correccion.index("iPhone 13")
    assert "U$D 650" in correccion


def test_un_pedido_nuevo_no_es_correccion():
    carga = {"id": "p1", "detalle": [{"nombre": "iPhone 13", "cantidad": 1}]}
    assert not mail_pedido._es_correccion(dict(carga), carga)
    assert mail_pedido._es_correccion(
        {"id": "p1", "detalle": [{"nombre": "iPhone 13", "cantidad": 2}]}, carga)
