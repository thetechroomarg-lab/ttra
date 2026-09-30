from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


ZONA_HORARIA = ZoneInfo("America/Argentina/Cordoba")
HORA_CORTE_MINUTOS = 16 * 60 + 45
# Corte propio para entrega en sábado: el viernes se puede pedir sin límite
# horario (el corte general de arriba no aplica para pedir el sábado), y el
# propio sábado se puede seguir pidiendo hasta esta hora.
HORA_CORTE_SABADO_MINUTOS = 10 * 60


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
    minutos_ahora = ahora.hour * 60 + ahora.minute
    despues_del_corte = minutos_ahora >= HORA_CORTE_MINUTOS

    # Sábado: se puede pedir para entrega ese mismo sábado hasta las 10:00.
    # Pasada esa hora se agenda directo al lunes (domingo no hay entregas).
    if dia_semana == 5:
        if minutos_ahora < HORA_CORTE_SABADO_MINUTOS:
            return [_opcion(fecha_hoy), _opcion(fecha_hoy + timedelta(days=2))]
        return [_opcion(fecha_hoy + timedelta(days=2))]
    # Domingo no hay entregas: todo se agenda al lunes.
    if dia_semana == 6:
        return [_opcion(fecha_hoy + timedelta(days=1))]

    # Viernes: sin corte horario para pedir el sábado (se puede pedir todo
    # el viernes sin límite) — el único corte para entrega en sábado es el
    # de las 10:00 del propio sábado, de arriba. El corte general de las
    # 16:45 solo saca la opción de entrega el mismo viernes.
    if dia_semana == 4:
        if despues_del_corte:
            return [_opcion(fecha_hoy + timedelta(days=1))]
        return [_opcion(fecha_hoy), _opcion(fecha_hoy + timedelta(days=1))]

    inicio = fecha_hoy + timedelta(days=1) if despues_del_corte else fecha_hoy
    opciones = []
    candidata = inicio
    cantidad_maxima = 2 if despues_del_corte else 3
    while len(opciones) < cantidad_maxima:
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
