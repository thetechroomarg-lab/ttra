"""Pure pricing helpers for the wholesale product catalogue."""

import math
from numbers import Real


GASTO_USD = 7
GANANCIA_LIMPIA_MINIMA_USD = 20
MARGEN_MINIMO_ELEGIBLE_USD = 35
DESCUENTO_MAXIMO_USD = 50
_CAMPOS_PRIVADOS = frozenset({"costo", "margen", "proveedor", "capacidad"})


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
        descuento = descuento_por_margen(precio_publico, costo)
        if descuento is None:
            continue

        copia = {
            campo: valor
            for campo, valor in producto.items()
            if campo not in _CAMPOS_PRIVADOS
        }
        precio_usd = precio_publico - descuento
        copia["usd"] = precio_usd
        for campo in ("pesos", "transferencia"):
            if campo in producto:
                copia[campo] = round(precio_usd * (producto[campo] / precio_publico))
        resultado.append(copia)
    return resultado
