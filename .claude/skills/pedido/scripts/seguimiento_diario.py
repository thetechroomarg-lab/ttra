#!/usr/bin/env python3
"""Manda los mails automáticos post-entrega, una vez por día con la skill
`schedule`:
- seguimiento a los 7 días del recibo (web/mailing/seguimiento.py);
- 5 productos recomendados a los 30 días del recibo (web/mailing/recomendacion.py).

Uso:
    ./.venv/bin/python .claude/skills/pedido/scripts/seguimiento_diario.py

Escribe DIRECTO en la base de producción, igual que cargar_pedido.py. El
catálogo se lee del endpoint público /api/productos (precios vigentes), no
de un archivo local, así corre igual desde la nube.
"""
import os
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

import httpx

from web.mailing import recomendacion, seguimiento
from web.supabase_client import get_client

BASE_URL = os.environ.get("MAILING_BASE_URL", "https://thetechroomarg.com")


def _catalogo():
    try:
        respuesta = httpx.get(f"{BASE_URL}/api/productos", timeout=15)
        respuesta.raise_for_status()
        return respuesta.json()
    except (httpx.HTTPError, ValueError):
        return None


def main():
    client = get_client()
    resultado = seguimiento.enviar_seguimientos(client)
    print(f"Seguimientos enviados: {resultado['enviados']}, fallidos: {resultado['fallidos']}")

    catalogo = _catalogo()
    if not catalogo:
        print(f"ERROR: no se pudo leer el catálogo desde {BASE_URL}/api/productos, "
              "no se mandaron recomendaciones (se reintenta mañana).", file=sys.stderr)
        sys.exit(1)
    resultado = recomendacion.enviar_recomendaciones(client, catalogo)
    print(f"Recomendaciones enviadas: {resultado['enviados']}, fallidos: {resultado['fallidos']}")


if __name__ == "__main__":
    main()
