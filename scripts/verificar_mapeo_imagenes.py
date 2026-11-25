"""Verifica que cada producto/color del catálogo esté mapeado a una imagen existente y transparente.

Uso: python scripts/verificar_mapeo_imagenes.py [productos.json]
Revisa tres cosas: (1) manifest: cada (producto, color) tiene asignación a un asset con archivo;
(2) índice web: cada (producto, color) apunta a un archivo que existe, con versión zoom;
(3) ninguna imagen del índice tiene fondo opaco (debe usarse su -cut). Sale con código 1 si algo falla.
"""
import json
import sys
from pathlib import Path
from PIL import Image

RAIZ = Path(__file__).resolve().parents[1]
WEB = RAIZ / "web/static/catalog-images"
prod = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "web/productos.json"
productos = json.loads(prod.read_text())
manifest = json.loads((RAIZ / "outputs/catalogo-imagenes/manifest.json").read_text())
indice = json.loads((WEB / "index.json").read_text())
assets = {a["id"]: a for a in manifest["assets"]}
asign = {(r["nombre"], r["color_original"]): r["asset_id"] for r in manifest["asignaciones"]}
sin_manifest, sin_indice, opacas = [], [], []
for p in productos:
    for c in p.get("colores") or [None]:
        a = assets.get(asign.get((p["nombre"], c)))
        if not a or a["estado"] != "generada_pendiente_revision":
            sin_manifest.append((p["nombre"], c))
        fila = next((r for r in indice.get(p["nombre"], []) if r["color"] == c), None)
        if not fila or not (WEB / fila["src"][len("/catalog-images/"):]).exists():
            sin_indice.append((p["nombre"], c))
            continue
        nombre = fila["src"][len("/catalog-images/"):]
        if nombre.startswith("usados/"):  # fotos reales cargadas a mano: no se recortan ni llevan zoom
            continue
        im = Image.open(WEB / nombre)
        if "A" not in im.getbands() or im.getchannel("A").getextrema()[0] >= 250:
            opacas.append(nombre)
        if not (WEB / "zoom" / nombre).exists():
            sin_indice.append((p["nombre"], c, "sin zoom"))
print(f"sin asignación en manifest: {len(sin_manifest)}; sin imagen en índice: {len(sin_indice)}; opacas: {len(set(opacas))}")
for x in sin_manifest[:15]:
    print(" manifest:", x)
for x in sin_indice[:15]:
    print(" índice:", x)
sys.exit(1 if (sin_manifest or sin_indice or opacas) else 0)
