import re
from urllib.parse import quote

MODELO = "claude-sonnet-5"
# Búsqueda web oficial de Claude: la usa solo cuando necesita specs/comparativas.
TOOLS = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}]


def responder(mensaje, historial, productos, client):
    from web.reglas import construir_system
    system_text = construir_system(productos)
    # Cache del prompt: el catálogo es fijo durante la charla, así los mensajes
    # siguientes pagan ~10% de la entrada en vez del 100%.
    system = [{"type": "text", "text": system_text,
               "cache_control": {"type": "ephemeral"}}]
    mensajes = list(historial) + [{"role": "user", "content": mensaje}]
    resp = client.messages.create(
        model=MODELO,
        max_tokens=2048,
        system=system,
        tools=TOOLS,
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
    # El modelo puede devolver bloques de "thinking" y de búsqueda web además del texto.
    # Unimos todos los bloques de tipo texto (la respuesta puede venir en varias partes).
    partes = [b.text for b in resp.content
              if getattr(b, "type", None) == "text" and hasattr(b, "text")]
    if partes:
        return "\n".join(p for p in partes if p).strip()
    otras = [b.text for b in resp.content if hasattr(b, "text")]
    return otras[0] if otras else ""
