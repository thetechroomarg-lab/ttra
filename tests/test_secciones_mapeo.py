"""Cada producto va a la sección que le corresponde, aunque llegue con la categoría de una marca de celulares."""
import pytest

from web.catalogo import seccion_de


@pytest.mark.parametrize("nombre,categoria,esperada", [
    ('SAMSUNG ODYSSEY ARK 2 MONITOR GAMER 55" 4K', "Samsung", "Gaming"),
    ("Chromebook SAMSUNG XE310XBA-K01US 4 11.6\"", "Samsung", "Notebooks y Macbooks"),
    ("Xiaomi 33W Power Bank 20000 MAh", "Xiaomi", "Accesorios Celulares"),
    ("Xiaomi Redmi Buds 8 Active", "Xiaomi", "Accesorios Celulares"),
    ("XIAOMI MI BAND 9", "Xiaomi", "Accesorios Celulares"),
    ("Aspiradora Xiaomi Robot Vacuum 5", "Xiaomi", "Accesorios Celulares"),
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
