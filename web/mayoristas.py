"""Pure pricing helpers for the wholesale product catalogue."""

import math
from numbers import Real


GANANCIA_LIMPIA_MINIMA_USD = 25
ENTREGA_USD = 15
ENTREGA_IPHONE_USD = 20
DESCUENTO_MAXIMO_USD = 50
_CAMPOS_PRIVADOS = frozenset({"costo", "margen", "proveedor", "capacidad"})


def descuento_por_margen(
    precio_publico: float, costo: float, entrega: float = ENTREGA_USD
) -> float | None:
    """Return the safe wholesale discount for a public price and cost.

    Nunca deja menos de GANANCIA_LIMPIA_MINIMA_USD limpios (margen - descuento -
    entrega). Si no alcanza para un descuento de al menos 5, no es elegible.
    """
    margen = precio_publico - costo
    piso = GANANCIA_LIMPIA_MINIMA_USD + entrega
    disponible = math.floor((margen - piso) / 5) * 5
    objetivo = min(DESCUENTO_MAXIMO_USD, math.floor(margen / 5) * 5 - 30, disponible)
    if objetivo < 5:
        return None
    return objetivo


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
        entrega = (
            ENTREGA_IPHONE_USD
            if "iphone" in str(producto.get("categoria", "")).lower()
            else ENTREGA_USD
        )
        descuento = descuento_por_margen(precio_publico, costo, entrega)
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
