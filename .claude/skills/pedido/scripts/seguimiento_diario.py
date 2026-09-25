#!/usr/bin/env python3
"""Manda el mail automático de seguimiento a los pedidos entregados hace 7
días (ver web/mailing/seguimiento.py). Pensado para correr una vez por día
con la skill `schedule`.

Uso:
    ./.venv/bin/python .claude/skills/pedido/scripts/seguimiento_diario.py

Escribe DIRECTO en la base de producción, igual que cargar_pedido.py.
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

from web.mailing import seguimiento
from web.supabase_client import get_client


def main():
    resultado = seguimiento.enviar_seguimientos(get_client())
    print(f"Seguimientos enviados: {resultado['enviados']}, fallidos: {resultado['fallidos']}")


if __name__ == "__main__":
    main()
