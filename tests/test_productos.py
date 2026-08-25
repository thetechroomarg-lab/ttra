import json
from web.productos import (
    generar_productos,
    generar_proveedores,
    resolver_proveedor,
    escribir_productos_json,
)


def test_genera_productos_sin_proveedor_y_con_3_precios():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 630, "proveedor": "fr"},
        {"nombre": "iphone 13 128gb", "costo": 610, "proveedor": "az"},
    ]
    prods = generar_productos(items, cotizacion=1540)
    assert len(prods) == 1                      # se consolida al más barato
    p = prods[0]
    assert "proveedor" not in p                 # NUNCA el proveedor
    assert p["usd"] == 670                      # 610 + margen iPhone 60 (601-900), redondeo a 5
    assert p["pesos"] == 670 * 1540
    assert p["transferencia"] == round(p["pesos"] / 0.97)
    assert p["link_imagen"].startswith("https://www.google.com/search?tbm=isch")
    assert p["categoria"]                       # tiene alguna categoría no vacía


def test_genera_indice_privado_del_proveedor_elegido():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 630, "proveedor": "fr"},
        {"nombre": "iphone 13 128gb", "costo": 610, "proveedor": "az"},
    ]

    assert generar_proveedores(items) == {"iphone 13 128gb": "az"}


def test_resuelve_proveedor_con_la_misma_normalizacion_del_catalogo():
    proveedores = {"Xiaomi Redmi Note 14 8GB 256GB": "az"}

    assert resolver_proveedor(proveedores, "Xiaomi Redmi Note 14 8GB 256GB slim") == "az"
    assert resolver_proveedor(proveedores, "Producto inexistente") == "Proveedor no identificado"


def test_modelos_redmi_poco_mi_sin_marca_en_el_nombre_van_a_xiaomi():
    nombres = [
        "C71 3GB 64GB",
        "C81 PRO 4GB 256GB",
        "C75X 8GB 256GB",
        "F7 5G 12GB 256GB",
        "F8 ULTRA 5G 16GB 512GB",
        "M8 PRO 5g 512gb/12gb",
        "X8 PRO MAX 12GB 512GB",
        "A5 3GB 64GB",
        "NOTE 70 4GB 128GB (4gb+8gb)",
        "MI BAND 9",
        "MI BUDS 6 PLAY",
        "Mi 17T Pro 5G 12GB 512GB",
        "17 ULTRA 5G 16GB 512GB",
    ]
    items = [{"nombre": n, "costo": 200, "proveedor": "az"} for n in nombres]

    prods = generar_productos(items, cotizacion=1540)

    assert len(prods) == len(nombres)
    assert all(p["categoria"] == "Xiaomi" for p in prods)


def test_modelos_de_otras_marcas_sin_marca_en_el_nombre_no_van_a_xiaomi():
    nombres = [
        "EDGE 60 FUSION 5G 8GB 256GB slim",       # Motorola
        "G86 5G 8GB 256GB",                       # Motorola
        "HP 15-FC0037 AMD Ryzen 5 7520U 256GB SSD 8GB 15.6\" WIN11",  # notebook, no celular
        "Mi 5-Blade Electric Shaver",              # Xiaomi pero no es celular
    ]
    items = [{"nombre": n, "costo": 200, "proveedor": "az"} for n in nombres]

    prods = generar_productos(items, cotizacion=1540)

    assert all(p["categoria"] != "Xiaomi" for p in prods)


def test_escribir_productos_json(tmp_path):
    items = [{"nombre": "Moto G15 128GB", "costo": 150, "proveedor": "va"}]
    ruta = tmp_path / "productos.json"
    escribir_productos_json(items, 1540, str(ruta))
    data = json.loads(ruta.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 1
    assert "proveedor" not in data[0]
    assert data[0]["nombre"] == "Moto G15 128GB"
    proveedores = json.loads((tmp_path / "proveedores.json").read_text(encoding="utf-8"))
    assert proveedores == {"Moto G15 128GB": "va"}
