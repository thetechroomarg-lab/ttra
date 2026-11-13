"""Cada producto va a la sección que le corresponde, aunque llegue con la categoría de una marca de celulares."""
import pytest

from web.catalogo import seccion_de


@pytest.mark.parametrize("nombre,categoria,esperada", [
    ('SAMSUNG ODYSSEY ARK 2 MONITOR GAMER 55" 4K', "Samsung", "Gaming"),
    ("Chromebook SAMSUNG XE310XBA-K01US 4 11.6\"", "Samsung", "Notebooks y Macbooks"),
    ("Xiaomi 33W Power Bank 20000 MAh", "Xiaomi", "Accesorios Celulares"),
    ("Xiaomi Redmi Buds 8 Active", "Xiaomi", "Accesorios Celulares"),
    ("XIAOMI MI BAND 9", "Xiaomi", "Accesorios Celulares"),
    ("Aspiradora Xiaomi Robot Vacuum 5", "Xiaomi", "Electro"),
    ("Xiaomi Cafetera Semi automatic Espresso Machine", "Xiaomi", "Electro"),
    ("Freidora de aire Philips 4L", "Otros", "Electro"),
    ("Cookut La Fabulosa Negro (meteoro) - FAB28NO", "Otros", "Electro"),
    ("Robot Limpiapiscinas Aiper Scuba S3 AR", "Otros", "Electro"),
    ("Cecotec Cecofry Fantastik 6500", "Otros", "Electro"),
    ("Amazon Fire TV Stick 4K Select 8GB", "Otros", "Accesorios Celulares"),
    ("Patinete Elétrico Xiaomi Mi Scooter Electric 6 Max", "Xiaomi", "Accesorios Celulares"),
    ("CARG ORIGINAL SAMSUNG 25W USB C", "Samsung", "Accesorios Celulares"),
    ("GALAXY SMART TAG 2 (2023) 1 PACK LOCALIZADOR BLUETOOTH", "Samsung", "Accesorios Celulares"),
    ("Xtrem Mochila Notebook Xtrem Force 15.6''", "Notebook", "Accesorios Celulares"),
    ("Pencil PRO ( con iPad )", "Apple - iPad", "Accesorios Celulares"),
    ("NB MSI CYBORG B2EWFKG-006US R9-270 16GB/1TBSSD", "Otros", "Notebooks y Macbooks"),
    ("A07S 4GB 64GB", "Otros", "Celulares"),
    ("Pixel 10 5G 12GB 256GB", "Otros", "Celulares"),
    ("SAMSUNG S25 ULTRA 5g 12GB 1TB Dual", "Samsung", "Celulares"),
    ("Xiaomi Redmi Note 14 5G 8GB 256GB", "Xiaomi", "Celulares"),
    ("MOTO G86 5G 8GB 256GB", "Motorola", "Celulares"),
    ("Tablet Xiaomi Redmi Pad 2 Pro 8GB 256GB Wifi", "Xiaomi", "Tablets"),
    ("iPhone 15 Pro 128GB (Usado)", "Apple - iPhone Usado", "Celulares"),
])
def test_seccion_por_producto(nombre, categoria, esperada):
    assert seccion_de({"nombre": nombre, "categoria": categoria}) == esperada


@pytest.mark.parametrize("nombre,categoria,tipo", [
    ("Aspiradora Xiaomi Robot Vacuum 5", "Xiaomi", "Aspiradoras"),
    ("Robot limpiavidrios ECOVACS WINBOT MINI", "Otros", "Robots"),
    ("NOAX Cafetera Espresso Portatil", "Otros", "Cafeteras"),
    ("Xiaomi Humidifier 2 Lite", "Xiaomi", "Humidificadores"),
    ("Xiaomi Mi Smart Scale S200", "Xiaomi", "Balanzas"),
    ("Licuadora Oster 600W", "Otros", "Licuadoras y batidoras"),
    ("Producto nuevo sin regla", "Electro", "Otros electro"),
    ("Robot Limpiapiscinas Aiper Scuba S3 AR", "Otros", "Limpiapiscinas"),
    ("Aspirador Limpiapiscinas Inalámbrico Aiper - Pilot X1 AR", "Otros", "Limpiapiscinas"),
    ("Carrito Aiper Caddy - AIPJ02210010001", "Otros", "Limpiapiscinas"),
    ("Robot Cortacésped Anthbot Genie 1000 EU", "Otros", "Robots"),
    ("Robot de cocina Mambo Cooking Victory (Europa) -4700 EU", "Otros", "Cocina"),
    ("Robot aspirador Conga X70 EU", "Otros", "Aspiradoras"),
    ("Fregona eléctrica FreeGo Wash Twice Spray", "Otros", "Aspiradoras"),
    ("Cecotec Cecofry Fantastik 6500", "Otros", "Freidoras de aire"),
    ("Tostador Cecotec - Toast&Taste Double W AR", "Otros", "Cocina"),
    ("Cepillo modelador de aire Cecotec CeramicCare 10in1 Styler", "Otros", "Cuidado personal"),
    ("Cookut La Fabulosa Negro (meteoro) - FAB28NO", "Otros", "Ollas y sartenes"),
    ("Heladera Termica Pinnacle Prudence 30 Ltr. Rojo", "Otros", "Heladeras"),
])
def test_tipo_electro(nombre, categoria, tipo):
    from web.catalogo import tipo_electro_de
    assert tipo_electro_de({"nombre": nombre, "categoria": categoria}) == tipo


def test_api_electro_trae_tipo():
    from web.catalogo import secciones_catalogo
    r = secciones_catalogo([{"nombre": "Xiaomi Humidifier 2 Lite", "categoria": "Xiaomi", "usd": 80}])
    assert r["Electro"][0]["tipo_electro"] == "Humidificadores"
    assert r["Accesorios Celulares"] == []
