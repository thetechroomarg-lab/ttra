from normalize import normalizar

_UMBRAL_SIMILITUD = 0.6


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

    # Posibles duplicados: solo entre proveedores DISTINTOS (que es cuando sirve para
    # elegir el más barato). Pares del mismo proveedor no se reportan (ruido).
    duplicados_posibles = []
    for i in range(len(orden)):
        for j in range(i + 1, len(orden)):
            if prov_rep[orden[i]] == prov_rep[orden[j]]:
                continue
            ta = set(orden[i].split())
            tb = set(orden[j].split())
            if not ta or not tb:
                continue
            jaccard = len(ta & tb) / len(ta | tb)
            if jaccard >= _UMBRAL_SIMILITUD:
                duplicados_posibles.append({
                    "nombre_a": grupos[orden[i]][0]["nombre"],
                    "nombre_b": grupos[orden[j]][0]["nombre"],
                    "similitud": round(jaccard, 2),
                })

    return {"lista": lista, "duplicados_posibles": duplicados_posibles}
