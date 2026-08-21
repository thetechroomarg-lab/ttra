"""Migración única de usuarios.db (mayoristas) y clientes.json (leads) a
Supabase. Correr una sola vez, antes de deployar el nuevo flujo de auth:

    python -m scripts.migrar_a_supabase

Requiere SUPABASE_URL / SUPABASE_SERVICE_KEY en el entorno (ver web/supabase_client.py).
"""
import json
import os
import sqlite3
import uuid
from pathlib import Path

from web.cuentas import normalizar_celular
from web.pedidos import guardar_pedido
from web.supabase_client import get_client

BASE = Path(__file__).parent.parent / "web"
USUARIOS_DB_PATH = BASE / "usuarios.db"


def resolver_clientes_json_path():
    """clientes.json vive en un volumen persistente en producción (Railway
    pisa el filesystem del contenedor en cada deploy), apuntado por
    CLIENTES_PATH o, si no está seteada, por el directorio de PRODUCTOS_PATH
    — misma resolución que usaba web/leads.py (ya eliminado) antes de esta
    migración. Se resuelve en cada llamado (no una sola vez al importar) para
    que sea testeable con monkeypatch de variables de entorno."""
    productos_path = os.environ.get("PRODUCTOS_PATH")
    clientes_dir = Path(
        os.environ.get("CLIENTES_PATH") or (Path(productos_path).parent if productos_path else BASE)
    )
    return clientes_dir / "clientes.json"


CLIENTES_JSON_PATH = resolver_clientes_json_path()


def _email_existe(client, email):
    filas = client.table("clientes").select("*").eq("email", email).execute().data
    return bool(filas)


def _migrar_mayoristas(client, db_path):
    if not Path(db_path).exists():
        return 0
    conn = sqlite3.connect(str(db_path))
    filas = conn.execute("SELECT nombre, email, creado FROM usuarios").fetchall()
    conn.close()
    migrados = 0
    for nombre, email, creado in filas:
        email = email.strip().lower()
        if _email_existe(client, email):
            continue
        client.table("clientes").insert({
            "id": str(uuid.uuid4()),
            "auth_id": None,  # se linkea cuando el mayorista resetea password y entra por /registro o /login
            "nombre": nombre,
            "apellido": "",
            "celular": f"pendiente-{uuid.uuid4()}",  # placeholder: no había celular en usuarios.db
            "email": email,
            "tipo_cliente": "mayorista",
            "creado_en": creado,
        }).execute()
        migrados += 1
    return migrados


def _migrar_leads(client, json_path):
    if not Path(json_path).exists():
        return 0
    db = json.loads(Path(json_path).read_text(encoding="utf-8"))
    migrados = 0
    for reg in db.values():
        celular = normalizar_celular(reg.get("celular", ""))
        if not celular:
            continue
        existentes = client.table("clientes").select("*").eq("celular", celular).execute().data
        if existentes:
            continue
        cliente_id = str(uuid.uuid4())
        client.table("clientes").insert({
            "id": cliente_id,
            "auth_id": None,
            "nombre": reg.get("nombre", ""),
            "apellido": "",
            "celular": celular,
            "email": f"pendiente-{uuid.uuid4()}@sin-email.local",  # placeholder: no había email en clientes.json
            "tipo_cliente": "minorista",
            "creado_en": reg.get("fecha", ""),
        }).execute()
        productos = reg.get("productos") or []
        if productos:
            guardar_pedido(client, cliente_id, productos, origen="whatsapp")
        migrados += 1
    return migrados


def migrar(client, usuarios_db_path=USUARIOS_DB_PATH, clientes_json_path=None):
    if clientes_json_path is None:
        clientes_json_path = resolver_clientes_json_path()
    return {
        "mayoristas": _migrar_mayoristas(client, usuarios_db_path),
        "leads": _migrar_leads(client, clientes_json_path),
    }


if __name__ == "__main__":
    resultado = migrar(get_client())
    print(f"Migrados: {resultado['mayoristas']} mayoristas, {resultado['leads']} leads")
