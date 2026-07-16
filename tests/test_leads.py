import csv
import json

from web.leads import guardar_lead


def test_guardar_lead_upsert_y_acumula_productos(tmp_path):
    jp = tmp_path / "clientes.json"
    cp = tmp_path / "clientes.csv"
    # primer contacto: nombre + un producto
    guardar_lead("s1", {"nombre": "Ana", "productos": ["iPhone 13"]},
                 fecha="2026-07-16 19:00", json_path=jp, csv_path=cp)
    # segundo mensaje de la misma sesión: agrega celular y otro producto
    reg = guardar_lead("s1", {"celular": "3510000", "productos": ["Samsung A16", "iPhone 13"]},
                       fecha="2026-07-16 19:05", json_path=jp, csv_path=cp)
    assert reg["nombre"] == "Ana"
    assert reg["celular"] == "3510000"
    assert reg["productos"] == ["iPhone 13", "Samsung A16"]  # sin duplicar, acumulado

    db = json.loads(jp.read_text(encoding="utf-8"))
    assert list(db.keys()) == ["s1"]

    filas = list(csv.reader(cp.open(encoding="utf-8-sig")))
    assert filas[0] == ["Nombre", "Numero de Celular", "Productos consultados", "Fecha", "Sesion"]
    assert filas[1][0] == "Ana"
    assert filas[1][1] == "3510000"
    assert "iPhone 13 | Samsung A16" == filas[1][2]
