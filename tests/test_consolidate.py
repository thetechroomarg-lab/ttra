from consolidate import consolidar


def test_una_fila_por_producto_con_el_mas_barato():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 650, "proveedor": "A"},
        {"nombre": "iphone 13 128gb", "costo": 630, "proveedor": "B"},
        {"nombre": "Motorola G54", "costo": 200, "proveedor": "A"},
    ]
    r = consolidar(items)
    lista = r["lista"]
    assert len(lista) == 2
    iphone = [x for x in lista if "iPhone" in x["nombre"] or "iphone" in x["nombre"]][0]
    assert iphone["costo"] == 630
    assert iphone["proveedor"] == "B"


def test_reporta_posibles_duplicados_no_identicos():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 650, "proveedor": "A"},
        {"nombre": "iPhone 13 256GB", "costo": 720, "proveedor": "B"},
    ]
    r = consolidar(items)
    assert len(r["lista"]) == 2
    dups = r["duplicados_posibles"]
    assert len(dups) == 1
    assert {dups[0]["nombre_a"], dups[0]["nombre_b"]} == {"iPhone 13 128GB", "iPhone 13 256GB"}


def test_productos_distintos_no_se_reportan():
    items = [
        {"nombre": "iPhone 13", "costo": 650, "proveedor": "A"},
        {"nombre": "Notebook Lenovo Slim 3", "costo": 500, "proveedor": "B"},
    ]
    r = consolidar(items)
    assert r["duplicados_posibles"] == []
