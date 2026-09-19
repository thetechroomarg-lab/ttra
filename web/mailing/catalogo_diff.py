"""Detecta productos nuevos comparando el catálogo actual contra el último
snapshot usado en una corrida anterior del cron de mailing, y arma la
selección final de la campaña: siempre exactamente `cantidad` productos."""
import random


def detectar_nuevos(productos_actuales, snapshot_anterior):
    nombres_anteriores = {p.get("nombre") for p in snapshot_anterior}
    return [p for p in productos_actuales if p.get("nombre") not in nombres_anteriores]


def seleccionar_para_campania(nuevos, catalogo_completo, cantidad=10):
    """La campaña siempre muestra `cantidad` productos, sin excepción:
    - Si hay `cantidad` o más nuevos, se eligen `cantidad` al azar entre los nuevos.
    - Si hay menos, se completa al azar con el resto del catálogo (no nuevos)
      hasta llegar a `cantidad`, o hasta agotar el catálogo si no alcanza."""
    if len(nuevos) >= cantidad:
        return random.sample(nuevos, cantidad)

    nombres_nuevos = {p.get("nombre") for p in nuevos}
    resto = [p for p in catalogo_completo if p.get("nombre") not in nombres_nuevos]
    faltan = cantidad - len(nuevos)
    relleno = random.sample(resto, min(faltan, len(resto)))
    return nuevos + relleno
