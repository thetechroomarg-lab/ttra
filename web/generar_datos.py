import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__file__)))
from web.productos import escribir_productos_json


def main():
    if len(sys.argv) != 4:
        print("uso: python web/generar_datos.py <entrada.json> <cotizacion> <salida.json>")
        sys.exit(1)
    entrada, cotiz, salida = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    with open(entrada, encoding="utf-8") as f:
        items = json.load(f)["items"]
    prods = escribir_productos_json(items, cotiz, salida)
    print(f"OK: {len(prods)} productos -> {salida}")


if __name__ == "__main__":
    main()
