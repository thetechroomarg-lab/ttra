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
    return resp.content[0].text
