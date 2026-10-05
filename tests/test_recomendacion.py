from datetime import date

from tests.fakes_supabase import FakeSupabaseClient
from web import email_util
from web.mailing import recomendacion

HOY = date(2026, 10, 5)

CATALOGO = [
    {"nombre": "IPHONE 16 128GB", "categoria": "Apple - iPhone", "usd": 900, "pesos": 1, "transferencia": 1},
    {"nombre": "IPHONE 13 128GB USADO", "categoria": "Apple - iPhone Usado", "usd": 400, "pesos": 1, "transferencia": 1},
    {"nombre": "Apple AirPods 4", "categoria": "Apple - AirPods", "usd": 155, "pesos": 1, "transferencia": 1},
    {"nombre": "AIRPODS PRO 2DA GENERACIÓN", "categoria": "Apple - AirPods", "usd": 260, "pesos": 1, "transferencia": 1},
    {"nombre": "Apple Watch SE 3 40MM GPS", "categoria": "Apple - Watch", "usd": 320, "pesos": 1, "transferencia": 1},
    {"nombre": "Airtag x 4", "categoria": "Otros", "usd": 160, "pesos": 1, "transferencia": 1},
    {"nombre": "Belkin Magsafe 3-in-1 Arbolito", "categoria": "Otros", "usd": 230, "pesos": 1, "transferencia": 1},
    {"nombre": "Cable Original Apple 1 metro USB-C a USB-C", "categoria": "Otros", "usd": 50, "pesos": 1, "transferencia": 1},
    {"nombre": "CARGADOR APPLE 20w ORIGINAL TIPO C", "categoria": "Otros", "usd": 55, "pesos": 1, "transferencia": 1},
    {"nombre": "Parlante JBL Charge 6", "categoria": "Otros", "usd": 185, "pesos": 1, "transferencia": 1},
    {"nombre": "Magic Mouse 2", "categoria": "Otros", "usd": 160, "pesos": 1, "transferencia": 1},
    {"nombre": "NOAX Adaptador Noax Connect Hub 8 en 1 HB8", "categoria": "Otros", "usd": 40, "pesos": 1, "transferencia": 1},
    {"nombre": "Generico Mochila Antirrobo 35L", "categoria": "Otros", "usd": 50, "pesos": 1, "transferencia": 1},
    {"nombre": "Haylou Solar 5", "categoria": "Otros", "usd": 75, "pesos": 1, "transferencia": 1},
    {"nombre": "QCY T13 ANC2", "categoria": "Otros", "usd": 60, "pesos": 1, "transferencia": 1},
    {"nombre": "MICRO SD 32GB CLASE 10", "categoria": "Otros", "usd": 40, "pesos": 1, "transferencia": 1},
    {"nombre": "Samsung Galaxy A56 8GB 256GB", "categoria": "Samsung", "usd": 450, "pesos": 1, "transferencia": 1},
    {"nombre": "Macbook Air 13 M5 10CPU 8GPU 512GB 16GB", "categoria": "Mac", "usd": 1475, "pesos": 1, "transferencia": 1},
]


def _cliente(fake, id_="cliente-1", email="juan@x.com", no_mailing=False):
    fake.table("clientes").insert({
        "id": id_, "nombre": "Juan", "apellido": "Pérez", "email": email, "no_mailing": no_mailing,
    }).execute()


def _pedido(fake, recibo_enviado_en, cliente_id="cliente-1", recomendacion_enviado_en=None,
            id_="pedido-1", producto="IPHONE 16 128GB"):
    fake.table("pedidos").insert({
        "id": id_, "cliente_id": cliente_id,
        "productos": [producto],
        "detalle": [{"nombre": producto, "cantidad": 1}],
        "recibo_enviado_en": recibo_enviado_en,
        "recomendacion_enviado_en": recomendacion_enviado_en,
    }).execute()


def _ids(pedidos):
    return [p["id"] for p in pedidos]


def _nombres(productos):
    return [p["nombre"] for p in productos]


def test_incluye_recibos_de_hace_treinta_dias():
    fake = FakeSupabaseClient()
    _pedido(fake, "2026-09-05T15:00:00+00:00")

    assert _ids(recomendacion.pedidos_para_recomendar(fake, hoy=HOY)) == ["pedido-1"]


def test_no_incluye_recibos_de_hace_veintinueve_dias():
    fake = FakeSupabaseClient()
    _pedido(fake, "2026-09-06T15:00:00+00:00")

    assert recomendacion.pedidos_para_recomendar(fake, hoy=HOY) == []


def test_cuenta_los_dias_en_hora_argentina():
    fake = FakeSupabaseClient()
    # 6/9 01:30 UTC = 5/9 22:30 en Argentina: ya pasaron 30 días.
    _pedido(fake, "2026-09-06T01:30:00+00:00")

    assert _ids(recomendacion.pedidos_para_recomendar(fake, hoy=HOY)) == ["pedido-1"]


def test_no_incluye_recibos_viejos():
    fake = FakeSupabaseClient()
    _pedido(fake, "2026-08-20T15:00:00+00:00")

    assert recomendacion.pedidos_para_recomendar(fake, hoy=HOY) == []


def test_excluye_los_ya_recomendados_y_los_sin_cuenta_ni_recibo():
    fake = FakeSupabaseClient()
    _pedido(fake, "2026-09-05T15:00:00+00:00", recomendacion_enviado_en="2026-10-04T09:00:00+00:00")
    _pedido(fake, "2026-09-05T15:00:00+00:00", cliente_id=None, id_="pedido-2")
    _pedido(fake, None, id_="pedido-3")

    assert recomendacion.pedidos_para_recomendar(fake, hoy=HOY) == []


def test_recomienda_cinco_productos():
    pedido = {"id": "p", "productos": ["IPHONE 16 128GB"], "detalle": []}

    assert len(recomendacion.recomendar(pedido, CATALOGO)) == 5


def test_a_un_iphone_le_recomienda_complementos_apple():
    pedido = {"id": "p", "detalle": [{"nombre": "IPHONE 16 128GB"}]}

    nombres = _nombres(recomendacion.recomendar(pedido, CATALOGO))

    assert "Apple AirPods 4" in nombres or "AIRPODS PRO 2DA GENERACIÓN" in nombres
    assert "Apple Watch SE 3 40MM GPS" in nombres
    assert "Airtag x 4" in nombres


def test_a_una_mac_le_recomienda_perifericos():
    pedido = {"id": "p", "detalle": [{"nombre": "Macbook Air 13 M5 10CPU 8GPU 512GB 16GB"}]}

    nombres = _nombres(recomendacion.recomendar(pedido, CATALOGO))

    assert "Magic Mouse 2" in nombres
    assert "NOAX Adaptador Noax Connect Hub 8 en 1 HB8" in nombres


def test_nunca_recomienda_usados_cargadores_ni_lo_ya_comprado():
    for producto in ("IPHONE 16 128GB", "Samsung Galaxy A56 8GB 256GB", "Producto que ya no existe"):
        pedido = {"id": producto, "detalle": [{"nombre": producto}, {"nombre": "Apple AirPods 4"}]}

        nombres = _nombres(recomendacion.recomendar(pedido, CATALOGO))

        assert len(nombres) == 5
        assert len(set(nombres)) == 5
        assert producto not in nombres
        assert "Apple AirPods 4" not in nombres
        assert not any("USADO" in n.upper() or "CARGADOR" in n.upper() for n in nombres)


def test_no_recomienda_otro_equipo_de_la_misma_familia():
    pedido = {"id": "p", "detalle": [{"nombre": "IPHONE 16 128GB"}]}

    nombres = _nombres(recomendacion.recomendar(pedido, CATALOGO))

    assert not any("IPHONE" in n.upper() for n in nombres)


def test_la_seleccion_es_estable_para_el_mismo_pedido():
    pedido = {"id": "p", "detalle": [{"nombre": "Samsung Galaxy A56 8GB 256GB"}]}

    assert recomendacion.recomendar(pedido, CATALOGO) == recomendacion.recomendar(pedido, CATALOGO)


def test_envia_y_marca_el_pedido():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido(fake, "2026-09-05T15:00:00+00:00")
    enviados = []

    resultado = recomendacion.enviar_recomendaciones(
        fake, CATALOGO, hoy=HOY,
        enviar_email_fn=lambda *a, **k: enviados.append((a, k)),
    )

    assert resultado == {"enviados": 1, "fallidos": 0}
    destinatario, asunto, html = enviados[0][0]
    assert destinatario == "juan@x.com"
    assert "IPHONE 16 128GB" in html
    assert "/mailing/baja/cliente-1" in html
    assert fake.table("pedidos").select("*").execute().data[0]["recomendacion_enviado_en"]


def test_respeta_la_baja_de_mailing_pero_marca_el_pedido():
    fake = FakeSupabaseClient()
    _cliente(fake, no_mailing=True)
    _pedido(fake, "2026-09-05T15:00:00+00:00")
    enviados = []

    resultado = recomendacion.enviar_recomendaciones(
        fake, CATALOGO, hoy=HOY, enviar_email_fn=lambda *a, **k: enviados.append(a),
    )

    assert enviados == []
    assert resultado == {"enviados": 0, "fallidos": 0}
    assert fake.table("pedidos").select("*").execute().data[0]["recomendacion_enviado_en"]


def test_si_falla_el_envio_no_marca_para_reintentar():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido(fake, "2026-09-05T15:00:00+00:00")

    def falla(*a, **k):
        raise email_util.EnvioEmailError("boom")

    resultado = recomendacion.enviar_recomendaciones(fake, CATALOGO, hoy=HOY, enviar_email_fn=falla)

    assert resultado == {"enviados": 0, "fallidos": 1}
    assert not fake.table("pedidos").select("*").execute().data[0]["recomendacion_enviado_en"]


def test_no_corre_con_catalogo_vacio():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido(fake, "2026-09-05T15:00:00+00:00")

    try:
        recomendacion.enviar_recomendaciones(fake, [], hoy=HOY, enviar_email_fn=lambda *a, **k: None)
    except ValueError:
        pass
    else:
        raise AssertionError("debería negarse a mandar sin catálogo")


def test_no_recomienda_nada_mas_caro_que_lo_que_compro():
    pedido = {"id": "p", "detalle": [{"nombre": "Samsung Galaxy A56 8GB 256GB"}]}
    catalogo = CATALOGO + [
        {"nombre": "MONITOR GAMER 55", "categoria": "Otros", "usd": 2215, "pesos": 1, "transferencia": 1},
    ]

    productos = recomendacion.recomendar(pedido, catalogo)

    assert all(p["usd"] <= 450 for p in productos)


def test_a_una_consola_le_recomienda_joysticks():
    catalogo = CATALOGO + [
        {"nombre": "PlayStation 5 Slim 825GB Digital", "categoria": "Otros", "usd": 770, "pesos": 1, "transferencia": 1},
        {"nombre": "Joystick PlayStation 5 Original", "categoria": "Otros", "usd": 115, "pesos": 1, "transferencia": 1},
    ]
    pedido = {"id": "p", "detalle": [{"nombre": "PlayStation 5 Slim 825GB Digital"}]}

    nombres = _nombres(recomendacion.recomendar(pedido, catalogo))

    assert "Joystick PlayStation 5 Original" in nombres
