import re

from normalize import normalizar

# Palabras de relleno/marca que no distinguen un producto de otro. Al ignorarlas,
# "AIRPODS MAX" y "Apple Airpods Max" quedan como el mismo producto (se unifican).
_RELLENO = {
    "apple", "samsung", "xiaomi", "redmi", "motorola", "moto", "celular", "smartphone",
    "original", "nuevo", "dual",
    # relleno de notebooks/Mac: no distinguen la config cuando chip+RAM+almacenamiento
    # coinciden (p. ej. "SSD", o los núcleos "10CPU 10GPU" que un proveedor omite).
    "ssd", "wifi",
}

# Tokens de cantidad de núcleos (10cpu, 8gpu, etc.): son relleno para el emparejamiento.
_NUCLEOS = re.compile(r"^\d+(cpu|gpu)$")

# La consola base PS5 se nombra distinto según el proveedor ("PS5 Digital 825GB" vs
# "PlayStation 5 Slim 825GB Digital") pero es el mismo producto — no confundir con la
# PS5 Pro ni con el combo que incluye el joystick DualSense.
_PS5_BASE = re.compile(r"(?i)\b(playstation\s*5|ps5)\b.*\b825\s*gb\b.*\bdigital\b|"
                        r"\b(playstation\s*5|ps5)\b.*\bdigital\b.*\b825\s*gb\b")
_PS5_EXCLUIR = re.compile(r"(?i)\bpro\b|\bdualsense\b|\bjoystick\b|\bcontrol\b")


# Alias de productos que cada proveedor nombra distinto (texto normalizado, regex).
_ALIAS = [
    (re.compile(r"\bairpods 4 (with )?(active )?noise cancellation\b"), "airpods 4 anc"),
    (re.compile(r"\bairpods pro 3(ra)?( g| generacion)?\b"), "airpods pro 3"),
    (re.compile(r"\bairpods pro 2(da)?( g| generacion)?\b"), "airpods pro 2"),
    (re.compile(r"\bairpods max( usb c| black)?$"), "airpods max"),
    (re.compile(r"^(?!.*\b(funda|ps4|xbox|retro)\b).*\b(joystick|dualsense)\b.*\b(playstation 5|ps5)\b.*$|"
                r"^(?!.*\b(funda|ps4|xbox|retro)\b).*\b(playstation 5|ps5)\b.*\b(joystick|dualsense)\b.*$"),
     "joystick ps5 dualsense"),
    (re.compile(r"\baluminum\b"), "aluminium"),
    (re.compile(r"\bwi fi\b"), ""),
    (re.compile(r"\b\d+ core (cpu|gpu)\b"), ""),
    (re.compile(r"\baspirador[a]?\b(?=.*\bvacuum\b)"), ""),
]

# Palabras que muchos proveedores omiten ("5G", "NFC", "Mi", "RAM"...): no distinguen
# el producto, salvo en las familias donde sí existen las dos versiones.
_BLANDAS = {"5g", "nfc", "mi", "ram", "pulgadas", "with"}
_CON_VERSION_4G = re.compile(r"\bnote (14|15|16|17)\b|\bredmi (15|16|17)\b(?! ?c)|\ba(06|07|16|17)\b")
_CON_VERSION_NFC = re.compile(r"\b15c\b")


def _clave(nombre):
    if _PS5_BASE.search(nombre) and not _PS5_EXCLUIR.search(nombre):
        nombre = "PS5 Digital 825GB"
    # Clave de producto: tokens normalizados sin palabras de relleno/marca ni núcleos
    # de CPU/GPU, ordenados. Así el mismo producto escrito distinto (marca de más,
    # specs en otro orden, "SSD"/"10CPU 10GPU" de más) cae en la misma clave.
    # Lista (no set): "MacBook Pro" + chip "M5 Pro" no deben perder la palabra "pro"
    # repetida — un set la colapsaría a una sola aparición y confundiría el chip base
    # (M5) con su variante Pro/Max (ver bug 2026-09-25: MacBook Pro M5 Pro se perdía
    # porque su clave quedaba igual a la del MacBook Pro M5 a secas).
    texto = normalizar(nombre)
    for patron, reemplazo in _ALIAS:
        texto = patron.sub(reemplazo, texto)
    blandas = set(_BLANDAS)
    if _CON_VERSION_4G.search(texto):
        blandas.discard("5g")
    if _CON_VERSION_NFC.search(texto):
        blandas.discard("nfc")
    toks = [t for t in texto.split()
            if t not in _RELLENO and t not in blandas and not _NUCLEOS.match(t)]
    # La MacBook Neo sólo existe en 13": el tamaño es relleno
    if "neo" in toks and "macbook" in toks and "13" in toks:
        toks.remove("13")
    return " ".join(sorted(toks))


# Siempre el proveedor más barato, sin excepciones (aunque tenga menos colores).
def _elegir_proveedor(grupo):
    return min(grupo, key=lambda x: x["costo"])


def consolidar(items):
    grupos = {}  # clave -> lista de items
    orden = []
    for it in items:
        clave = _clave(it["nombre"])
        if clave not in grupos:
            grupos[clave] = []
            orden.append(clave)
        grupos[clave].append(it)

    lista = []
    for clave in orden:
        grupo = grupos[clave]
        barato = _elegir_proveedor(grupo)
        fila = {
            "nombre": barato["nombre"],
            "costo": barato["costo"],
            "proveedor": barato["proveedor"],
        }
        if barato.get("colores"):
            fila["colores"] = barato["colores"]
        if barato.get("variantes"):
            fila["variantes"] = barato["variantes"]
        lista.append(fila)

    return {"lista": lista, "duplicados_posibles": []}
