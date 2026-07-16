MODELO = "claude-sonnet-5"


def responder(mensaje, historial, productos, client):
    from web.reglas import construir_system
    system = construir_system(productos)
    mensajes = list(historial) + [{"role": "user", "content": mensaje}]
    resp = client.messages.create(
        model=MODELO,
        max_tokens=2048,
        system=system,
        messages=mensajes,
    )
    return _extraer_texto(resp)


def _extraer_texto(resp):
    # El modelo puede devolver bloques de "thinking" antes del texto; tomamos el
    # primer bloque de tipo texto (no asumimos que sea el primero de la lista).
    for bloque in resp.content:
        if getattr(bloque, "type", None) == "text":
            return bloque.text
    partes = [b.text for b in resp.content if hasattr(b, "text")]
    return partes[0] if partes else ""
