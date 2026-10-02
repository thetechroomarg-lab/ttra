import secrets
import string
from datetime import datetime, timezone

from web import cupones

PREMIO_REFERIDO_USD = 5
# Sin 0/O ni 1/I: el código se puede dictar por WhatsApp sin confusiones.
_ALFABETO = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")


def _cliente(client, cliente_id):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    return filas[0] if filas else None


def obtener_o_crear_codigo(client, cliente_id):
    cliente = _cliente(client, cliente_id)
    if not cliente:
        return None
    if cliente.get("codigo_referido"):
        return cliente["codigo_referido"]
    for _ in range(12):
        codigo = "".join(secrets.choice(_ALFABETO) for _ in range(7))
        if client.table("clientes").select("id").eq("codigo_referido", codigo).execute().data:
            continue
        # Condicional: si dos pestañas lo piden a la vez, gana la primera.
        ganado = (
            client.table("clientes").update({"codigo_referido": codigo})
            .eq("id", cliente_id).is_("codigo_referido", "null")
            .execute().data
        )
        if ganado:
            return codigo
        return (_cliente(client, cliente_id) or {}).get("codigo_referido")
    raise RuntimeError("No se pudo generar un código de referido único")


def resolver_referente(client, codigo):
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return None
    filas = client.table("clientes").select("*").eq("codigo_referido", codigo).execute().data
    return filas[0]["id"] if filas else None


def _generar_codigo_premio(client):
    for _ in range(12):
        codigo = "TTRA-REF-" + "".join(secrets.choice(_ALFABETO) for _ in range(6))
        if not client.table("codigos_descuento").select("*").eq("code", codigo).execute().data:
            return codigo
    raise RuntimeError("No se pudo generar un código de premio único")


def sumar_a_cupon(client, codigo, monto):
    """Suma `monto` a un cupón con tope todavía sin usar. Devuelve el saldo
    nuevo, o None si el cupón no existe o ya se usó."""
    if not codigo:
        return None
    filas = (
        client.table("codigos_descuento").select("*")
        .eq("code", codigo).is_("usado_en", "null").execute().data
    )
    # Reservado para un pedido en curso: ese pedido ya se calculó con el monto
    # anterior, así que el premio nuevo va a un cupón aparte.
    if not filas or cupones.reservado(client, filas[0]):
        return None
    nuevo = int(filas[0].get("descuento_usd") or 0) + monto
    # Si justo se consumió en un pedido, el update no matchea y quien llama
    # emite un cupón nuevo: el premio nunca se pierde.
    actualizado = (
        client.table("codigos_descuento")
        .update({"descuento_usd": nuevo, "tope_total_usd": nuevo})
        .eq("code", codigo).is_("usado_en", "null")
        .execute().data
    )
    return nuevo if actualizado else None


def _sumar_premio(client, referente_id):
    """Suma US$5 al premio pendiente del referente (de referidos o de
    fidelidad: los dos van en un solo cupón), o emite uno nuevo."""
    referente = _cliente(client, referente_id)
    if not referente:
        return None
    # Solo entra un código por compra: si ya hay un premio sin usar, se suma ahí.
    for codigo_actual in (referente.get("referidos_codigo_premio"), referente.get("fidelidad_ultimo_codigo")):
        saldo = sumar_a_cupon(client, codigo_actual, PREMIO_REFERIDO_USD)
        if saldo is not None:
            client.table("clientes").update({"referidos_codigo_premio": codigo_actual}).eq("id", referente_id).execute()
            return {"codigo": codigo_actual, "saldo_usd": saldo}
    codigo = _generar_codigo_premio(client)
    client.table("codigos_descuento").insert({
        "cliente_id": referente_id,
        "code": codigo,
        # Sin productos + tope: vale para cualquier producto, en total.
        "productos": [],
        "descuento_usd": PREMIO_REFERIDO_USD,
        "tope_total_usd": PREMIO_REFERIDO_USD,
        "activo": True,
    }).execute()
    client.table("clientes").update({"referidos_codigo_premio": codigo}).eq("id", referente_id).execute()
    return {"codigo": codigo, "saldo_usd": PREMIO_REFERIDO_USD}


def acreditar_por_compra(client, cliente_id):
    """Se llama al enviar el primer recibo de un pedido del cliente.

    Si el cliente vino referido y todavía no generó premio, el referente
    recibe US$5. Solo la primera compra del referido cuenta.
    """
    cliente = _cliente(client, cliente_id)
    if not cliente or not cliente.get("referido_por") or cliente.get("referido_premiado_en"):
        return None
    # Marca condicional: dos recibos simultáneos no pagan dos premios.
    ganado = (
        client.table("clientes").update({"referido_premiado_en": datetime.now(timezone.utc).isoformat()})
        .eq("id", cliente_id).is_("referido_premiado_en", "null")
        .execute().data
    )
    if not ganado:
        return None
    referente = _cliente(client, cliente["referido_por"])
    # Los códigos solo aplican a precio minorista.
    if not referente or referente.get("tipo_cliente") == "mayorista":
        return None
    premio = _sumar_premio(client, referente["id"])
    if premio:
        client.table("clientes").update({"referido_premio_codigo": premio["codigo"]}).eq("id", cliente_id).execute()
    return premio


def marcar_premio_usado(client, cliente_id, codigo):
    cliente = _cliente(client, cliente_id)
    if not cliente or not codigo or cliente.get("referidos_codigo_premio") != codigo:
        return False
    client.table("clientes").update({"referidos_codigo_premio": None}).eq("id", cliente_id).execute()
    return True


def _cupon_sin_usar(client, codigo):
    fila = cupones.fila_por_codigo(client, codigo)
    return fila is not None and not fila.get("usado_en")


def resumen(client, cliente_id):
    cliente = _cliente(client, cliente_id) or {}
    saldo = 0
    codigo_premio = cliente.get("referidos_codigo_premio")
    if codigo_premio:
        filas = (
            client.table("codigos_descuento").select("*")
            .eq("code", codigo_premio).is_("usado_en", "null").execute().data
        )
        if filas:
            saldo = int(filas[0].get("descuento_usd") or 0)
        else:
            codigo_premio = None
    referidos = client.table("clientes").select("*").eq("referido_por", cliente_id).execute().data or []
    pendientes = [
        {
            "nombre": f"{(r.get('nombre') or '').strip()} {(r.get('apellido') or '').strip()[:1]}.".strip(),
            "acreditado_en": r.get("referido_premiado_en"),
            "monto_usd": PREMIO_REFERIDO_USD,
        }
        for r in referidos
        if codigo_premio and r.get("referido_premio_codigo") == codigo_premio
    ]
    # Historial completo: todos los amigos que compraron, con o sin el
    # descuento ya usado.
    amigos_con_compra = sorted(
        (
            {
                "nombre": f"{(r.get('nombre') or '').strip()} {(r.get('apellido') or '').strip()[:1]}.".strip(),
                "compro_en": r.get("referido_premiado_en"),
                "descuento_pendiente": _cupon_sin_usar(client, r.get("referido_premio_codigo")),
            }
            for r in referidos if r.get("referido_premiado_en")
        ),
        key=lambda a: a["compro_en"] or "",
        reverse=True,
    )
    return {
        "codigo_premio": codigo_premio,
        "pendientes": pendientes,
        "amigos_con_compra": amigos_con_compra,
        "saldo_usd": saldo,
        "referidos_registrados": len(referidos),
        "referidos_con_compra": sum(1 for r in referidos if r.get("referido_premiado_en")),
    }
