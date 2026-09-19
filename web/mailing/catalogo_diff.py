"""Detecta productos nuevos comparando el catálogo actual contra el último
snapshot usado en una corrida anterior del cron de mailing."""


def detectar_nuevos(productos_actuales, snapshot_anterior):
    nombres_anteriores = {p.get("nombre") for p in snapshot_anterior}
    return [p for p in productos_actuales if p.get("nombre") not in nombres_anteriores]
