"""Remera gratis de The Tech Room Arg para los pedidos que dejan buena ganancia.

- Si el pedido deja GANANCIA_LIMPIA_MINIMA_USD limpios, el cliente elige talle al
  confirmar y la remera se suma al detalle como regalo (US$ 0).
- El stock vive en un JSON propio (junto al catálogo, en el volumen de
  producción). Se resta recién cuando se envía el recibo; hasta entonces las
  remeras pedidas quedan reservadas y no se ofrecen de nuevo.
- Ganancia limpia = Σ(precio − costo) de los productos del catálogo − descuentos
  − COSTO_ENTREGA_USD. Los cargadores promocionales no cuentan, y si falta el
  costo de algún producto no se ofrece (nunca se regala sin poder medirlo).
"""
import json
import os
import re
import threading
from decimal import Decimal
from pathlib import Path

TALLES = ("S", "M", "L", "XL")
STOCK_INICIAL = {"S": 0, "M": 0, "L": 75, "XL": 15}
GANANCIA_LIMPIA_MINIMA_USD = Decimal("60")
COSTO_ENTREGA_USD = Decimal("15")
NOMBRE_BASE = "Remera The Tech Room Arg"
PROVEEDOR_REGALO = "regalo"

_TRABA = threading.Lock()
_ITEM = re.compile(rf"^{re.escape(NOMBRE_BASE)} \(talle (S|M|L|XL)\) — Regalo$")


def ruta_stock():
    explicita = os.environ.get("REMERAS_PATH")
    if explicita:
        return Path(explicita)
    productos = os.environ.get("PRODUCTOS_PATH") or str(Path(__file__).parent / "productos.json")
    return Path(productos).with_name("remeras-stock.json")


def nombre_item(talle):
    return f"{NOMBRE_BASE} (talle {talle}) — Regalo"


def talle_de_item(item):
    coincide = _ITEM.match(str((item or {}).get("nombre") or ""))
    return coincide.group(1) if coincide else None


def talles_del_detalle(detalle):
    return [t for t in (talle_de_item(i) for i in detalle or []) if t]


def item_regalo(talle):
    return {
        "nombre": nombre_item(talle), "color": None, "cantidad": 1,
        "usd_unitario": 0, "usd_subtotal": 0, "proveedor": PROVEEDOR_REGALO,
    }


def leer_stock():
    ruta = ruta_stock()
    try:
        crudo = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        crudo = {}
    return {t: max(int(crudo.get(t, STOCK_INICIAL[t]) or 0), 0) for t in TALLES}


def _escribir(stock):
    ruta = ruta_stock()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(".tmp")
    temporal.write_text(json.dumps(stock, indent=2), encoding="utf-8")
    temporal.replace(ruta)


def fijar_stock(talle, cantidad):
    if talle not in TALLES or int(cantidad) < 0:
        raise ValueError("Talle o cantidad inválidos.")
    with _TRABA:
        stock = leer_stock()
        stock[talle] = int(cantidad)
        _escribir(stock)
        return stock


def descontar(talles):
    """Resta una remera por cada talle. Nunca baja de cero."""
    if not talles:
        return leer_stock()
    with _TRABA:
        stock = leer_stock()
        for talle in talles:
            if talle in stock:
                stock[talle] = max(stock[talle] - 1, 0)
        _escribir(stock)
        return stock


def reservadas(client):
    """Remeras ya pedidas cuyo recibo todavía no se envió."""
    filas = client.table("pedidos").select("*").is_("recibo_enviado_en", "null").execute().data or []
    cuenta = {t: 0 for t in TALLES}
    for fila in filas:
        if fila.get("borrado_en"):
            continue
        for talle in talles_del_detalle(fila.get("detalle")):
            cuenta[talle] += 1
    return cuenta


def disponibles(client):
    stock, pedidas = leer_stock(), reservadas(client)
    return {t: max(stock[t] - pedidas[t], 0) for t in TALLES}


def ganancia_limpia(detalle, costos, descuento_usd=0):
    """Ganancia limpia en USD, o None si algún producto no tiene costo."""
    margen = Decimal("0")
    for item in detalle or []:
        proveedor = item.get("proveedor")
        if proveedor in ("envío", PROVEEDOR_REGALO) or talle_de_item(item):
            continue
        if proveedor == "stock propio" and item.get("nombre") not in costos:
            continue  # cargador promocional: precio fijo, no suma ganancia
        costo = costos.get(item.get("nombre"))
        if costo is None:
            return None
        cantidad = Decimal(str(item.get("cantidad") or 0))
        subtotal = Decimal(str(item.get("usd_subtotal") or 0))
        margen += subtotal - Decimal(str(costo)) * cantidad
    return margen - Decimal(str(descuento_usd or 0)) - COSTO_ENTREGA_USD


def merece_remera(detalle, costos, descuento_usd=0):
    if talles_del_detalle(detalle):
        return False
    ganancia = ganancia_limpia(detalle, costos, descuento_usd)
    return ganancia is not None and ganancia >= GANANCIA_LIMPIA_MINIMA_USD


def oferta(client):
    """Talles con su disponibilidad, o None si no queda ninguno para regalar."""
    libres = disponibles(client)
    if not any(libres.values()):
        return None
    return {"talles": [{"talle": t, "disponible": libres[t] > 0} for t in TALLES]}
