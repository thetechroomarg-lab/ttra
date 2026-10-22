"""Lector de especificaciones del catálogo (web/static/especificaciones.js).

Corre el JS con Node: los filtros solo pueden ofrecer lo que el nombre del
producto dice, así que cada caso es un nombre real del catálogo."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "web" / "static" / "especificaciones.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="Node no está instalado")


def especificaciones(nombre, seccion, categoria=""):
    codigo = (
        f"const E=require({json.dumps(str(SCRIPT))});"
        f"console.log(JSON.stringify(E.especificacionesDe({json.dumps({'nombre': nombre, 'categoria': categoria})},"
        f"{json.dumps(seccion)})))"
    )
    salida = subprocess.run([NODE, "-e", codigo], capture_output=True, text=True, check=True)
    return json.loads(salida.stdout)


@pytest.mark.parametrize("nombre,ram,memoria", [
    ("SAMSUNG A07 5G 4GB 128GB Dual (s/ cargador)", 4, 128),
    ("Moto Signature 5G 16GB 1TB", 16, 1024),
    ("CELULAR LUSH MINT 2GB 16GB", 2, 16),
    # El iPhone no informa RAM: no se completa.
    ("iPhone 17 256GB", None, 256),
    ("MOTO E15 64GB", None, 64),
    # Un accesorio dentro de Celulares no tiene especificaciones.
    ("Xiaomi Mi Band 11 Active", None, None),
])
def test_celulares_leen_ram_y_memoria_del_nombre(nombre, ram, memoria):
    espec = especificaciones(nombre, "Celulares")
    assert espec["ram"] == ram
    assert espec["almacenamiento"] == memoria


def test_notebook_no_confunde_la_memoria_de_la_grafica_con_la_ram():
    espec = especificaciones(
        "NOTEBOOK ASUS TUF GAMING AMD RYZEN 7 260 16GB RAM 1TB SSD NVIDIA RTX 5050 8GB 18\" WUXGA 144Hz",
        "Notebooks y Macbooks", "Notebook")
    assert espec == {"procesador": "AMD Ryzen 7", "ram": 16, "disco": 1024, "pantalla": 18, "grafica": "dedicada"}


def test_macbook_lee_chip_ram_disco_y_pantalla():
    espec = especificaciones("Macbook Air 15 M5 10CPU 10GPU 512GB 16GB", "Notebooks y Macbooks", "Mac")
    assert espec == {"procesador": "Apple M5", "ram": 16, "disco": 512, "pantalla": 15, "grafica": "integrada"}


@pytest.mark.parametrize("nombre,procesador", [
    ("HP VICTUS 15-FA2013 GAMING Core i5-13420H 512GB SSD 8GB 15.6\"", "Intel Core i5"),
    ("NOTEBOOK MSI CYBORG 15 GAMING INTEL ULTRA 7 240H 16GB RAM 1TB SSD", "Intel Core Ultra 7"),
    ("MSI Cyborg 15 GAMING Core 7-240H 512GB SSD 16GB 15.6\"", "Intel Core 7"),
    ("NOTEBOOK HP ELITEBOOK 855 G7 AMD RYZENPRO 7-4750U 16GB 256GB SSD 15.6\"", "AMD Ryzen 7"),
    ("NOTEBOOK HP G9 250RT INTEL N150 8GB RAM 256GB SSD 15.6\" HD", "Intel N150"),
])
def test_notebooks_agrupan_el_procesador_por_familia(nombre, procesador):
    assert especificaciones(nombre, "Notebooks y Macbooks", "Notebook")["procesador"] == procesador


def test_pantalla_sin_comillas_no_se_adivina():
    espec = especificaciones(
        "Acer Predator Triton 300 SE PT314-52S-747P 14 Intel Core i7-12700H 512GB SSD 16GB RAM NVIDIA GeForce RTX 3060 6 GB",
        "Notebooks y Macbooks", "Notebook")
    assert espec["pantalla"] is None
    assert espec["ram"] == 16


def test_una_mochila_no_es_una_notebook():
    assert especificaciones("Xtrem Mochila Notebook Xtrem Force 15.6''", "Notebooks y Macbooks", "Notebook") == {}


def test_catalogo_carga_los_filtros_de_especificacion():
    static = SCRIPT.parent
    html = (static / "catalogo.html").read_text(encoding="utf-8")
    script = (static / "catalogo.js").read_text(encoding="utf-8")
    assert 'id="spec-filters"' in html
    assert html.index("especificaciones.js") < html.index('src="catalogo.js"')
    assert "function filtrarPorEspec(productos, seccion)" in script
