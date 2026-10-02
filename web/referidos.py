import math
import secrets
import string
from datetime import datetime, timezone

from web import cupones

PREMIO_REFERIDO_USD = 5
# Bolsa de red (niveles de más arriba y compras repetidas): tope de saldo.
TOPE_RED_USD = 15
MAX_NIVELES = 40
# Por debajo de esto la cadena ya no aporta nada medible.
MONTO_MINIMO_USD = 0.000001
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


def sumar_a_cupon(client, codigo, monto, red_usd=0):
    """Suma `monto` a un cupón con tope todavía sin usar. Devuelve el saldo
    nuevo, o None si el cupón no existe, ya se usó o está reservado.

    `red_usd` es la parte del monto que viene de la red (bolsa con tope de
    US$15): se guarda en el cupón para descontarla del saldo de red cuando
    el cupón se consume.
    """
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
    fila = filas[0]
    tope_actual = float(fila.get("tope_total_usd") or fila.get("descuento_usd") or 0)
    nuevo = round(tope_actual + monto, 2)
    # Si justo se consumió en un pedido, el update no matchea y quien llama
    # emite un cupón nuevo: el premio nunca se pierde.
    actualizado = (
        client.table("codigos_descuento")
        .update({
            # descuento_usd es por unidad y entero: el tope (con centavos) es
            # el que limita el total.
            "descuento_usd": math.ceil(nuevo),
            "tope_total_usd": nuevo,
            "red_usd": round(float(fila.get("red_usd") or 0) + red_usd, 2),
        })
        .eq("code", codigo).is_("usado_en", "null")
        .execute().data
    )
    return nuevo if actualizado else None


def _sumar_premio(client, beneficiario_id, monto, red_usd=0):
    """Suma el premio al cupón pendiente del cliente (referidos y fidelidad
    van en un solo cupón: entra un código por compra), o emite uno nuevo."""
    beneficiario = _cliente(client, beneficiario_id)
    if not beneficiario:
        return None
    for codigo_actual in (beneficiario.get("referidos_codigo_premio"), beneficiario.get("fidelidad_ultimo_codigo")):
        saldo = sumar_a_cupon(client, codigo_actual, monto, red_usd)
        if saldo is not None:
            client.table("clientes").update({"referidos_codigo_premio": codigo_actual}).eq("id", beneficiario_id).execute()
            return {"codigo": codigo_actual, "saldo_usd": saldo}
    codigo = _generar_codigo_premio(client)
    monto = round(monto, 2)
    client.table("codigos_descuento").insert({
        "cliente_id": beneficiario_id,
        "code": codigo,
        # Sin productos + tope: vale para cualquier producto, en total.
        "productos": [],
        "descuento_usd": math.ceil(monto),
        "tope_total_usd": monto,
        "red_usd": round(red_usd, 2),
        "activo": True,
    }).execute()
    client.table("clientes").update({"referidos_codigo_premio": codigo}).eq("id", beneficiario_id).execute()
    return {"codigo": codigo, "saldo_usd": monto}


def monto_por_compra(nivel, compra_numero):
    """US$5 para el padrino por la primera compra; la mitad por cada nivel
    hacia arriba y la mitad por cada compra repetida de la misma persona."""
    return PREMIO_REFERIDO_USD / (2 ** (nivel - 1)) / (2 ** (compra_numero - 1))


def _acreditar_red(client, beneficiario, monto):
    """Bolsa de red: nunca acumula más de US$15 sin usar. Las fracciones de
    centavo se guardan y pasan al cupón cuando completan un centavo.
    Devuelve (acreditado_exacto, centavos_al_cupon)."""
    saldo = float(beneficiario.get("red_saldo_usd") or 0)
    acreditado = max(0.0, min(monto, TOPE_RED_USD - saldo))
    if acreditado <= 0:
        return 0.0, 0.0
    fraccion = float(beneficiario.get("red_fraccion_usd") or 0) + acreditado
    centavos = math.floor(round(fraccion * 100, 6)) / 100
    client.table("clientes").update({
        "red_saldo_usd": round(saldo + acreditado, 6),
        "red_fraccion_usd": round(fraccion - centavos, 6),
    }).eq("id", beneficiario["id"]).execute()
    return acreditado, centavos


def _compras_concretadas(client, cliente_id):
    filas = client.table("pedidos").select("*").eq("cliente_id", cliente_id).execute().data or []
    return sum(1 for p in filas if p.get("recibo_enviado_en") and not p.get("borrado_en"))


def acreditar_por_compra(client, cliente_id, pedido_id=None):
    """Se llama al enviar el primer recibo de un pedido del cliente.

    Recorre la cadena de padrinos hacia arriba y le acredita a cada uno su
    parte (ver monto_por_compra). La primera compra al padrino directo va a
    la bolsa de directos (sin tope); todo lo demás va a la bolsa de red.
    """
    cliente = _cliente(client, cliente_id)
    if not cliente or not cliente.get("referido_por"):
        return []
    compra_numero = max(1, _compras_concretadas(client, cliente_id))
    if not cliente.get("referido_premiado_en"):
        client.table("clientes").update({"referido_premiado_en": datetime.now(timezone.utc).isoformat()}).eq("id", cliente_id).execute()
    acreditados = []
    visitados = {cliente_id}
    actual, nivel = cliente, 1
    while actual.get("referido_por") and nivel <= MAX_NIVELES:
        beneficiario = _cliente(client, actual["referido_por"])
        if not beneficiario or beneficiario["id"] in visitados:
            break
        visitados.add(beneficiario["id"])
        monto = monto_por_compra(nivel, compra_numero)
        if monto < MONTO_MINIMO_USD:
            break
        # Idempotente: un mismo pedido no paga dos veces al mismo padrino.
        ya = pedido_id and (
            client.table("referidos_ganancias").select("*")
            .eq("beneficiario_id", beneficiario["id"]).eq("pedido_id", pedido_id).execute().data
        )
        # Los códigos solo aplican a precio minorista.
        if not ya and beneficiario.get("tipo_cliente") != "mayorista":
            directo = nivel == 1 and compra_numero == 1
            if directo:
                acreditado, al_cupon = monto, monto
                premio = _sumar_premio(client, beneficiario["id"], monto)
                if premio:
                    client.table("clientes").update({"referido_premio_codigo": premio["codigo"]}).eq("id", cliente_id).execute()
            else:
                acreditado, al_cupon = _acreditar_red(client, beneficiario, monto)
                if al_cupon > 0:
                    _sumar_premio(client, beneficiario["id"], al_cupon, red_usd=al_cupon)
            client.table("referidos_ganancias").insert({
                "beneficiario_id": beneficiario["id"],
                "origen_cliente_id": cliente_id,
                "pedido_id": pedido_id,
                "nivel": nivel,
                "compra_numero": compra_numero,
                "monto_usd": round(monto, 6),
                "acreditado_usd": round(acreditado, 6),
                "bolsa": "directo" if directo else "red",
            }).execute()
            acreditados.append({"beneficiario_id": beneficiario["id"], "nivel": nivel, "acreditado_usd": round(acreditado, 6)})
        actual, nivel = beneficiario, nivel + 1
    return acreditados


def marcar_premio_usado(client, cliente_id, codigo):
    """Se llama cuando el cupón se consume (recibo enviado)."""
    cliente = _cliente(client, cliente_id)
    if not cliente or not codigo:
        return False
    fila = cupones.fila_por_codigo(client, codigo) or {}
    red_usd = float(fila.get("red_usd") or 0)
    cambios = {}
    if red_usd > 0:
        # La bolsa de red vuelve a juntar desde lo que no se gastó.
        cambios["red_saldo_usd"] = round(max(0.0, float(cliente.get("red_saldo_usd") or 0) - red_usd), 6)
    if cliente.get("referidos_codigo_premio") == codigo:
        cambios["referidos_codigo_premio"] = None
    if cambios:
        client.table("clientes").update(cambios).eq("id", cliente_id).execute()
    return "referidos_codigo_premio" in cambios


def _cupon_sin_usar(client, codigo):
    fila = cupones.fila_por_codigo(client, codigo)
    return fila is not None and not fila.get("usado_en")


def _nombre_corto(cliente):
    return f"{(cliente.get('nombre') or '').strip()} {(cliente.get('apellido') or '').strip()[:1]}.".strip()


def _arbol(client, cliente_id, ganancias):
    """Árbol de la red: solo quienes compraron y le generaron una ganancia al
    cliente. Si alguien del medio no compró, su rama cuelga del ancestro más
    cercano que sí aparece. Solo nombre e inicial: ni contacto ni compras."""
    origenes = {g["origen_cliente_id"] for g in ganancias if g.get("origen_cliente_id")}
    clientes = {}
    for origen in origenes:
        fila = _cliente(client, origen)
        if fila:
            clientes[origen] = fila

    def padre_visible(fila):
        visto = set()
        actual = fila
        while actual.get("referido_por") and actual["referido_por"] not in visto:
            visto.add(actual["referido_por"])
            if actual["referido_por"] == cliente_id or actual["referido_por"] in clientes:
                return actual["referido_por"]
            actual = _cliente(client, actual["referido_por"]) or {}
        return cliente_id

    hijos = {}
    for origen, fila in clientes.items():
        hijos.setdefault(padre_visible(fila), []).append(origen)

    def nodo(origen, profundidad=0):
        if profundidad > MAX_NIVELES:
            return None
        return {
            "nombre": _nombre_corto(clientes[origen]),
            "hijos": [n for n in (nodo(h, profundidad + 1) for h in sorted(hijos.get(origen, []), key=lambda h: _nombre_corto(clientes[h]))) if n],
        }

    return [n for n in (nodo(h) for h in sorted(hijos.get(cliente_id, []), key=lambda h: _nombre_corto(clientes[h]))) if n]


def resumen(client, cliente_id):
    cliente = _cliente(client, cliente_id) or {}
    saldo = 0.0
    codigo_premio = cliente.get("referidos_codigo_premio")
    if codigo_premio:
        fila = cupones.fila_por_codigo(client, codigo_premio)
        if fila and not fila.get("usado_en"):
            saldo = float(fila.get("tope_total_usd") or fila.get("descuento_usd") or 0)
        else:
            codigo_premio = None
    referidos = client.table("clientes").select("*").eq("referido_por", cliente_id).execute().data or []
    ganancias = client.table("referidos_ganancias").select("*").eq("beneficiario_id", cliente_id).execute().data or []
    ganancias.sort(key=lambda g: g.get("creado_en") or "", reverse=True)
    return {
        "codigo_premio": codigo_premio,
        "saldo_usd": round(saldo, 2),
        "red_saldo_usd": round(float(cliente.get("red_saldo_usd") or 0), 2),
        "red_tope_usd": TOPE_RED_USD,
        "ganado_total_usd": round(sum(float(g.get("acreditado_usd") or 0) for g in ganancias), 2),
        # Montos y fechas, sin decir quién los generó ni qué compró.
        "ultimas_ganancias": [
            {"monto_usd": round(float(g.get("acreditado_usd") or 0), 4), "fecha": g.get("creado_en"), "nivel": g.get("nivel")}
            for g in ganancias[:10] if float(g.get("acreditado_usd") or 0) > 0
        ],
        "arbol": _arbol(client, cliente_id, ganancias),
        "personas_en_red": len({g.get("origen_cliente_id") for g in ganancias if g.get("origen_cliente_id")}),
        "referidos_registrados": len(referidos),
        "referidos_con_compra": sum(1 for r in referidos if r.get("referido_premiado_en")),
    }
