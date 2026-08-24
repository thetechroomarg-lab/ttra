from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


ZONA_HORARIA = ZoneInfo("America/Argentina/Cordoba")
HORA_CORTE_MINUTOS = 16 * 60 + 30


def ahora_argentina():
    return datetime.now(ZONA_HORARIA)


def _opcion(fecha, requiere_confirmacion=False):
    return {
        "fecha": fecha.isoformat(),
        "requiere_confirmacion": requiere_confirmacion,
    }


def opciones_entrega(ahora=None):
    ahora = ahora or ahora_argentina()
    fecha_hoy = ahora.date()
    dia_semana = fecha_hoy.weekday()
    despues_del_corte = ahora.hour * 60 + ahora.minute >= HORA_CORTE_MINUTOS

    # Durante el fin de semana no hay entregas: todo se agenda al lunes.
    if dia_semana == 5:
        return [_opcion(fecha_hoy + timedelta(days=2))]
    if dia_semana == 6:
        return [_opcion(fecha_hoy + timedelta(days=1))]

    # El viernes posterior al corte no admite entrega el sábado.
    if dia_semana == 4 and despues_del_corte:
        return [_opcion(fecha_hoy + timedelta(days=3), requiere_confirmacion=True)]

    # El viernes previo al corte conserva las dos últimas entregas posibles.
    if dia_semana == 4:
        return [_opcion(fecha_hoy), _opcion(fecha_hoy + timedelta(days=1))]

    inicio = fecha_hoy + timedelta(days=1) if despues_del_corte else fecha_hoy
    opciones = []
    candidata = inicio
    while len(opciones) < 3:
        if candidata.weekday() != 6:
            opciones.append(_opcion(candidata))
        candidata += timedelta(days=1)
    return opciones


def fecha_entrega_valida(fecha, ahora=None):
    return fecha.isoformat() in {opcion["fecha"] for opcion in opciones_entrega(ahora)}


def etiqueta_entrega(fecha_iso, ahora=None):
    ahora = ahora or ahora_argentina()
    fecha = datetime.fromisoformat(fecha_iso).date()
    dias = (fecha - ahora.date()).days
    prefijo = "HOY" if dias == 0 else "MAÑANA" if dias == 1 else "PASADO MAÑANA"
    meses = ("Ene.", "Feb.", "Mar.", "Abr.", "May.", "Jun.", "Jul.", "Ago.", "Sep.", "Oct.", "Nov.", "Dic.")
    return f"{prefijo} {fecha.day} de {meses[fecha.month - 1]}"
