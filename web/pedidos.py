import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def decimal_monetario(valor):
    if isinstance(valor, bool):
        raise ValueError("Valor monetario inválido")
    try:
        resultado = Decimal(str(0 if valor is None else valor))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Valor monetario inválido") from exc
    if not resultado.is_finite():
        raise ValueError("Valor monetario inválido")
    return resultado


def numero_monetario_db(valor):
    decimal = decimal_monetario(valor)
    if decimal == decimal.to_integral_value():
        return int(decimal)
    return float(decimal)


def _sumar_monetarios(izquierdo, derecho):
    return numero_monetario_db(
        decimal_monetario(izquierdo) + decimal_monetario(derecho)
    )


def _normalizar_detalles(detalle):
    normalizados = []
    for item in detalle or []:
        copia = dict(item)
        for campo in ("usd_unitario", "usd_subtotal"):
            if copia.get(campo) is not None:
                copia[campo] = numero_monetario_db(copia[campo])
        normalizados.append(copia)
    return normalizados


def _combinar_detalles(actual, nuevo):
    combinados = [dict(item) for item in actual or []]
    posiciones = {
        (
            item.get("nombre"),
            item.get("color"),
            decimal_monetario(item.get("usd_unitario")),
            item.get("tipo"),
            item.get("codigo_promo"),
        ): indice
        for indice, item in enumerate(combinados)
    }
    for item in nuevo or []:
        clave = (
            item.get("nombre"),
            item.get("color"),
            decimal_monetario(item.get("usd_unitario")),
            item.get("tipo"),
            item.get("codigo_promo"),
        )
        if clave not in posiciones:
            posiciones[clave] = len(combinados)
            combinados.append(dict(item))
            continue
        destino = combinados[posiciones[clave]]
        destino["cantidad"] = int(destino.get("cantidad") or 0) + int(item.get("cantidad") or 0)
        destino["usd_subtotal"] = _sumar_monetarios(
            destino.get("usd_subtotal"), item.get("usd_subtotal")
        )
    return combinados


def _unir_productos(actual, nuevo):
    return list(dict.fromkeys([*(actual or []), *(nuevo or [])]))


def guardar_pedido(
    client,
    cliente_id,
    productos,
    fecha_entrega=None,
    direccion_entrega=None,
    detalle=None,
    total_usd=None,
    descuento_usd=0,
    modo_precio="minorista",
    descuento_mayorista_usd=0,
    origen="whatsapp",
    lat=None,
    lng=None,
):
    fecha_iso = fecha_entrega.isoformat() if fecha_entrega else None
    detalle = _normalizar_detalles(detalle)
    total_usd = None if total_usd is None else numero_monetario_db(total_usd)
    descuento_usd = numero_monetario_db(descuento_usd)
    descuento_mayorista_usd = numero_monetario_db(descuento_mayorista_usd)
    if fecha_iso and detalle and total_usd is not None:
        existentes = client.table("pedidos").select("*").eq("cliente_id", cliente_id).execute().data
        pendiente = next(
            (
                pedido for pedido in existentes
                if pedido.get("fecha_entrega") == fecha_iso
                and not pedido.get("recibo_enviado_en")
                and pedido.get("detalle")
                and pedido.get("total_usd") is not None
                and pedido.get("modo_precio", "minorista") == modo_precio
                and pedido.get("direccion_entrega") == direccion_entrega
            ),
            None,
        )
        if pendiente:
            actualizado = {
                "productos": _unir_productos(pendiente.get("productos"), productos),
                "detalle": _combinar_detalles(pendiente.get("detalle"), detalle),
                "total_usd": _sumar_monetarios(pendiente.get("total_usd"), total_usd),
                "descuento_usd": _sumar_monetarios(
                    pendiente.get("descuento_usd"), descuento_usd
                ),
                "descuento_mayorista_usd": _sumar_monetarios(
                    pendiente.get("descuento_mayorista_usd"),
                    descuento_mayorista_usd,
                ),
                "direccion_entrega": direccion_entrega or pendiente.get("direccion_entrega"),
                "lat": lat if lat is not None else pendiente.get("lat"),
                "lng": lng if lng is not None else pendiente.get("lng"),
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
        "modo_precio": modo_precio,
        "descuento_mayorista_usd": descuento_mayorista_usd,
        "fecha_entrega": fecha_iso,
        "direccion_entrega": direccion_entrega,
        "origen": origen,
        "fecha": datetime.now(timezone.utc).isoformat(),
        "lat": lat,
        "lng": lng,
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
            and otro.get("modo_precio", "minorista") == pedido.get("modo_precio", "minorista")
            and otro.get("direccion_entrega") == pedido.get("direccion_entrega")
        ),
        None,
    )
    if destino:
        actualizado = {
            "productos": _unir_productos(destino.get("productos"), pedido.get("productos")),
            "detalle": _combinar_detalles(destino.get("detalle"), pedido.get("detalle")),
            "total_usd": _sumar_monetarios(destino.get("total_usd"), pedido.get("total_usd")),
            "descuento_usd": _sumar_monetarios(
                destino.get("descuento_usd"), pedido.get("descuento_usd")
            ),
            "descuento_mayorista_usd": _sumar_monetarios(
                destino.get("descuento_mayorista_usd"),
                pedido.get("descuento_mayorista_usd"),
            ),
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
