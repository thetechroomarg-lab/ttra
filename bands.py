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
