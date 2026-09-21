#!/usr/bin/env python3
"""Devuelve el resumen actual de una campaña sin aprobarla ni enviarla."""
import argparse
import json
import sys

from api_mailing import MailingApi


def ejecutar(api, version_id):
    return api.get(f"/admin/mailing/campanias/{version_id}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version_id")
    args = parser.parse_args(argv)
    api = MailingApi()
    try:
        version = ejecutar(api, args.version_id)
        manifiesto = version.get("manifest") or {}
        resumen = {
            "id": version.get("id"),
            "campaign_id": version.get("campaign_id"),
            "version": version.get("version"),
            "estado": version.get("estado"),
            "asunto": manifiesto.get("asunto"),
            "productos": manifiesto.get("productos", []),
            "hero_url": manifiesto.get("asset_url"),
            "destinatarios_actuales": version.get("destinatarios_actuales"),
            "catalogo_vigente": version.get("catalogo_vigente"),
            "asset_disponible": version.get("asset_disponible"),
            "envio_disponible": version.get("envio_disponible"),
        }
        print(json.dumps(resumen, ensure_ascii=False))
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        api.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
