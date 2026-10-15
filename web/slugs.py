"""Links estables a un producto: /?producto=<slug>.

El slug sale del nombre, pero el nombre lo pone el proveedor y cambia entre
catálogos (mayúsculas, "5G", "Dual", "(s/ cargador)", la marca adelante...).
Por eso un link no se resuelve por igualdad de slug sino por `clave_producto`,
que descarta lo que no distingue a un producto. Así un link que se mandó hace
semanas sigue abriendo el mismo producto con el precio de hoy."""
import re
import unicodedata
from urllib.parse import urlencode

# Palabras que el proveedor agrega o saca sin que cambie el producto. Ojo con
# sumar acá algo que sí distingue (usado, activado, cpo, pro, max...). "5g" NO
# es ruido: hay modelos con versión 4G y 5G a distinto precio (Redmi 17, A17).
_RUIDO = {
    "4g", "lte", "dual", "sim", "ram", "nuevo", "nueva",
    "s", "sin", "cargador", "con", "de", "y",
    "xiaomi", "motorola", "samsung", "galaxy", "apple",
}
_UNIDADES = {"gb", "tb", "mm", "w"}


def slug(nombre):
    n = (nombre or "").replace("+", " plus ")
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
    n = n.lower()
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return n


def clave_producto(nombre_o_slug):
    """Conjunto de palabras que identifica al producto, sin orden ni ruido.
    Acepta tanto un nombre como un slug: los dos dan la misma clave."""
    tokens = [t for t in slug(nombre_o_slug).split("-") if t]
    unidos = []
    for t in tokens:
        # "1 TB" y "1TB" son lo mismo.
        if t in _UNIDADES and unidos and unidos[-1].isdigit():
            unidos[-1] += t
        else:
            unidos.append(t)
    return frozenset(t for t in unidos if t not in _RUIDO)


def resolver_producto(ref, productos):
    """Nombre del producto actual al que apunta un link, o None si ya no está.

    `ref` puede ser el slug de un link nuevo o el nombre crudo de un link
    viejo. Si varios productos comparten la clave (duplicados de proveedor),
    gana el más barato."""
    if not ref:
        return None
    for p in productos:
        if p.get("nombre") == ref:
            return ref
    buscado = slug(ref)
    for p in productos:
        if slug(p.get("nombre")) == buscado:
            return p["nombre"]
    clave = clave_producto(ref)
    if not clave:
        return None
    candidatos = [p for p in productos if clave_producto(p.get("nombre")) == clave]
    if not candidatos:
        return None
    return min(candidatos, key=lambda p: p.get("usd") or float("inf"))["nombre"]


def url_producto(nombre, base="https://thetechroomarg.com"):
    return f"{base}/?{urlencode({'producto': slug(nombre)})}"
