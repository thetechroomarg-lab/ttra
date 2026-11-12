import math

# Piso global: margen 40 (ganancia limpia >= $25 con $15 de entrega).
# (limite_superior_inclusive, monto). La última banda es abierta (float('inf')).
_BANDAS = [
    (300, 40),
    (600, 40),
    (900, 40),
    (1300, 60),
    (1600, 75),
    (2000, 120),
    (2400, 150),
    (float("inf"), 190),
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
# arriba). Ganancia limpia = margen - $15 (costo de entrega): piso de $25 limpios
# (margen 40), nunca más de $50 limpios en los Android más caros.
_BANDAS_ANDROID = [
    (150, 40),
    (300, 40),
    (450, 40),
    (600, 45),
    (800, 50),
    (1000, 55),
    (1300, 60),
    (float("inf"), 65),
]


def _monto_por_banda_android(costo):
    for limite, monto in _BANDAS_ANDROID:
        if costo <= limite:
            return monto
    return _BANDAS_ANDROID[-1][1]


# Escala de margen para iPhone (nuevo y usado). Ganancia limpia = margen - $20 (costo
# de entrega): piso de $25 limpios (margen 45), nunca más de $50 limpios en los tope de gama.
_BANDAS_IPHONE = [
    (300, 45),
    (600, 45),
    (900, 50),
    (1200, 55),
    (1500, 60),
    (1800, 65),
    (float("inf"), 70),
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
