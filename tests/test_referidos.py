from tests.fakes_supabase import FakeSupabaseClient
from web import referidos


def _alta(fake, id_, tipo_cliente="minorista", referido_por=None):
    fake.table("clientes").insert({
        "id": id_, "nombre": id_, "apellido": "X", "tipo_cliente": tipo_cliente,
        "codigo_referido": None, "referido_por": referido_por,
        "referido_premiado_en": None, "referidos_codigo_premio": None, "referido_premio_codigo": None,
    }).execute()
    return id_


def _leer(fake, id_):
    return fake.table("clientes").select("*").eq("id", id_).execute().data[0]


def _cupon(fake, code):
    return fake.table("codigos_descuento").select("*").eq("code", code).execute().data[0]


def test_codigo_personal_es_estable():
    fake = FakeSupabaseClient()
    _alta(fake, "ana")
    codigo = referidos.obtener_o_crear_codigo(fake, "ana")
    assert codigo and referidos.obtener_o_crear_codigo(fake, "ana") == codigo
    assert referidos.resolver_referente(fake, codigo.lower()) == "ana"
    assert referidos.resolver_referente(fake, "NOEXISTE") is None


def test_primera_compra_del_referido_acredita_5_una_sola_vez():
    fake = FakeSupabaseClient()
    _alta(fake, "ana")
    _alta(fake, "beto", referido_por="ana")

    premio = referidos.acreditar_por_compra(fake, "beto")
    assert premio["saldo_usd"] == 5
    cupon = _cupon(fake, premio["codigo"])
    assert cupon["cliente_id"] == "ana"
    assert cupon["tope_total_usd"] == 5 and cupon["productos"] == []

    # Segunda compra del mismo referido: no suma nada.
    assert referidos.acreditar_por_compra(fake, "beto") is None
    assert _cupon(fake, premio["codigo"])["descuento_usd"] == 5


def test_varios_referidos_se_suman_en_el_mismo_cupon():
    fake = FakeSupabaseClient()
    _alta(fake, "ana")
    for nombre in ("beto", "caro", "dani"):
        _alta(fake, nombre, referido_por="ana")
        referidos.acreditar_por_compra(fake, nombre)

    codigo = _leer(fake, "ana")["referidos_codigo_premio"]
    cupon = _cupon(fake, codigo)
    assert cupon["descuento_usd"] == 15 and cupon["tope_total_usd"] == 15
    resumen = referidos.resumen(fake, "ana")
    assert resumen["saldo_usd"] == 15 and resumen["codigo_premio"] == codigo
    assert resumen["referidos_registrados"] == 3 and resumen["referidos_con_compra"] == 3
    assert [p["nombre"] for p in resumen["pendientes"]] == ["beto X.", "caro X.", "dani X."]
    assert all(p["monto_usd"] == 5 for p in resumen["pendientes"])


def test_cupon_usado_arranca_uno_nuevo():
    fake = FakeSupabaseClient()
    _alta(fake, "ana")
    _alta(fake, "beto", referido_por="ana")
    _alta(fake, "caro", referido_por="ana")
    primero = referidos.acreditar_por_compra(fake, "beto")["codigo"]
    fake.table("codigos_descuento").update({"usado_en": "2026-10-02T12:00:00+00:00"}).eq("code", primero).execute()
    assert referidos.marcar_premio_usado(fake, "ana", primero)

    segundo = referidos.acreditar_por_compra(fake, "caro")
    assert segundo["codigo"] != primero and segundo["saldo_usd"] == 5
    # Beto ya se usó: solo Caro figura como descuento pendiente.
    assert [p["nombre"] for p in referidos.resumen(fake, "ana")["pendientes"]] == ["caro X."]


def test_sin_referente_o_referente_mayorista_no_hay_premio():
    fake = FakeSupabaseClient()
    _alta(fake, "solo")
    assert referidos.acreditar_por_compra(fake, "solo") is None

    _alta(fake, "mayo", tipo_cliente="mayorista")
    _alta(fake, "beto", referido_por="mayo")
    assert referidos.acreditar_por_compra(fake, "beto") is None
    assert fake.table("codigos_descuento").select("*").execute().data == []


def test_premio_de_referido_se_suma_al_de_fidelidad_pendiente():
    from web import fidelidad
    fake = FakeSupabaseClient()
    _alta(fake, "ana")
    fake.table("clientes").update({"sellos_fidelidad": 4, "fidelidad_ultimo_codigo": None}).eq("id", "ana").execute()
    codigo_fidelidad = fidelidad.registrar_entrega_completada(fake, "ana")["codigo_emitido"]
    _alta(fake, "beto", referido_por="ana")

    premio = referidos.acreditar_por_compra(fake, "beto")

    assert premio == {"codigo": codigo_fidelidad, "saldo_usd": 25}
    assert _cupon(fake, codigo_fidelidad)["tope_total_usd"] == 25
    assert _leer(fake, "ana")["referidos_codigo_premio"] == codigo_fidelidad


def test_premio_de_fidelidad_se_suma_al_de_referidos_pendiente_y_ambos_se_cierran():
    from web import fidelidad
    fake = FakeSupabaseClient()
    _alta(fake, "ana")
    _alta(fake, "beto", referido_por="ana")
    codigo = referidos.acreditar_por_compra(fake, "beto")["codigo"]
    fake.table("clientes").update({"sellos_fidelidad": 4}).eq("id", "ana").execute()

    resultado = fidelidad.registrar_entrega_completada(fake, "ana")

    assert resultado["codigo_emitido"] == codigo
    assert _cupon(fake, codigo)["descuento_usd"] == 25
    assert len(fake.table("codigos_descuento").select("*").execute().data) == 1
    # Al usarlo en un pedido se cierran los dos programas.
    assert fidelidad.marcar_codigo_fidelidad_usado(fake, "ana", codigo)
    assert referidos.marcar_premio_usado(fake, "ana", codigo)
    ana = _leer(fake, "ana")
    assert ana["sellos_fidelidad"] == 0 and ana["referidos_codigo_premio"] is None
