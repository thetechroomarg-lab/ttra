import json
from pathlib import Path
import re

from consolidate import consolidar
from bands import calcular_precio, calcular_precio_celular
from imagelink import google_image_link

_SLIM = re.compile(r"(?i)\bslim\b")
_MARCAS_SLIM = ("xiaomi", "poco", "redmi", "moto", "motorola", "samsung", "galaxy")
_SIN_CARGADOR = re.compile(r"(?i)\bs/cargador\b|\bslim\b")


def _sin_cargador(nombre):
    # "slim" en celulares Xiaomi/Motorola/Samsung significa sin cargador en la caja.
    if any(m in nombre.lower() for m in _MARCAS_SLIM):
        return _SLIM.sub("s/cargador", nombre)
    return nombre


# La línea Note es la misma línea de producto sea que el proveedor la llame "Xiaomi
# Note", "Redmi Note" o directamente "Note" (sin marca) — se estandariza el nombre
# para no mostrarle al cliente 3 variantes de marca del mismo modelo.
_NOTE_PREFIJO = re.compile(r"(?i)^(?:xiaomi\s+)?(?:redmi\s+)?note\s+(?=\d)")


def _nombre_estandar_note(nombre):
    return _NOTE_PREFIJO.sub("Xiaomi Redmi Note ", nombre)


# Algunos proveedores (ej. AZ) mandan el nombre del modelo sin la marca (ej. "A17 5G
# 6GB 128GB" en vez de "Samsung A17..."). Estos patrones de código de modelo permiten
# reconocer la marca aunque la palabra no esté en el nombre.
_SAMSUNG_MODELO = re.compile(r"(?i)\ba\d{2}\b|\bs2[0-9]\b|\bf1[0-9]\b|\bz\s*(flip|fold)\b")
_XIAOMI_NOTE = re.compile(r"(?i)\bnote\s*1[0-9]\b")

# Modelos Redmi/POCO/Mi que algunos proveedores mandan sin la marca en el
# nombre (ej. "C71 3GB 64GB", "F7 5G 12GB 256GB", "NOTE 70 4GB 128GB"). Van
# anclados al inicio del nombre porque son justo el primer token de estas
# filas — así no confunden specs sueltas de otros productos (ej. una
# notebook con pantalla de "15.6"").
_XIAOMI_MODELO = re.compile(
    r"(?i)^(?:"
    r"c7[15]x?|c8[15](?:\s*pro)?|"           # Redmi C: C71, C75X, C81(-PRO), C85
    r"f[678](?:\s*(?:pro|ultra))?|"          # POCO F: F6/F7/F8 (PRO/ULTRA)
    r"m[78](?:\s*pro)?|"                     # POCO M: M7/M8 (PRO)
    r"x[78](?:\s*(?:pro|ultra))?(?:\s*max)?|"  # POCO X: X7/X8 (PRO/ULTRA/MAX)
    r"a[457](?:\s*pro)?|"                    # Redmi A: A4/A5/A7 (PRO)
    r"note\s*\d+[a-z]?x?|"                   # Redmi Note: NOTE 14S/60X/70
    r"mi\s+(?:band|buds|\d+[a-z]?)|"         # Mi-branded: MI BAND, MI BUDS, Mi 17/17T...
    r"1[4-7]c?t?(?:\s*ultra)?"               # Redmi numerado: 14C, 15(C/T), 17(T/ULTRA)
    r")(?=\s|$)"
)

# Marcas de PC (HP/Dell/Lenovo/Asus/Acer/MSI/Gigabyte) suelen mandarse sin la palabra
# "notebook"/"laptop" en el nombre (ej. "HP 15-EF0022 Ryzen 7 ... SSD ..."). Si el nombre
# tiene la marca de PC Y una spec típica de notebook, es notebook.
_MARCA_PC = re.compile(r"(?i)\b(hp|dell|lenovo|asus|acer|msi|gigabyte)\b")
_SPEC_NOTEBOOK = re.compile(r"(?i)\bssd\b|\bryzen\b|core\s*i\d|\bghz\b|\bwin(dows)?\s*1[01]\b")


def _categoria(nombre):
    l = nombre.lower()
    if "iphone" in l:
        return "Apple - iPhone" if "usad" not in l else "Apple - iPhone Usado"
    if "ipad" in l:
        return "Apple - iPad"
    if "airpod" in l:
        return "Apple - AirPods"
    if "watch" in l:
        return "Apple - Watch"
    if "macbook" in l or "mac mini" in l or "macmini" in l or "imac" in l:
        return "Mac"
    if "notebook" in l or "laptop" in l:
        return "Notebook"
    if _MARCA_PC.search(l) and _SPEC_NOTEBOOK.search(l):
        return "Notebook"
    if "samsung" in l or "galaxy" in l or _SAMSUNG_MODELO.search(l):
        return "Samsung"
    if any(b in l for b in ("xiaomi", "poco", "redmi")) or _XIAOMI_NOTE.search(l) or _XIAOMI_MODELO.search(l):
        return "Xiaomi"
    if l.startswith("moto") or "motorola" in l:
        return "Motorola"
    if "realme" in l:
        return "Realme"
    return "Otros"


_EXCLUIR_KW = ("modulo", "módulo", "bateria", "batería", "pantalla", "perfume", "edp",
               "edt", "vaper", "vape", "paleta", "padel", "pádel",
               "caja abierta", "caja abollada", "caja manchada")


def _excluido(nombre):
    l = nombre.lower()
    return any(k in l for k in _EXCLUIR_KW)


# Todo lo que NO es un celular en sí (accesorios, wearables, tablets, notebooks, etc.),
# aunque la marca coincida con Samsung/Xiaomi/Motorola/Realme por nombre. Se usa para
# no aplicarle a estos la regla de margen mínimo/extra de celulares.
_NO_CELULAR_KW = (
    "tablet", "ipad", "watch", "cargador", "cable", "airpod", "auricular", "buds",
    "earphone", "audifono", "amazfit", "haylou", "robot", "vacuum", "aspiradora",
    "camara", "cámara", "drone", "monopatin", "monopatín", "scooter", "cerradura",
    "lock", "parlante", "speaker", "jbl", "consola", "joystick", "volante",
    "nintendo", "playstation", "xbox", "game console", "tag", "localizador",
    "pencil", "keyboard", "mouse", "ring", "anillo", "monitor", "mini pc",
    "repetidor", "extensor", "cartucho", "gafas", "quest", "shaver", "afeitadora",
    "band", "fanny pack", "mochila", "power bank", "instax", "radio",
    "terminal pos", "lavadora", "cafetera", "humidifier", "lampara", "lamp",
    "pilas", "destornillador", "lint remover", "daypack", "lonchera", "termo",
    "botella", "bolso", "stick tripod", "tv stick", "e-reader", "conversor",
    "kindle", "printer", "impresora", "scale", "router", "smart plug",
    "enchufe inteligente",
)

# Marcas de otros celulares que el clasificador de categoría general manda a "Otros"
# (no tienen su propia categoría dedicada) pero SÍ son celulares Android.
_OTRAS_MARCAS_CEL = re.compile(
    r"(?i)\bnokia\b|\binfinix\b|\boppo\b|\balcatel\b|\bhonor\b|\bhuawei\b|\bcat\b|"
    r"\bcelular\b|\bitel\b"
)

_MARCAS_ANDROID_CATEGORIA = {"Samsung", "Motorola", "Xiaomi", "Realme"}


def _celular_y_android(nombre, categoria):
    l = nombre.lower()
    if any(k in l for k in _NO_CELULAR_KW):
        return False, False
    if categoria in _MARCAS_ANDROID_CATEGORIA:
        return True, True
    if categoria in ("Apple - iPhone", "Apple - iPhone Usado"):
        return True, False
    if categoria == "Otros" and _OTRAS_MARCAS_CEL.search(l):
        return True, True
    return False, False


def generar_productos(items, cotizacion):
    consolidados = consolidar(items)["lista"]
    productos = []
    for fila in consolidados:
        if _excluido(fila["nombre"]):
            continue
        categoria = _categoria(fila["nombre"])
        es_celular, es_android = _celular_y_android(fila["nombre"], categoria)
        if es_celular:
            es_iphone = categoria in ("Apple - iPhone", "Apple - iPhone Usado")
            usd = calcular_precio_celular(fila["costo"], es_android, es_iphone)
        else:
            usd = calcular_precio(fila["costo"])
        pesos = round(usd * cotizacion)
        transferencia = round(pesos / 0.97)
        producto = {
            "nombre": _nombre_estandar_note(_sin_cargador(fila["nombre"])),
            "categoria": categoria,
            "usd": usd,
            "pesos": pesos,
            "transferencia": transferencia,
            "link_imagen": google_image_link(fila["nombre"]),
        }
        if fila.get("colores"):
            producto["colores"] = fila["colores"]
        if fila.get("variantes"):
            producto["variantes"] = fila["variantes"]
        productos.append(producto)
    return productos


def generar_proveedores(items):
    """Devuelve el proveedor elegido por producto para uso interno."""
    proveedores = {}
    for fila in consolidar(items)["lista"]:
        if _excluido(fila["nombre"]):
            continue
        nombre = _nombre_estandar_note(_sin_cargador(fila["nombre"]))
        proveedores[nombre] = fila.get("proveedor") or "Proveedor no identificado"
    return proveedores


def generar_costos(items):
    """Devuelve el costo consolidado por producto para uso privado."""
    return {
        _nombre_estandar_note(_sin_cargador(fila["nombre"])): fila["costo"]
        for fila in consolidar(items)["lista"]
        if not _excluido(fila["nombre"])
    }


def resolver_proveedor(proveedores, nombre):
    """Resuelve un proveedor aplicando la normalización del catálogo público."""
    if not nombre:
        return "Proveedor no identificado"
    nombre_normalizado = _nombre_estandar_note(_sin_cargador(nombre))
    proveedor = proveedores.get(nombre) or proveedores.get(nombre_normalizado)
    if proveedor:
        return proveedor

    # Algunos pedidos históricos conservaron "slim" donde la lista actual
    # dice "s/cargador". Solo aceptamos ese fallback cuando hay un único
    # producto candidato, para no atribuir un proveedor equivocado.
    def simplificar(valor):
        return " ".join(_SIN_CARGADOR.sub("", valor).split()).casefold()

    candidatos = {
        proveedor for producto, proveedor in proveedores.items()
        if simplificar(producto) == simplificar(nombre_normalizado)
    }
    return candidatos.pop() if len(candidatos) == 1 else "Proveedor no identificado"


def escribir_productos_json(items, cotizacion, ruta):
    productos = generar_productos(items, cotizacion)
    ruta = Path(ruta)
    with ruta.open("w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)
    with ruta.with_name("proveedores.json").open("w", encoding="utf-8") as f:
        json.dump(generar_proveedores(items), f, ensure_ascii=False, indent=2)
    with ruta.with_name("costos.json").open("w", encoding="utf-8") as f:
        json.dump(generar_costos(items), f, ensure_ascii=False, indent=2)
    return productos
