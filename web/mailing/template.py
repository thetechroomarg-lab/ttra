"""Arma el HTML del mail semanal de novedades, con la paleta del modo Classic
de la web (ver web/static/classic.css — carbón, blanco/crema, rojo coral,
tipografía Nunito). Usa estilos inline para degradar razonablemente en
clientes de mail que ignoran CSS embebido."""
import html

from web.slugs import url_producto

BASE_URL = "https://thetechroomarg.com"

_BG = "#1a1a1a"
_PANEL = "#262626"
_BLANCO = "#ffffff"
_CREMA = "#e6e6e6"
_GRIS_TENUE = "#a8a8a8"
_ROJO = "#ff6b5e"
_FUENTE = "'Nunito', 'Segoe UI', system-ui, sans-serif"


def _tarjeta_producto(producto, base_url):
    nombre = html.escape(producto.get("nombre", ""))
    colores = producto.get("colores") or []
    colores_html = (
        f"<p style='margin:4px 0 0; font-size:13px; color:{_GRIS_TENUE};'>"
        f"{html.escape(', '.join(colores))}</p>"
        if colores else ""
    )
    link = url_producto(producto.get("nombre", ""), base=base_url)
    # height en el <table> Y en el <td> (no solo CSS) porque Outlook/algunos
    # clientes de mail ignoran min-height por CSS pero sí respetan el
    # atributo HTML height — así todas las cards miden lo mismo aunque el
    # nombre o la lista de colores varíen en largo.
    return f"""
<td style="padding:12px; vertical-align:top; width:50%;">
  <table role="presentation" width="100%" height="260" cellpadding="0" cellspacing="0"
         style="background:{_PANEL}; border:1px solid #3a3a3a; border-radius:6px; height:260px;">
    <tr><td height="260" style="padding:16px; vertical-align:top; height:260px;">
      <p style="margin:0; font-family:{_FUENTE}; font-size:15px; font-weight:800; color:{_BLANCO};">{nombre}</p>
      {colores_html}
      <p style="margin:10px 0 0; font-family:{_FUENTE}; font-size:14px; font-weight:700; color:{_ROJO};">U$D {producto.get("usd")}</p>
      <p style="margin:2px 0 0; font-family:{_FUENTE}; font-size:12px; color:{_GRIS_TENUE};">$ {producto.get("pesos")} contado &middot; $ {producto.get("transferencia")} transferencia</p>
      <a href="{link}" style="display:inline-block; margin-top:12px; padding:8px 14px; background:{_ROJO}; color:{_BLANCO}; text-decoration:none; font-family:{_FUENTE}; font-weight:700; font-size:13px; border-radius:4px;">Ver producto</a>
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
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background:{_BG};">
<tr><td style="padding:0 20px 20px; text-align:center;">
  <p style="margin:0; font-family:{_FUENTE}; font-size:20px; font-weight:800; color:{_BLANCO}; letter-spacing:0.5px;">THE TECH ROOM ARG</p>
  <p style="margin:4px 0 0; font-family:{_FUENTE}; font-size:12px; color:{_GRIS_TENUE};">Novedades de la semana</p>
</td></tr>
{banner_nota}
<tr><td style="padding:0 12px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas_productos}</table>
</td></tr>
<tr><td style="padding:24px 20px 8px; text-align:center;">
  <p style="margin:0; font-family:{_FUENTE}; font-size:11px; color:{_GRIS_TENUE};">
    <a href="{baja_url}" style="color:{_GRIS_TENUE};">No quiero recibir más novedades por mail</a>
  </p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
