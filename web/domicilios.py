import uuid

MAX_DOMICILIOS = 5
MAX_PISO_DEPTO = 20


def opcional(valor):
    """Piso/depto son opcionales: vacío pasa a None, y se recorta a un largo sano."""
    valor = (valor or "").strip()[:MAX_PISO_DEPTO]
    return valor or None


def _normalizar(fila):
    return {
        "id": fila["id"],
        "alias": fila.get("alias") or "",
        "direccion": fila.get("direccion") or "",
        "piso": fila.get("piso") or "",
        "depto": fila.get("depto") or "",
        "predeterminado": bool(fila.get("predeterminado")),
        "lat": fila.get("lat"),
        "lng": fila.get("lng"),
    }


def listar(client, cliente_id):
    filas = client.table("domicilios_cliente").select("*").eq("cliente_id", cliente_id).execute().data
    filas.sort(key=lambda f: (not f.get("predeterminado"), f.get("creado_en") or ""))
    return [_normalizar(f) for f in filas]


def _desmarcar_predeterminados(client, cliente_id):
    actuales = (
        client.table("domicilios_cliente").select("*")
        .eq("cliente_id", cliente_id).eq("predeterminado", True).execute().data
    )
    for fila in actuales:
        client.table("domicilios_cliente").update({"predeterminado": False}).eq("id", fila["id"]).execute()


def _obtener_propio(client, cliente_id, domicilio_id):
    filas = (
        client.table("domicilios_cliente").select("*")
        .eq("id", domicilio_id).eq("cliente_id", cliente_id).execute().data
    )
    if not filas:
        raise ValueError("No existe ese domicilio")
    return filas[0]


def crear(client, cliente_id, alias, direccion, lat=None, lng=None, predeterminado=False, piso=None, depto=None):
    alias = (alias or "").strip()
    direccion = (direccion or "").strip()
    if not alias:
        raise ValueError("Ingresá un nombre para el domicilio")
    if not direccion:
        raise ValueError("Ingresá una dirección")
    existentes = client.table("domicilios_cliente").select("*").eq("cliente_id", cliente_id).execute().data
    if len(existentes) >= MAX_DOMICILIOS:
        raise ValueError(f"Ya tenés el máximo de {MAX_DOMICILIOS} domicilios guardados")
    hacer_predeterminado = predeterminado or not existentes
    if hacer_predeterminado:
        _desmarcar_predeterminados(client, cliente_id)
    fila = {
        "id": str(uuid.uuid4()),
        "cliente_id": cliente_id,
        "alias": alias,
        "direccion": direccion,
        "piso": opcional(piso),
        "depto": opcional(depto),
        "predeterminado": hacer_predeterminado,
        "lat": lat,
        "lng": lng,
    }
    client.table("domicilios_cliente").insert(fila).execute()
    return _normalizar(fila)


def actualizar(client, cliente_id, domicilio_id, alias, direccion, lat=None, lng=None, piso=None, depto=None):
    fila = _obtener_propio(client, cliente_id, domicilio_id)
    alias = (alias or "").strip()
    direccion = (direccion or "").strip()
    if not alias:
        raise ValueError("Ingresá un nombre para el domicilio")
    if not direccion:
        raise ValueError("Ingresá una dirección")
    cambios = {"alias": alias, "direccion": direccion, "lat": lat, "lng": lng, "piso": opcional(piso), "depto": opcional(depto)}
    client.table("domicilios_cliente").update(cambios).eq("id", domicilio_id).execute()
    fila.update(cambios)
    return _normalizar(fila)


def eliminar(client, cliente_id, domicilio_id):
    fila = _obtener_propio(client, cliente_id, domicilio_id)
    client.table("domicilios_cliente").delete().eq("id", domicilio_id).execute()
    if fila.get("predeterminado"):
        restantes = client.table("domicilios_cliente").select("*").eq("cliente_id", cliente_id).execute().data
        if restantes:
            client.table("domicilios_cliente").update({"predeterminado": True}).eq("id", restantes[0]["id"]).execute()


def marcar_predeterminado(client, cliente_id, domicilio_id):
    _obtener_propio(client, cliente_id, domicilio_id)
    _desmarcar_predeterminados(client, cliente_id)
    client.table("domicilios_cliente").update({"predeterminado": True}).eq("id", domicilio_id).execute()
