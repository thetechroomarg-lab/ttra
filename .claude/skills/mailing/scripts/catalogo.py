#!/usr/bin/env python3
"""Consulta el catálogo público y filtra productos por términos de búsqueda."""
import argparse
import json
import sys

from api_mailing import MailingApi


def buscar(api, terminos=None):
    productos = api.get("/api/productos")
    tokens = [token.strip().casefold() for token in (terminos or []) if token.strip()]
    if not tokens:
        return productos
    return [
        producto for producto in productos
        if all(token in str(producto.get("nombre", "")).casefold() for token in tokens)
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buscar", action="append", default=[])
    args = parser.parse_args(argv)
    api = MailingApi()
    try:
        print(json.dumps(buscar(api, args.buscar), ensure_ascii=False))
    except (RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        api.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
