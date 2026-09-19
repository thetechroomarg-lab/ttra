#!/usr/bin/env python3
"""Deja una nota/promo pendiente para que la incluya el próximo borrador
semanal de la campaña de mailing de novedades. Se guarda en Supabase, así
que sirve tanto para el borrador que arma un script local como para el que
arma la rutina en la nube.

Uso:
    ./.venv/bin/python .claude/skills/mailing/scripts/nota.py "texto de la nota"
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

from web.mailing import estado
from web.supabase_client import get_client


def main():
    if len(sys.argv) != 2:
        print("ERROR: pasá la nota como único argumento (entre comillas).", file=sys.stderr)
        sys.exit(1)
    texto = sys.argv[1].strip()
    if not texto:
        print("ERROR: la nota no puede estar vacía.", file=sys.stderr)
        sys.exit(1)

    client = get_client()

    anterior = estado.leer_nota_pendiente(client)
    if anterior:
        print(f"AVISO: pisaste una nota pendiente que no se había usado: {anterior!r}")

    estado.guardar_nota_pendiente(client, texto)
    print("OK: nota guardada para el próximo borrador.")


if __name__ == "__main__":
    main()
