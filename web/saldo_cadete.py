"""Saldo del cadete: cada entrega que completa Alejo le suma un movimiento.

Un movimiento vale MONTO_POR_MOVIMIENTO pesos salvo que el pedido o la tarea
traigan su propio `monto_cadete`. El admin puede corregir el monto o borrar un
movimiento, y "Registrar pago" marca como pagados los pendientes que cubre el monto
transferido (todos, salvo que Vlad pague menos de lo que debe).

Si Vlad transfiere más de lo pendiente, lo de más queda como saldo a favor: un
movimiento negativo sin pagar (no se muestra en el historial) que va cubriendo,
en orden, lo que Alejo sume después. Cuando se agota, todo sigue como siempre.

Todo acá es tolerante a que la tabla todavía no exista en Supabase: registrar
un movimiento nunca puede voltear la entrega que lo generó.
"""

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MONTO_POR_MOVIMIENTO = 6000
CADETE_POR_DEFECTO = "alejo"  # las filas viejas, sin cadete, son de Alejo


def de_cadete(fila):
    return fila.get("cadete") or CADETE_POR_DEFECTO
# Los pedidos se pagan en dólares pero el saldo se lleva en pesos: al registrar
# el movimiento se pasan a pesos con la cotización de ese día.
MONTO_PEDIDO_USD = 10


def monto_pedido_ars(cotizacion):
    return round(MONTO_PEDIDO_USD * cotizacion)
TABLA = "movimientos_cadete"
TABLA_PAGOS = "pagos_cadete"
# Los comprobantes van al mismo bucket privado que las fotos de series.
BUCKET_COMPROBANTES = "recibos-series"


def monto_de(fila, por_defecto=MONTO_POR_MOVIMIENTO):
    monto = fila.get("monto_cadete")
    if monto is None:
        return por_defecto
    try:
        return max(0, int(monto))
    except (TypeError, ValueError):
        return por_defecto


def registrar(client, tipo, fila, descripcion, por_defecto=MONTO_POR_MOVIMIENTO, cadete=None):
    """Suma un movimiento por la entrega `fila`. No duplica si ya existe."""
    referencia_id = fila.get("id")
    try:
        existentes = client.table(TABLA).select("id").eq("tipo", tipo).eq(
            "referencia_id", referencia_id
        ).execute().data
        if existentes:
            # Ya estaba registrado y pagado, pero se restauró: completarlo de
            # nuevo levanta la anulación que había restado su monto.
            client.table(TABLA).delete().eq("tipo", TIPO_ANULACION).eq(
                "referencia_id", _referencia_anulacion(tipo, referencia_id)
            ).is_("pagado_en", "null").execute()
            return None
        movimiento = {
            "id": str(uuid.uuid4()),
            "cadete": cadete or CADETE_POR_DEFECTO,
            "tipo": tipo,
            "referencia_id": referencia_id,
            "descripcion": (descripcion or "").strip()[:300] or tipo.capitalize(),
            "fecha_entrega": fila.get("fecha_entrega"),
            "monto_ars": monto_de(fila, por_defecto),
            "creado_en": datetime.now(timezone.utc).isoformat(),
        }
        client.table(TABLA).insert(movimiento).execute()
        return movimiento
    except Exception:
        logger.exception("No se pudo registrar el movimiento del cadete (%s %s)", tipo, referencia_id)
        return None


TIPO_ANULACION = "anulacion"
TIPO_SALDO_A_FAVOR = "saldo_a_favor"


def _referencia_anulacion(tipo, referencia_id):
    return f"{tipo}:{referencia_id}"


def anular(client, tipo, referencia_id):
    """Resta del saldo lo que sumó una entrega que se restauró.

    Si el movimiento sigue pendiente se borra, así completarla de nuevo lo
    vuelve a crear. Si ya se pagó, queda un movimiento negativo que se
    descuenta del próximo pago. Devuelve el monto restado.
    """
    try:
        movimientos = client.table(TABLA).select("*").eq("tipo", tipo).eq(
            "referencia_id", referencia_id
        ).execute().data or []
        restado = 0
        for movimiento in movimientos:
            monto = int(movimiento.get("monto_ars") or 0)
            if not movimiento.get("pagado_en"):
                client.table(TABLA).delete().eq("id", movimiento["id"]).execute()
                restado += monto
                continue
            referencia = _referencia_anulacion(tipo, referencia_id)
            if client.table(TABLA).select("id").eq("tipo", TIPO_ANULACION).eq(
                "referencia_id", referencia
            ).is_("pagado_en", "null").execute().data:
                continue
            client.table(TABLA).insert({
                "id": str(uuid.uuid4()),
                "cadete": de_cadete(movimiento),
                "tipo": TIPO_ANULACION,
                "referencia_id": referencia,
                "descripcion": f"Restaurada: {movimiento.get('descripcion') or tipo}"[:300],
                "fecha_entrega": movimiento.get("fecha_entrega"),
                "monto_ars": -monto,
                "creado_en": datetime.now(timezone.utc).isoformat(),
            }).execute()
            restado += monto
        return restado
    except Exception:
        logger.exception("No se pudo anular el movimiento del cadete (%s %s)", tipo, referencia_id)
        return 0


def listar(client, cadete=None):
    """Movimientos, de un cadete o (sin `cadete`) de todos."""
    try:
        filas = client.table(TABLA).select("*").execute().data or []
        if cadete is not None:
            filas = [m for m in filas if de_cadete(m) == cadete]
    except Exception:
        logger.exception("No se pudieron leer los movimientos del cadete")
        return []
    return sorted(filas, key=lambda m: m.get("creado_en") or "", reverse=True)


def es_saldo_a_favor(movimiento):
    return movimiento.get("tipo") == TIPO_SALDO_A_FAVOR


def cobertura(movimientos):
    """Cuánto de cada movimiento pendiente cubre el saldo a favor, del más viejo al más nuevo.

    Devuelve ({id: monto cubierto}, saldo a favor que sobra).
    """
    pendientes = [m for m in movimientos if not m.get("pagado_en")]
    credito = -sum(int(m.get("monto_ars") or 0) for m in pendientes if es_saldo_a_favor(m))
    cubiertos = {}
    for m in sorted((m for m in pendientes if not es_saldo_a_favor(m)), key=lambda m: m.get("creado_en") or ""):
        monto = int(m.get("monto_ars") or 0)
        if credito <= 0 or monto <= 0:
            continue
        cubiertos[m.get("id")] = min(credito, monto)
        credito -= cubiertos[m.get("id")]
    return cubiertos, max(credito, 0)


def resumen(movimientos):
    visibles = [m for m in movimientos if not es_saldo_a_favor(m)]
    cubiertos, _ = cobertura(movimientos)
    sin_pagar = [
        m for m in visibles
        if not m.get("pagado_en") and cubiertos.get(m.get("id"), 0) < int(m.get("monto_ars") or 0)
    ]
    return {
        "movimientos_total": len(visibles),
        "movimientos_pendientes": len(sin_pagar),
        "saldo_pendiente": sum(int(m.get("monto_ars") or 0) for m in movimientos if not m.get("pagado_en")),
    }


class PagoInvalido(ValueError):
    pass


def validar_pago(client, monto_transferido=None, cadete=CADETE_POR_DEFECTO):
    """Devuelve (pendientes, saldo, monto) o levanta PagoInvalido si no se puede pagar."""
    pendientes = [m for m in listar(client, cadete) if not m.get("pagado_en")]
    saldo = sum(int(m.get("monto_ars") or 0) for m in pendientes)
    monto = saldo if monto_transferido is None else int(monto_transferido)
    if monto <= 0:
        raise PagoInvalido("No hay saldo para pagar" if monto_transferido is None else "El monto tiene que ser mayor a cero")
    return pendientes, saldo, monto


def registrar_pago(client, comprobante=None, monto_transferido=None, cotizacion=None, cadete=CADETE_POR_DEFECTO):
    """Marca los pendientes como pagados y deja un registro del pago.

    `comprobante` es la ruta en Storage del archivo de la transferencia, si
    Vlad lo subió. `monto_transferido` es lo que transfirió de verdad: si
    supera lo pendiente, el excedente queda como saldo a favor. Sin él, se
    paga justo lo pendiente. El registro se guarda antes de tocar los movimientos.
    """
    ahora = datetime.now(timezone.utc).isoformat()
    pendientes, saldo, monto = validar_pago(client, monto_transferido, cadete)
    parcial = monto < saldo
    # Lo transferido más el saldo a favor que ya tenía se aplica a lo más viejo;
    # lo que no alcance a cubrir un movimiento entero queda a favor, y va
    # cubriendo (en parte) el siguiente pendiente.
    disponible = monto - saldo + sum(int(m.get("monto_ars") or 0) for m in pendientes if not es_saldo_a_favor(m))
    a_pagar = [m for m in pendientes if es_saldo_a_favor(m)]
    for m in sorted((m for m in pendientes if not es_saldo_a_favor(m)), key=lambda m: m.get("creado_en") or ""):
        importe = int(m.get("monto_ars") or 0)
        if importe > disponible:
            break
        disponible -= importe
        a_pagar.append(m)
    excedente = disponible
    pago = {
        "id": str(uuid.uuid4()),
        "cadete": cadete,
        "monto_ars": monto,
        "movimientos": len([m for m in a_pagar if not es_saldo_a_favor(m)]),
        "comprobante": comprobante,
        "creado_en": ahora,
    }
    if cotizacion is not None:
        from web.ganancia import numero
        if numero(cotizacion) <= 0:
            raise PagoInvalido("Cotización inválida")
        pago["cotizacion_ars_usd"] = float(cotizacion)
    client.table(TABLA_PAGOS).insert(pago).execute()
    from web import ganancia_servicio
    ganancia_servicio.intentar(ganancia_servicio.conciliar_pago_cadete, client, pago["id"])
    for movimiento in a_pagar:
        client.table(TABLA).update({"pagado_en": ahora, "pago_id": pago["id"]}).eq("id", movimiento["id"]).execute()
    if excedente:
        client.table(TABLA).insert({
            "id": str(uuid.uuid4()),
            "cadete": cadete,
            "tipo": TIPO_SALDO_A_FAVOR,
            "referencia_id": pago["id"],
            "descripcion": "Saldo a favor (pago parcial)" if parcial else "Saldo a favor (pago de más)",
            "monto_ars": -excedente,
            "creado_en": ahora,
        }).execute()
    return {
        "pagados": pago["movimientos"], "monto": monto,
        "saldo_a_favor": 0 if parcial else excedente,
        "saldo_restante": saldo - monto if parcial else 0,
        "pago": pago,
    }


def registrar_pagos_viejos(client, cadete=CADETE_POR_DEFECTO):
    """Crea el registro de los pagos hechos antes de que existiera pagos_cadete.

    Un pago viejo es el grupo de movimientos marcados con el mismo pagado_en
    y sin pago_id. Es idempotente: al vincularlos, no se vuelven a agrupar.
    """
    grupos = {}
    for movimiento in listar(client, cadete):
        if movimiento.get("pagado_en") and not movimiento.get("pago_id"):
            grupos.setdefault(movimiento["pagado_en"], []).append(movimiento)
    for pagado_en, movimientos in grupos.items():
        try:
            pago = {
                "id": str(uuid.uuid4()),
                "cadete": cadete,
                "monto_ars": sum(int(m.get("monto_ars") or 0) for m in movimientos),
                "movimientos": len(movimientos),
                "comprobante": None,
                "creado_en": pagado_en,
            }
            client.table(TABLA_PAGOS).insert(pago).execute()
            for movimiento in movimientos:
                client.table(TABLA).update({"pago_id": pago["id"]}).eq("id", movimiento["id"]).execute()
        except Exception:
            logger.exception("No se pudo registrar el pago viejo del %s", pagado_en)


def listar_pagos(client, cadete=None):
    try:
        filas = client.table(TABLA_PAGOS).select("*").execute().data or []
        if cadete is not None:
            filas = [p for p in filas if de_cadete(p) == cadete]
    except Exception:
        logger.exception("No se pudieron leer los pagos del cadete")
        return []
    return sorted(filas, key=lambda p: p.get("creado_en") or "", reverse=True)
