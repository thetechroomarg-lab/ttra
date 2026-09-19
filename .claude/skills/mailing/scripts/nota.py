#!/usr/bin/env python3
"""Deja una nota/promo pendiente para que la incluya el próximo borrador
semanal de la campaña de mailing de novedades.

Uso:
    ./.venv/bin/python .claude/skills/mailing/scripts/nota.py "texto de la nota"
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from web.mailing import estado

DATA_DIR = PROJECT_DIR / "web" / "mailing" / "data"


def main():
    if len(sys.argv) != 2:
        print("ERROR: pasá la nota como único argumento (entre comillas).", file=sys.stderr)
        sys.exit(1)
    texto = sys.argv[1].strip()
    if not texto:
        print("ERROR: la nota no puede estar vacía.", file=sys.stderr)
        sys.exit(1)

    anterior = estado.leer_nota_pendiente(DATA_DIR)
    if anterior:
        print(f"AVISO: pisaste una nota pendiente que no se había usado: {anterior!r}")

    estado.guardar_nota_pendiente(DATA_DIR, texto)
    print("OK: nota guardada para el próximo borrador.")


if __name__ == "__main__":
    main()
