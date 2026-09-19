#!/usr/bin/env python3
"""Envía la campaña de mailing de novedades ya aprobada por Vladimir a todos
los clientes elegibles. NUNCA se corre automáticamente — solo cuando
Vladimir confirmó el borrador que armó armar_borrador.py.

Uso:
    ./.venv/bin/python .claude/skills/mailing/scripts/enviar_campania.py
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

from web.mailing import destinatarios, estado, template
from web.email_util import EnvioEmailError, enviar_email
from web.supabase_client import get_client

DATA_DIR = PROJECT_DIR / "web" / "mailing" / "data"
ASUNTO = "Novedades de la semana en The Tech Room Arg"


def main():
    borrador = estado.leer_borrador(DATA_DIR)
    if borrador is None:
        print("ERROR: no hay ningún borrador armado. Corré armar_borrador.py primero.", file=sys.stderr)
        sys.exit(1)
    if borrador.get("usado"):
        print("ERROR: el último borrador ya fue enviado. Esperá al próximo borrador semanal.", file=sys.stderr)
        sys.exit(1)

    client = get_client()
    elegibles = destinatarios.clientes_elegibles(client)
    productos = borrador["productos"]
    nota = borrador.get("nota")

    ok, fallidos = 0, 0
    for cliente in elegibles:
        html = template.armar_html(productos, nota, cliente_id=cliente["id"])
        try:
            enviar_email(cliente["email"], ASUNTO, html)
            ok += 1
        except Exception as e:
            fallidos += 1
            print(f"FALLÓ envío a {cliente['email']}: {e}", file=sys.stderr)
        time.sleep(0.4)

    estado.marcar_borrador_usado(DATA_DIR)
    estado.registrar_envio(
        DATA_DIR,
        f"{datetime.now(timezone.utc).isoformat()} | productos={len(productos)} | ok={ok} | fallidos={fallidos}",
    )

    print(f"ENVIADA: {ok}/{ok + fallidos} destinatarios, {fallidos} fallidos.")


if __name__ == "__main__":
    main()
