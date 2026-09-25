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


def registrar_entrega_completada(client, cliente_id):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        return None
    cliente = filas[0]
    # Los códigos de descuento solo aplican a precio minorista: un mayorista
    # juntaría un premio que nunca podría usar.
    if cliente.get("tipo_cliente") == "mayorista":
        return None
    # Con un premio pendiente sin usar, el contador queda congelado en 5.
    if cliente.get("fidelidad_ultimo_codigo"):
        return None

    previo = int(cliente.get("sellos_fidelidad") or 0)
    sellos = previo + 1
    codigo_emitido = _generar_codigo_fidelidad(client) if sellos >= SELLOS_PARA_PREMIO else None
    actualizacion = {"sellos_fidelidad": sellos}
    if codigo_emitido:
        actualizacion["fidelidad_ultimo_codigo"] = codigo_emitido

    # Update condicional: si otro envío de recibo cambió el contador entre la
    # lectura y acá, no se pisa su sello ni se emite un segundo código.
    ganado = (
        client.table("clientes").update(actualizacion)
        .eq("id", cliente_id)
        .eq("sellos_fidelidad", previo)
        .is_("fidelidad_ultimo_codigo", "null")
        .execute().data
    )
    if not ganado:
        return None

    if codigo_emitido:
        try:
            client.table("codigos_descuento").insert({
                "cliente_id": cliente_id,
                "code": codigo_emitido,
                # Sin lista de productos + tope: vale para cualquier producto,
                # también los que entren al catálogo después, US$20 en total.
                "productos": [],
                "descuento_usd": DESCUENTO_FIDELIDAD_USD,
                "tope_total_usd": DESCUENTO_FIDELIDAD_USD,
                "activo": True,
            }).execute()
        except Exception:
            client.table("clientes").update({
                "sellos_fidelidad": previo, "fidelidad_ultimo_codigo": None,
            }).eq("id", cliente_id).execute()
            raise
    return {"sellos_fidelidad": sellos, "codigo_emitido": codigo_emitido}


def marcar_codigo_fidelidad_usado(client, cliente_id, codigo):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas or not codigo or filas[0].get("fidelidad_ultimo_codigo") != codigo:
        return False
    client.table("clientes").update({
        "sellos_fidelidad": 0, "fidelidad_ultimo_codigo": None,
    }).eq("id", cliente_id).execute()
    return True
