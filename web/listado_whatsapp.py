"""Datos del LISTADO WHATSAPP, la sección exclusiva para cuentas mayoristas.

El mayorista recibe tres listados para pegar en WhatsApp:
  1. su precio (el del catálogo mayorista),
  2. el precio al que vende Vlad al público,
  3. el precio del público más un recargo de US$ 10 a 15 de ganancia.

Acá solo se calculan los dólares de cada columna. Los pesos dependen de la
cotización que elija el mayorista, así que los resuelve la página.
"""

from web import catalogo

# Los usados llevan condiciones propias (garantía, batería) que no se pueden
# revender en un listado genérico.
_CATEGORIAS_EXCLUIDAS = frozenset({"Apple - iPhone Usado"})

# Recargo en USD de la tercera columna: 10 hasta el tope, 15 desde ahí.
RECARGO_BAJO_USD = 10
RECARGO_ALTO_USD = 15
TOPE_RECARGO_BAJO_USD = 500

# Mismo orden de marcas que el catálogo (ORDEN_MARCAS en landing-base.js); lo que
# no está acá va al final, en el orden en que aparece.
_ORDEN_MARCAS = (
    "Apple", "Samsung", "Xiaomi", "Motorola", "Realme",
    "Oppo", "Honor", "Infinix", "Nokia", "Itel", "JBL", "Logitech", "Otras marcas",
)


def _lugar_de_marca(marca: str) -> int:
    return _ORDEN_MARCAS.index(marca) if marca in _ORDEN_MARCAS else len(_ORDEN_MARCAS) - 1


def recargo_usd(precio_publico: float) -> int:
    """US$ que se suman al precio del público en la tercera columna."""
    return RECARGO_BAJO_USD if precio_publico < TOPE_RECARGO_BAJO_USD else RECARGO_ALTO_USD


def secciones_listado(productos_mayorista: list[dict]) -> list[dict]:
    """Agrupa el catálogo mayorista en secciones y marcas, con las 3 columnas en USD.

    Espera productos ya pasados por `mayoristas.catalogo_mayorista`, que traen
    `usd` (precio mayorista) y `usd_publico`. Cada ítem devuelve solo lo que la
    página necesita: nombre (n) y los tres precios (a, b, c).
    """
    elegibles = [
        p for p in productos_mayorista
        if p.get("categoria") not in _CATEGORIAS_EXCLUIDAS
        and p.get("usd") is not None
        and p.get("usd_publico") is not None
    ]
    por_seccion = catalogo.secciones_catalogo(elegibles)
    resultado = []
    for seccion in catalogo.SECCIONES:
        grupos: dict[str, list[dict]] = {}
        for p in por_seccion[seccion]:
            publico = p["usd_publico"]
            grupos.setdefault(p.get("marca") or "Otras marcas", []).append({
                "n": p["nombre"],
                "a": p["usd"],
                "b": publico,
                "c": publico + recargo_usd(publico),
            })
        if grupos:
            resultado.append({
                "seccion": seccion,
                "grupos": [
                    {"titulo": marca, "items": items}
                    for marca, items in sorted(grupos.items(), key=lambda g: _lugar_de_marca(g[0]))
                ],
            })
    return resultado
