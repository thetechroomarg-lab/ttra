#!/usr/bin/env python3
"""Busca un producto en las listas consolidadas y calcula los 5 precios.

Uso:
    python3 consultar_precio.py "s26 ultra"
    python3 consultar_precio.py "s26 ultra" --cotizacion 1575
    python3 consultar_precio.py "s26 ultra" --mayorista
    python3 consultar_precio.py --listar Celulares
"""

import argparse
import csv
import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode

PRECIOS_DIR = Path("/Users/toraba/Precios Claude")
PROJECT_DIR = Path(__file__).resolve().parents[4]
APP_PY = PROJECT_DIR / "web" / "app.py"
COSTOS_JSON = PROJECT_DIR / "web" / "costos.json"
PROVEEDORES_JSON = PROJECT_DIR / "web" / "proveedores.json"

sys.path.insert(0, str(PROJECT_DIR / "web"))
try:
    from mayoristas import descuento_por_margen
except ImportError:
    descuento_por_margen = None

PRODUCTOS_JSON = PROJECT_DIR / "web" / "productos.json"
BASE_URL = "https://www.thetechroomarg.com"

MAYORISTA = PRECIOS_DIR / "Lista_Mayorista.csv"

TRANSFERENCIA_USD_DIVISOR = 0.975  # ceil(usd / 0.975), igual que web/app.py:461
USDT_DIVISOR = 0.99  # ceil(usd / 0.99), igual que web/app.py:462
TRANSFERENCIA_PESOS_DIVISOR = 0.97  # round(pesos / 0.97), igual que web/productos.json

_CATEGORIAS_CELULAR = {
    "Apple - iPhone", "Apple - iPhone Usado", "Samsung", "Xiaomi", "Motorola", "Realme",
}
_CATEGORIAS_NOTEBOOK = {"Notebook", "Mac"}


def _grupo(categoria):
    if categoria in _CATEGORIAS_CELULAR:
        return "Celulares"
    if categoria in _CATEGORIAS_NOTEBOOK:
        return "Notebooks_Macbooks"
    return "Accesorios"


def _emoji(categoria):
    if categoria in _CATEGORIAS_CELULAR:
        return "📱"
    if categoria in _CATEGORIAS_NOTEBOOK:
        return "💻"
    return "📦"


def cotizacion_actual():
    """Lee COTIZACION_DOLAR de web/app.py. Si no lo encuentra, obliga a pasar --cotizacion."""
    if APP_PY.exists():
        m = re.search(r"COTIZACION_DOLAR\s*=\s*(\d+)", APP_PY.read_text())
        if m:
            return int(m.group(1))
    return None


def cargar_todo():
    """Fuente única de verdad: web/productos.json — el mismo archivo que sirve la web
    en producción. NO usar los CSV de /Users/toraba/Precios Claude para precios: quedan
    desactualizados cada vez que se regenera el catálogo sin regenerarlos a ellos
    también (bug detectado 2026-09-18, ver memoria feedback-precios-fuente-productos-json)."""
    if not PRODUCTOS_JSON.exists():
        return []
    productos = json.loads(PRODUCTOS_JSON.read_text(encoding="utf-8"))
    filas = []
    for p in productos:
        categoria = p.get("categoria", "Otros")
        filas.append({
            "Producto": p.get("nombre", ""),
            "Colores": ", ".join(p.get("colores") or []),
            "USD": p.get("usd"),
            "_categoria": _grupo(categoria),
            "Emoji": _emoji(categoria),
        })
    return filas


def cargar_mayorista():
    filas = []
    if not MAYORISTA.exists():
        return filas
    with open(MAYORISTA, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            filas.append(row)
    return filas


def cargar_costos():
    if not COSTOS_JSON.exists():
        return {}
    return json.loads(COSTOS_JSON.read_text())


def calcular_mayorista_en_vivo(nombre, usd_publico):
    """Calcula el precio mayorista con la fórmula real de web/mayoristas.py
    (margen-based), a partir de costos.json — más confiable que
    Lista_Mayorista.csv, que puede quedar desactualizado si no se
    regenera cada vez que cambia costos.json."""
    if descuento_por_margen is None:
        return None, "no se pudo importar web/mayoristas.py"
    costos = cargar_costos()
    costo = costos.get(nombre)
    if costo is None:
        return None, f"'{nombre}' no está en costos.json"
    descuento = descuento_por_margen(usd_publico, costo)
    if descuento is None:
        return None, f"margen insuficiente (costo {costo}, público {usd_publico}) — no elegible para mayorista"
    return usd_publico - descuento, None


def buscar(termino, filas, campo="Producto"):
    termino_norm = termino.strip().lower()
    palabras = termino_norm.split()
    resultados = []
    for row in filas:
        nombre = (row.get(campo) or "").lower()
        if all(p in nombre for p in palabras):
            resultados.append(row)
    return resultados


def calcular_precios(usd, cotizacion):
    usd = int(round(usd))
    transferencia_usd = math.ceil(usd / TRANSFERENCIA_USD_DIVISOR)
    usdt = math.ceil(usd / USDT_DIVISOR)
    pesos = round(usd * cotizacion)
    transferencia_pesos = round(pesos / TRANSFERENCIA_PESOS_DIVISOR)
    return {
        "usd": usd,
        "transferencia_usd": transferencia_usd,
        "usdt": usdt,
        "pesos": pesos,
        "transferencia_pesos": transferencia_pesos,
    }


def es_usado(nombre):
    return "usado" in nombre.lower()


def es_iphone(nombre):
    return "iphone" in nombre.lower()


def accesorios_incluidos(categoria, nombre):
    base = ["bolsa", "escarapela", "calcomanía", "llavero"]
    if categoria == "Celulares":
        if es_iphone(nombre) and not es_usado(nombre):
            return base + ["cargador original gratis"]
        return base
    if categoria == "Notebooks_Macbooks":
        return ["bolsa tamaño notebook", "llavero", "escarapela", "calcomanía", "mouse pad"]
    return base


def formatear_pesos(n):
    return f"{n:,}".replace(",", ".")


def link_producto(termino):
    """Link real de producción — el mismo que arma "compartir producto" en la
    web (ver web/static/landing.js:compartirProducto): https://www.thetechroomarg.com/?producto=<nombre>.
    Busca `termino` en web/productos.json (fuente canónica del nombre — el
    CSV local puede tener el nombre levemente distinto, ej. sin prefijo de
    marca). None si no hay match único o faltan las piezas."""
    if not PRODUCTOS_JSON.exists():
        return None
    productos = json.loads(PRODUCTOS_JSON.read_text(encoding="utf-8"))
    palabras = termino.strip().lower().split()
    candidatos = [p for p in productos if all(pa in (p.get("nombre") or "").lower() for pa in palabras)]
    if len(candidatos) != 1:
        return None
    nombre = candidatos[0]["nombre"]
    return f"{BASE_URL}/?{urlencode({'producto': nombre})}"


def cargar_proveedores():
    if not PROVEEDORES_JSON.exists():
        return {}
    return json.loads(PROVEEDORES_JSON.read_text(encoding="utf-8"))


def _antiguedad_dias(path):
    return (date.today() - datetime.fromtimestamp(path.stat().st_mtime).date()).days


def buscar_proveedor(nombre):
    """Busca en web/proveedores.json + web/costos.json — el mismo par de
    archivos que usa la web en producción (resolver_proveedor en
    web/productos.py), generados juntos en cada regeneración de catálogo así
    que siempre están sincronizados entre sí. Devuelve
    (sigla_o_None, costo_o_None, antiguedad_dias_o_None, motivo_si_no_hay)."""
    if not PROVEEDORES_JSON.exists() or not COSTOS_JSON.exists():
        return None, None, None, "no se encontró web/proveedores.json o web/costos.json"
    proveedores = cargar_proveedores()
    costos = cargar_costos()
    sigla = proveedores.get(nombre)
    costo = costos.get(nombre)
    if sigla is None and costo is None:
        return None, None, None, f"'{nombre}' no está en proveedores.json/costos.json (nombre no matchea)"
    antiguedad = _antiguedad_dias(PROVEEDORES_JSON)
    return sigla, costo, antiguedad, None


def mostrar_producto(row, cotizacion, es_mayorista=False):
    categoria = row.get("_categoria", "Mayorista")
    nombre = row.get("Producto") or ""
    colores = row.get("Colores", "")
    usd_key = "Precio USD" if es_mayorista else "USD"
    usd = row.get(usd_key)
    if usd in (None, ""):
        print(f"(sin precio USD para {nombre})")
        return
    usd = float(usd)
    precios = calcular_precios(usd, cotizacion)

    print(f"{row.get('Emoji', '📦')} {nombre}")
    if colores:
        print(f"Colores disponibles: {colores}")
    print(f"🇺🇸 U$D {precios['usd']}")
    print(f"🏦 U$D {precios['transferencia_usd']} (transferencia exterior)")
    print(f"🪙 USDT {precios['usdt']}")
    print(f"🇦🇷 ${formatear_pesos(precios['pesos'])} (pesos contado)")
    print(f"🏦 ${formatear_pesos(precios['transferencia_pesos'])} (transferencia pesos)")

    link = link_producto(nombre)
    if link:
        print(f"🔗 {link}")
    else:
        print("🔗 (no se encontró un link único de producción para este nombre — revisar a mano)")

    if es_usado(nombre):
        print("⚠️  Es un equipo USADO — agregar el disclaimer de condiciones (ver memoria: disclaimer-iphones-usados).")

    sigla, costo, antiguedad, motivo = buscar_proveedor(nombre)
    print()
    print("--- Nota interna (NO mostrar al cliente) ---")
    if motivo:
        print(f"Proveedor: no disponible ({motivo})")
    else:
        aviso = f"(último catálogo regenerado hace {antiguedad} día(s))"
        partes = []
        if sigla:
            partes.append(f"proveedor {sigla}")
        if costo is not None:
            margen = round(usd - costo, 2)
            partes.append(f"costo USD {costo} (margen ${margen})")
        print(f"{' — '.join(partes) if partes else 'sin datos'} {aviso}")
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("termino", nargs="?", help="texto a buscar en el nombre del producto")
    ap.add_argument("--cotizacion", type=float, help="cotización del dólar a usar (si no, se lee de web/app.py)")
    ap.add_argument("--mayorista", action="store_true", help="calcular precio mayorista en vivo (costos.json + web/mayoristas.py)")
    ap.add_argument("--listar", choices=["Celulares", "Accesorios", "Notebooks_Macbooks"], help="listar todos los productos de una categoría")
    args = ap.parse_args()

    cotizacion = args.cotizacion or cotizacion_actual()
    if cotizacion is None:
        print("No se pudo determinar la cotización del dólar. Pasá --cotizacion <valor>.", file=sys.stderr)
        sys.exit(1)

    if args.listar:
        filas = [f for f in cargar_todo() if f["_categoria"] == args.listar]
        for row in filas:
            print(f"{row.get('Emoji','')} {row.get('Producto','')} — USD {row.get('USD','')}")
        return

    if not args.termino:
        ap.print_help()
        sys.exit(1)

    if args.mayorista:
        filas = cargar_todo()
        resultados = buscar(args.termino, filas)
        if not resultados:
            print(f"No se encontraron coincidencias para '{args.termino}'.")
            return
        for row in resultados:
            nombre = row.get("Producto") or ""
            usd_publico = row.get("USD")
            if usd_publico in (None, ""):
                continue
            usd_publico = float(usd_publico)
            usd_mayorista, motivo = calcular_mayorista_en_vivo(nombre, usd_publico)
            print(f"{row.get('Emoji', '📦')} {nombre}")
            if usd_mayorista is None:
                print(f"(no se pudo calcular mayorista en vivo: {motivo})")
                # fallback: mostrar el valor del CSV estático si existe
                fila_csv = buscar(nombre, cargar_mayorista())
                if fila_csv:
                    mostrar_producto(fila_csv[0], cotizacion, es_mayorista=True)
                print()
                continue
            precios = calcular_precios(usd_mayorista, cotizacion)
            print(f"🇺🇸 U$D {precios['usd']} (mayorista, calculado en vivo desde costos.json)")
            print(f"🏦 U$D {precios['transferencia_usd']} (transferencia exterior)")
            print(f"🪙 USDT {precios['usdt']}")
            print(f"🇦🇷 ${formatear_pesos(precios['pesos'])} (pesos contado)")
            print(f"🏦 ${formatear_pesos(precios['transferencia_pesos'])} (transferencia pesos)")
            print()
        return

    filas = cargar_todo()
    resultados = buscar(args.termino, filas)
    if not resultados:
        print(f"No se encontraron coincidencias para '{args.termino}'.")
        return
    for row in resultados:
        mostrar_producto(row, cotizacion)


if __name__ == "__main__":
    main()
