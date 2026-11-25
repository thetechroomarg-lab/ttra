"""Mail de promo para quien miró productos y no compró: US$10 con código que
vence a las 72 hs. Misma paleta Classic que el mail de novedades (carbón,
crema, coral, Nunito) y estilos inline para los clientes de mail."""
import html
from datetime import timedelta, timezone
from urllib.parse import urlencode

from web.mailing.template import (
    BASE_URL, _BG, _BLANCO, _CREMA, _EMAIL, _FUENTE, _GRIS_TENUE, _INSTAGRAM,
    _PANEL, _ROJO, _TIKTOK,
)
from web.reglas import WHATSAPP
from web.slugs import slug

DESCUENTO_USD = 10
HORAS_VIGENCIA = 72
MAX_PRODUCTOS = 4
_AR = timezone(timedelta(hours=-3))
_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "octubre", "noviembre", "diciembre",
]
_FONDO_CODIGO = "#1a1a1a"
_TEXTO_SOBRE_ROJO = "#1a1a1a"


def _miles(n):
    return f"{int(round(n)):,}".replace(",", ".")


def texto_vencimiento(vence_en):
    """'jueves 28 de noviembre a las 15:40' en hora Argentina (UTC-3 fijo)."""
    v = vence_en.astimezone(_AR)
    return f"{_DIAS[v.weekday()]} {v.day} de {_MESES[v.month - 1]} a las {v:%H:%M}"


def link_producto(nombre, codigo, base_url=BASE_URL):
    query = urlencode({"producto": slug(nombre), "agregar": "1", "codigo": codigo})
    return f"{base_url.rstrip('/')}/?{query}"


def _fila_producto(producto, codigo, base_url):
    usd = producto["usd"]
    pesos = producto["pesos"]
    transf = producto["transferencia"]
    usd_con = max(usd - DESCUENTO_USD, 0)
    # Mismo criterio que el checkout: el descuento en pesos sale de la
    # proporción pesos/usd del producto.
    pesos_con = pesos - round(DESCUENTO_USD * pesos / usd)
    transf_con = transf - round(DESCUENTO_USD * transf / usd)
    nombre = html.escape(producto["nombre"])
    colores = producto.get("colores") or []
    texto_colores = (
        f'<p style="margin:2px 0 0; font-size:13px; color:{_GRIS_TENUE};">'
        f'{html.escape(", ".join(colores))}</p>' if colores else ""
    )
    link = html.escape(link_producto(producto["nombre"], codigo, base_url), quote=True)
    return f"""
<tr><td style="padding:16px 0; border-top:1px solid #3a3a3a;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="vertical-align:top; padding-right:12px;">
      <p style="margin:0; font-family:{_FUENTE}; font-size:16px; line-height:1.35; font-weight:800; color:{_BLANCO};">{nombre}</p>
      {texto_colores}
      <p style="margin:8px 0 0; font-family:{_FUENTE}; font-size:15px; color:{_CREMA};">
        <span style="color:{_GRIS_TENUE}; text-decoration:line-through;">U$D {_miles(usd)}</span>
        &nbsp;<strong style="color:{_ROJO}; font-size:18px;">U$D {_miles(usd_con)}</strong>
      </p>
      <p style="margin:2px 0 0; font-family:{_FUENTE}; font-size:12px; color:{_GRIS_TENUE};">
        $ {_miles(pesos_con)} contado &middot; $ {_miles(transf_con)} transferencia
      </p>
    </td>
    <td style="vertical-align:middle; text-align:right; white-space:nowrap;">
      <a href="{link}" style="display:inline-block; padding:11px 16px; background:{_ROJO}; color:{_TEXTO_SOBRE_ROJO}; text-decoration:none; font-family:{_FUENTE}; font-weight:800; font-size:14px; border-radius:6px;">Lo quiero</a>
    </td>
  </tr></table>
</td></tr>"""


def armar_mail(nombre, productos, codigo, vence_en, cliente_id, base_url=BASE_URL):
    """Devuelve (asunto, html). `productos` ya viene filtrado a lo que sigue
    en catálogo, con usd/pesos/transferencia/colores."""
    productos = productos[:MAX_PRODUCTOS]
    if not productos:
        raise ValueError("Sin productos para mencionar")
    una = len(productos) == 1
    nombre = html.escape((nombre or "").strip() or "")
    saludo = f"Hola {nombre}," if nombre else "Hola,"
    vence = texto_vencimiento(vence_en)
    filas = "".join(_fila_producto(p, codigo, base_url) for p in productos)
    miraste = "este equipo" if una else "estos equipos"
    asunto = f"U$D {DESCUENTO_USD} menos en lo que estuviste viendo"
    baja_url = f"{base_url}/mailing/baja/{cliente_id}"
    codigo_h = html.escape(codigo)
    preheader = f"Tu código {codigo} vence el {vence}."
    cuerpo = f"""<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(asunto)}</title></head>
<body style="margin:0; padding:0; background:{_BG};">
<div style="display:none; max-height:0; overflow:hidden; opacity:0; mso-hide:all; font-size:1px; line-height:1px;">{html.escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background:{_BG};">
<tr><td style="padding:0 20px 28px;">
  <p style="margin:0; font-family:{_FUENTE}; font-size:18px; font-weight:800; color:{_BLANCO}; letter-spacing:0.5px;">THE TECH ROOM ARG<span style="color:{_ROJO};">.</span></p>
</td></tr>
<tr><td style="padding:0 20px 8px;">
  <h1 style="margin:0; font-family:{_FUENTE}; font-size:34px; line-height:1.1; font-weight:800; color:{_BLANCO}; letter-spacing:-0.5px;">U$D {DESCUENTO_USD} menos en lo que estuviste viendo.</h1>
</td></tr>
<tr><td style="padding:12px 20px 24px;">
  <p style="margin:0; font-family:{_FUENTE}; font-size:16px; line-height:1.55; color:{_CREMA};">{saludo} soy Vlad. Vi que pasaste por la tienda y miraste {miraste}. Si te quedó la duda, te dejo U$D {DESCUENTO_USD} de descuento con este código.</p>
</td></tr>
<tr><td style="padding:0 20px 24px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_PANEL}; border:1px dashed {_ROJO}; border-radius:12px;">
    <tr><td style="padding:20px; text-align:center;">
      <p style="margin:0; font-family:{_FUENTE}; font-size:13px; color:{_GRIS_TENUE};">Tu código</p>
      <p style="margin:6px 0 0; font-family:'SFMono-Regular', Menlo, Consolas, monospace; font-size:28px; font-weight:700; letter-spacing:2px; color:{_BLANCO};">{codigo_h}</p>
      <p style="margin:10px 0 0; font-family:{_FUENTE}; font-size:14px; line-height:1.4; color:{_CREMA};">Vale hasta el <strong style="color:{_BLANCO};">{vence}</strong> (hora Argentina). Es personal, de un solo uso, y se carga en el carrito.</p>
    </td></tr>
  </table>
</td></tr>
<tr><td style="padding:0 20px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas}</table>
</td></tr>
<tr><td style="padding:16px 20px 8px;">
  <p style="margin:0; font-family:{_FUENTE}; font-size:14px; line-height:1.5; color:{_CREMA};">Si preferís resolverlo por WhatsApp, escribime y lo armo con vos: <a href="{WHATSAPP}" style="color:{_ROJO}; font-weight:700;">hablar con Vlad</a>.</p>
</td></tr>
<tr><td style="padding:24px 20px 8px; text-align:center;">
  <p style="margin:0; font-family:{_FUENTE}; font-size:12px; color:{_GRIS_TENUE};">
    <a href="{WHATSAPP}" style="color:{_BLANCO}; text-decoration:none; font-weight:700;">WhatsApp</a>
    &nbsp;&middot;&nbsp;
    <a href="mailto:{_EMAIL}" style="color:{_BLANCO}; text-decoration:none; font-weight:700;">Mail</a>
    &nbsp;&middot;&nbsp;
    <a href="{_INSTAGRAM}" style="color:{_BLANCO}; text-decoration:none; font-weight:700;">Instagram</a>
    &nbsp;&middot;&nbsp;
    <a href="{_TIKTOK}" style="color:{_BLANCO}; text-decoration:none; font-weight:700;">TikTok</a>
  </p>
  <p style="margin:10px 0 0; font-family:{_FUENTE}; font-size:11px; color:{_GRIS_TENUE};">
    <a href="{baja_url}" style="color:{_GRIS_TENUE};">No quiero recibir más novedades por mail</a>
  </p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
    return asunto, cuerpo
