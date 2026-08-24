from datetime import datetime

from zoneinfo import ZoneInfo

from web import entregas


TZ = ZoneInfo("America/Argentina/Cordoba")


def _fechas(ahora):
    return [opcion["fecha"] for opcion in entregas.opciones_entrega(ahora)]


def test_lunes_antes_del_corte_ofrece_hoy_manana_y_pasado():
    ahora = datetime(2026, 8, 24, 16, 29, tzinfo=TZ)

    assert _fechas(ahora) == ["2026-08-24", "2026-08-25", "2026-08-26"]


def test_lunes_despues_del_corte_ofrece_solo_manana_y_pasado():
    ahora = datetime(2026, 8, 24, 16, 31, tzinfo=TZ)

    assert _fechas(ahora) == ["2026-08-25", "2026-08-26"]


def test_viernes_despues_del_corte_programa_lunes_y_pide_confirmacion():
    ahora = datetime(2026, 8, 28, 16, 31, tzinfo=TZ)

    opciones = entregas.opciones_entrega(ahora)

    assert _fechas(ahora) == ["2026-08-31"]
    assert opciones[0]["requiere_confirmacion"] is True


def test_viernes_antes_del_corte_ofrece_viernes_o_sabado():
    ahora = datetime(2026, 8, 28, 16, 29, tzinfo=TZ)

    assert _fechas(ahora) == ["2026-08-28", "2026-08-29"]


def test_fin_de_semana_programa_directamente_lunes():
    sabado = datetime(2026, 8, 29, 11, 0, tzinfo=TZ)
    domingo = datetime(2026, 8, 30, 11, 0, tzinfo=TZ)

    assert _fechas(sabado) == ["2026-08-31"]
    assert _fechas(domingo) == ["2026-08-31"]
