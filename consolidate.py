from normalize import normalizar

# Palabras de relleno/marca que no distinguen un producto de otro. Al ignorarlas,
# "AIRPODS MAX" y "Apple Airpods Max" quedan como el mismo producto (se unifican).
_RELLENO = {
    "apple", "samsung", "xiaomi", "motorola", "moto", "celular", "smartphone",
    "original", "nuevo", "dual",
}


def _clave(nombre):
    # Clave de producto: tokens normalizados sin palabras de relleno/marca, ordenados.
    # Así el mismo producto escrito distinto (marca de más, specs en otro orden)
    # cae en la misma clave y se unifica al más barato.
    toks = set(normalizar(nombre).split()) - _RELLENO
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
        lista.append({
            "nombre": barato["nombre"],
            "costo": barato["costo"],
            "proveedor": barato["proveedor"],
        })

    return {"lista": lista, "duplicados_posibles": []}
