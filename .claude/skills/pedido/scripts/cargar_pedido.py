#!/usr/bin/env python3
"""Carga un cliente (si no existe) + un pedido en la base de producción (Supabase).

Uso:
    ./.venv/bin/python .claude/skills/pedido/scripts/cargar_pedido.py \\
        --nombre "Inti Nahuel" --apellido "Algarbe" \\
        --email intialgarbe@gmail.com --celular "+54 9 3516 09-8597" \\
        --direccion "Bv. Quinta Sta. Ana 162, X5000 Córdoba" \\
        --producto "s26 ultra 256gb" --fecha manana

Si el celular ya existe como cliente, NO crea cuenta nueva ni manda mail de
credenciales — reusa ese cliente_id y solo agrega el pedido.

Escribe DIRECTO en la base de producción. No hay ambiente de prueba separado
(ver web/supabase_client.py) — revisar bien los datos antes de correr.
"""
import argparse
import json
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

from web.supabase_client import get_client
from web import cuentas, domicilios, pedidos, email_util
from web.productos import resolver_proveedor


def buscar_producto(termino):
    productos = json.loads((PROJECT_DIR / "web" / "productos.json").read_text(encoding="utf-8"))
    palabras = termino.strip().lower().split()
    exactos = [p for p in productos if (p.get("nombre") or "").strip().lower() == " ".join(palabras)]
    if exactos:
        return exactos
    return [
        p for p in productos
        if all(palabra in (p.get("nombre") or "").lower() for palabra in palabras)
    ]


def resolver_fecha(valor):
    hoy = date.today()
    if valor in (None, "", "manana", "mañana"):
        return hoy + timedelta(days=1)
    if valor in ("hoy",):
        return hoy
    if valor in ("pasado", "pasado manana", "pasado mañana"):
        return hoy + timedelta(days=2)
    return datetime.strptime(valor, "%Y-%m-%d").date()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--nombre", required=True)
    ap.add_argument("--apellido", required=True)
    ap.add_argument("--email", required=True)
    ap.add_argument("--celular", required=True)
    ap.add_argument("--direccion", required=True, help="dirección de entrega (y domicilio principal si es cliente nuevo)")
    ap.add_argument("--piso", default=None, help="piso (opcional)")
    ap.add_argument("--depto", default=None, help="departamento (opcional)")
    ap.add_argument("--producto", required=True, help="término de búsqueda, debe matchear EXACTAMENTE un producto de productos.json")
    ap.add_argument("--cantidad", type=int, default=1)
    ap.add_argument("--fecha", default="manana", help="YYYY-MM-DD, o 'hoy'/'manana'/'pasado manana' (default: manana)")
    args = ap.parse_args()
    # Solo se pasan si vienen: así el script sigue andando con código web/
    # que todavía no conozca piso/depto.
    extra_domicilio = {k: v for k, v in {"piso": args.piso, "depto": args.depto}.items() if v}
    extra_pedido = {k: v for k, v in {"piso_entrega": args.piso, "depto_entrega": args.depto}.items() if v}

    candidatos = buscar_producto(args.producto)
    if len(candidatos) == 0:
        print(f"ERROR: ningún producto matchea '{args.producto}' en productos.json.", file=sys.stderr)
        sys.exit(1)
    if len(candidatos) > 1:
        print(f"ERROR: '{args.producto}' matchea {len(candidatos)} productos, sé más específico:", file=sys.stderr)
        for p in candidatos:
            print(f"  - {p['nombre']}", file=sys.stderr)
        sys.exit(1)
    producto = candidatos[0]
    nombre_producto = producto["nombre"]
    usd_unitario = pedidos.numero_monetario_db(producto["usd"])

    try:
        fecha_entrega = resolver_fecha(args.fecha)
    except ValueError:
        print(f"ERROR: fecha '{args.fecha}' inválida, usá YYYY-MM-DD.", file=sys.stderr)
        sys.exit(1)

    client = get_client()
    celular_norm = cuentas.normalizar_celular(args.celular)
    email_norm = args.email.strip().lower()

    existentes_celular = client.table("clientes").select("*").eq("celular", celular_norm).execute().data
    existentes_email = client.table("clientes").select("*").eq("email", email_norm).execute().data

    password = None
    if existentes_celular:
        cliente = existentes_celular[0]
        cliente_id = cliente["id"]
        cliente_nuevo = False
        print(f"Cliente ya existe (celular {celular_norm}) — reuso cliente_id {cliente_id}, no creo cuenta ni mando mail.")
    else:
        if existentes_email:
            print(f"ERROR: el email {email_norm} ya está usado por otro cliente (celular distinto). Revisar a mano.", file=sys.stderr)
            sys.exit(1)
        password = cuentas.generar_password_temporal()
        auth_resp = client.auth.admin.create_user({
            "email": email_norm,
            "password": password,
            "email_confirm": True,
        })
        auth_id = auth_resp.user.id
        cliente_id = str(uuid.uuid4())
        client.table("clientes").insert({
            "id": cliente_id,
            "auth_id": auth_id,
            "nombre": cuentas.capitalizar_nombre(args.nombre),
            "apellido": cuentas.capitalizar_nombre(args.apellido),
            "celular": celular_norm,
            "email": email_norm,
            "provincia": "Córdoba",
            "direccion": args.direccion,
            "tipo_cliente": "minorista",
            "debe_cambiar_password": True,
        }).execute()
        try:
            domicilios.crear(client, cliente_id, "Principal", args.direccion, predeterminado=True, **extra_domicilio)
        except Exception as e:
            print(f"AVISO: no se pudo guardar el domicilio inicial: {e}")
        cliente_nuevo = True

    usd_subtotal = round(usd_unitario * args.cantidad, 2)
    proveedores = {}
    proveedores_path = PROJECT_DIR / "web" / "proveedores.json"
    if proveedores_path.exists():
        proveedores = json.loads(proveedores_path.read_text(encoding="utf-8"))
    proveedor = resolver_proveedor(proveedores, nombre_producto)

    detalle = [{
        "nombre": nombre_producto,
        "color": None,
        "cantidad": args.cantidad,
        "usd_unitario": usd_unitario,
        "usd_subtotal": usd_subtotal,
        "proveedor": proveedor,
    }]

    pedido = pedidos.guardar_pedido(
        client,
        cliente_id,
        [nombre_producto],
        fecha_entrega,
        direccion_entrega=args.direccion,
        detalle=detalle,
        total_usd=usd_subtotal,
        descuento_usd=0,
        modo_precio="minorista",
        descuento_mayorista_usd=0,
        origen="manual",
        **extra_pedido,
    )

    mail_ok = None
    if cliente_nuevo:
        html = f"""
<p>Hola {cuentas.capitalizar_nombre(args.nombre)}, ¿cómo estás? Soy Vladimir de The Tech Room Arg.</p>
<p>Te creé tu cuenta para que puedas hacer seguimiento de tu pedido en la web:</p>
<p><b>Email:</b> {email_norm}<br><b>Contraseña temporal:</b> {password}</p>
<p>Al entrar por primera vez te va a pedir que elijas una contraseña nueva.</p>
<p>Cualquier cosa, quedo a disposición.</p>
"""
        try:
            email_util.enviar_email(email_norm, "Tu cuenta en The Tech Room Arg", html)
            mail_ok = True
        except Exception as e:
            mail_ok = f"FALLÓ: {e}"

    print("OK")
    print("cliente_id:", cliente_id)
    print("cliente_nuevo:", cliente_nuevo)
    if password:
        print("password_temporal:", password)
    print("producto:", nombre_producto)
    print("proveedor (interno):", proveedor)
    print("pedido_id:", pedido.get("id"))
    print("fecha_entrega:", fecha_entrega.isoformat())
    print("total_usd:", usd_subtotal)
    if mail_ok is not None:
        print("mail_enviado:", mail_ok)


if __name__ == "__main__":
    main()
