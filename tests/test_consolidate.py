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


def test_unifica_specs_en_distinto_orden_entre_proveedores():
    # "64/2GB" (va) y "2GB 64GB" (az) son el mismo equipo -> una fila, el más barato.
    items = [
        {"nombre": "MOTO E15 2GB 64GB", "costo": 107, "proveedor": "az"},
        {"nombre": "MOTO E15 64/2GB", "costo": 95, "proveedor": "va"},
    ]
    r = consolidar(items)
    assert len(r["lista"]) == 1
    assert r["lista"][0]["costo"] == 95
    assert r["lista"][0]["proveedor"] == "va"


def test_reporta_mismo_producto_con_relleno_de_marca():
    # "AIRPODS MAX" vs "Apple Airpods Max": mismo producto, otro nombre -> se reporta.
    items = [
        {"nombre": "AIRPODS MAX", "costo": 510, "proveedor": "az"},
        {"nombre": "Apple Airpods Max", "costo": 560, "proveedor": "fr"},
    ]
    r = consolidar(items)
    assert len(r["lista"]) == 2
    dups = r["duplicados_posibles"]
    assert len(dups) == 1
    assert {dups[0]["nombre_a"], dups[0]["nombre_b"]} == {"AIRPODS MAX", "Apple Airpods Max"}


def test_modelos_distintos_no_se_reportan():
    # 16 vs 15 Pro Max comparten palabras pero son modelos distintos: no se reportan.
    items = [
        {"nombre": "iPhone 16 Pro Max 256GB", "costo": 1290, "proveedor": "az"},
        {"nombre": "iPhone 15 Pro Max 256GB", "costo": 1100, "proveedor": "fr"},
    ]
    r = consolidar(items)
    assert r["duplicados_posibles"] == []


def test_no_reporta_del_mismo_proveedor():
    items = [
        {"nombre": "AIRPODS MAX", "costo": 510, "proveedor": "az"},
        {"nombre": "Apple Airpods Max", "costo": 560, "proveedor": "az"},
    ]
    r = consolidar(items)
    assert r["duplicados_posibles"] == []
