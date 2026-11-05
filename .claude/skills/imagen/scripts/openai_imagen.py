"""Genera o edita imágenes con OpenAI (gpt-image) y las guarda en disco.

Uso:
  python3 openai_imagen.py "prompt" [--ref foto.jpg ...] [--aspect 1:1] [--calidad high] [--out carpeta] [--nombre base]

Lee la key de OPENAI_API_KEY (entorno o .env de la raíz del repo). Modelo por defecto en OPENAI_IMAGE_MODEL.
Con --ref usa el endpoint de edición. Solo usa la librería estándar.
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path

MODELO_DEFAULT = "gpt-image-1"
SALIDA_DEFAULT = Path("/Users/toraba/Precios Claude/Imagenes")
API = "https://api.openai.com/v1/images"

ENV_REPO = Path(__file__).resolve().parents[4] / ".env"

# gpt-image solo genera cuadrado, apaisado o vertical: cada aspecto va al más cercano.
TAMANIOS = {
    "1:1": "1024x1024",
    "16:9": "1536x1024", "3:2": "1536x1024", "4:3": "1536x1024",
    "9:16": "1024x1536", "2:3": "1024x1536", "3:4": "1024x1536", "4:5": "1024x1536",
}


def _leer_key():
    key = os.environ.get("OPENAI_API_KEY")
    if key or not ENV_REPO.is_file():
        return key
    for linea in ENV_REPO.read_text().splitlines():
        nombre, _, valor = linea.strip().partition("=")
        if nombre.removeprefix("export ").strip() == "OPENAI_API_KEY":
            return valor.strip().strip("\"'")
    return None


def _multipart(campos, archivos):
    limite = uuid.uuid4().hex
    cuerpo = b""
    for nombre, valor in campos.items():
        cuerpo += (f"--{limite}\r\nContent-Disposition: form-data; name=\"{nombre}\"\r\n\r\n{valor}\r\n").encode()
    for nombre, ruta in archivos:
        mime = mimetypes.guess_type(ruta)[0] or "image/png"
        cuerpo += (
            f"--{limite}\r\nContent-Disposition: form-data; name=\"{nombre}\"; filename=\"{Path(ruta).name}\"\r\n"
            f"Content-Type: {mime}\r\n\r\n"
        ).encode() + Path(ruta).read_bytes() + b"\r\n"
    cuerpo += f"--{limite}--\r\n".encode()
    return cuerpo, f"multipart/form-data; boundary={limite}"


def generar(prompt, refs, tamanio, calidad, modelo, key):
    campos = {"model": modelo, "prompt": prompt, "size": tamanio, "quality": calidad}
    if refs:
        datos, tipo = _multipart(campos, [("image[]", r) for r in refs])
        url = f"{API}/edits"
    else:
        datos, tipo = json.dumps(campos).encode(), "application/json"
        url = f"{API}/generations"
    req = urllib.request.Request(url, data=datos, headers={"Content-Type": tipo, "Authorization": f"Bearer {key}"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"OpenAI respondió {e.code}: {e.read().decode(errors='replace')[:800]}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("prompt")
    p.add_argument("--ref", action="append", default=[], help="imagen de referencia (repetible)")
    p.add_argument("--aspect", default="1:1", choices=sorted(TAMANIOS), help="se aproxima a cuadrado, apaisado o vertical")
    p.add_argument("--calidad", default="high", choices=["low", "medium", "high"])
    p.add_argument("--out", type=Path, default=SALIDA_DEFAULT)
    p.add_argument("--nombre", default="imagen")
    p.add_argument("--modelo", default=os.environ.get("OPENAI_IMAGE_MODEL", MODELO_DEFAULT))
    a = p.parse_args()

    key = _leer_key()
    if not key:
        sys.exit(f"Falta OPENAI_API_KEY (cargala en {ENV_REPO}).")
    for r in a.ref:
        if not Path(r).is_file():
            sys.exit(f"No existe la referencia: {r}")

    resp = generar(a.prompt, a.ref, TAMANIOS[a.aspect], a.calidad, a.modelo, key)
    a.out.mkdir(parents=True, exist_ok=True)
    sello = datetime.now().strftime("%Y%m%d-%H%M%S")
    guardadas = 0
    for item in resp.get("data", []):
        if item.get("b64_json"):
            guardadas += 1
            ruta = a.out / f"{a.nombre}-{sello}-{guardadas}.png"
            ruta.write_bytes(base64.b64decode(item["b64_json"]))
            print(ruta)
    if not guardadas:
        sys.exit(f"OpenAI no devolvió imagen: {json.dumps(resp)[:800]}")


if __name__ == "__main__":
    main()
