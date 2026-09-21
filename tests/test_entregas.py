from datetime import datetime

from zoneinfo import ZoneInfo

from web import entregas


TZ = ZoneInfo("America/Argentina/Cordoba")


def _fechas(ahora):
    return [opcion["fecha"] for opcion in entregas.opciones_entrega(ahora)]


def test_lunes_antes_del_corte_ofrece_hoy_manana_y_pasado():
    ahora = datetime(2026, 8, 24, 16, 44, tzinfo=TZ)

    assert _fechas(ahora) == ["2026-08-24", "2026-08-25", "2026-08-26"]


def test_lunes_despues_del_corte_ofrece_solo_manana_y_pasado():
    ahora = datetime(2026, 8, 24, 16, 46, tzinfo=TZ)

    assert _fechas(ahora) == ["2026-08-25", "2026-08-26"]


def test_viernes_despues_del_corte_general_sigue_ofreciendo_el_sabado():
    ahora = datetime(2026, 8, 28, 16, 46, tzinfo=TZ)

    opciones = entregas.opciones_entrega(ahora)

    assert _fechas(ahora) == ["2026-08-29"]
    assert opciones[0]["requiere_confirmacion"] is False


def test_viernes_a_cualquier_hora_ofrece_sabado_sin_corte():
    # El viernes no tiene corte horario para pedir el sábado: a la noche
    # sigue ofreciendo la entrega del sábado (solo se cae la opción de
    # entrega el mismo viernes, por el corte general de las 16:45).
    ahora = datetime(2026, 8, 28, 23, 59, tzinfo=TZ)

    assert _fechas(ahora) == ["2026-08-29"]


def test_viernes_antes_del_corte_ofrece_viernes_o_sabado():
    ahora = datetime(2026, 8, 28, 16, 44, tzinfo=TZ)

    assert _fechas(ahora) == ["2026-08-28", "2026-08-29"]


def test_sabado_antes_de_las_10_ofrece_el_mismo_sabado():
    ahora = datetime(2026, 8, 29, 9, 59, tzinfo=TZ)

    assert _fechas(ahora) == ["2026-08-29", "2026-08-31"]


def test_sabado_despues_de_las_10_programa_directamente_lunes():
    ahora = datetime(2026, 8, 29, 10, 1, tzinfo=TZ)

    assert _fechas(ahora) == ["2026-08-31"]


def test_domingo_programa_directamente_lunes():
    domingo = datetime(2026, 8, 30, 11, 0, tzinfo=TZ)

    assert _fechas(domingo) == ["2026-08-31"]
