from datetime import date

from tests.fakes_supabase import FakeSupabaseClient
from web import email_util
from web.mailing import seguimiento

HOY = date(2026, 9, 25)


def _cliente(fake, id_="cliente-1", email="juan@x.com"):
    fake.table("clientes").insert({"id": id_, "nombre": "Juan", "apellido": "Pérez", "email": email}).execute()


def _pedido(fake, recibo_enviado_en, cliente_id="cliente-1", seguimiento_enviado_en=None, id_="pedido-1"):
    fake.table("pedidos").insert({
        "id": id_, "cliente_id": cliente_id,
        "productos": ["iPhone 13"],
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1}],
        "recibo_enviado_en": recibo_enviado_en,
        "seguimiento_enviado_en": seguimiento_enviado_en,
    }).execute()


def _ids(pedidos):
    return [p["id"] for p in pedidos]


def test_incluye_entregas_de_hace_siete_dias():
    fake = FakeSupabaseClient()
    _pedido(fake, "2026-09-18T15:00:00+00:00")

    assert _ids(seguimiento.pedidos_para_notificar(fake, hoy=HOY)) == ["pedido-1"]


def test_no_incluye_entregas_de_hace_seis_dias():
    fake = FakeSupabaseClient()
    _pedido(fake, "2026-09-19T15:00:00+00:00")

    assert seguimiento.pedidos_para_notificar(fake, hoy=HOY) == []


def test_cuenta_el_dia_de_entrega_en_hora_argentina():
    fake = FakeSupabaseClient()
    # 19/9 01:30 UTC = 18/9 22:30 en Argentina: ya pasaron 7 días.
    _pedido(fake, "2026-09-19T01:30:00+00:00")

    assert _ids(seguimiento.pedidos_para_notificar(fake, hoy=HOY)) == ["pedido-1"]


def test_sigue_incluyendo_un_pedido_pendiente_al_dia_siguiente():
    fake = FakeSupabaseClient()
    _pedido(fake, "2026-09-17T15:00:00+00:00")

    assert _ids(seguimiento.pedidos_para_notificar(fake, hoy=HOY)) == ["pedido-1"]


def test_no_manda_seguimiento_a_entregas_viejas():
    fake = FakeSupabaseClient()
    _pedido(fake, "2026-09-01T15:00:00+00:00")

    assert seguimiento.pedidos_para_notificar(fake, hoy=HOY) == []


def test_excluye_los_ya_notificados_y_los_sin_cuenta():
    fake = FakeSupabaseClient()
    _pedido(fake, "2026-09-18T15:00:00+00:00", seguimiento_enviado_en="2026-09-25T09:00:00+00:00")
    _pedido(fake, "2026-09-18T15:00:00+00:00", cliente_id=None, id_="pedido-2")
    _pedido(fake, None, id_="pedido-3")

    assert seguimiento.pedidos_para_notificar(fake, hoy=HOY) == []


def test_enviar_marca_el_pedido_y_manda_con_reply_to():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido(fake, "2026-09-18T15:00:00+00:00")
    enviados = []

    resultado = seguimiento.enviar_seguimientos(
        fake, hoy=HOY, enviar_email_fn=lambda *a, **k: enviados.append((a, k)),
    )

    assert resultado == {"enviados": 1, "fallidos": 0}
    (destinatario, asunto, html), kwargs = enviados[0]
    assert destinatario == "juan@x.com"
    assert "iPhone 13" in html and "Juan" in html
    assert kwargs["reply_to"] == seguimiento.REPLY_TO_SEGUIMIENTO
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    assert pedido["seguimiento_enviado_en"]


def test_correr_dos_veces_el_mismo_dia_manda_un_solo_mail():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido(fake, "2026-09-18T15:00:00+00:00")
    enviados = []

    for _ in range(2):
        seguimiento.enviar_seguimientos(fake, hoy=HOY, enviar_email_fn=lambda *a, **k: enviados.append(a))

    assert len(enviados) == 1


def test_si_el_envio_falla_no_marca_el_pedido():
    fake = FakeSupabaseClient()
    _cliente(fake)
    _pedido(fake, "2026-09-18T15:00:00+00:00")

    def falla(*_a, **_k):
        raise email_util.EnvioEmailError("Resend caído")

    resultado = seguimiento.enviar_seguimientos(fake, hoy=HOY, enviar_email_fn=falla)

    assert resultado == {"enviados": 0, "fallidos": 1}
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    assert pedido["seguimiento_enviado_en"] is None


def test_escapa_el_nombre_del_cliente_en_el_html():
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({"id": "cliente-1", "nombre": "<b>Juan</b>", "email": "juan@x.com"}).execute()
    _pedido(fake, "2026-09-18T15:00:00+00:00")
    enviados = []

    seguimiento.enviar_seguimientos(fake, hoy=HOY, enviar_email_fn=lambda *a, **k: enviados.append(a))

    assert "<b>Juan</b>" not in enviados[0][2]
