"""Precarga las fichas de especificaciones (comparativa) de todo el catálogo
vigente, una sola vez, para no depender de la API en el momento en que un
cliente pide comparar dos productos. Corre DENTRO del contenedor de Railway
(donde vive el volumen /data y las env vars de producción):

    railway ssh --service ttra --environment production -- \
        python3 -m scripts.backfill_specs

Usa el mismo SpecStore y el mismo proveedor (Anthropic) que ya usa la app en
vivo, así que lo que quede cacheado acá es exactamente lo que va a servir
/api/comparativa/ficha — sin tocar el catálogo ni ninguna otra tabla.
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from web.catalogo import seccion_de
from web.comparativa import spec_key
from web.comparativa_specs import SpecStore, research

CATEGORIAS_CON_FICHA = {"Celulares", "Tablets", "Notebooks y Macbooks"}


def main():
    productos_path = Path(os.environ.get("PRODUCTOS_PATH", "/data/productos.json"))
    productos = json.loads(productos_path.read_text(encoding="utf-8"))

    store = SpecStore(productos_path.parent / ".security" / "comparison-specs.sqlite3")

    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"], timeout=45.0, max_retries=0)

    # Un producto por spec_key (el mismo modelo en varios colores comparte
    # ficha; spec_key ya ignora el color y el estado usado/nuevo/CPO).
    vistos = {}
    for p in productos:
        try:
            if seccion_de(p) not in CATEGORIAS_CON_FICHA:
                continue
        except Exception:
            continue
        vistos.setdefault(spec_key(p), p)

    pendientes = [(key, p) for key, p in vistos.items() if store.get(key) is None]
    print(f"{len(vistos)} modelos únicos, {len(pendientes)} sin ficha cacheada todavía.")

    ok = fail = 0
    for i, (key, producto) in enumerate(pendientes, 1):
        owner = f"backfill-{os.getpid()}-{i}"
        if not store.claim(key, owner):
            print(f"[{i}/{len(pendientes)}] {producto['nombre']}: ya lo está procesando otro worker, salteo")
            continue
        try:
            sheet = research(producto, client)
            if store.save(key, owner, sheet):
                ok += 1
                print(f"[{i}/{len(pendientes)}] OK  {producto['nombre']}")
            else:
                print(f"[{i}/{len(pendientes)}] SKIP {producto['nombre']} (lease vencido)")
        except Exception as e:
            fail += 1
            store.fail(key, owner)
            print(f"[{i}/{len(pendientes)}] FALLÓ {producto['nombre']}: {e}")
        time.sleep(1.5)  # no golpear la API en ráfaga

    print(f"\nListo. {ok} fichas nuevas, {fail} fallaron (quedan para reintentar después).")


if __name__ == "__main__":
    main()
