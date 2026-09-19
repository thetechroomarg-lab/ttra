"""Arma el HTML del mail semanal de novedades, con estilo terminal oscuro
consistente con la web (ver web/static/theme.css). Usa estilos inline para
degradar razonablemente en clientes de mail que ignoran CSS embebido."""
import html

from web.slugs import url_producto

BASE_URL = "https://thetechroomarg.com"

_BG = "#030a03"
_PANEL = "#0b1f0b"
_VERDE = "#33ff66"
_VERDE_BRILLANTE = "#7bffa0"
_VERDE_TENUE = "#1f8c3f"
_FUENTE = "'Share Tech Mono', 'Courier New', monospace"


def _tarjeta_producto(producto, base_url):
    nombre = html.escape(producto.get("nombre", ""))
    colores = producto.get("colores") or []
    colores_html = (
        f"<p style='margin:4px 0 0; font-size:13px; color:{_VERDE_TENUE};'>"
        f"{html.escape(', '.join(colores))}</p>"
        if colores else ""
    )
    link = url_producto(producto.get("nombre", ""), base=base_url)
    return f"""
<td style="padding:12px; vertical-align:top; width:50%;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:{_PANEL}; border:1px solid {_VERDE_TENUE}; border-radius:6px;">
    <tr><td style="padding:16px;">
      <p style="margin:0; font-family:{_FUENTE}; font-size:15px; font-weight:bold; color:{_VERDE_BRILLANTE};">{nombre}</p>
      {colores_html}
      <p style="margin:10px 0 0; font-family:{_FUENTE}; font-size:14px; color:{_VERDE};">U$D {producto.get("usd")}</p>
      <p style="margin:2px 0 0; font-family:{_FUENTE}; font-size:12px; color:{_VERDE_TENUE};">$ {producto.get("pesos")} contado &middot; $ {producto.get("transferencia")} transferencia</p>
      <a href="{link}" style="display:inline-block; margin-top:12px; padding:8px 14px; background:{_VERDE}; color:{_BG}; text-decoration:none; font-family:{_FUENTE}; font-weight:bold; font-size:13px; border-radius:4px;">Ver producto</a>
    </td></tr>
  </table>
</td>"""


def armar_html(productos_nuevos, nota=None, cliente_id=None, base_url=BASE_URL):
    baja_url = f"{base_url}/mailing/baja/{cliente_id}" if cliente_id else "#"

    banner_nota = ""
    if nota:
        banner_nota = f"""
<tr><td style="padding:0 20px 20px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:{_VERDE_TENUE}; border-radius:6px;">
    <tr><td style="padding:16px; font-family:{_FUENTE}; font-size:14px; color:{_BG}; font-weight:bold;">
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
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background:{_BG};">
<tr><td style="padding:0 20px 20px; text-align:center;">
  <p style="margin:0; font-family:'Archivo Black', sans-serif; font-size:20px; color:{_VERDE_BRILLANTE}; letter-spacing:1px;">THE TECH ROOM ARG</p>
  <p style="margin:4px 0 0; font-family:{_FUENTE}; font-size:12px; color:{_VERDE_TENUE};">Novedades de la semana</p>
</td></tr>
{banner_nota}
<tr><td style="padding:0 12px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas_productos}</table>
</td></tr>
<tr><td style="padding:24px 20px 8px; text-align:center;">
  <p style="margin:0; font-family:{_FUENTE}; font-size:11px; color:{_VERDE_TENUE};">
    <a href="{baja_url}" style="color:{_VERDE_TENUE};">No quiero recibir más novedades por mail</a>
  </p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
