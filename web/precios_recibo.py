"""Corrección administrativa de precios de un pedido todavía no emitido."""
import hashlib
import json
from decimal import Decimal

from web import pedidos


def version(pedido):
    valores = [pedido.get(c) for c in ("detalle", "total_usd", "descuento_usd")]
    return hashlib.sha256(json.dumps(valores, sort_keys=True, default=str).encode()).hexdigest()


def editable(pedido):
    return not any(pedido.get(c) for c in ("recibo_enviado_en", "recibo_emitido_en", "recibo_pago"))


def actualizar(pedido, precios):
    detalle = pedido.get("detalle")
    if pedido.get("total_usd") is None or not isinstance(precios, list) or not detalle or len(precios) != len(detalle):
        raise ValueError("Revisá el precio de cada producto.")
    nuevo = []
    total = pedidos.decimal_monetario(pedido["total_usd"])
    for item, precio in zip(detalle, precios):
        if item.get("usd_subtotal") is None:
            raise ValueError("El producto no tiene un subtotal válido.")
        if precio is None or isinstance(precio, bool):
            raise ValueError("Ingresá un precio válido.")
        valor = pedidos.decimal_monetario(precio)
        if valor < 0 or valor > 1000000000 or valor != valor.quantize(Decimal(".01")):
            raise ValueError("Ingresá un precio desde cero, de hasta dos decimales.")
        cantidad = pedidos.decimal_monetario(item.get("cantidad"))
        if cantidad <= 0 or cantidad != cantidad.to_integral_value():
            raise ValueError("El producto no tiene una cantidad válida.")
        subtotal = valor * cantidad
        total += subtotal - pedidos.decimal_monetario(item.get("usd_subtotal"))
        nuevo.append({**item, "usd_unitario": pedidos.numero_monetario_db(valor),
                      "usd_subtotal": pedidos.numero_monetario_db(subtotal)})
    if total < 0 or total > 1000000000000:
        raise ValueError("El total no puede ser negativo ni superar el límite permitido. Revisá los descuentos.")
    return {"detalle": nuevo, "total_usd": pedidos.numero_monetario_db(total)}


def filtrar_snapshot(consulta, pedido):
    """Comparación atómica en PostgreSQL: evita sobrescribir otra edición."""
    return (consulta.eq("id", pedido["id"]).eq("total_usd", pedido["total_usd"])
            .eq("detalle", json.dumps(pedido["detalle"], ensure_ascii=False))
            .is_("recibo_emitido_en", "null").is_("recibo_enviado_en", "null")
            .is_("recibo_pago", "null").is_("borrado_en", "null"))
