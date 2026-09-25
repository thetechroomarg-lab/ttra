from tests.fakes_supabase import FakeSupabaseClient
from web import fidelidad


def _cliente(fake, sellos=0, codigo=None):
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Juan", "apellido": "Pérez",
        "sellos_fidelidad": sellos, "fidelidad_ultimo_codigo": codigo,
    }).execute()
    return "cliente-1"


def _leer(fake, cliente_id):
    return fake.table("clientes").select("*").eq("id", cliente_id).execute().data[0]


def test_suma_un_sello_sin_llegar_a_cinco():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=1)

    resultado = fidelidad.registrar_entrega_completada(fake, cliente_id, ["iPhone 13"])

    cliente = _leer(fake, cliente_id)
    assert cliente["sellos_fidelidad"] == 2
    assert cliente["fidelidad_ultimo_codigo"] is None
    assert resultado == {"sellos_fidelidad": 2, "codigo_emitido": None}


def test_cinco_entregas_seguidas_emiten_el_codigo_recien_en_la_quinta():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=0)

    resultados = [
        fidelidad.registrar_entrega_completada(fake, cliente_id, ["iPhone 13"])
        for _ in range(5)
    ]

    assert [r["codigo_emitido"] is not None for r in resultados] == [False] * 4 + [True]
    assert fake.table("codigos_descuento").select("*").execute().data.__len__() == 1


def test_al_llegar_a_cinco_emite_codigo_de_veinte_dolares_y_no_resetea():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=4)

    resultado = fidelidad.registrar_entrega_completada(fake, cliente_id, ["iPhone 13", "iPhone 14"])

    cliente = _leer(fake, cliente_id)
    assert cliente["sellos_fidelidad"] == 5
    assert cliente["fidelidad_ultimo_codigo"] == resultado["codigo_emitido"]
    codigos = fake.table("codigos_descuento").select("*").eq("code", resultado["codigo_emitido"]).execute().data
    assert codigos[0] == {
        "cliente_id": cliente_id,
        "code": resultado["codigo_emitido"],
        "productos": ["iPhone 13", "iPhone 14"],
        "descuento_usd": 20,
        "activo": True,
    }


def test_no_suma_de_largo_si_ya_tiene_un_codigo_pendiente():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=5, codigo="TTRA-PENDIENTE")

    resultado = fidelidad.registrar_entrega_completada(fake, cliente_id, ["iPhone 13"])

    cliente = _leer(fake, cliente_id)
    assert cliente["sellos_fidelidad"] == 5
    assert cliente["fidelidad_ultimo_codigo"] == "TTRA-PENDIENTE"
    assert resultado is None


def test_cliente_inexistente_no_hace_nada():
    fake = FakeSupabaseClient()

    assert fidelidad.registrar_entrega_completada(fake, "no-existe", ["iPhone 13"]) is None
    assert fake.table("codigos_descuento").select("*").execute().data == []


def test_marcar_codigo_usado_resetea_el_ciclo_si_coincide():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=5, codigo="TTRA-ABC123")

    reseteo = fidelidad.marcar_codigo_fidelidad_usado(fake, cliente_id, "TTRA-ABC123")

    cliente = _leer(fake, cliente_id)
    assert reseteo is True
    assert cliente["sellos_fidelidad"] == 0
    assert cliente["fidelidad_ultimo_codigo"] is None


def test_marcar_codigo_usado_ignora_codigos_que_no_son_de_fidelidad():
    fake = FakeSupabaseClient()
    cliente_id = _cliente(fake, sellos=5, codigo="TTRA-ABC123")

    reseteo = fidelidad.marcar_codigo_fidelidad_usado(fake, cliente_id, "TTRA-MAILING")

    cliente = _leer(fake, cliente_id)
    assert reseteo is False
    assert cliente["sellos_fidelidad"] == 5
    assert cliente["fidelidad_ultimo_codigo"] == "TTRA-ABC123"
