import itertools

from tests.fakes_supabase import FakeSupabaseClient
from web import cupones, fidelidad, referidos

_ids = itertools.count(1)


def _alta(fake, id_, referido_por=None, tipo_cliente="minorista", apellido="X"):
    fake.table("clientes").insert({
        "id": id_, "nombre": id_.capitalize(), "apellido": apellido, "tipo_cliente": tipo_cliente,
        "codigo_referido": None, "referido_por": referido_por, "referido_premiado_en": None,
        "referidos_codigo_premio": None, "referido_premio_codigo": None,
        "sellos_fidelidad": 0, "fidelidad_ultimo_codigo": None,
        "red_saldo_usd": 0, "red_fraccion_usd": 0,
    }).execute()
    return id_


def _compra(fake, cliente_id):
    """Simula una venta concretada (recibo enviado) y acredita la cadena."""
    pedido_id = f"pedido-{next(_ids)}"
    fake.table("pedidos").insert({
        "id": pedido_id, "cliente_id": cliente_id, "recibo_enviado_en": "2026-10-02T12:00:00+00:00",
    }).execute()
    return referidos.acreditar_por_compra(fake, cliente_id, pedido_id)


def _leer(fake, id_):
    return fake.table("clientes").select("*").eq("id", id_).execute().data[0]


def _saldo(fake, id_):
    return referidos.resumen(fake, id_)["saldo_usd"]


def test_codigo_personal_es_estable():
    fake = FakeSupabaseClient()
    _alta(fake, "ana")
    codigo = referidos.obtener_o_crear_codigo(fake, "ana")
    assert codigo and referidos.obtener_o_crear_codigo(fake, "ana") == codigo
    assert referidos.resolver_referente(fake, codigo.lower()) == "ana"
    assert referidos.resolver_referente(fake, "NOEXISTE") is None


def test_ejemplo_de_vladimir_juan_luis_pedro():
    fake = FakeSupabaseClient()
    _alta(fake, "juan")
    _alta(fake, "luis", referido_por="juan")
    _alta(fake, "pedro", referido_por="luis")
    _alta(fake, "ana", referido_por="pedro")

    _compra(fake, "luis")       # Juan +5
    _compra(fake, "pedro")      # Luis +5, Juan +2.50
    _compra(fake, "ana")        # Pedro +5, Luis +2.50, Juan +1.25

    assert _saldo(fake, "juan") == 8.75
    assert _saldo(fake, "luis") == 7.5
    assert _saldo(fake, "pedro") == 5


def test_compra_repetida_paga_la_mitad_y_va_a_la_bolsa_de_red():
    fake = FakeSupabaseClient()
    _alta(fake, "juan")
    _alta(fake, "luis", referido_por="juan")
    _compra(fake, "luis")   # 5 directo
    _compra(fake, "luis")   # 2.50 a la red, no otros 5
    _compra(fake, "luis")   # 1.25

    assert _saldo(fake, "juan") == 8.75
    assert _leer(fake, "juan")["red_saldo_usd"] == 3.75


def test_bolsa_de_red_nunca_pasa_de_15():
    fake = FakeSupabaseClient()
    _alta(fake, "juan")
    _alta(fake, "luis", referido_por="juan")
    # 20 nietos que compran: 20 x 2.50 = 50, pero la bolsa de red topea en 15.
    for i in range(20):
        _alta(fake, f"nieto{i}", referido_por="luis")
        _compra(fake, f"nieto{i}")

    juan = _leer(fake, "juan")
    assert juan["red_saldo_usd"] == 15
    assert _saldo(fake, "juan") == 15
    # Los directos no tienen tope: Luis tiene 20 x 5.
    assert _saldo(fake, "luis") == 100


def test_al_gastar_el_cupon_la_bolsa_de_red_vuelve_a_juntar():
    fake = FakeSupabaseClient()
    _alta(fake, "juan")
    _alta(fake, "luis", referido_por="juan")
    _alta(fake, "pedro", referido_por="luis")
    _compra(fake, "pedro")      # Juan +2.50 de red
    codigo = _leer(fake, "juan")["referidos_codigo_premio"]
    fake.table("pedidos").insert({"id": "pedido-juan", "cliente_id": "juan"}).execute()
    fake.table("codigos_descuento").update({"reservado_pedido_id": "pedido-juan"}).eq("code", codigo).execute()

    for fila in cupones.consumir_reservados(fake, "pedido-juan"):
        referidos.marcar_premio_usado(fake, fila["cliente_id"], fila["code"])

    assert _leer(fake, "juan")["red_saldo_usd"] == 0
    assert _saldo(fake, "juan") == 0
    _compra(fake, "pedro")      # 2da compra de Pedro: Juan (2 niveles) +5/2/2 = 1.25
    assert _saldo(fake, "juan") == 1.25


def test_fracciones_de_centavo_no_se_pierden():
    fake = FakeSupabaseClient()
    # Cadena larga: el de arriba de todo recibe fracciones de centavo.
    anterior = _alta(fake, "n0")
    for i in range(1, 12):
        anterior = _alta(fake, f"n{i}", referido_por=anterior)
    _compra(fake, "n11")
    tope = _leer(fake, "n0")
    # n0 está a 11 niveles: 5/2^10 = 0.0048828 -> todavía no completa un centavo.
    assert _saldo(fake, "n0") == 0
    assert round(tope["red_fraccion_usd"], 6) == round(5 / 2 ** 10, 6)
    # Dos compras más de gente nueva a esa distancia completan el centavo.
    for extra in ("e1", "e2"):
        _alta(fake, extra, referido_por="n10")
        _compra(fake, extra)
    assert _saldo(fake, "n0") == 0.01


def test_mismo_pedido_no_paga_dos_veces():
    fake = FakeSupabaseClient()
    _alta(fake, "juan")
    _alta(fake, "luis", referido_por="juan")
    fake.table("pedidos").insert({"id": "p1", "cliente_id": "luis", "recibo_enviado_en": "2026-10-02"}).execute()
    referidos.acreditar_por_compra(fake, "luis", "p1")
    referidos.acreditar_por_compra(fake, "luis", "p1")
    assert _saldo(fake, "juan") == 5


def test_mayorista_no_gana_pero_la_cadena_sigue():
    fake = FakeSupabaseClient()
    _alta(fake, "juan")
    _alta(fake, "mayo", referido_por="juan", tipo_cliente="mayorista")
    _alta(fake, "luis", referido_por="mayo")
    _compra(fake, "luis")
    assert _saldo(fake, "mayo") == 0
    assert _saldo(fake, "juan") == 2.5


def test_sin_padrino_no_hay_premio():
    fake = FakeSupabaseClient()
    _alta(fake, "solo")
    assert _compra(fake, "solo") == []
    assert fake.table("codigos_descuento").select("*").execute().data == []


def test_premio_de_referido_se_suma_al_de_fidelidad_pendiente():
    fake = FakeSupabaseClient()
    _alta(fake, "ana")
    fake.table("clientes").update({"sellos_fidelidad": 4}).eq("id", "ana").execute()
    codigo_fidelidad = fidelidad.registrar_entrega_completada(fake, "ana")["codigo_emitido"]
    _alta(fake, "beto", referido_por="ana")
    _compra(fake, "beto")
    assert _leer(fake, "ana")["referidos_codigo_premio"] == codigo_fidelidad
    assert _saldo(fake, "ana") == 25


def test_arbol_muestra_solo_quienes_compraron_con_nombre_e_inicial():
    fake = FakeSupabaseClient()
    _alta(fake, "juan")
    _alta(fake, "luis", referido_por="juan", apellido="Gómez")
    _alta(fake, "mudo", referido_por="luis")          # se registró, no compró
    _alta(fake, "pedro", referido_por="mudo", apellido="Ruiz")
    _alta(fake, "nadie", referido_por="juan")         # no compró
    _compra(fake, "luis")
    _compra(fake, "pedro")

    resumen = referidos.resumen(fake, "juan")
    # Pedro cuelga de Luis aunque "Mudo" (que no compró) esté en el medio.
    assert resumen["arbol"] == [{"nombre": "Luis G.", "hijos": [{"nombre": "Pedro R.", "hijos": []}]}]
    assert resumen["personas_en_red"] == 2
    assert "pedido" not in str(resumen["arbol"])
