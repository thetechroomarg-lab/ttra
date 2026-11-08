"""Activa o consulta un código de descuento público de un solo uso.

Uso (en el servidor, p. ej. vía `railway ssh`):
    python scripts/codigo_publico.py activar GRACIASBOBIS 20
    python scripts/codigo_publico.py estado GRACIASBOBIS
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from web import codigos_publicos  # noqa: E402
from web.supabase_client import get_client  # noqa: E402


def main(argv):
    if len(argv) >= 3 and argv[0] == "activar":
        resultado = codigos_publicos.activar(get_client(), argv[1], argv[2])
    elif len(argv) >= 2 and argv[0] == "estado":
        resultado = codigos_publicos.estado(get_client(), argv[1])
    else:
        print(__doc__)
        return 2
    print(json.dumps(resultado, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
