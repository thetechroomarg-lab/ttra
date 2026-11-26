"""Promo de U$D 10 (código de 72 hs) para minoristas que miraron productos y no compraron.

Uso (desde la raíz del repo, con web/.env):
    python scripts/promo_visto.py                     # simulación: lista destinatarios y guarda previews
    python scripts/promo_visto.py --enviar            # crea los códigos y manda los mails
Opciones: --dias 7 (ventana de vistas/pedidos), --max 50 (tope de mails).

Requiere la columna codigos_descuento.vence_en (supabase/migrations/20261125_*).
"""
import argparse
import collections
import secrets
import string
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parents[1] / "web" / ".env")

from web.email_util import EnvioEmailError, enviar_email  # noqa: E402
from web.mailing import promo_visto  # noqa: E402
from web.supabase_client import get_client  # noqa: E402

CATALOGO_URL = "https://www.thetechroomarg.com/api/productos"
TOPE_MAXIMO = 50


def _todas(query_fn):
    filas, desde = [], 0
    while True:
        lote = query_fn().range(desde, desde + 999).execute().data
        filas += lote
        if len(lote) < 1000:
            return filas
        desde += 1000


def _codigo_nuevo(client):
    alfabeto = string.ascii_uppercase + string.digits
    for _ in range(12):
        codigo = "TTRA-" + "".join(secrets.choice(alfabeto) for _ in range(8))
        if not client.table("codigos_descuento").select("id").eq("code", codigo).execute().data:
            return codigo
    raise RuntimeError("No se pudo generar un código único")


def candidatos(client, catalogo, dias, tope, enviar=False):
    desde = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()
    vistas = _todas(lambda: client.table("interacciones_cliente").select("*").gte("fecha", desde))
    por_cliente = collections.defaultdict(collections.Counter)
    for f in vistas:
        if f.get("cliente_id") and f.get("producto_nombre"):
            por_cliente[f["cliente_id"]][f["producto_nombre"]] += 1
    if not por_cliente:
        return []
    ids = list(por_cliente)
    clientes = client.table("clientes").select("*").in_("id", ids).execute().data
    pedidos = client.table("pedidos").select("cliente_id,fecha,borrado_en").in_("cliente_id", ids).execute().data
    con_pedido = {p["cliente_id"] for p in pedidos if not p.get("borrado_en") and (p.get("fecha") or "") >= desde}
    try:
        ya_promo = {
            c["cliente_id"] for c in client.table("codigos_descuento").select("cliente_id,tope_total_usd,vence_en")
            .in_("cliente_id", ids).execute().data
            if c.get("vence_en") and c.get("tope_total_usd") is not None
        }
    except Exception as e:
        if enviar:
            raise SystemExit(f"Falta la columna vence_en en codigos_descuento: correr la migración primero ({e})")
        print("AVISO: no existe vence_en todavía; no se pudo chequear promos previas (solo simulación)")
        ya_promo = set()
    por_nombre = {p["nombre"]: p for p in catalogo}
    vistos_mail, salida = set(), []
    for c in sorted(clientes, key=lambda c: c["id"]):
        email = (c.get("email") or "").strip().lower()
        if (c.get("tipo_cliente") != "minorista" or c.get("no_mailing") or not email
                or c["id"] in con_pedido or c["id"] in ya_promo or email in vistos_mail):
            continue
        productos = []
        for nombre, _ in por_cliente[c["id"]].most_common():
            p = por_nombre.get(nombre)
            # Nunca usados/CPO en un mailing.
            if p and p.get("usd") and "usado" not in nombre.lower() and "cpo" not in nombre.lower():
                productos.append(p)
        if not productos:
            continue
        vistos_mail.add(email)
        salida.append({"cliente": c, "email": email, "productos": productos[:promo_visto.MAX_PRODUCTOS]})
    return salida[:tope]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--enviar", action="store_true")
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--max", type=int, default=TOPE_MAXIMO)
    ap.add_argument("--excluir", action="append", default=[], help="email a dejar afuera")
    ap.add_argument("--preview-dir", default="/tmp")
    args = ap.parse_args()
    tope = min(args.max, TOPE_MAXIMO)
    client = get_client()
    catalogo = httpx.get(CATALOGO_URL, timeout=30).json()
    lista = [d for d in candidatos(client, catalogo, args.dias, tope, args.enviar) if d["email"] not in {e.lower() for e in args.excluir}]
    print(f"Destinatarios: {len(lista)} (tope {tope})")
    ahora = datetime.now(timezone.utc)
    vence = ahora + timedelta(hours=promo_visto.HORAS_VIGENCIA)
    enviados = 0
    for d in lista:
        c = d["cliente"]
        nombre = (c.get("nombre") or "").strip()
        print(f"- {d['email']} ({nombre}): {[p['nombre'] for p in d['productos']]}")
        if not args.enviar:
            _, cuerpo = promo_visto.armar_mail(nombre, d["productos"], "TTRA-EJEMPLO1", vence, c["id"])
            (Path(args.preview_dir) / f"promo_{c['id'][:8]}.html").write_text(cuerpo)
            continue
        codigo = _codigo_nuevo(client)
        client.table("codigos_descuento").insert({
            "cliente_id": c["id"], "code": codigo, "productos": [p["nombre"] for p in d["productos"]],
            "descuento_usd": promo_visto.DESCUENTO_USD, "tope_total_usd": promo_visto.DESCUENTO_USD,
            "vence_en": vence.isoformat(), "activo": False,
        }).execute()
        asunto, cuerpo = promo_visto.armar_mail(nombre, d["productos"], codigo, vence, c["id"])
        try:
            enviar_email(d["email"], asunto, cuerpo)
        except EnvioEmailError as e:
            print(f"  FALLÓ el mail ({e}); el código {codigo} queda inactivo")
            continue
        client.table("codigos_descuento").update({"activo": True}).eq("code", codigo).execute()
        enviados += 1
        print(f"  enviado, código {codigo}")
    if args.enviar:
        print(f"ENVIADOS: {enviados}/{len(lista)}  vence {promo_visto.texto_vencimiento(vence)}")


if __name__ == "__main__":
    main()
