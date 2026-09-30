import csv
import json
import math
import shutil
from datetime import date
from pathlib import Path

from web.mayoristas import catalogo_mayorista
from xlsx_writer import escribir_xlsx


ROOT = Path("/Users/toraba/TTRA Project")
DEST = Path("/Users/toraba/Precios Claude")
WEB = ROOT / "web"
COTIZACION = 1565

CELULARES = {"Apple - iPhone", "Apple - iPhone Usado", "Samsung", "Xiaomi", "Motorola", "Realme"}
NOTEBOOKS = {"Notebook", "Mac"}


def grupo(producto):
    categoria = producto.get("categoria", "Otros")
    if categoria in CELULARES:
        return "Celulares"
    if categoria in NOTEBOOKS:
        return "Notebooks_Macbooks"
    return "Accesorios"


def emoji(producto):
    return {"Celulares": "📱", "Notebooks_Macbooks": "💻"}.get(grupo(producto), "📦")


def colores(producto):
    return ", ".join(producto.get("colores") or [])


def escribir_csvs(productos):
    for nombre in ("Celulares", "Notebooks_Macbooks", "Accesorios"):
        with (DEST / f"{nombre}.csv").open("w", encoding="utf-8", newline="") as archivo:
            writer = csv.writer(archivo)
            writer.writerow(["Emoji", "Producto", "Colores", "USD"])
            for producto in productos:
                if grupo(producto) == nombre:
                    writer.writerow([emoji(producto), producto["nombre"], colores(producto), producto["usd"]])


def escribir_mayorista(productos, costos):
    mayoristas = catalogo_mayorista(productos, costos)
    with (DEST / "Lista_Mayorista.csv").open("w", encoding="utf-8", newline="") as archivo:
        writer = csv.writer(archivo)
        writer.writerow(["Producto", "Precio USD"])
        for producto in mayoristas:
            writer.writerow([producto["nombre"], producto["usd"]])
    lista = [
        {
            "nombre": p["nombre"],
            "link": p.get("link_imagen", ""),
            "pais": "🇺🇸",
            "precio": p["usd"],
        }
        for p in mayoristas
    ]
    escribir_xlsx(lista, {"filtrados": [], "duplicados_posibles": [], "dudas_precio": []}, DEST / "Lista_Mayorista.xlsx")
    return mayoristas


def linea(producto):
    detalle = f" Colores disponibles: {colores(producto)}" if colores(producto) else ""
    return f"{emoji(producto)}\t{producto['nombre']}{detalle}\t🇺🇸\t{producto['usd']}"


def escribir_textos(productos, proveedores):
    por_grupo = {
        "TTRA_Celulares.txt": [p for p in productos if grupo(p) == "Celulares"],
        "TTRA_Notebooks.txt": [p for p in productos if grupo(p) == "Notebooks_Macbooks"],
        "TTRA_Accesorios.txt": [p for p in productos if grupo(p) == "Accesorios"],
    }
    for archivo, filas in por_grupo.items():
        titulo = archivo.removeprefix("TTRA_").removesuffix(".txt").replace("_", " ").upper()
        contenido = [f"⚫ {titulo}", ""] + [linea(p) for p in filas]
        (DEST / archivo).write_text("\n".join(contenido) + "\n", encoding="utf-8")

    encabezado = [
        "WhatsApp: https://wa.me/543512145217",
        "Web: www.thetechroomarg.com — los pedidos se hacen a través de la plataforma",
        "",
        "THE TECH ROOM ARG",
        "",
        f"📅 {date.today().strftime('%d/%m/%Y')}",
        f"💵 Dólar: ${COTIZACION} (puede variar sin previo aviso)",
        "📄 Precios en dólares, pesos y transferencia en pesos",
        "",
    ]
    bloques = []
    for p in productos:
        pesos = round(p["usd"] * COTIZACION)
        transferencia = round(pesos / 0.97)
        bloques.extend([
            f"{emoji(p)} {p['nombre']}" + (f" — Colores: {colores(p)}" if colores(p) else ""),
            f"🇺🇸 ${p['usd']} · 🇦🇷 ${pesos} · 🏦 ${transferencia}",
            p.get("link_imagen", ""),
            "",
        ])
    mitad = math.ceil(len(bloques) / 8) * 4
    (DEST / "TTRA_Listado_completo_Parte1.txt").write_text("\n".join(encabezado + bloques[:mitad]), encoding="utf-8")
    (DEST / "TTRA_Listado_completo_Parte2.txt").write_text("\n".join(encabezado + bloques[mitad:]), encoding="utf-8")

    oh = [p for p in productos if proveedores.get(p["nombre"]) == "oh"]
    (DEST / "TTRA_OH_Ganadores.txt").write_text(
        "⚫ PRODUCTOS OH GANADORES\n\n" + "\n".join(linea(p) for p in oh) + "\n",
        encoding="utf-8",
    )


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    productos = json.loads((WEB / "productos.json").read_text(encoding="utf-8"))
    costos = json.loads((WEB / "costos.json").read_text(encoding="utf-8"))
    proveedores = json.loads((WEB / "proveedores.json").read_text(encoding="utf-8"))
    escribir_csvs(productos)
    mayoristas = escribir_mayorista(productos, costos)
    escribir_textos(productos, proveedores)
    shutil.copy2(
        ROOT / "outputs/catalogo_20260921/catalogo_actualizado_2026-09-21.xlsx",
        DEST / "Lista_Consolidada_2026-09-21.xlsx",
    )
    print(json.dumps({"productos": len(productos), "mayoristas": len(mayoristas)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
