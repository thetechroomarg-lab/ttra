import json
import subprocess
import sys
from pathlib import Path


def test_genera_productos_json_desde_entrada(tmp_path):
    entrada = tmp_path / "entrada.json"
    entrada.write_text(json.dumps({"items": [
        {"nombre": "iPhone 13 128GB", "costo": 610, "proveedor": "az"}
    ]}), encoding="utf-8")
    salida = tmp_path / "productos.json"
    proj = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "web/generar_datos.py", str(entrada), "1540", str(salida)],
        cwd=str(proj), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    data = json.loads(salida.read_text(encoding="utf-8"))
    assert data[0]["nombre"] == "iPhone 13 128GB"
    assert "proveedor" not in data[0]
    assert data[0]["usd"] == 660
