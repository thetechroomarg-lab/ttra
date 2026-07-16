import json

from consolidate import consolidar
from bands import calcular_precio
from imagelink import google_image_link


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
    if "samsung" in l or "galaxy" in l:
        return "Samsung"
    if any(b in l for b in ("xiaomi", "poco", "redmi")):
        return "Xiaomi"
    if l.startswith("moto") or "motorola" in l:
        return "Motorola"
    if "realme" in l:
        return "Realme"
    return "Otros"


def generar_productos(items, cotizacion):
    consolidados = consolidar(items)["lista"]
    productos = []
    for fila in consolidados:
        usd = calcular_precio(fila["costo"])
        pesos = round(usd * cotizacion)
        transferencia = round(pesos / 0.97)
        productos.append({
            "nombre": fila["nombre"],
            "categoria": _categoria(fila["nombre"]),
            "usd": usd,
            "pesos": pesos,
            "transferencia": transferencia,
            "link_imagen": google_image_link(fila["nombre"]),
        })
    return productos


def escribir_productos_json(items, cotizacion, ruta):
    productos = generar_productos(items, cotizacion)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)
    return productos
