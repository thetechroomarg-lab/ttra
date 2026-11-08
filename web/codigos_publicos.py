"""Códigos de descuento públicos (sin cliente) de un solo uso, reactivables.

El mismo código (p. ej. GRACIASBOBIS) se puede volver a activar cuantas veces
haga falta: si el anterior ya se usó o está reservado por un pedido en curso,
se archiva renombrándolo con la fecha (queda el historial de quién lo ganó) y
se crea uno nuevo con el nombre original.
"""
from datetime import datetime, timezone

from web import cupones


def _tomado(client, fila):
    return bool(fila.get("usado_en")) or cupones.reservado(client, fila)


def activar(client, codigo, monto_usd, ahora=None):
    codigo = (codigo or "").strip().upper()
    monto_usd = int(monto_usd)
    if not codigo or monto_usd <= 0:
        raise ValueError("Hace falta un código y un monto mayor a cero")
    ahora = ahora or datetime.now(timezone.utc)
    nueva = {
        "cliente_id": None, "code": codigo, "productos": [],
        "descuento_usd": monto_usd, "tope_total_usd": monto_usd, "activo": True,
        "usado_en": None, "reservado_pedido_id": None, "reservado_en": None, "aplicado_usd": None,
    }
    filas = client.table("codigos_descuento").select("*").eq("code", codigo).execute().data
    if not filas:
        client.table("codigos_descuento").insert(nueva).execute()
        return {"codigo": codigo, "monto_usd": monto_usd, "archivado": None}
    fila = filas[0]
    if fila.get("cliente_id"):
        raise ValueError(f"{codigo} ya existe como código privado de un cliente")
    archivado = None
    if _tomado(client, fila):
        archivado = f"{codigo}-{ahora.strftime('%Y%m%d-%H%M%S')}"
        client.table("codigos_descuento").update({"code": archivado}).eq("code", codigo).execute()
        client.table("codigos_descuento").insert(nueva).execute()
    else:
        # Nunca usado (o su pedido se borró): se reutiliza la misma fila.
        client.table("codigos_descuento").update(
            {k: v for k, v in nueva.items() if k != "code"}
        ).eq("code", codigo).execute()
    return {"codigo": codigo, "monto_usd": monto_usd, "archivado": archivado}


def estado(client, codigo):
    codigo = (codigo or "").strip().upper()
    filas = client.table("codigos_descuento").select("*").eq("code", codigo).execute().data
    if not filas:
        return {"codigo": codigo, "estado": "no existe"}
    fila = filas[0]
    if fila.get("usado_en"):
        est = "usado"
    elif cupones.reservado(client, fila):
        est = "reservado"
    elif fila.get("activo"):
        est = "disponible"
    else:
        est = "inactivo"
    return {"codigo": codigo, "estado": est, "monto_usd": fila.get("tope_total_usd"),
            "pedido_id": fila.get("reservado_pedido_id")}
