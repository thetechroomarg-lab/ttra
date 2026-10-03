from tests.fakes_supabase import FakeSupabaseClient
from web import cupones


def _codigo(fake, **extra):
    fake.table("codigos_descuento").insert({
        "cliente_id": "c1", "code": "TTRA-X", "productos": [], "descuento_usd": 5, "activo": True, **extra,
    }).execute()
    return fake.table("codigos_descuento").select("*").eq("code", "TTRA-X").execute().data[0]


def test_reservado_para_un_pedido_en_curso_no_se_puede_volver_a_usar():
    fake = FakeSupabaseClient()
    fake.table("pedidos").insert({"id": "p1", "cliente_id": "c1"}).execute()
    fila = _codigo(fake, reservado_pedido_id="p1")
    assert cupones.reservado(fake, fila)
    assert not cupones.disponible(fake, fila)


def test_si_el_pedido_se_borra_el_cliente_conserva_el_descuento():
    fake = FakeSupabaseClient()
    fake.table("pedidos").insert({"id": "p1", "cliente_id": "c1", "borrado_en": "2026-10-02T12:00:00+00:00"}).execute()
    fila = _codigo(fake, reservado_pedido_id="p1")
    assert cupones.disponible(fake, fila)


def test_consumir_reservados_marca_usado_una_sola_vez():
    fake = FakeSupabaseClient()
    fake.table("pedidos").insert({"id": "p1", "cliente_id": "c1"}).execute()
    _codigo(fake, reservado_pedido_id="p1")
    assert [f["code"] for f in cupones.consumir_reservados(fake, "p1")] == ["TTRA-X"]
    assert cupones.consumir_reservados(fake, "p1") == []
    assert fake.table("codigos_descuento").select("*").execute().data[0]["usado_en"]
