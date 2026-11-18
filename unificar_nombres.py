"""Unifica el mismo producto cuando distintos proveedores lo nombran distinto.

Dos niveles:
1. Celulares: clave (modelo, almacenamiento, RAM). Ignora cargador/slim/NFC/dual,
   el orden de RAM/almacenamiento ("256/8gb", "8GB 256GB") y completa la RAM
   faltante si el modelo+almacenamiento tiene una sola RAM conocida.
2. Resto: clave genérica por tokens (sin orden, sin "gb/ram/ssd", sin marca
   Xiaomi/Motorola/Samsung). Conservadora: no ignora ningún otro dato.
"""
import collections
import re

PHONE = re.compile(r"\b(moto|samsung|poco|redmi|xiaomi|realme|infinix|oppo|zte|nokia|alcatel)\b|^[a-z]\d{2}s?\b", re.I)
NO_PHONE = re.compile(r"iphone|ipad|notebook|tablet|\bpad\b|watch|band|buds|power ?bank|vacuum|robot|aspira|scooter|patinete|smart ?lock|compresor|auricular|parlante|cargador|charger")
SUFIJOS = r"s/\s*cargador|sin cargador|con cargador"
FLAG_PREF = re.compile(r"s/\s*cargador|con cargador|sin cargador|slim|nfc", re.I)


def clave_celular(name):
    n = re.sub(SUFIJOS, " ", name.lower())
    if not PHONE.search(n) or NO_PHONE.search(n):
        return None
    n = re.sub(SUFIJOS + r"|caja grande\.?|\bdual\b|\bnfc\b|\bslim\b|\bturbo\b", " ", n)
    n = re.sub(r"\(.*?\)", " ", n)
    nums = [int(a) * (1024 if u == "tb" else 1) for a, u in re.findall(r"(\d+)\s*(gb|tb)", n)]
    for a, b in re.findall(r"(\d+)\s*[/-]\s*(\d+)\s*gb", n):
        nums += [int(a), int(b)]
    nums = sorted(set(nums))
    if not nums:
        return None
    storage, ram = max(nums), (min(nums) if len(nums) > 1 else None)
    base = re.sub(r"\d+\s*(gb|tb)\b|\b\d+\s*[/-]\s*\d+\s*(gb)?\b", " ", n)
    base = re.sub(r"\b(motorola|xiaomi|samsung)\b", " ", base)
    base = re.sub(r"\bredmi note\b", "note", base)
    base = re.sub(r"\bmi (?=\d)", "", base)
    if re.search(r"\bmoto\b", base) and re.search(r"\b(g47|g56|g67|g77|g86|edge)\b", base):
        base = re.sub(r"\b5g\b", " ", base)
    base = " ".join(re.sub(r"[^\w+]", " ", base).split())
    return ("cel", base, storage, ram)


def clave_generica(name):
    n = name.lower().replace("️", "")
    n = re.sub(r"\b(motorola|xiaomi|samsung)\b", " ", n)
    n = re.sub(r"(?<=\d)\s*(gb|tb)\b", " ", n)
    n = re.sub(r"\b(ram|ssd)\b", " ", n)
    toks = re.sub(r"[^a-z0-9+]+", " ", n).split()
    return ("gen",) + tuple(sorted(set(toks))) if len(toks) >= 3 else None


def unificar(items, previous_names=()):
    """Renombra in situ los items al nombre canónico. Devuelve el reporte."""
    previous_names = set(previous_names)
    keys = {id(i): clave_celular(i["nombre"]) for i in items}
    rams = collections.defaultdict(set)
    for i in items:
        k = keys[id(i)]
        if k and k[3]:
            rams[(k[1], k[2])].add(k[3])
    for i in items:
        k = keys[id(i)]
        if k and k[3] is None and len(rams.get((k[1], k[2]), ())) == 1:
            keys[id(i)] = k[:3] + (next(iter(rams[(k[1], k[2])])),)
    for i in items:  # lo que no es celular cae a la clave genérica
        if keys[id(i)] is None:
            keys[id(i)] = clave_generica(i["nombre"])
    grupos = collections.defaultdict(list)
    for i in items:
        if keys[id(i)]:
            grupos[keys[id(i)]].append(i)
    reporte = []
    for k, lst in grupos.items():
        nombres = list(dict.fromkeys(i["nombre"] for i in lst))
        if len(nombres) < 2:
            continue

        def pref(nm):
            return (bool(FLAG_PREF.search(nm)), nm not in previous_names,
                    -len(re.findall(r"\d+\s*gb", nm, re.I)), len(nm))

        canon = sorted(nombres, key=pref)[0]
        reporte.append({"clave": list(k), "nombres": nombres, "canonico": canon})
        for i in lst:
            i["nombre"] = canon
    return reporte
