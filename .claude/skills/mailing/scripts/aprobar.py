#!/usr/bin/env python3
"""Aprueba una versión concreta. La aprobación no ejecuta el envío."""
import argparse
import json
import sys

from api_mailing import MailingApi


def ejecutar(api, version_id):
    return api.post(f"/admin/mailing/campanias/{version_id}/aprobar")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version_id")
    args = parser.parse_args(argv)
    api = MailingApi()
    try:
        print(json.dumps(ejecutar(api, args.version_id), ensure_ascii=False))
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        api.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
