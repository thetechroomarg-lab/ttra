from web.catalogo import SECCIONES, secciones_catalogo


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
