import json
import openpyxl
from generar_lista import procesar, main


def test_procesar_arma_lista_con_precio_link_y_pais():
    datos = {
        "items": [
            {"nombre": "iPhone 13 128GB", "costo": 650, "proveedor": "A"},
            {"nombre": "iphone 13 128gb", "costo": 630, "proveedor": "B"},
        ],
        "filtrados": [{"nombre": "iPhone 12 (caja abollada)", "motivo": "caja abollada"}],
        "dudas_precio": [],
    }
    lista, reporte = procesar(datos)
    assert len(lista) == 1
    fila = lista[0]
    assert fila["pais"] == "🇺🇸"
    assert fila["precio"] == 680        # 630 + 50 = 680 -> 680
    assert fila["link"].startswith("https://www.google.com/search?tbm=isch&q=")
    assert reporte["filtrados"][0]["motivo"] == "caja abollada"


def test_main_escribe_archivo(tmp_path):
    entrada = tmp_path / "in.json"
    salida = tmp_path / "out.xlsx"
    entrada.write_text(json.dumps({
        "items": [{"nombre": "Motorola G54", "costo": 200, "proveedor": "A"}],
        "filtrados": [],
        "dudas_precio": [],
    }), encoding="utf-8")

    main([str(entrada), str(salida)])

    wb = openpyxl.load_workbook(str(salida))
    hoja = wb["Lista"]
    assert [c.value for c in hoja[2]] == [
        "Motorola G54",
        "https://www.google.com/search?tbm=isch&q=Motorola+G54",
        "🇺🇸",
        230,  # 200 + 30 = 230
    ]
