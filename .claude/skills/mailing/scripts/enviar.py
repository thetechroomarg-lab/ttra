#!/usr/bin/env python3
"""Envía una versión ya aprobada tras confirmación exacta de su UUID."""
import argparse
import json
import sys

from api_mailing import MailingApi


def ejecutar(api, version_id, confirmacion):
    esperado = f"ENVIAR {version_id}"
    if confirmacion != esperado:
        raise ValueError(f"Para enviar, la confirmación debe ser exactamente: {esperado}")
    return api.post(
        f"/admin/mailing/campanias/{version_id}/enviar",
        json={"confirmacion": confirmacion},
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version_id")
    parser.add_argument("--confirmacion", required=True)
    args = parser.parse_args(argv)
    api = MailingApi()
    try:
        print(json.dumps(ejecutar(api, args.version_id, args.confirmacion), ensure_ascii=False))
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        api.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
