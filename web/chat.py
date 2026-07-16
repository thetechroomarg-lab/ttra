import logging
import re
from urllib.parse import quote

logger = logging.getLogger("web")

MODELO = "claude-haiku-4-5-20251001"  # el más barato; suficiente para consultas/precios
# Búsqueda web oficial de Claude: la usa solo cuando necesita specs/comparativas.
TOOLS = [{"type": "web_search_20250305", "name": "web_search", "max_uses": 2}]

# Precios Haiku 4.5 por millón de tokens (USD): entrada, lectura de cache, escritura de
# cache, salida. Web search: 0,01 USD por búsqueda.
_PRECIO = {"in": 1.0, "cache_read": 0.10, "cache_write": 1.25, "out": 5.0}
_PRECIO_BUSQUEDA = 0.01


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
        max_tokens=1200,
        system=system,
        tools=TOOLS,
        messages=mensajes,
    )
    costo = _costo(resp)
    return _formatear_pedido(_extraer_texto(resp)), costo


def _costo(resp):
    # Calcula el costo en USD del mensaje y lo loguea. Devuelve el número.
    u = getattr(resp, "usage", None)
    if u is None:
        return 0.0
    ent = getattr(u, "input_tokens", 0) or 0
    cr = getattr(u, "cache_read_input_tokens", 0) or 0
    cw = getattr(u, "cache_creation_input_tokens", 0) or 0
    out = getattr(u, "output_tokens", 0) or 0
    busquedas = 0
    su = getattr(u, "server_tool_use", None)
    if su is not None:
        busquedas = getattr(su, "web_search_requests", 0) or 0
    costo = (ent * _PRECIO["in"] + cr * _PRECIO["cache_read"]
             + cw * _PRECIO["cache_write"] + out * _PRECIO["out"]) / 1_000_000
    costo += busquedas * _PRECIO_BUSQUEDA
    logger.info(
        "COSTO msg: in=%d cache_read=%d cache_write=%d out=%d busquedas=%d -> USD %.4f",
        ent, cr, cw, out, busquedas, costo)
    return costo


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
