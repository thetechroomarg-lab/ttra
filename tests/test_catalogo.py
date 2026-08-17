from web.catalogo import SECCIONES, marca_de, secciones_catalogo


def _prod(nombre, categoria):
    return {"nombre": nombre, "categoria": categoria}


def test_todas_las_secciones_estan_presentes_aunque_vacias():
    resultado = secciones_catalogo([])
    assert set(resultado.keys()) == set(SECCIONES)
    assert all(resultado[s] == [] for s in SECCIONES)


def test_categorias_conocidas_van_a_su_seccion():
    productos = [
        _prod("iPhone 15", "Apple - iPhone"),
        _prod("Galaxy A17", "Samsung"),
        _prod("MacBook Air M2", "Mac"),
        _prod("HP 15-EF0022", "Notebook"),
        _prod("iPad 9na", "Apple - iPad"),
        _prod("AirPods Pro", "Apple - AirPods"),
        _prod("Apple Watch SE", "Apple - Watch"),
    ]
    resultado = secciones_catalogo(productos)
    assert [p["nombre"] for p in resultado["Celulares"]] == ["iPhone 15", "Galaxy A17"]
    assert [p["nombre"] for p in resultado["Notebooks y Macbooks"]] == ["MacBook Air M2", "HP 15-EF0022"]
    assert [p["nombre"] for p in resultado["Tablets"]] == ["iPad 9na"]
    assert [p["nombre"] for p in resultado["Accesorios Celulares"]] == ["AirPods Pro", "Apple Watch SE"]


def test_otros_oppo_va_a_celulares():
    resultado = secciones_catalogo([_prod("Oppo Reno 14F DARK SIDE 5g 256/12gb", "Otros")])
    assert resultado["Celulares"][0]["nombre"].startswith("Oppo")


def test_otros_playstation_va_a_gaming():
    resultado = secciones_catalogo([_prod("PlayStation 5 Slim 825GB Digital", "Otros")])
    assert resultado["Gaming"][0]["nombre"] == "PlayStation 5 Slim 825GB Digital"


def test_otros_cargador_va_a_accesorios_por_defecto():
    resultado = secciones_catalogo([_prod("CARGADOR APPLE 35W CERTIFICADO USB C", "Otros")])
    assert resultado["Accesorios Celulares"][0]["nombre"] == "CARGADOR APPLE 35W CERTIFICADO USB C"


def test_otros_drone_va_a_accesorios_por_defecto():
    resultado = secciones_catalogo([_prod("Drone DJI Flip Plegable Ultraliviano 4K 48MP", "Otros")])
    assert resultado["Accesorios Celulares"][0]["nombre"].startswith("Drone")


def test_tablet_samsung_no_se_mezcla_con_celulares():
    resultado = secciones_catalogo([
        _prod("TABLET SAMSUNG X526 TAB S10 FE 8GB 128GB WIFI+5G 10.9¨ +PEN", "Samsung"),
    ])
    assert resultado["Celulares"] == []
    assert len(resultado["Tablets"]) == 1
    assert resultado["Tablets"][0]["nombre"].startswith("TABLET SAMSUNG")


def test_tablet_xiaomi_no_se_mezcla_con_celulares():
    resultado = secciones_catalogo([
        _prod("TABLET XIAOMI MI PAD 7 8GB 128GB 11.2¨", "Xiaomi"),
        _prod("Xiaomi Redmi Pad SE 4GB RAM 128GB 8.7\" Verde", "Xiaomi"),
    ])
    assert resultado["Celulares"] == []
    assert len(resultado["Tablets"]) == 2


def test_marca_de_categorias_conocidas():
    assert marca_de(_prod("iPhone 15", "Apple - iPhone")) == "Apple"
    assert marca_de(_prod("iPad 9na", "Apple - iPad")) == "Apple"
    assert marca_de(_prod("Galaxy A17", "Samsung")) == "Samsung"
    assert marca_de(_prod("Redmi Note 14", "Xiaomi")) == "Xiaomi"


def test_marca_de_otros_por_nombre():
    assert marca_de(_prod("Oppo Reno 14F", "Otros")) == "Oppo"
    assert marca_de(_prod("CARGADOR APPLE 35W", "Otros")) == "Apple"
    assert marca_de(_prod("AURICULAR JBL TUNE 110", "Otros")) == "JBL"
    assert marca_de(_prod("Repetidor Extensor de rango Wi-Fi TP-Link", "Otros")) == "Otras marcas"


def test_secciones_catalogo_incluye_marca_en_cada_producto():
    resultado = secciones_catalogo([_prod("iPhone 15", "Apple - iPhone")])
    assert resultado["Celulares"][0]["marca"] == "Apple"
