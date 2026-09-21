#!/usr/bin/env python3
"""Sube arte generado y crea una versión previsualizada; nunca envía correo."""
import argparse
import json
import sys
import uuid
from pathlib import Path

from api_mailing import MailingApi


def ejecutar(api, imagen, productos, brief, asunto, preheader, alt, nota=None, parent_id=None):
    if not productos:
        raise ValueError("Seleccioná al menos un producto")
    if parent_id:
        padre = api.get(f"/admin/mailing/campanias/{parent_id}")
        campaign_id = padre["campaign_id"]
    else:
        campaign_id = str(uuid.uuid4())
    asset = api.post_file(f"/admin/mailing/assets/{campaign_id}", Path(imagen))
    payload = {
        "campaign_id": campaign_id,
        "parent_id": parent_id,
        "brief": brief,
        "asunto": asunto,
        "preheader": preheader,
        "nota": nota,
        "productos": productos,
        "hero": {
            "url": asset["url"],
            "sha256": asset["sha256"],
            "alt": alt,
            "width": asset["width"],
            "height": asset["height"],
        },
    }
    version = api.post("/admin/mailing/campanias", json=payload)
    return {**version, "campaign_id": campaign_id, "asset_url": asset["url"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--imagen", required=True, type=Path)
    parser.add_argument("--producto", action="append", required=True)
    parser.add_argument("--brief", default="")
    parser.add_argument("--asunto", required=True)
    parser.add_argument("--preheader", default="")
    parser.add_argument("--alt", required=True)
    parser.add_argument("--nota")
    parser.add_argument("--parent-id")
    args = parser.parse_args(argv)
    if not args.imagen.is_file():
        parser.error("--imagen debe apuntar a un archivo existente")
    api = MailingApi()
    try:
        resultado = ejecutar(
            api, args.imagen, args.producto, args.brief, args.asunto,
            args.preheader, args.alt, args.nota, args.parent_id,
        )
        print(json.dumps(resultado, ensure_ascii=False))
    except (RuntimeError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        api.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
