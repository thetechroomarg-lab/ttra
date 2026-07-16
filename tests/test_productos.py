import json
from web.productos import generar_productos, escribir_productos_json


def test_genera_productos_sin_proveedor_y_con_3_precios():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 630, "proveedor": "fr"},
        {"nombre": "iphone 13 128gb", "costo": 610, "proveedor": "az"},
    ]
    prods = generar_productos(items, cotizacion=1540)
    assert len(prods) == 1                      # se consolida al más barato
    p = prods[0]
    assert "proveedor" not in p                 # NUNCA el proveedor
    assert p["usd"] == 660                      # 610 + banda 50, redondeo a 5
    assert p["pesos"] == 660 * 1540
    assert p["transferencia"] == round(p["pesos"] / 0.97)
    assert p["link_imagen"].startswith("https://www.google.com/search?tbm=isch")
    assert p["categoria"]                       # tiene alguna categoría no vacía


def test_escribir_productos_json(tmp_path):
    items = [{"nombre": "Moto G15 128GB", "costo": 150, "proveedor": "va"}]
    ruta = tmp_path / "productos.json"
    escribir_productos_json(items, 1540, str(ruta))
    data = json.loads(ruta.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 1
    assert "proveedor" not in data[0]
    assert data[0]["nombre"] == "Moto G15 128GB"
