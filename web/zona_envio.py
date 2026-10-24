"""Costo de envío según la distancia a la Circunvalación de Córdoba Capital.

Los km se miden por ruta (Google Routes) desde el punto de la Circunvalación
más cercano hasta el domicilio. Adentro del anillo y hasta FRANJA_GRATIS_KM
de ruta afuera: gratis. De ahí hasta LIMITE_KM se cobra la nafta de ida y
vuelta por los km excedentes más RECARGO_DESGASTE_TIEMPO por desgaste del
vehículo y tiempo. Más lejos: el cliente tiene que consultar. Si Google no
responde, se estima con la línea recta por FACTOR_RUTA.
"""
import json
import logging
import math
import os
import urllib.request

logger = logging.getLogger(__name__)

FRANJA_GRATIS_KM = 5
LIMITE_KM = 60
# Nafta Súper YPF Córdoba, $ por litro. Se actualiza a mano, como el dólar.
NAFTA_ARS_LITRO = 2149
KM_POR_LITRO = 10
FACTOR_RUTA = 1.3
RECARGO_DESGASTE_TIEMPO = 1.0
NOMBRE_ENVIO = "Envío fuera de zona"

# Trazado aproximado de la Av. Circunvalación (lat, lng), en sentido horario
# desde el norte. Ajustar acá si algún barrio limítrofe queda mal clasificado.
CIRCUNVALACION = [
    (-31.3530, -64.1800),
    (-31.3600, -64.1450),
    (-31.3900, -64.1180),
    (-31.4200, -64.1120),
    (-31.4450, -64.1220),
    (-31.4680, -64.1500),
    (-31.4780, -64.1900),
    (-31.4620, -64.2350),
    (-31.4300, -64.2580),
    (-31.3950, -64.2550),
    (-31.3700, -64.2300),
    (-31.3550, -64.2050),
]

_KM_POR_GRADO_LAT = 111.32
_KM_POR_GRADO_LNG = _KM_POR_GRADO_LAT * math.cos(math.radians(-31.42))


def _a_km(lat, lng):
    return lng * _KM_POR_GRADO_LNG, lat * _KM_POR_GRADO_LAT


def _adentro(x, y, poligono):
    dentro = False
    for i, (x1, y1) in enumerate(poligono):
        x2, y2 = poligono[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            dentro = not dentro
    return dentro


def _distancia_segmento(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _punto_mas_cercano(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return ax + t * dx, ay + t * dy


def distancia_km(lat, lng):
    """Km en línea recta hasta la Circunvalación; 0 si el punto está adentro."""
    return _borde_mas_cercano(lat, lng)[0]


def _borde_mas_cercano(lat, lng):
    """(km en línea recta, (lat, lng) del punto de la Circunvalación más cercano)."""
    poligono = [_a_km(la, ln) for la, ln in CIRCUNVALACION]
    x, y = _a_km(lat, lng)
    if _adentro(x, y, poligono):
        return 0.0, None
    km, cx, cy = min(
        (_distancia_segmento(x, y, *poligono[i - 1], *poligono[i]),
         *_punto_mas_cercano(x, y, *poligono[i - 1], *poligono[i]))
        for i in range(len(poligono))
    )
    return km, (cy / _KM_POR_GRADO_LAT, cx / _KM_POR_GRADO_LNG)


# La cotización que ve el cliente y la que valida el pedido tienen que dar
# igual: se cachea por coordenadas redondeadas (~10 m).
_cache_ruta = {}


def km_por_ruta(origen, destino):
    """Km manejando de origen a destino según Google Routes, o None si falla."""
    clave_cache = (round(origen[0], 4), round(origen[1], 4), round(destino[0], 4), round(destino[1], 4))
    if clave_cache in _cache_ruta:
        return _cache_ruta[clave_cache]
    clave = (os.environ.get("GOOGLE_ROUTES_API_KEY") or os.environ.get("GOOGLE_MAPS_API_KEY") or "").strip()
    if not clave:
        return None
    punto = lambda c: {"location": {"latLng": {"latitude": c[0], "longitude": c[1]}}}
    pedido = urllib.request.Request(
        "https://routes.googleapis.com/directions/v2:computeRoutes",
        data=json.dumps({"origin": punto(origen), "destination": punto(destino), "travelMode": "DRIVE"}).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": clave,
            "X-Goog-FieldMask": "routes.distanceMeters",
        },
    )
    try:
        with urllib.request.urlopen(pedido, timeout=8) as r:
            km = json.load(r)["routes"][0]["distanceMeters"] / 1000
    except Exception:
        logger.exception("Google Routes no respondió; se estima el envío en línea recta")
        return None
    if len(_cache_ruta) > 5000:
        _cache_ruta.clear()
    _cache_ruta[clave_cache] = km
    return km


def cotizar(lat, lng, cotizacion_dolar):
    """Devuelve {zona, envio_usd, distancia_km, desglose}.

    zona: "sin_ubicacion" | "gratis" | "con_cargo" | "consultar".
    """
    if lat is None or lng is None:
        return {"zona": "sin_ubicacion", "envio_usd": 0, "distancia_km": None, "desglose": None}
    km_recta, borde = _borde_mas_cercano(lat, lng)
    if borde is None:
        return {"zona": "gratis", "envio_usd": 0, "distancia_km": 0.0, "desglose": None}
    km = km_por_ruta(borde, (lat, lng))
    estimado = km is None
    if estimado:
        km = km_recta * FACTOR_RUTA
    km = round(km, 1)
    if km <= FRANJA_GRATIS_KM:
        return {"zona": "gratis", "envio_usd": 0, "distancia_km": km, "desglose": None}
    if km > LIMITE_KM:
        return {"zona": "consultar", "envio_usd": 0, "distancia_km": km, "desglose": None}
    km_excedentes = round(km - FRANJA_GRATIS_KM, 1)
    km_recorridos = round(km_excedentes * 2, 1)
    litros = round(km_recorridos / KM_POR_LITRO, 2)
    combustible_usd = round(litros * NAFTA_ARS_LITRO / cotizacion_dolar, 2)
    desgaste_tiempo_usd = round(combustible_usd * RECARGO_DESGASTE_TIEMPO, 2)
    return {
        "zona": "con_cargo",
        "envio_usd": round(combustible_usd + desgaste_tiempo_usd, 2),
        "distancia_km": km,
        "desglose": {
            "km_gratis": FRANJA_GRATIS_KM,
            "km_excedentes": km_excedentes,
            "km_recorridos": km_recorridos,
            "estimado": estimado,
            "km_por_litro": KM_POR_LITRO,
            "litros": litros,
            "nafta_ars_litro": NAFTA_ARS_LITRO,
            "cotizacion_dolar": cotizacion_dolar,
            "combustible_usd": combustible_usd,
            "recargo_pct": round(RECARGO_DESGASTE_TIEMPO * 100),
            "desgaste_tiempo_usd": desgaste_tiempo_usd,
        },
    }
