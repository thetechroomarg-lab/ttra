import math

# (limite_superior_inclusive, monto). La última banda es abierta (float('inf')).
_BANDAS = [
    (300, 30),
    (600, 40),
    (900, 50),
    (1300, 70),
    (1600, 85),
    (2000, 130),
    (2400, 160),
    (float("inf"), 200),
]


def monto_por_banda(costo):
    for limite, monto in _BANDAS:
        if costo <= limite:
            return monto
    return _BANDAS[-1][1]


def calcular_precio(costo):
    total = round(costo + monto_por_banda(costo), 2)
    return int(math.ceil(total / 5) * 5)


# Escala de margen para celulares Android (Apple sigue con las bandas normales de
# arriba). Ganancia limpia = margen - $15 (costo de entrega): nunca menos de $25
# limpios, nunca más de $60 limpios en los Android más caros.
_BANDAS_ANDROID = [
    (150, 40),
    (300, 45),
    (450, 50),
    (600, 55),
    (800, 60),
    (1000, 65),
    (1300, 70),
    (float("inf"), 75),
]


def _monto_por_banda_android(costo):
    for limite, monto in _BANDAS_ANDROID:
        if costo <= limite:
            return monto
    return _BANDAS_ANDROID[-1][1]


# Escala de margen para iPhone (nuevo y usado). Ganancia limpia = margen - $20 (costo
# de entrega): nunca menos de $30 limpios, nunca más de $60 limpios en los tope de gama.
_BANDAS_IPHONE = [
    (300, 50),
    (600, 55),
    (900, 60),
    (1200, 65),
    (1500, 70),
    (1800, 75),
    (float("inf"), 80),
]


def _monto_por_banda_iphone(costo):
    for limite, monto in _BANDAS_IPHONE:
        if costo <= limite:
            return monto
    return _BANDAS_IPHONE[-1][1]


def calcular_precio_celular(costo, es_android, es_iphone=False):
    if es_android:
        margen = _monto_por_banda_android(costo)
    elif es_iphone:
        margen = _monto_por_banda_iphone(costo)
    else:
        margen = monto_por_banda(costo)
    total = round(costo + margen, 2)
    return int(math.ceil(total / 5) * 5)
