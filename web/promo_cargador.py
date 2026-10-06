"""Cargador de premio promocional al sumar un teléfono al carrito (solo minoristas).

- iPhone de menos de US$900: Cargador Apple 20W Original a US$30.
- Android que no trae cargador: Cargador Samsung 45W Turbo Charge a US$35.

Hasta un cargador promocional por cada teléfono que califica del pedido. No
cuenta para el descuento por cantidad ni para los códigos de descuento.
"""
import re

from web import catalogo

PROMOS = {
    "apple": {"nombre": "Cargador Apple 20W Original (premio promocional)", "usd": 30},
    "samsung": {"nombre": "Cargador Samsung 45W Turbo Charge (premio promocional)", "usd": 35},
}
PROMO_POR_NOMBRE = {promo["nombre"]: clave for clave, promo in PROMOS.items()}
TOPE_IPHONE_USD = 900

_CAPACIDAD = re.compile(r"(?i)\d+\s*(gb|tb)\b")
_ES_ACCESORIO = re.compile(r"(?i)^\W*(xiaomi\s+)?(cargador|charger)|power\s*bank|\bcharger\b")
_SIN_CARGADOR = re.compile(r"(?i)\bs/\s*cargador|\bsin\s+cargador")
_CON_CARGADOR = re.compile(r"(?i)\bcon\s+cargador")
# Marcas cuyos teléfonos vienen sin cargador en la caja aunque el nombre no lo diga.
_MARCAS_SIN_CARGADOR = {"Apple", "Samsung"}
_SIN_CARGADOR_POR_NOMBRE = re.compile(r"(?i)\bpixel\b|\bgoogle\b|\bnothing\b")


def _es_telefono(producto):
    nombre = producto.get("nombre") or ""
    return (
        catalogo.seccion_de(producto) == "Celulares"
        and bool(_CAPACIDAD.search(nombre))
        and not _ES_ACCESORIO.search(nombre)
    )


def _trae_cargador(producto):
    nombre = producto.get("nombre") or ""
    if _SIN_CARGADOR.search(nombre):
        return False
    if _CON_CARGADOR.search(nombre):
        return True
    if catalogo.marca_de(producto) in _MARCAS_SIN_CARGADOR or _SIN_CARGADOR_POR_NOMBRE.search(nombre):
        return False
    return True


def promo_para_producto(producto):
    """Clave de PROMOS que se le ofrece a este producto, o None."""
    if not _es_telefono(producto) or _trae_cargador(producto):
        return None
    if catalogo.marca_de(producto) == "Apple":
        usd = producto.get("usd")
        if isinstance(usd, (int, float)) and 0 < usd < TOPE_IPHONE_USD:
            return "apple"
        return None
    return "samsung"


def item_promo(clave, cotizacion):
    """El cargador promocional como ítem de carrito, con los mismos precios que el catálogo."""
    promo = PROMOS[clave]
    pesos = round(promo["usd"] * cotizacion)
    return {
        "nombre": promo["nombre"],
        "usd": promo["usd"],
        "pesos": pesos,
        "transferencia": round(pesos / 0.97),
    }


def con_ofertas(secciones, cotizacion):
    """Copia de las secciones del catálogo con `oferta_cargador` en cada teléfono que califica."""
    resultado = {}
    for seccion, productos in secciones.items():
        lista = []
        for producto in productos:
            clave = promo_para_producto(producto)
            lista.append({**producto, "oferta_cargador": item_promo(clave, cotizacion)} if clave else producto)
        resultado[seccion] = lista
    return resultado
