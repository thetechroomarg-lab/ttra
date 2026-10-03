"""Reporta qué productos del catálogo muestran la card con imagen (misma lógica que catalog-images.js).

Uso: python scripts/check_catalog_images.py web/productos.json [productos_anterior.json]
Con el catálogo anterior, lista los productos que tenían card con imagen y la pierden.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

INDEX = Path(__file__).resolve().parents[1] / "web/static/catalog-images/index.json"
FILLER = {"apple", "samsung", "xiaomi", "redmi", "motorola", "moto", "celular", "smartphone", "original", "nuevo", "dual"}


def _plain(s):
    s = unicodedata.normalize("NFD", str(s or "").strip().lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def color_key(s):
    return re.sub(r"\s+", " ", re.sub(r"\b(pantone|awesome|awesomw|cosmic|deep)\b", " ", _plain(s))).strip()


def name_key(s):
    return " ".join(sorted(t for t in re.sub(r"[^a-z0-9+]+", " ", _plain(s)).split() if t not in FILLER))


def con_imagen(productos, index):
    por_clave = {}
    for k, v in index.items():
        por_clave.setdefault(name_key(k), v)
    ok = set()
    for p in productos:
        entry = index.get(p["nombre"]) or por_clave.get(name_key(p["nombre"]))
        if not entry:
            continue
        colores = p.get("colores") or [None]
        solo_modelo = not p.get("colores") and len(entry) == 1
        if solo_modelo or any(color_key(v.get("color")) == color_key(c) for c in colores for v in entry):
            ok.add(p["nombre"])
    return ok


def main():
    index = json.loads(INDEX.read_text())
    nuevo = json.loads(Path(sys.argv[1]).read_text())
    ok = con_imagen(nuevo, index)
    print(f"{len(ok)}/{len(nuevo)} productos con card con imagen")
    if len(sys.argv) > 2:
        viejo = json.loads(Path(sys.argv[2]).read_text())
        nombres = {p["nombre"] for p in nuevo}
        antes = con_imagen(viejo, index)
        perdidos = sorted(n for n in antes if n in nombres and n not in ok)
        for n in perdidos:
            print("pierde imagen:", n)
        return 1 if perdidos else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
