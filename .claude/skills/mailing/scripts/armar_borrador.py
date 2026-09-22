#!/usr/bin/env python3
"""Arma el borrador semanal de la campaña de mailing de novedades: detecta
productos nuevos del catálogo, completa hasta 10 productos siempre (sin
excepción, 5 por columna), suma la nota pendiente (si hay), arma el HTML
y lo deja guardado en Supabase para que el agente lo publique como Artifact.

Uso:
    ./.venv/bin/python .claude/skills/mailing/scripts/armar_borrador.py

Corre igual desde una máquina local o desde la rutina programada en la nube:
todo el estado (snapshot, nota, borrador) vive en Supabase, y el catálogo se
lee del endpoint público /api/productos, no de un archivo local.

No envía nada — solo arma el borrador. El envío real lo dispara
enviar_campania.py, siempre a mano (ver .claude/skills/mailing/SKILL.md).
"""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

from web.mailing import catalogo_diff, destinatarios, estado, template
from web.supabase_client import get_client

BASE_URL = os.environ.get("MAILING_BASE_URL", "https://thetechroomarg.com")


def main():
    try:
        respuesta = httpx.get(f"{BASE_URL}/api/productos", timeout=15)
        respuesta.raise_for_status()
        productos_actuales = respuesta.json()
    except (httpx.HTTPError, ValueError):
        productos_actuales = None

    if not productos_actuales:
        print(
            f"ERROR: no se pudo leer el catálogo desde {BASE_URL}/api/productos, no se puede armar el borrador.",
            file=sys.stderr,
        )
        sys.exit(1)

    client = get_client()

    # En la primera corrida no hay snapshot previo: se trata como catálogo
    # vacío, así que "nuevos" queda siendo todo el catálogo — no cambia el
    # resultado, porque seleccionar_para_campania igual recorta a 10 al azar.
    snapshot_anterior = estado.leer_snapshot(client) or []

    nuevos = catalogo_diff.detectar_nuevos(productos_actuales, snapshot_anterior)
    nota = estado.leer_nota_pendiente(client)

    # Se actualiza en cada corrida, se arme borrador o no, para que la
    # próxima comparación sea siempre contra el catálogo más reciente.
    estado.guardar_snapshot(client, productos_actuales)

    # La campaña siempre sale con 10 productos, sin excepción — si hay menos
    # de 10 nuevos esta semana, se completa al azar con el resto del catálogo.
    seleccion = catalogo_diff.seleccionar_para_campania(nuevos, productos_actuales, cantidad=10)

    elegibles = destinatarios.clientes_elegibles(client)
    html = template.armar_html(seleccion, nota)

    borrador = {
        "productos": seleccion,
        "nota": nota,
        "html_preview": html,
        "destinatarios": len(elegibles),
        "armado_en": datetime.now(timezone.utc).isoformat(),
        "usado": False,
    }
    estado.guardar_borrador(client, borrador)
    estado.limpiar_nota_pendiente(client)

    print("BORRADOR_LISTO")
    print("productos_en_la_campania:", len(seleccion))
    print("de_los_cuales_nuevos_esta_semana:", len(nuevos))
    for producto in seleccion:
        marca = "(nuevo)" if producto in nuevos else "(relleno)"
        print("  -", producto["nombre"], marca)
    print("incluye_nota:", bool(nota))
    print("destinatarios:", len(elegibles))


if __name__ == "__main__":
    main()
