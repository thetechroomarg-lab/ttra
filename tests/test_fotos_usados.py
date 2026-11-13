"""Fotos reales de usados: carrusel + visor. El JS no se ejecuta acá; se afirma sobre datos y texto."""
import json
from pathlib import Path

ESTATICO = Path(__file__).resolve().parent.parent / "web" / "static"


def test_usado_con_fotos_reales_existentes():
    indice = json.loads((ESTATICO / "catalog-images" / "index.json").read_text(encoding="utf-8"))
    variante = indice["iPhone 15 Pro 128GB (Usado)"][0]
    assert variante["color"] == "Black 87%"
    assert len(variante["fotos"]) == 7
    for src in variante["fotos"]:
        assert (ESTATICO / src.removeprefix("/")).is_file(), src


def test_carrusel_solo_para_usados_y_visor_sin_cierre_por_fondo():
    js = (ESTATICO / "catalog-images.js").read_text(encoding="utf-8")
    assert "esUsado(p)&&v.fotos?.length>1" in js
    assert "showModal()" in js and "ArrowLeft" in js and "pointerup" in js
    assert "Cerrar" in js
    # tocar afuera no cierra: no hay listener de click sobre el <dialog> que llame a close()
    assert "dlg.addEventListener('click'" not in js


def test_iphone_14_usado_con_fotos_reales_existentes():
    indice = json.loads((ESTATICO / "catalog-images" / "index.json").read_text(encoding="utf-8"))
    variante = next(v for v in indice["iPhone 14 128GB (Usado)"] if v["color"] == "Black 86%")
    assert len(variante["fotos"]) == 5
    assert variante["src"] == variante["fotos"][0]
    for src in variante["fotos"]:
        assert (ESTATICO / src.removeprefix("/")).is_file(), src


def test_toda_imagen_del_catalogo_tiene_version_grande_para_el_visor():
    """Tocar una card abre el visor con /catalog-images/zoom/<mismo archivo>; tiene que existir."""
    indice = json.loads((ESTATICO / "catalog-images" / "index.json").read_text(encoding="utf-8"))
    falta = sorted({
        v["src"] for variantes in indice.values() for v in variantes
        if v["src"].startswith("/catalog-images/") and "/usados/" not in v["src"] and "placeholder" not in v["src"]
        and not (ESTATICO / "catalog-images" / "zoom" / v["src"].removeprefix("/catalog-images/")).is_file()
    })
    assert not falta, falta[:5]


def test_ampliar_imagen_de_la_card_usa_el_mismo_visor_sin_cierre_por_fondo():
    js = (ESTATICO / "catalog-images.js").read_text(encoding="utf-8")
    assert "zoomDe(actual.src)" in js and "/catalog-images/zoom/" in js
    assert "abrirVisor([zoomDe(actual.src)]" in js          # un solo visor para usados y para el resto
    assert "dlg.addEventListener('click'" not in js
    css = (ESTATICO / "catalog-images.css").read_text(encoding="utf-8")
    assert ".ai-picture-zoom{cursor:zoom-in}" in css


def test_visor_tiene_marca_de_agua_de_fondo():
    css = (ESTATICO / "catalog-images.css").read_text(encoding="utf-8")
    assert css.count("url(watermark-ttra.svg)") == 2          # visor de usados y visor de imagen recortada
    assert (ESTATICO / "watermark-ttra.svg").is_file()
