import pytest

from tests.fakes_supabase import FakeSupabaseClient
from web.mailing import campanias


def manifiesto():
    return {
        "brief": "premium minimalista",
        "asunto": "Novedades TTRA",
        "preheader": "Equipos seleccionados",
        "productos": [{"nombre": "IPHONE 16 128GB", "usd": 800, "pesos": 1252000}],
        "html": "<html>preview</html>",
        "asset_url": "https://thetechroomarg.com/mailing/assets/abc/sha.jpg",
        "asset_sha256": "a" * 64,
    }


def test_crear_version_empieza_previsualizada_y_es_inmutable():
    fake = FakeSupabaseClient()
    fila = campanias.crear_version(fake, manifiesto())
    assert fila["estado"] == "previsualizado"
    assert fila["version"] == 1
    assert campanias.obtener_version(fake, fila["id"])["manifest"]["asunto"] == "Novedades TTRA"


def test_solo_una_aprobacion_atomica_puede_ganar():
    fake = FakeSupabaseClient()
    fila = campanias.crear_version(fake, manifiesto())
    aprobada = campanias.transicionar(fake, fila["id"], "previsualizado", "aprobado")
    assert aprobada["estado"] == "aprobado"
    with pytest.raises(campanias.InvalidTransition):
        campanias.transicionar(fake, fila["id"], "previsualizado", "aprobado")


def test_transicion_rechaza_salto_de_estado():
    fake = FakeSupabaseClient()
    fila = campanias.crear_version(fake, manifiesto())
    with pytest.raises(campanias.InvalidTransition):
        campanias.transicionar(fake, fila["id"], "previsualizado", "enviado")


def test_regenerar_crea_version_nueva_sin_mutar_la_anterior():
    fake = FakeSupabaseClient()
    primera = campanias.crear_version(fake, manifiesto())
    segunda_manifest = {**manifiesto(), "parent_id": primera["id"], "brief": "más contraste"}
    segunda = campanias.crear_version(fake, segunda_manifest)
    assert segunda["version"] == 2
    assert campanias.obtener_version(fake, primera["id"])["manifest"]["brief"] == "premium minimalista"
