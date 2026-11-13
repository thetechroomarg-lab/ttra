"""Genera las versiones grandes (hasta 1100 px) que usa el visor al tocar una card.

Cada imagen del catálogo (web/static/catalog-images/X.webp, 640 px) tiene su versión grande en
web/static/catalog-images/zoom/X.webp. El visor la pide recién al tocar; si no existe, usa la chica.

Fuentes, en orden:
  1. catalogo-imagenes-originales/X.webp   (originales sin pérdida del banco, ya recortados)
  2. outputs/catalogo-imagenes/assets/*.png (originales 1254 px; si no traen transparencia se
     recortan con scripts/recortar_fondo.swift, solo macOS)

Uso: python scripts/generar_zoom_imagenes.py [--forzar]
"""
import json
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web/static/catalog-images"
ZOOM = WEB / "zoom"
ORIGINALES = RAIZ / "catalogo-imagenes-originales"
ASSETS = RAIZ / "outputs/catalogo-imagenes/assets"
LADO = 1100


def archivos_del_catalogo():
    index = json.loads((WEB / "index.json").read_text())
    return sorted({
        v["src"][len("/catalog-images/"):] for vs in index.values() for v in vs
        if v.get("src", "").startswith("/catalog-images/") and "/usados/" not in v["src"] and "placeholder" not in v["src"]
    })


def fuente_png(nombre):
    base = nombre[:-5]
    base = base[:-4] if base.endswith("-cut") else base
    for c in (ASSETS / f"{base}.png", ASSETS / f"{base.replace('-v2', '')}.png"):
        if c.exists():
            return c
    return None


def tiene_alpha(im):
    return "A" in im.getbands() and im.getchannel("A").getextrema()[0] < 250


def normalizar(im):
    """Mismo encuadre que las imágenes chicas recortadas: bbox + 6% de aire, cuadrado."""
    im = im.convert("RGBA")
    caja = im.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    im = im.crop(caja)
    s = max(im.size)
    pad = int(s * 0.06)
    lienzo = Image.new("RGBA", (s + 2 * pad,) * 2, (0, 0, 0, 0))
    lienzo.paste(im, ((lienzo.width - im.width) // 2, (lienzo.height - im.height) // 2))
    return lienzo


def guardar(args):
    nombre, origen, recortado = args
    im = Image.open(origen)
    im.load()
    im = normalizar(im) if recortado else im.convert("RGBA")
    im.thumbnail((LADO, LADO), Image.LANCZOS)
    im.save(ZOOM / nombre, "WEBP", quality=80, method=4)
    return nombre


def main(forzar=False):
    ZOOM.mkdir(exist_ok=True)
    tareas, a_recortar, sin_fuente = [], {}, []
    for nombre in archivos_del_catalogo():
        if (ZOOM / nombre).exists() and not forzar:
            continue
        if (ORIGINALES / nombre).exists():
            tareas.append((nombre, ORIGINALES / nombre, True))
            continue
        png = fuente_png(nombre)
        if png is None:
            sin_fuente.append(nombre)
            continue
        if tiene_alpha(Image.open(png)):
            tareas.append((nombre, png, nombre.endswith("-cut.webp")))
        else:
            a_recortar[nombre] = png
    if a_recortar:
        tmp = Path(tempfile.mkdtemp(prefix="zoom-recorte-"))
        (tmp / "in").mkdir()
        for nombre, png in a_recortar.items():
            shutil.copy(png, tmp / "in" / (nombre[:-5] + ".png"))
        exe = tmp / "recortar"
        subprocess.run(["swiftc", "-O", str(RAIZ / "scripts/recortar_fondo.swift"), "-o", str(exe)], check=True)
        subprocess.run([str(exe), str(tmp / "in"), str(tmp / "out")], check=True, stdout=subprocess.DEVNULL)
        for nombre in a_recortar:
            tareas.append((nombre, tmp / "out" / (nombre[:-5] + ".png"), True))
    with ProcessPoolExecutor() as pool:
        hechas = sum(1 for _ in pool.map(guardar, tareas, chunksize=8))
    peso = sum(f.stat().st_size for f in ZOOM.glob("*.webp")) / 1e6
    print(f"{hechas} versiones grandes nuevas; {len(list(ZOOM.glob('*.webp')))} en total ({peso:.0f} MB); sin fuente: {sin_fuente}")


if __name__ == "__main__":
    main("--forzar" in sys.argv)
