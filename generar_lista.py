import json
import sys

from bands import calcular_precio
from consolidate import consolidar
from imagelink import google_image_link
from xlsx_writer import escribir_xlsx

PAIS_DEFECTO = "🇺🇸"


def procesar(datos):
    items = datos.get("items", [])
    cons = consolidar(items)

    lista = []
    for fila in cons["lista"]:
        lista.append({
            "nombre": fila["nombre"],
            "link": google_image_link(fila["nombre"]),
            "pais": PAIS_DEFECTO,
            "precio": calcular_precio(fila["costo"]),
            "proveedor": fila["proveedor"],
        })

    reporte = {
        "filtrados": datos.get("filtrados", []),
        "duplicados_posibles": cons["duplicados_posibles"],
        "dudas_precio": datos.get("dudas_precio", []),
    }
    return lista, reporte


def main(argv):
    if len(argv) != 2:
        raise SystemExit("Uso: python generar_lista.py <entrada.json> <salida.xlsx>")
    ruta_entrada, ruta_salida = argv
    with open(ruta_entrada, encoding="utf-8") as f:
        datos = json.load(f)
    lista, reporte = procesar(datos)
    escribir_xlsx(lista, reporte, ruta_salida)
    print(ruta_salida)


if __name__ == "__main__":
    main(sys.argv[1:])
