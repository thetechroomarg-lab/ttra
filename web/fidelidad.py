import secrets
import string

DESCUENTO_FIDELIDAD_USD = 20
SELLOS_PARA_PREMIO = 5


def _generar_codigo_fidelidad(client):
    alfabeto = string.ascii_uppercase + string.digits
    for _ in range(12):
        codigo = "TTRA-" + "".join(secrets.choice(alfabeto) for _ in range(8))
        existe = client.table("codigos_descuento").select("*").eq("code", codigo).execute().data
        if not existe:
            return codigo
    raise RuntimeError("No se pudo generar un código de fidelidad único")


def registrar_entrega_completada(client, cliente_id, nombres_catalogo):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        return None
    cliente = filas[0]
    # Con un premio pendiente sin usar, el contador queda congelado en 5.
    if cliente.get("fidelidad_ultimo_codigo"):
        return None

    sellos = int(cliente.get("sellos_fidelidad") or 0) + 1
    actualizacion = {"sellos_fidelidad": sellos}
    codigo_emitido = None
    if sellos >= SELLOS_PARA_PREMIO:
        codigo_emitido = _generar_codigo_fidelidad(client)
        client.table("codigos_descuento").insert({
            "cliente_id": cliente_id,
            "code": codigo_emitido,
            "productos": list(nombres_catalogo),
            "descuento_usd": DESCUENTO_FIDELIDAD_USD,
            "activo": True,
        }).execute()
        actualizacion["fidelidad_ultimo_codigo"] = codigo_emitido

    client.table("clientes").update(actualizacion).eq("id", cliente_id).execute()
    return {"sellos_fidelidad": sellos, "codigo_emitido": codigo_emitido}


def marcar_codigo_fidelidad_usado(client, cliente_id, codigo):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas or not codigo or filas[0].get("fidelidad_ultimo_codigo") != codigo:
        return False
    client.table("clientes").update({
        "sellos_fidelidad": 0, "fidelidad_ultimo_codigo": None,
    }).eq("id", cliente_id).execute()
    return True
