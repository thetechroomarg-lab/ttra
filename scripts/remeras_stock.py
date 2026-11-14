"""Consulta o actualiza el stock de remeras de regalo.

Uso (en el servidor, p. ej. vía `railway ssh`):
    python scripts/remeras_stock.py ver
    python scripts/remeras_stock.py fijar L 75
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from web import remeras  # noqa: E402


def main(argv):
    if argv[:1] == ["ver"]:
        resultado = remeras.leer_stock()
    elif len(argv) == 3 and argv[0] == "fijar":
        resultado = remeras.fijar_stock(argv[1].upper(), int(argv[2]))
    else:
        print(__doc__)
        return 2
    print(json.dumps(resultado))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
