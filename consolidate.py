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


def _clave(nombre):
    if _PS5_BASE.search(nombre) and not _PS5_EXCLUIR.search(nombre):
        nombre = "PS5 Digital 825GB"
    # Clave de producto: tokens normalizados sin palabras de relleno/marca ni núcleos
    # de CPU/GPU, ordenados. Así el mismo producto escrito distinto (marca de más,
    # specs en otro orden, "SSD"/"10CPU 10GPU" de más) cae en la misma clave.
    toks = {t for t in normalizar(nombre).split()
            if t not in _RELLENO and not _NUCLEOS.match(t)}
    return " ".join(sorted(toks))


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
        barato = min(grupo, key=lambda x: x["costo"])
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
