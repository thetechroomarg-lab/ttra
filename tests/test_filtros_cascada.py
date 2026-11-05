"""Filtros en cascada del catálogo y menú sin "Todo el catálogo". El JS no se ejecuta: se afirma sobre su texto."""
from pathlib import Path

ESTATICO = Path(__file__).resolve().parent.parent / "web" / "static"


def test_cascadas_por_seccion():
    js = (ESTATICO / "catalogo.js").read_text(encoding="utf-8")
    assert 'CASCADA_MOVIL = ["almacenamiento", "ram"]' in js
    assert 'CASCADA_MAC = ["procesador", "ram", "disco"]' in js
    assert 'CASCADA_NOTEBOOK = ["procesador", "ram", "disco", "pantalla", "grafica"]' in js
    # Mac nunca ofrece pantalla ni gráfica
    assert "pantalla" not in js.split("CASCADA_MAC")[1].split("\n")[0]
    # Apple en Celulares: sin memoria ni RAM
    assert "!permiteFiltroCondicion(seccion, marcaActiva) ? CASCADA_MOVIL" in js
    # el siguiente menú no aparece hasta elegir el anterior
    assert "if (!filtrosEspec[clave]) cortada = true;" in js


def test_menu_de_categorias_sin_todo_el_catalogo():
    js = (ESTATICO / "site-header.js").read_text(encoding="utf-8")
    assert "Todo el catálogo" not in js
    assert "['Celulares', '/catalogo?categoria=Celulares']" in js


def test_dropdowns_no_parten_palabras():
    css = (ESTATICO / "disclosure.css").read_text(encoding="utf-8")
    assert "overflow-wrap: anywhere" not in css
    assert "inline-size: max-content" in css
    assert "overflow-wrap: anywhere" not in (ESTATICO / "site-header.css").read_text(encoding="utf-8")
