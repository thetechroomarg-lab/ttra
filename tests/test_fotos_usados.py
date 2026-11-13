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
