import csv
import json
from pathlib import Path

BASE = Path(__file__).parent
JSON_PATH = BASE / "clientes.json"
CSV_PATH = BASE / "clientes.csv"


def _cargar():
    if JSON_PATH.exists():
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    return {}


def guardar_lead(sesion, datos, fecha="", json_path=JSON_PATH, csv_path=CSV_PATH):
    """Upsert de un cliente por sesión. Acumula los productos consultados.
    `datos` es un dict con claves opcionales: nombre, celular, productos (lista)."""
    db = json.loads(Path(json_path).read_text(encoding="utf-8")) if Path(json_path).exists() else {}
    reg = db.get(sesion, {"nombre": "", "celular": "", "productos": []})
    if datos.get("nombre"):
        reg["nombre"] = datos["nombre"]
    if datos.get("celular"):
        reg["celular"] = datos["celular"]
    for p in (datos.get("productos") or []):
        if p and p not in reg["productos"]:
            reg["productos"].append(p)
    if fecha:
        reg["fecha"] = fecha
    db[sesion] = reg
    Path(json_path).write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")
    _exportar_csv(db, csv_path)
    return reg


def _exportar_csv(db, csv_path=CSV_PATH):
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Nombre", "Numero de Celular", "Productos consultados", "Fecha", "Sesion"])
        for sesion, r in db.items():
            w.writerow([r.get("nombre", ""), r.get("celular", ""),
                        " | ".join(r.get("productos", [])), r.get("fecha", ""), sesion])
