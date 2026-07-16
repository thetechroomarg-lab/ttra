import re
from urllib.parse import quote

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
    return _formatear_pedido(_extraer_texto(resp))


def _formatear_pedido(texto):
    # Si el modelo marcó el pedido final con [PEDIDO]...[/PEDIDO], lo convertimos en un
    # link de WhatsApp con el mensaje ya cargado (así al cliente le llega preformado al
    # dueño). El encoding lo hacemos acá para que nunca falle.
    from web.reglas import WHATSAPP
    m = re.search(r"\[PEDIDO\](.*?)\[/PEDIDO\]", texto, re.DOTALL)
    if not m:
        return texto
    pedido = m.group(1).strip()
    link = WHATSAPP + "?text=" + quote(pedido)
    cta = ("👉 Tocá este enlace para enviarme tu pedido por WhatsApp y coordinar "
           "pago y envío:\n" + link)
    return (texto[:m.start()].rstrip() + "\n\n" + cta + texto[m.end():]).strip()


def _extraer_texto(resp):
    # El modelo puede devolver bloques de "thinking" antes del texto; tomamos el
    # primer bloque de tipo texto (no asumimos que sea el primero de la lista).
    for bloque in resp.content:
        if getattr(bloque, "type", None) == "text":
            return bloque.text
    partes = [b.text for b in resp.content if hasattr(b, "text")]
    return partes[0] if partes else ""
