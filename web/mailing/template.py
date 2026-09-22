"""Arma el HTML del mail semanal de novedades, con la paleta del modo Classic
de la web (ver web/static/classic.css — carbón, blanco/crema, rojo coral,
tipografía Nunito). Usa estilos inline para degradar razonablemente en
clientes de mail que ignoran CSS embebido."""
import html
from urllib.parse import urlencode, urlparse

from web.reglas import WHATSAPP
BASE_URL = "https://www.thetechroomarg.com"

_INSTAGRAM = "https://instagram.com/thetechroomarg"
_TIKTOK = "https://tiktok.com/@thetechroomarg"
_EMAIL = "thetechroomarg@gmail.com"

_BG = "#1a1a1a"
_PANEL = "#262626"
_BLANCO = "#ffffff"
_CREMA = "#e6e6e6"
_GRIS_TENUE = "#a8a8a8"
_ROJO = "#ff6b5e"
_FUENTE = "'Nunito', 'Segoe UI', system-ui, sans-serif"


_ALTO_NOMBRE = 58
_ALTO_COLORES = 34
_ALTO_USD = 22
_ALTO_PESOS = 34
_ALTO_BOTON = 46


def _fila_fija(alto, contenido, padding_top=0):
    # Cada franja de la card (nombre, color, precio USD, precios pesos,
    # botón) es su propia fila de tabla con altura fija — así el precio de
    # una card cae en la misma línea que el precio de la de al lado, aunque
    # el nombre o la lista de colores ocupen distinto número de líneas.
    return (
        f'<tr><td height="{alto}" style="height:{alto}px; padding-top:{padding_top}px; '
        f'vertical-align:top;">{contenido}</td></tr>'
    )


def _tarjeta_producto(producto, base_url):
    nombre = html.escape(producto.get("nombre", ""))
    colores = producto.get("colores") or []
    texto_colores = html.escape(", ".join(colores)) if colores else "&nbsp;"
    link = f"{base_url.rstrip('/')}/?{urlencode({'producto': producto.get('nombre', '')})}"

    fila_nombre = _fila_fija(
        _ALTO_NOMBRE,
        f'<p style="margin:0; font-family:{_FUENTE}; font-size:15px; font-weight:800; color:{_BLANCO};">{nombre}</p>',
    )
    fila_colores = _fila_fija(
        _ALTO_COLORES,
        f'<p style="margin:0; font-size:13px; color:{_GRIS_TENUE};">{texto_colores}</p>',
    )
    fila_usd = _fila_fija(
        _ALTO_USD,
        f'<p style="margin:0; font-family:{_FUENTE}; font-size:14px; font-weight:700; color:{_ROJO};">U$D {producto.get("usd")}</p>',
    )
    fila_pesos = _fila_fija(
        _ALTO_PESOS,
        f'<p style="margin:0; font-family:{_FUENTE}; font-size:12px; color:{_GRIS_TENUE};">$ {producto.get("pesos")} contado &middot; $ {producto.get("transferencia")} transferencia</p>',
    )
    fila_boton = _fila_fija(
        _ALTO_BOTON,
        f'<a href="{link}" style="display:inline-block; padding:8px 14px; background:{_ROJO}; color:{_BLANCO}; text-decoration:none; font-family:{_FUENTE}; font-weight:700; font-size:13px; border-radius:4px;">Ver producto</a>',
        padding_top=10,
    )

    return f"""
<td style="padding:12px; vertical-align:top; width:50%;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:{_PANEL}; border:1px solid #3a3a3a; border-radius:6px;">
    <tr><td style="padding:16px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        {fila_nombre}
        {fila_colores}
        {fila_usd}
        {fila_pesos}
        {fila_boton}
      </table>
    </td></tr>
  </table>
</td>"""


def _hero_html(hero):
    if not hero:
        return ""
    url = str(hero.get("url", "")).strip()
    parsed = urlparse(url)
    preview_local = parsed.scheme == "data" and url.startswith("data:image/")
    if (parsed.scheme != "https" or not parsed.netloc) and not preview_local:
        raise ValueError("La URL del hero debe usar HTTPS")
    try:
        width = int(hero.get("width", 0))
        height = int(hero.get("height", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Dimensiones del hero inválidas") from exc
    if width <= 0 or height <= 0:
        raise ValueError("Dimensiones del hero inválidas")
    alto_email = max(1, round(560 * height / width))
    alt = html.escape(str(hero.get("alt", "")), quote=True)
    url = html.escape(url, quote=True)
    return f'''
<tr><td style="padding:0 20px 20px;">
  <img src="{url}" alt="{alt}" width="560" height="{alto_email}"
       style="display:block; width:100%; max-width:560px; height:auto; border:0; border-radius:8px;">
</td></tr>'''


def armar_html(productos_nuevos, nota=None, cliente_id=None, base_url=BASE_URL,
               hero=None, preheader=""):
    baja_url = f"{base_url}/mailing/baja/{cliente_id}" if cliente_id else "#"
    preheader_html = ""
    if preheader:
        preheader_html = (
            '<div style="display:none; max-height:0; overflow:hidden; opacity:0; '
            'mso-hide:all; font-size:1px; line-height:1px;">'
            f'{html.escape(preheader)}'
            '</div>'
        )
    hero_html = _hero_html(hero)

    banner_nota = ""
    if nota:
        banner_nota = f"""
<tr><td style="padding:0 20px 20px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:{_ROJO}; border-radius:6px;">
    <tr><td style="padding:16px; font-family:{_FUENTE}; font-size:14px; color:{_BLANCO}; font-weight:800;">
      {html.escape(nota)}
    </td></tr>
  </table>
</td></tr>"""

    filas_productos = ""
    for i in range(0, len(productos_nuevos), 2):
        par = productos_nuevos[i:i + 2]
        celdas = "".join(_tarjeta_producto(p, base_url) for p in par)
        if len(par) == 1:
            celdas += "<td style='width:50%;'></td>"
        filas_productos += f"<tr>{celdas}</tr>"

    return f"""<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0; padding:0; background:{_BG};">
{preheader_html}
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background:{_BG};">
<tr><td style="padding:0 20px 20px; text-align:center;">
  <p style="margin:0; font-family:{_FUENTE}; font-size:20px; font-weight:800; color:{_BLANCO}; letter-spacing:0.5px;">THE TECH ROOM ARG</p>
  <p style="margin:4px 0 0; font-family:{_FUENTE}; font-size:12px; color:{_GRIS_TENUE};">Novedades de la semana</p>
</td></tr>
{hero_html}
{banner_nota}
<tr><td style="padding:0 12px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas_productos}</table>
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
