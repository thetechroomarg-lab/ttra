"""Saldo del cadete: cada entrega que completa Alejo le suma un movimiento.

Un movimiento vale MONTO_POR_MOVIMIENTO pesos salvo que el pedido o la tarea
traigan su propio `monto_cadete`. El admin puede corregir el monto o borrar un
movimiento, y "Registrar pago" marca todos los pendientes como pagados.

Todo acá es tolerante a que la tabla todavía no exista en Supabase: registrar
un movimiento nunca puede voltear la entrega que lo generó.
"""

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

MONTO_POR_MOVIMIENTO = 6000
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


def registrar(client, tipo, fila, descripcion, por_defecto=MONTO_POR_MOVIMIENTO):
    """Suma un movimiento por la entrega `fila`. No duplica si ya existe."""
    referencia_id = fila.get("id")
    try:
        existentes = client.table(TABLA).select("id").eq("tipo", tipo).eq(
            "referencia_id", referencia_id
        ).execute().data
        if existentes:
            return None
        movimiento = {
            "id": str(uuid.uuid4()),
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


def listar(client):
    try:
        filas = client.table(TABLA).select("*").execute().data or []
    except Exception:
        logger.exception("No se pudieron leer los movimientos del cadete")
        return []
    return sorted(filas, key=lambda m: m.get("creado_en") or "", reverse=True)


def resumen(movimientos):
    pendientes = [m for m in movimientos if not m.get("pagado_en")]
    return {
        "movimientos_total": len(movimientos),
        "movimientos_pendientes": len(pendientes),
        "saldo_pendiente": sum(int(m.get("monto_ars") or 0) for m in pendientes),
    }


def registrar_pago(client, comprobante=None):
    """Marca los pendientes como pagados y deja un registro del pago.

    `comprobante` es la ruta en Storage del archivo de la transferencia, si
    Vlad lo subió. El registro se guarda antes de tocar los movimientos.
    """
    ahora = datetime.now(timezone.utc).isoformat()
    pendientes = [m for m in listar(client) if not m.get("pagado_en")]
    monto = sum(int(m.get("monto_ars") or 0) for m in pendientes)
    pago = {
        "id": str(uuid.uuid4()),
        "monto_ars": monto,
        "movimientos": len(pendientes),
        "comprobante": comprobante,
        "creado_en": ahora,
    }
    client.table(TABLA_PAGOS).insert(pago).execute()
    for movimiento in pendientes:
        client.table(TABLA).update({"pagado_en": ahora, "pago_id": pago["id"]}).eq("id", movimiento["id"]).execute()
    return {"pagados": len(pendientes), "monto": monto, "pago": pago}


def registrar_pagos_viejos(client):
    """Crea el registro de los pagos hechos antes de que existiera pagos_cadete.

    Un pago viejo es el grupo de movimientos marcados con el mismo pagado_en
    y sin pago_id. Es idempotente: al vincularlos, no se vuelven a agrupar.
    """
    grupos = {}
    for movimiento in listar(client):
        if movimiento.get("pagado_en") and not movimiento.get("pago_id"):
            grupos.setdefault(movimiento["pagado_en"], []).append(movimiento)
    for pagado_en, movimientos in grupos.items():
        try:
            pago = {
                "id": str(uuid.uuid4()),
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


def listar_pagos(client):
    try:
        filas = client.table(TABLA_PAGOS).select("*").execute().data or []
    except Exception:
        logger.exception("No se pudieron leer los pagos del cadete")
        return []
    return sorted(filas, key=lambda p: p.get("creado_en") or "", reverse=True)
