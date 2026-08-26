"""Pure pricing helpers for the wholesale product catalogue."""

import math


GASTO_USD = 7
GANANCIA_LIMPIA_MINIMA_USD = 20
MARGEN_MINIMO_ELEGIBLE_USD = 35
DESCUENTO_MAXIMO_USD = 50


def descuento_por_margen(precio_publico: float, costo: float) -> float | None:
    """Return the safe wholesale discount for a public price and cost."""
    margen = precio_publico - costo
    if margen < MARGEN_MINIMO_ELEGIBLE_USD:
        return None
    objetivo = min(DESCUENTO_MAXIMO_USD, math.floor(margen / 5) * 5 - 30)
    return max(0, min(objetivo, precio_publico - costo - 27))


def catalogo_mayorista(productos: list[dict], costos: dict[str, float]) -> list[dict]:
    """Build wholesale products without mutating or leaking private data."""
    resultado = []
    for producto in productos:
        nombre = producto.get("nombre")
        costo = costos.get(nombre)
        if costo is None:
            continue

        precio_publico = producto.get("usd")
        if precio_publico is None:
            continue
        descuento = descuento_por_margen(precio_publico, costo)
        if descuento is None:
            continue

        copia = producto.copy()
        precio_usd = precio_publico - descuento
        copia["usd"] = precio_usd
        for campo in ("pesos", "transferencia"):
            if campo in producto:
                copia[campo] = round(precio_usd * (producto[campo] / precio_publico))
        resultado.append(copia)
    return resultado
