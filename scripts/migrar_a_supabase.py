"""Migración única de usuarios.db (mayoristas) y clientes.json (leads) a
Supabase. Correr una sola vez, antes de deployar el nuevo flujo de auth:

    python -m scripts.migrar_a_supabase

Requiere SUPABASE_URL / SUPABASE_SERVICE_KEY en el entorno (ver web/supabase_client.py).
"""
import json
import os
import secrets
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
    """Cada mayorista recibe una cuenta REAL de Supabase Auth desde el
    momento de la migración (auth.admin.create_user), no una fila "invitada"
    sin auth_id — así su fila nunca puede ser reclamada por otra persona
    registrándose con ese email (ver web/cuentas.py: la vinculación de una
    fila invitada es solo por celular, nunca por email, justamente para
    evitar esa apropiación). El mayorista entra con el flujo nativo de
    "restablecer contraseña" de Supabase (dispara el mail acá mismo), nunca
    con el formulario público de /registro."""
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
        password_temporal = secrets.token_urlsafe(24)
        auth_resp = client.auth.admin.create_user({
            "email": email,
            "password": password_temporal,
            "email_confirm": True,
        })
        client.table("clientes").insert({
            "id": str(uuid.uuid4()),
            "auth_id": auth_resp.user.id,
            "nombre": nombre,
            "apellido": "",
            "celular": f"pendiente-{uuid.uuid4()}",  # placeholder: no había celular en usuarios.db
            "email": email,
            "tipo_cliente": "mayorista",
            "creado_en": creado,
        }).execute()
        client.auth.reset_password_for_email(email)
        migrados += 1
    return migrados


def _fusionar_leads_por_celular(db):
    """clientes.json puede tener la misma persona guardada varias veces con
    formatos de celular distintos (ej. "+543513017015" y "3513017015" en
    sesiones distintas) — normalizar_celular los unifica, pero si cada
    entrada se migrara por separado, la primera "ganaría" el celular y las
    demás se descartarían enteras por "ya existe", perdiendo sus productos.
    Acá se fusionan ANTES de tocar Supabase: se acumulan todos los
    productos, se queda el nombre más largo/completo y la fecha más
    reciente."""
    fusionados = {}
    for reg in db.values():
        celular = normalizar_celular(reg.get("celular", ""))
        if not celular:
            continue
        actual = fusionados.setdefault(celular, {"nombre": "", "productos": [], "fecha": ""})
        if len(reg.get("nombre") or "") > len(actual["nombre"]):
            actual["nombre"] = reg["nombre"]
        for producto in (reg.get("productos") or []):
            if producto not in actual["productos"]:
                actual["productos"].append(producto)
        if (reg.get("fecha") or "") > actual["fecha"]:
            actual["fecha"] = reg["fecha"]
    return fusionados


def _migrar_leads(client, json_path):
    if not Path(json_path).exists():
        return 0
    db = json.loads(Path(json_path).read_text(encoding="utf-8"))
    migrados = 0
    for celular, datos in _fusionar_leads_por_celular(db).items():
        existentes = client.table("clientes").select("*").eq("celular", celular).execute().data
        if existentes:
            continue
        cliente_id = str(uuid.uuid4())
        client.table("clientes").insert({
            "id": cliente_id,
            "auth_id": None,
            "nombre": datos["nombre"],
            "apellido": "",
            "celular": celular,
            "email": f"pendiente-{uuid.uuid4()}@sin-email.local",  # placeholder: no había email en clientes.json
            "tipo_cliente": "minorista",
            "creado_en": datos["fecha"],
        }).execute()
        if datos["productos"]:
            guardar_pedido(client, cliente_id, datos["productos"], origen="whatsapp")
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
