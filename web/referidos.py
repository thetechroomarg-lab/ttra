import math
import secrets
import string
from datetime import datetime, timezone

from web import cupones

PREMIO_REFERIDO_USD = 5
# Bolsa de red (niveles de más arriba y compras repetidas): acumula sin
# límite, pero en cada compra se aplican como máximo US$15.
TOPE_RED_POR_COMPRA_USD = 15
# Premio de los 5 sellos (ver fidelidad.py; acá para no importar en círculo).
DESCUENTO_FIDELIDAD_USD = 20
MAX_NIVELES = 40
# Por debajo de esto la cadena ya no aporta nada medible.
MONTO_MINIMO_USD = 0.000001
# Sin 0/O ni 1/I: el código se puede dictar por WhatsApp sin confusiones.
_ALFABETO = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")


def _cliente(client, cliente_id):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    return filas[0] if filas else None


class MayoristaSinLinkError(Exception):
    """Las cuentas mayoristas no invitan: el link vuelve si pasa a minorista."""


def obtener_o_crear_codigo(client, cliente_id):
    cliente = _cliente(client, cliente_id)
    if not cliente:
        return None
    if cliente.get("tipo_cliente") == "mayorista":
        raise MayoristaSinLinkError()
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
    # El link de alguien que hoy es mayorista no vincula a nadie.
    if not filas or filas[0].get("tipo_cliente") == "mayorista":
        return None
    return filas[0]["id"]


def _generar_codigo_premio(client):
    for _ in range(12):
        codigo = "TTRA-REF-" + "".join(secrets.choice(_ALFABETO) for _ in range(6))
        if not client.table("codigos_descuento").select("*").eq("code", codigo).execute().data:
            return codigo
    raise RuntimeError("No se pudo generar un código de premio único")


def _centavos(monto):
    return math.floor(round(float(monto) * 100, 6)) / 100


def _desglose(cliente):
    """Lo que el cliente puede aplicar en su próxima compra, por bolsa."""
    fidelidad = DESCUENTO_FIDELIDAD_USD if cliente.get("fidelidad_ultimo_codigo") else 0
    directos = _centavos(cliente.get("saldo_directos_usd") or 0)
    red = _centavos(min(float(cliente.get("red_saldo_usd") or 0), TOPE_RED_POR_COMPRA_USD))
    return {"fidelidad": fidelidad, "directos": directos, "red": red,
            "total": round(fidelidad + directos + red, 2)}


def refrescar_cupon(client, cliente_id):
    """Deja un único cupón del cliente con todo lo que puede aplicar hoy:
    sellos + directos + hasta US$15 de la red. Si el cupón está reservado
    para un pedido en curso no se toca (ese pedido ya se calculó)."""
    cliente = _cliente(client, cliente_id)
    if not cliente or cliente.get("tipo_cliente") == "mayorista":
        return None
    codigo = cliente.get("referidos_codigo_premio") or cliente.get("fidelidad_ultimo_codigo")
    fila = cupones.fila_por_codigo(client, codigo) if codigo else None
    if fila and fila.get("usado_en"):
        fila, codigo = None, None
    if fila and cupones.reservado(client, fila):
        return codigo
    total = _desglose(cliente)["total"]
    if total <= 0:
        if fila:
            client.table("codigos_descuento").update({"activo": False}).eq("code", codigo).execute()
        client.table("clientes").update({"referidos_codigo_premio": None}).eq("id", cliente_id).execute()
        return None
    datos = {
        # descuento_usd es por unidad y entero: el tope (con centavos) es el
        # que limita el total del descuento.
        "descuento_usd": math.ceil(total),
        "tope_total_usd": total,
        "activo": True,
        "aplicado_usd": None,
    }
    if fila:
        client.table("codigos_descuento").update(datos).eq("code", codigo).execute()
    else:
        codigo = _generar_codigo_premio(client)
        client.table("codigos_descuento").insert({
            "cliente_id": cliente_id, "code": codigo, "productos": [], **datos,
        }).execute()
    cambios = {"referidos_codigo_premio": codigo}
    viejo_fidelidad = cliente.get("fidelidad_ultimo_codigo")
    if viejo_fidelidad and viejo_fidelidad != codigo:
        # El premio de sellos pasa a vivir en el cupón único.
        client.table("codigos_descuento").update({"activo": False}).eq("code", viejo_fidelidad).is_("usado_en", "null").execute()
        cambios["fidelidad_ultimo_codigo"] = codigo
    client.table("clientes").update(cambios).eq("id", cliente_id).execute()
    return codigo


def aplicar_consumo(client, fila):
    """Se llama cuando un cupón se consume (recibo enviado). Descuenta de cada
    bolsa lo que realmente se usó en la compra —primero sellos, después
    directos, después red— y lo que sobra queda para la próxima compra."""
    cliente = _cliente(client, fila.get("cliente_id"))
    codigo = fila.get("code")
    if not cliente or codigo not in (cliente.get("referidos_codigo_premio"), cliente.get("fidelidad_ultimo_codigo")):
        return None  # Código de mailing u otro: no toca los saldos.
    aplicado = fila.get("aplicado_usd")
    restante = float(aplicado if aplicado is not None else (fila.get("tope_total_usd") or 0))
    cambios = {"referidos_codigo_premio": None}
    directos = float(cliente.get("saldo_directos_usd") or 0)
    if cliente.get("fidelidad_ultimo_codigo") == codigo:
        usado = min(restante, DESCUENTO_FIDELIDAD_USD)
        restante -= usado
        # Si la compra no alcanzó a usar los US$20 enteros, el resto no se pierde.
        directos += DESCUENTO_FIDELIDAD_USD - usado
        cambios.update({"sellos_fidelidad": 0, "fidelidad_ultimo_codigo": None})
    usado = min(restante, directos)
    directos -= usado
    restante -= usado
    red = float(cliente.get("red_saldo_usd") or 0)
    red -= min(restante, red, TOPE_RED_POR_COMPRA_USD)
    cambios.update({"saldo_directos_usd": round(directos, 6), "red_saldo_usd": round(red, 6)})
    client.table("clientes").update(cambios).eq("id", cliente["id"]).execute()
    return refrescar_cupon(client, cliente["id"])


def monto_por_compra(nivel, compra_numero):
    """US$5 para el padrino por la primera compra; la mitad por cada nivel
    hacia arriba y la mitad por cada compra repetida de la misma persona."""
    return PREMIO_REFERIDO_USD / (2 ** (nivel - 1)) / (2 ** (compra_numero - 1))


def _acreditar(client, beneficiario, monto, directo):
    campo = "saldo_directos_usd" if directo else "red_saldo_usd"
    client.table("clientes").update({
        campo: round(float(beneficiario.get(campo) or 0) + monto, 6),
    }).eq("id", beneficiario["id"]).execute()
    refrescar_cupon(client, beneficiario["id"])


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
            acreditado = monto
            _acreditar(client, beneficiario, monto, directo)
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


def _cupon_sin_usar(client, codigo):
    fila = cupones.fila_por_codigo(client, codigo)
    return fila is not None and not fila.get("usado_en")


def reiniciar_beneficios(client, cliente_id):
    """Al cambiar entre minorista y mayorista el cliente arranca de cero:
    pierde sellos, premios y saldos sin usar, y "Mi red" solo cuenta lo que
    gane desde ahora. Un descuento ya reservado en un pedido en curso se
    respeta (ese precio ya se le pasó al cliente)."""
    codigos = (
        client.table("codigos_descuento").select("*")
        .eq("cliente_id", cliente_id).is_("usado_en", "null").execute().data
    ) or []
    for fila in codigos:
        if not cupones.reservado(client, fila):
            client.table("codigos_descuento").update({"activo": False}).eq("code", fila["code"]).execute()
    client.table("clientes").update({
        "sellos_fidelidad": 0,
        "fidelidad_ultimo_codigo": None,
        "referidos_codigo_premio": None,
        "saldo_directos_usd": 0,
        "red_saldo_usd": 0,
        "beneficios_desde": datetime.now(timezone.utc).isoformat(),
    }).eq("id", cliente_id).execute()


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
    desde = cliente.get("beneficios_desde")
    if desde:
        ganancias = [g for g in ganancias if (g.get("creado_en") or "") >= desde]
    ganancias.sort(key=lambda g: g.get("creado_en") or "", reverse=True)
    return {
        "codigo_premio": codigo_premio,
        "saldo_usd": round(saldo, 2),
        "red_saldo_usd": round(float(cliente.get("red_saldo_usd") or 0), 2),
        "red_tope_por_compra_usd": TOPE_RED_POR_COMPRA_USD,
        "desglose": _desglose(cliente),
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
