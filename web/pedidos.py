import uuid
from datetime import datetime, timezone


def _combinar_detalles(actual, nuevo):
    combinados = [dict(item) for item in actual or []]
    posiciones = {
        (item.get("nombre"), item.get("color"), item.get("usd_unitario")): indice
        for indice, item in enumerate(combinados)
    }
    for item in nuevo or []:
        clave = (item.get("nombre"), item.get("color"), item.get("usd_unitario"))
        if clave not in posiciones:
            posiciones[clave] = len(combinados)
            combinados.append(dict(item))
            continue
        destino = combinados[posiciones[clave]]
        destino["cantidad"] = int(destino.get("cantidad") or 0) + int(item.get("cantidad") or 0)
        destino["usd_subtotal"] = int(destino.get("usd_subtotal") or 0) + int(item.get("usd_subtotal") or 0)
    return combinados


def _unir_productos(actual, nuevo):
    return list(dict.fromkeys([*(actual or []), *(nuevo or [])]))


def guardar_pedido(
    client,
    cliente_id,
    productos,
    fecha_entrega=None,
    detalle=None,
    total_usd=None,
    descuento_usd=0,
    origen="whatsapp",
):
    fecha_iso = fecha_entrega.isoformat() if fecha_entrega else None
    if fecha_iso and detalle and total_usd is not None:
        existentes = client.table("pedidos").select("*").eq("cliente_id", cliente_id).execute().data
        pendiente = next(
            (
                pedido for pedido in existentes
                if pedido.get("fecha_entrega") == fecha_iso
                and not pedido.get("recibo_enviado_en")
                and pedido.get("detalle")
                and pedido.get("total_usd") is not None
            ),
            None,
        )
        if pendiente:
            actualizado = {
                "productos": _unir_productos(pendiente.get("productos"), productos),
                "detalle": _combinar_detalles(pendiente.get("detalle"), detalle),
                "total_usd": int(pendiente.get("total_usd") or 0) + int(total_usd),
                "descuento_usd": int(pendiente.get("descuento_usd") or 0) + int(descuento_usd or 0),
            }
            client.table("pedidos").update(actualizado).eq("id", pendiente["id"]).execute()
            return {**pendiente, **actualizado}

    fila = {
        "id": str(uuid.uuid4()),
        "cliente_id": cliente_id,
        "productos": productos,
        "detalle": detalle or None,
        "total_usd": total_usd,
        "descuento_usd": descuento_usd,
        "fecha_entrega": fecha_iso,
        "origen": origen,
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    client.table("pedidos").insert(fila).execute()
    return fila


def editar_fecha_entrega(client, pedido_id, fecha_entrega):
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise ValueError("Pedido no encontrado")
    pedido = filas[0]
    fecha_iso = fecha_entrega.isoformat()
    if pedido.get("fecha_entrega") == fecha_iso:
        return pedido
    candidatos = client.table("pedidos").select("*").eq("cliente_id", pedido["cliente_id"]).execute().data
    destino = next(
        (
            otro for otro in candidatos
            if otro.get("id") != pedido_id
            and otro.get("fecha_entrega") == fecha_iso
            and not otro.get("recibo_enviado_en")
            and otro.get("detalle")
            and pedido.get("detalle")
            and otro.get("total_usd") is not None
            and pedido.get("total_usd") is not None
        ),
        None,
    )
    if destino:
        actualizado = {
            "productos": _unir_productos(destino.get("productos"), pedido.get("productos")),
            "detalle": _combinar_detalles(destino.get("detalle"), pedido.get("detalle")),
            "total_usd": int(destino.get("total_usd") or 0) + int(pedido.get("total_usd") or 0),
            "descuento_usd": int(destino.get("descuento_usd") or 0) + int(pedido.get("descuento_usd") or 0),
        }
        client.table("pedidos").update(actualizado).eq("id", destino["id"]).execute()
        client.table("pedidos").delete().eq("id", pedido_id).execute()
        return {**destino, **actualizado}
    client.table("pedidos").update({"fecha_entrega": fecha_iso}).eq("id", pedido_id).execute()
    return {**pedido, "fecha_entrega": fecha_iso}


def eliminar_pedido(client, pedido_id):
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise ValueError("Pedido no encontrado")
    client.table("pedidos").delete().eq("id", pedido_id).execute()
