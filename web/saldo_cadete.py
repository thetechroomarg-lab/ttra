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


def registrar_pago(client):
    ahora = datetime.now(timezone.utc).isoformat()
    pendientes = [m for m in listar(client) if not m.get("pagado_en")]
    for movimiento in pendientes:
        client.table(TABLA).update({"pagado_en": ahora}).eq("id", movimiento["id"]).execute()
    return {"pagados": len(pendientes), "monto": sum(int(m.get("monto_ars") or 0) for m in pendientes)}
