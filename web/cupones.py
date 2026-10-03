"""Ciclo de vida de los códigos de descuento (mailing, fidelidad, referidos).

Regla de oro: un descuento se le resta al cliente recién cuando se envía el
recibo de la venta que lo usó. Al confirmar el pedido el código queda
*reservado* para ese pedido (no se puede usar en otro); al enviar el recibo
se *consume*. Si el pedido se borra, la reserva deja de valer y el cliente
lo conserva.
"""
from datetime import datetime, timezone


def _pedido_vigente(client, pedido_id):
    if not pedido_id:
        return False
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    return bool(filas) and not filas[0].get("borrado_en")


def reservado(client, fila):
    """True si el código está apartado para un pedido que sigue en pie."""
    return _pedido_vigente(client, (fila or {}).get("reservado_pedido_id"))


def disponible(client, fila):
    """True si el código se puede aplicar a un pedido nuevo."""
    return bool(
        fila and fila.get("activo") and not fila.get("usado_en") and not reservado(client, fila)
    )


def fila_por_codigo(client, codigo):
    if not codigo:
        return None
    filas = client.table("codigos_descuento").select("*").eq("code", codigo).execute().data
    return filas[0] if filas else None


def consumir_reservados(client, pedido_id):
    """Marca como usados los códigos reservados para este pedido.

    Devuelve las filas consumidas (con cliente_id y code) para que quien
    llama cierre los ciclos de fidelidad/referidos de cada cliente.
    """
    filas = (
        client.table("codigos_descuento").select("*")
        .eq("reservado_pedido_id", pedido_id).is_("usado_en", "null")
        .execute().data
    ) or []
    consumidos = []
    ahora = datetime.now(timezone.utc).isoformat()
    for fila in filas:
        # Condicional: dos envíos simultáneos del recibo no consumen dos veces.
        ok = (
            client.table("codigos_descuento").update({"usado_en": ahora})
            .eq("code", fila["code"]).is_("usado_en", "null")
            .execute().data
        )
        if ok:
            consumidos.append(fila)
    return consumidos
