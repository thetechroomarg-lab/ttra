"""Garantías: una sola fuente para la web y el recibo.

Los textos viven en web/static/garantias.json (los mismos que muestran las
cards de Garantías de la home). Acá se decide qué garantía corresponde a cada
ítem de un pedido y se aplanan los bloques a líneas que el PDF y el mail del
recibo pueden dibujar.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

from .productos import _categoria

GARANTIAS_PATH = Path(__file__).resolve().parent / "static" / "garantias.json"

# Orden en que se listan en el recibo (el mismo que las cards de la home).
ORDEN = ("apple", "samsung", "motorola", "xiaomi", "notebooks", "gaming", "usados")

_USADO = re.compile(r"(?i)\busad[oa]s?\b")
# "Certificado"/"réplica" son cargadores y cables no originales: no tienen
# garantía oficial de Apple aunque digan Apple en el nombre.
_NO_ORIGINAL = re.compile(r"(?i)certificad|r[ée]plica")
_APPLE = re.compile(r"(?i)\bapple\b|\bairtag|\bmagic (keyboard|mouse)\b|\bpencil\b")


@lru_cache(maxsize=1)
def cargar():
    return json.loads(GARANTIAS_PATH.read_text(encoding="utf-8"))


def clave_para_nombre(nombre):
    """Qué garantía corresponde a un producto, a partir de su nombre."""
    texto = nombre or ""
    if _USADO.search(texto):
        return "usados"
    categoria = _categoria(texto)
    # Las marcas de celulares van primero: un auricular o un reloj Samsung,
    # Xiaomi o Motorola lleva la garantía de su marca.
    if categoria in ("Samsung", "Xiaomi", "Motorola"):
        return categoria.lower()
    if re.search(r"(?i)xiaomi|redmi|\bpoco\b", texto):
        return "xiaomi"
    if re.search(r"(?i)samsung|galaxy", texto):
        return "samsung"
    if _NO_ORIGINAL.search(texto):
        return "gaming"
    if categoria in ("Apple - iPhone", "Apple - iPad", "Apple - AirPods", "Mac") or _APPLE.search(texto):
        return "apple"
    if categoria == "Notebook":
        return "notebooks"
    return "gaming"


def claves_para_detalle(detalle):
    """Garantías del pedido sin repetir, en el orden de las cards."""
    claves = {clave_para_nombre(item.get("nombre")) for item in (detalle or [])}
    return [clave for clave in ORDEN if clave in claves]


def plazo_texto(garantia):
    numero, unidad = garantia["plazo"]
    return f"{numero} {unidad}".strip()


def secciones(garantia):
    """Aplana los bloques de una garantía a secciones con líneas tipadas.

    Cada línea es (tipo, texto) con tipo en: parrafo, item, etiqueta, nota,
    destacado, excepcion, enlace (texto, url), fuerte, firma.
    """
    resultado = []
    indice = 0
    for bloque in garantia["bloques"]:
        tipo = bloque["tipo"]
        if tipo == "firma":
            lineas = []
            if bloque.get("cierre"):
                lineas.append(("fuerte", bloque["cierre"]))
            lineas.append(("firma", bloque["firma"]))
            resultado.append({"indice": None, "titulo": None, "lineas": lineas})
            continue
        indice += 1
        lineas = []
        if tipo == "aviso":
            lineas.append(("parrafo", bloque["texto"]))
        elif tipo == "servicios":
            for lugar in bloque["lugares"]:
                lineas.append(("fuerte", f"{lugar['nombre']} · {lugar['lugar']}"))
                lineas.extend(("enlace", (texto, url)) for texto, url in lugar["links"])
            if bloque.get("turnos"):
                lineas.append(("enlace", tuple(bloque["turnos"])))
        elif tipo == "cobertura":
            if bloque.get("cubre"):
                lineas.append(("etiqueta", "Cubre"))
                lineas.extend(("item", texto) for texto in bloque["cubre"])
            lineas.append(("etiqueta", "No cubre"))
            lineas.extend(("item", texto) for texto in bloque["noCubre"])
        elif tipo == "destacado":
            numero, unidad = bloque["cifra"]
            lineas.append(("destacado", f"{numero} {unidad}: {bloque['texto']}"))
        elif tipo in ("requisitos", "lista"):
            lineas.extend(("item", texto) for texto in bloque["items"])
        elif tipo == "proceso":
            for paso in bloque["pasos"]:
                numero, unidad = paso["cifra"]
                lineas.append(("item", f"{paso['titulo']} ({numero} {unidad}): {paso['texto']}"))
        elif tipo == "opciones":
            for letra, opcion in zip("ABCDEFG", bloque["opciones"]):
                lineas.append(("item", f"{letra}. {opcion['titulo']}: {opcion['texto']}"))
        elif tipo == "excepciones":
            numero, unidad = bloque["cifra"]
            lineas.append(("excepcion", f"{numero} {unidad}: {bloque['cifraNota']}"))
            lineas.extend(("item", texto) for texto in bloque["items"])
        elif tipo == "importante":
            lineas.extend(("parrafo", texto) for texto in bloque["parrafos"])
            if bloque.get("cierre"):
                lineas.append(("fuerte", bloque["cierre"]))
        if bloque.get("nota"):
            lineas.append(("nota", bloque["nota"]))
        resultado.append({"indice": f"{indice:02d}", "titulo": bloque["titulo"], "lineas": lineas})
        if bloque.get("firma"):
            resultado.append({"indice": None, "titulo": None, "lineas": [("firma", bloque["firma"])]})
    return resultado


def texto_plano(clave):
    """La garantía completa como texto corrido (para búsquedas y tests)."""
    garantia = cargar()[clave]
    partes = [f"Garantía {garantia['titulo']}: {plazo_texto(garantia)}. {garantia['desde']}"]
    if garantia.get("alcance"):
        partes.append(garantia["alcance"])
    for seccion in secciones(garantia):
        if seccion["titulo"]:
            partes.append(f"{seccion['titulo']}:")
        for tipo, valor in seccion["lineas"]:
            partes.append(f"{valor[0]}: {valor[1]}" if tipo == "enlace" else valor)
    return " ".join(partes)
