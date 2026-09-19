"""Lógica pura del recibo manual: un recibo standalone armado desde una nota
del cadete, sin depender de una fila en ``pedidos``. Ver
docs/superpowers/specs/2026-09-19-recibo-manual-y-papelera-design.md.
"""


def construir_items(items_crudos):
    if not items_crudos:
        raise ValueError("El recibo necesita al menos un ítem")
    items = []
    for item in items_crudos:
        nombre = str(item.get("nombre") or "").strip()
        if not nombre:
            raise ValueError("Cada ítem necesita un nombre")
        try:
            precio = float(item.get("precio_usd"))
        except (TypeError, ValueError):
            raise ValueError(f"Precio inválido para '{nombre}'")
        if precio <= 0:
            raise ValueError(f"El precio de '{nombre}' tiene que ser mayor a 0")
        items.append({"nombre": nombre, "precio_usd": precio})
    return items


def calcular_total(items):
    return sum(item["precio_usd"] for item in items)


def armar_pedido_like(nombre_cliente, items, total_usd, recibo_id, emitido_en, creado_por):
    return {
        "detalle": [
            {
                "nombre": item["nombre"],
                "color": None,
                "cantidad": 1,
                "usd_unitario": item["precio_usd"],
                "usd_subtotal": item["precio_usd"],
            }
            for item in items
        ],
        "total_usd": total_usd,
        "descuento_usd": 0,
        "recibo_id": recibo_id,
        "recibo_emitido_en": emitido_en,
        "entregado_por_cadete": True,
        "_nombre_cliente_manual": nombre_cliente,
    }
