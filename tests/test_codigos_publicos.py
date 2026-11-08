from datetime import datetime, timezone

import pytest

from tests.fakes_supabase import FakeSupabaseClient
from web import codigos_publicos


def _fila(fake, codigo):
    filas = fake.table("codigos_descuento").select("*").eq("code", codigo).execute().data
    return filas[0] if filas else None


def test_activar_crea_el_codigo_publico():
    fake = FakeSupabaseClient()
    r = codigos_publicos.activar(fake, "graciasbobis", 20)
    fila = _fila(fake, "GRACIASBOBIS")
    assert r == {"codigo": "GRACIASBOBIS", "monto_usd": 20, "archivado": None}
    assert fila["cliente_id"] is None and fila["activo"] and fila["tope_total_usd"] == 20
    assert codigos_publicos.estado(fake, "GRACIASBOBIS")["estado"] == "disponible"


def test_reactivar_un_codigo_usado_lo_archiva_y_crea_uno_nuevo():
    fake = FakeSupabaseClient()
    codigos_publicos.activar(fake, "GRACIASBOBIS", 20)
    fake.table("pedidos").insert({"id": "p1", "cliente_id": "c1", "productos": []}).execute()
    fake.table("codigos_descuento").update({"reservado_pedido_id": "p1"}).eq("code", "GRACIASBOBIS").execute()
    assert codigos_publicos.estado(fake, "GRACIASBOBIS")["estado"] == "reservado"

    ahora = datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc)
    r = codigos_publicos.activar(fake, "GRACIASBOBIS", 15, ahora=ahora)

    assert r["archivado"] == "GRACIASBOBIS-20261120-150000"
    assert _fila(fake, "GRACIASBOBIS-20261120-150000")["reservado_pedido_id"] == "p1"
    nuevo = _fila(fake, "GRACIASBOBIS")
    assert nuevo["tope_total_usd"] == 15 and not nuevo.get("reservado_pedido_id")


def test_reactivar_un_codigo_sin_usar_reutiliza_la_fila():
    fake = FakeSupabaseClient()
    codigos_publicos.activar(fake, "GRACIASBOBIS", 20)
    r = codigos_publicos.activar(fake, "GRACIASBOBIS", 25)
    assert r["archivado"] is None
    assert len(fake.table("codigos_descuento").select("*").execute().data) == 1
    assert _fila(fake, "GRACIASBOBIS")["tope_total_usd"] == 25


def test_no_pisa_un_codigo_privado_de_cliente():
    fake = FakeSupabaseClient()
    fake.table("codigos_descuento").insert({"cliente_id": "c1", "code": "TTRA-X", "activo": True}).execute()
    with pytest.raises(ValueError):
        codigos_publicos.activar(fake, "TTRA-X", 20)
