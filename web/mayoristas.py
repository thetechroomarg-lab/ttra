"""Precios del catálogo mayorista.

Regla: el mayorista recibe un descuento del 50% de la ganancia del precio
normal de venta, y nunca se muestra un producto que deje menos de
GANANCIA_MINIMA_USD de ganancia. Con el 50%, tu ganancia queda igual al
descuento, así que ambos pisos coinciden: ganancia normal >= 2 * piso.

Este módulo solo lo usa el catálogo mayorista; el minorista no lo toca.
"""

import math
from numbers import Real


GANANCIA_MINIMA_USD = 20
PORCENTAJE_DESCUENTO = 0.5
_CAMPOS_PRIVADOS = frozenset({"costo", "margen", "proveedor", "capacidad"})


def descuento_mayorista(precio_publico: float, costo: float) -> int | None:
    """Return the wholesale discount in USD, or None if the product doesn't qualify.

    El descuento es el 50% de la ganancia, redondeado hacia abajo a dólares
    enteros (así tu ganancia nunca queda por debajo del descuento). Si el
    descuento da menos de GANANCIA_MINIMA_USD, el producto no se muestra.
    """
    ganancia = precio_publico - costo
    descuento = math.floor(ganancia * PORCENTAJE_DESCUENTO)
    if descuento < GANANCIA_MINIMA_USD:
        return None
    return descuento


def catalogo_mayorista(productos: list[dict], costos: dict[str, float]) -> list[dict]:
    """Build wholesale products without mutating or leaking private data."""
    resultado = []
    for producto in productos:
        costo = costos.get(producto.get("nombre"))
        if (
            isinstance(costo, bool)
            or not isinstance(costo, Real)
            or not math.isfinite(costo)
            or costo <= 0
        ):
            continue

        precio_publico = producto.get("usd")
        if precio_publico is None:
            continue
        descuento = descuento_mayorista(precio_publico, costo)
        if descuento is None:
            continue

        copia = {
            campo: valor
            for campo, valor in producto.items()
            if campo not in _CAMPOS_PRIVADOS
        }
        precio_usd = precio_publico - descuento
        copia["usd"] = precio_usd
        # El precio público va al lado, para que el mayorista vea su descuento.
        copia["usd_publico"] = precio_publico
        for campo in ("pesos", "transferencia"):
            if campo in producto:
                copia[campo] = round(precio_usd * (producto[campo] / precio_publico))
                copia[f"{campo}_publico"] = producto[campo]
        resultado.append(copia)
    return resultado
