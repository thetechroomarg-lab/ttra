"""Persistencia en disco del estado de las campañas de mailing (snapshot del
catálogo, nota pendiente, borrador actual, log de envíos). Vive fuera de
Supabase: son archivos JSON simples, sin necesidad de una tabla nueva."""
import json
from datetime import datetime, timezone


def _leer(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _escribir(path, datos):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def leer_snapshot(data_dir):
    return _leer(data_dir / "snapshot_catalogo.json")


def guardar_snapshot(data_dir, productos):
    _escribir(data_dir / "snapshot_catalogo.json", productos)


def leer_nota_pendiente(data_dir):
    datos = _leer(data_dir / "nota_pendiente.json")
    return (datos or {}).get("texto")


def guardar_nota_pendiente(data_dir, texto):
    _escribir(data_dir / "nota_pendiente.json", {
        "texto": texto,
        "creada_en": datetime.now(timezone.utc).isoformat(),
    })


def limpiar_nota_pendiente(data_dir):
    _escribir(data_dir / "nota_pendiente.json", {"texto": None, "creada_en": None})


def leer_borrador(data_dir):
    return _leer(data_dir / "borrador_actual.json")


def guardar_borrador(data_dir, borrador):
    _escribir(data_dir / "borrador_actual.json", borrador)


def marcar_borrador_usado(data_dir):
    borrador = leer_borrador(data_dir)
    if borrador is not None:
        borrador["usado"] = True
        guardar_borrador(data_dir, borrador)


def registrar_envio(data_dir, linea):
    path = data_dir / "enviados.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(linea.rstrip("\n") + "\n")
