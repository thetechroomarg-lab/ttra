from normalize import normalizar

# Palabras de relleno/marca que no distinguen un producto de otro. Al ignorarlas,
# "AIRPODS MAX" y "Apple Airpods Max" quedan iguales (mismo producto, otro nombre).
_RELLENO = {
    "apple", "samsung", "xiaomi", "motorola", "moto", "celular", "smartphone",
    "original", "nuevo", "dual",
}


def consolidar(items):
    grupos = {}  # clave normalizada -> lista de items (preserva orden de aparición)
    orden = []
    for it in items:
        clave = normalizar(it["nombre"])
        if clave not in grupos:
            grupos[clave] = []
            orden.append(clave)
        grupos[clave].append(it)

    lista = []
    prov_rep = {}  # clave normalizada -> proveedor del ítem más barato (el que va a la lista)
    for clave in orden:
        grupo = grupos[clave]
        barato = min(grupo, key=lambda x: x["costo"])
        prov_rep[clave] = barato["proveedor"]
        lista.append({
            "nombre": barato["nombre"],
            "costo": barato["costo"],
            "proveedor": barato["proveedor"],
        })

    # Posibles duplicados: mismo producto escrito distinto entre proveedores DISTINTOS.
    # Se reporta solo si, al ignorar palabras de relleno/marca, los tokens son idénticos
    # (ej. "AIRPODS MAX" vs "Apple Airpods Max"). Modelos distintos que comparten
    # palabras (16 vs 15 Pro Max) NO se reportan.
    duplicados_posibles = []
    for i in range(len(orden)):
        for j in range(i + 1, len(orden)):
            if prov_rep[orden[i]] == prov_rep[orden[j]]:
                continue
            ta = set(orden[i].split()) - _RELLENO
            tb = set(orden[j].split()) - _RELLENO
            if ta and ta == tb:
                duplicados_posibles.append({
                    "nombre_a": grupos[orden[i]][0]["nombre"],
                    "nombre_b": grupos[orden[j]][0]["nombre"],
                    "similitud": 1.0,
                })

    return {"lista": lista, "duplicados_posibles": duplicados_posibles}
