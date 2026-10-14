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
    iphone = [x for x in lista if "hone 13" in x["nombre"]][0]
    assert iphone["costo"] == 630
    assert iphone["proveedor"] == "B"


def test_unifica_specs_en_distinto_orden():
    # "64/2GB" (va) y "2GB 64GB" (az) son el mismo equipo -> una fila, el más barato.
    items = [
        {"nombre": "MOTO E15 2GB 64GB", "costo": 107, "proveedor": "az"},
        {"nombre": "MOTO E15 64/2GB", "costo": 95, "proveedor": "va"},
    ]
    r = consolidar(items)
    assert len(r["lista"]) == 1
    assert r["lista"][0]["costo"] == 95
    assert r["lista"][0]["proveedor"] == "va"


def test_unifica_mismo_producto_con_relleno_de_marca():
    # "AIRPODS MAX" vs "Apple Airpods Max": mismo producto -> una fila, el más barato.
    items = [
        {"nombre": "AIRPODS MAX", "costo": 510, "proveedor": "az"},
        {"nombre": "Apple Airpods Max", "costo": 560, "proveedor": "fr"},
    ]
    r = consolidar(items)
    assert len(r["lista"]) == 1
    assert r["lista"][0]["costo"] == 510
    assert r["lista"][0]["proveedor"] == "az"


def test_unifica_macbook_con_nucleos_y_ssd():
    # Mismo MacBook Air 15 M5 16GB/512GB: em lo trae con "10CPU 10GPU" y fr con "SSD".
    # Esos tokens son relleno -> deben unificarse y quedar el más barato (em).
    items = [
        {"nombre": "Macbook Air 15 M5 10CPU 10GPU 512GB 16GB", "costo": 1750, "proveedor": "em"},
        {"nombre": "MacBook Air 15 M5 16GB / 512GB SSD", "costo": 1880, "proveedor": "fr"},
    ]
    r = consolidar(items)
    assert len(r["lista"]) == 1
    assert r["lista"][0]["costo"] == 1750
    assert r["lista"][0]["proveedor"] == "em"


def test_modelos_distintos_no_se_unifican():
    # 16 vs 15 Pro Max comparten palabras pero son modelos distintos: 2 filas.
    items = [
        {"nombre": "iPhone 16 Pro Max 256GB", "costo": 1290, "proveedor": "az"},
        {"nombre": "iPhone 15 Pro Max 256GB", "costo": 1100, "proveedor": "fr"},
    ]
    r = consolidar(items)
    assert len(r["lista"]) == 2


def test_specs_distintas_no_se_unifican():
    # 128GB vs 256GB son productos distintos: 2 filas.
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 650, "proveedor": "az"},
        {"nombre": "iPhone 13 256GB", "costo": 720, "proveedor": "fr"},
    ]
    r = consolidar(items)
    assert len(r["lista"]) == 2


def test_elige_siempre_el_mas_barato_aunque_sea_por_poco():
    items = [
        {"nombre": "Redmi 15 8GB 256GB", "costo": 200, "proveedor": "az"},
        {"nombre": "Redmi 15 8GB 256GB", "costo": 199, "proveedor": "fr"},
    ]
    fila = consolidar(items)["lista"][0]
    assert fila["proveedor"] == "fr"
    assert fila["costo"] == 199


def test_unifica_macbook_neo_y_se_queda_con_los_colores_del_mas_barato():
    items = [
        {"nombre": "MacBook Neo A18 Pro 6 Core CPU 256GB 8GB", "costo": 910, "proveedor": "em",
         "colores": ["Silver", "Indigo", "Citrus"]},
        {"nombre": "MACBOOK NEO A18 PRO 6CPU 8GB 256GB 13\u00a8", "costo": 830, "proveedor": "az",
         "colores": ["Citrus"]},
        {"nombre": "MacBook Neo 13 A18 Pro \u2013 8GB RAM / 256GB SSD", "costo": 870, "proveedor": "fr"},
    ]
    lista = consolidar(items)["lista"]
    assert len(lista) == 1
    assert lista[0]["proveedor"] == "az" and lista[0]["colores"] == ["Citrus"]


def test_5g_omitido_se_unifica_salvo_familias_con_version_4g():
    assert len(consolidar([
        {"nombre": "MOTO G77 8GB 256GB", "costo": 315, "proveedor": "az"},
        {"nombre": "Moto G77 5G 8GB 256GB", "costo": 320, "proveedor": "va"},
    ])["lista"]) == 1
    assert len(consolidar([
        {"nombre": "Xiaomi Redmi Note 14 5G 8GB 256GB", "costo": 295, "proveedor": "az"},
        {"nombre": "Xiaomi Redmi Note 14 8GB 256GB", "costo": 275, "proveedor": "az"},
    ])["lista"]) == 2


def test_macbook_pro_m5_y_m5_pro_siguen_separadas():
    assert len(consolidar([
        {"nombre": "MacBook Pro 14 M5 10CPU 10GPU 1TB 24GB", "costo": 2420, "proveedor": "em"},
        {"nombre": "MacBook Pro 14 M5 PRO 15CPU 16GPU 1TB 24GB", "costo": 2820, "proveedor": "em"},
    ])["lista"]) == 2


def test_unifica_ipad_a16_con_nombres_distintos():
    lista = consolidar([
        {"nombre": "iPad 11\u00aa Generaci\u00f3n A16 \u2013 256GB Wi-Fi", "costo": 620, "proveedor": "fr"},
        {"nombre": "iPad A16 11\" 2025 256GB", "costo": 610, "proveedor": "em"},
    ])["lista"]
    assert len(lista) == 1 and lista[0]["proveedor"] == "em"
