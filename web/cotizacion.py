"""Cotización manual persistente, independiente de las publicaciones de catálogo."""
import json
import math
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def ruta(productos_path):
    return Path(os.environ.get("COTIZACION_PATH") or
                Path(productos_path).with_name("cotizacion-admin.json"))


def validar(valor):
    if isinstance(valor, bool) or not isinstance(valor, (str, int)):
        raise ValueError("Ingresá solo números, sin puntos ni comas.")
    texto = str(valor)
    if not re.fullmatch(r"[0-9]{1,9}", texto) or int(texto) <= 0:
        raise ValueError("Ingresá un número mayor que cero, de hasta 9 dígitos, sin puntos ni comas.")
    return int(texto)


def leer(productos_path):
    try:
        contenido = ruta(productos_path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    datos = json.loads(contenido)
    datos["valor"] = validar(datos["valor"])
    return datos


def guardar(productos_path, valor):
    datos = {"valor": validar(valor), "actualizado_en": datetime.now(timezone.utc).isoformat()}
    destino = ruta(productos_path)
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporal = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destino.parent,
                                         prefix=".cotizacion-", delete=False) as archivo:
            temporal = Path(archivo.name)
            json.dump(datos, archivo)
            archivo.flush()
            os.fsync(archivo.fileno())
        os.replace(temporal, destino)
    finally:
        if temporal is not None:
            temporal.unlink(missing_ok=True)
    return datos


def aplicar(productos, datos):
    if datos is None:
        return productos
    resultado = []
    for producto in productos:
        copia = dict(producto)
        usd = copia.get("usd")
        if isinstance(usd, (int, float)) and not isinstance(usd, bool) and math.isfinite(usd):
            copia["pesos"] = round(usd * datos["valor"])
            copia["transferencia"] = round(copia["pesos"] / 0.97)
        resultado.append(copia)
    return resultado
