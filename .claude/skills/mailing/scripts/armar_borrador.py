#!/usr/bin/env python3
"""Arma el borrador semanal de la campaña de mailing de novedades: detecta
productos nuevos del catálogo, completa hasta 10 productos siempre (sin
excepción, 5 por columna), suma la nota pendiente (si hay), arma el HTML
y lo deja guardado para que el agente lo publique como Artifact.

Uso:
    ./.venv/bin/python .claude/skills/mailing/scripts/armar_borrador.py

No envía nada — solo arma el borrador. El envío real lo dispara
enviar_campania.py, siempre a mano (ver .claude/skills/mailing/SKILL.md).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

from web.mailing import catalogo_diff, destinatarios, estado, template
from web.supabase_client import get_client

DATA_DIR = PROJECT_DIR / "web" / "mailing" / "data"


def main():
    try:
        productos_actuales = json.loads(
            (PROJECT_DIR / "web" / "productos.json").read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        productos_actuales = None

    if not productos_actuales:
        print(
            "ERROR: productos.json no accesible o vacío, no se puede armar el borrador.",
            file=sys.stderr,
        )
        sys.exit(1)

    snapshot_anterior = estado.leer_snapshot(DATA_DIR)
    if snapshot_anterior is None:
        estado.guardar_snapshot(DATA_DIR, productos_actuales)
        print("PRIMERA_CORRIDA: snapshot inicializado, no hay borrador para armar todavía.")
        return

    nuevos = catalogo_diff.detectar_nuevos(productos_actuales, snapshot_anterior)
    nota = estado.leer_nota_pendiente(DATA_DIR)

    # Se actualiza en cada corrida, se arme borrador o no, para que la
    # próxima comparación sea siempre contra el catálogo más reciente.
    estado.guardar_snapshot(DATA_DIR, productos_actuales)

    # La campaña siempre sale con 10 productos, sin excepción — si hay menos
    # de 10 nuevos esta semana, se completa al azar con el resto del catálogo.
    seleccion = catalogo_diff.seleccionar_para_campania(nuevos, productos_actuales, cantidad=10)

    client = get_client()
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
    estado.guardar_borrador(DATA_DIR, borrador)
    estado.limpiar_nota_pendiente(DATA_DIR)

    print("BORRADOR_LISTO")
    print("productos_en_la_campania:", len(seleccion))
    print("de_los_cuales_nuevos_esta_semana:", len(nuevos))
    for producto in seleccion:
        marca = "(nuevo)" if producto in nuevos else "(relleno)"
        print("  -", producto["nombre"], marca)
    print("incluye_nota:", bool(nota))
    print("destinatarios:", len(elegibles))
    print("archivo:", DATA_DIR / "borrador_actual.json")


if __name__ == "__main__":
    main()
