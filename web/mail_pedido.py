"""Mail de pedido confirmado: le llega al cliente cada vez que se le carga un pedido.

Se manda tanto cuando el cliente confirma desde la web como cuando Vladimir lo
carga a mano (skill /pedido). Si el admin elimina un pedido sin entregar, le
llega el de pedido cancelado, con las mismas piezas. Es la web en modo Classic oscuro hecha mail:
grafito, títulos pesados que cierran con ":" o un punto coral, números grandes
con la unidad en coral (como las cards de Garantías), cards con la flecha ↗ y
el sticker "Hola, soy Vlad" como firma.

Todo va con tablas y estilos inline, que es lo único que respetan todos los
clientes de correo. Las fuentes de la web (Geist, Instrument Serif, Caveat) se
cargan donde el cliente lo permite (Apple Mail, iOS); el resto cae a Helvetica.
"""
import html
import json
import logging
import math
import os
from collections import Counter
from datetime import date
from pathlib import Path

from . import garantias
from .email_util import enviar_email

logger = logging.getLogger(__name__)

URL_SITIO = "https://thetechroomarg.com"
PRODUCTOS_PATH = Path(__file__).resolve().parent / "productos.json"

# Tokens de Classic oscuro (web/static/classic.css) y del sticker
# (classic-editorial.css).
_FONDO = "#101010"
_BG = "#1a1a1a"
_PANEL = "#262626"
_BORDE = "#3a3a3a"
_TEXTO = "#e6e6e6"
_BLANCO = "#ffffff"
_TENUE = "#a8a8a8"
_CORAL = "#ff6b5e"
_VERDE = "#34d399"
_CREMA = "#f2f2f2"
_TINTA = "#161616"
_TINTA_TENUE = "#555555"
_ROJO_CREMA = "#c6283b"
_STICKER_ROJO = "#e9524f"
_STICKER_PAPEL = "#fffaf2"
_STICKER_TINTA = "#272a35"
_STICKER_SOY = "#ba3936"

_SANS = "Geist,'Helvetica Neue',Helvetica,Arial,sans-serif"
_MONO = "'Geist Mono',Menlo,Consolas,monospace"
_SERIF = "'Instrument Serif',Georgia,serif"
_MANO = "Caveat,'Bradley Hand','Segoe Print',cursive"

_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

_ESTILOS = """
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@500;700&family=Geist+Mono:wght@500;600;700&family=Geist:wght@400;600;700;800;900&family=Instrument+Serif:ital@0;1&display=swap');
:root { color-scheme: dark; supported-color-schemes: dark; }
a { text-decoration: none; }
@media (max-width: 620px) {
  .px { padding-left: 20px !important; padding-right: 20px !important; }
  .titulo { font-size: 46px !important; letter-spacing: -2px !important; }
  .cifra { font-size: 62px !important; }
  .total { font-size: 30px !important; }
}
"""


def _usd(valor):
    return f"U$D {int(round(float(valor or 0))):,}".replace(",", ".")


def _pesos(valor):
    return f"$ {int(valor):,}".replace(",", ".")


def cotizacion_catalogo():
    """El dólar con el que está armado el catálogo (pesos / usd de productos.json).

    Así los pesos del mail son los mismos que el cliente vio en la web.
    """
    try:
        productos = json.loads(PRODUCTOS_PATH.read_text(encoding="utf-8"))
        ratios = Counter(
            round(p["pesos"] / p["usd"]) for p in productos if p.get("usd") and p.get("pesos")
        )
        return ratios.most_common(1)[0][0] if ratios else None
    except (OSError, ValueError, TypeError, KeyError):
        logger.exception("No se pudo leer la cotización del catálogo")
        return None


def precios(usd, cotizacion):
    """Los 5 precios de un monto en dólares, con las mismas cuentas que la web (precios.js)."""
    usd = int(round(float(usd or 0)))
    lineas = [
        ("U$D contado", _usd(usd)),
        ("Transf. USA", _usd(math.ceil(usd / 0.975))),
        ("USDT", f"USDT {math.ceil(usd / 0.99):,}".replace(",", ".")),
    ]
    if cotizacion:
        pesos = usd * cotizacion
        lineas += [("Pesos contado", _pesos(pesos)), ("Pesos transf.", _pesos(math.ceil(pesos / 0.97)))]
    return lineas


def _fecha(valor):
    if not valor:
        return None
    try:
        return valor if isinstance(valor, date) else date.fromisoformat(str(valor)[:10])
    except ValueError:
        return None


def _fecha_larga(dia):
    """date -> 'martes 13 de octubre'."""
    return f"{_DIAS[dia.weekday()]} {dia.day} de {_MESES[dia.month - 1]}"


def numero_pedido(pedido):
    return (pedido.get("id") or "").replace("-", "")[:8].upper()


def _primer_nombre(cliente):
    partes = str(cliente.get("nombre") or "").strip().split()
    return partes[0].capitalize() if partes else ""


def _items(pedido):
    """Las filas del pedido. Los pedidos viejos sin detalle solo tienen nombres."""
    detalle = pedido.get("detalle") or []
    if detalle:
        return detalle
    return [{"nombre": nombre, "cantidad": 1} for nombre in (pedido.get("productos") or []) if nombre]


def garantias_resumidas(detalle):
    """Lo esencial de cada garantía que aplica: plazo, desde cuándo, qué cubre y qué no."""
    datos = garantias.cargar()
    resumen = []
    for clave in garantias.claves_para_detalle(detalle):
        g = datos[clave]
        cobertura = next((b for b in g["bloques"] if b["tipo"] == "cobertura"), {})
        aviso = next((b for b in g["bloques"] if b["tipo"] == "aviso"), None)
        numero, unidad = g["plazo"]
        resumen.append({
            "clave": clave,
            "titulo": g["titulo"],
            "numero": numero,
            "unidad": unidad,
            "desde": g["desde"],
            "como": aviso["texto"] if aviso else None,
            "cubre": (cobertura.get("cubre") or [None])[0],
            "no_cubre": (cobertura.get("noCubre") or [None])[0],
        })
    return resumen


# ── Piezas ──────────────────────────────────────────────────────────────────

def _tabla(filas, estilo=""):
    return ('<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="border-collapse:collapse;{estilo}">{filas}</table>')


def _bloque(contenido, padding_top=48):
    """Una franja del mail, con los márgenes laterales que se achican en mobile."""
    return f'<tr><td class="px" style="padding:{padding_top}px 32px 0">{contenido}</td></tr>'


def _etiqueta(texto, color=_TENUE):
    return (f'<p style="margin:0;font:600 11px/1.4 {_MONO};letter-spacing:2px;'
            f'text-transform:uppercase;color:{color}">{texto}</p>')


def _titulo_seccion(texto):
    """Como en la home: 'Garantías:', 'Categorías:'."""
    return (f'<p style="margin:0 0 18px;font:800 30px/1.05 {_SANS};letter-spacing:-1.2px;'
            f'color:{_BLANCO}">{texto}:</p>')


def _cifra(numero, unidad, color, color_unidad, tamano):
    """Número enorme con la unidad chica en mayúsculas al lado (las cards de Garantías)."""
    return (f'<p class="cifra" style="margin:0;font:900 {tamano}px/0.85 {_SANS};letter-spacing:-3.5px;color:{color}">'
            f'{numero}<span style="font:700 12px/1 {_MONO};letter-spacing:2px;text-transform:uppercase;'
            f'color:{color_unidad}">&nbsp;&nbsp;{unidad}</span></p>')


def _flecha():
    """El círculo con ↗ de las cards de la web."""
    return ('<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:separate">'
            f'<tr><td width="30" height="30" align="center" valign="middle" style="width:30px;height:30px;'
            f'border:1.5px solid {_TEXTO};border-radius:50%;font:700 15px/1 {_SANS};color:{_TEXTO}">&#8599;</td></tr></table>')


def _logo():
    return ('<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse"><tr>'
            f'<td style="background:#000000;padding:10px 12px 10px 10px">'
            f'<p style="margin:0;font:900 15px/0.9 {_SANS};letter-spacing:-0.8px;color:{_BLANCO}">'
            f'THE<br>TECH<br>ROOM<br>ARG<span style="color:{_CORAL}">.</span></p></td></tr></table>')


def _encabezado(numero):
    fila = (f'<tr><td valign="middle">{_logo()}</td>'
            f'<td valign="middle" align="right">{_etiqueta("Pedido")}'
            f'<p style="margin:6px 0 0;font:700 17px/1 {_MONO};letter-spacing:0.5px;color:{_BLANCO}">#{numero}</p></td></tr>')
    return f'<tr><td class="px" style="padding:24px 32px;border-bottom:1px solid {_BORDE}">{_tabla(fila)}</td></tr>'


def _hero(nombre, dia, correccion=False):
    saludo = f"¡Gracias, {html.escape(nombre)}!" if nombre else "¡Gracias por tu compra!"
    cuando = f' para el <b style="color:{_BLANCO};font-weight:600">{_fecha_larga(dia)}</b>' if dia else ""
    if correccion:
        texto = (f"Sumé lo que agregaste a tu pedido{cuando}. Abajo tenés el detalle actualizado, con lo nuevo "
                 f"marcado, el nuevo total y la garantía de cada producto.")
    else:
        texto = (f"Tu pedido está confirmado y ya lo estoy preparando{cuando}. Abajo tenés todo el detalle "
                 f"y la garantía de cada producto.")
    return _bloque(
        f'<p style="margin:0 0 22px;font:600 11px/1 {_MONO};letter-spacing:2px;text-transform:uppercase;color:{_CORAL}">'
        f'&#9679;&nbsp;&nbsp;{"Corrección de pedido" if correccion else "Pedido confirmado"}</p>'
        f'<p class="titulo" style="margin:0;font:800 58px/0.95 {_SANS};letter-spacing:-2.6px;color:{_BLANCO}">'
        f'Ya casi es tuyo<span style="color:{_CORAL}">.</span></p>'
        f'<p style="margin:26px 0 0;font:italic 27px/1.15 {_SERIF};color:{_TEXTO}">{saludo}</p>'
        f'<p style="margin:10px 0 0;font:400 16px/1.6 {_SANS};color:{_TENUE}">{texto}</p>',
        padding_top=44,
    )


def _entrega(pedido, dia):
    """La card destacada en crema, como la de Apple en Garantías."""
    direccion = (pedido.get("direccion_entrega") or "").strip()
    if not dia and not direccion:
        return ""
    piso_depto = " · ".join(
        f"{etiqueta} {html.escape(str(pedido[campo]))}"
        for campo, etiqueta in (("piso_entrega", "Piso"), ("depto_entrega", "Depto"))
        if pedido.get(campo)
    )
    partes = []
    if dia:
        partes.append(
            _cifra(dia.day, _MESES[dia.month - 1], _TINTA, _ROJO_CREMA, 76)
            + f'<p style="margin:14px 0 0">{_etiqueta(f"{_DIAS[dia.weekday()]} · Día de entrega", _TINTA_TENUE)}</p>'
        )
    if direccion:
        separador = "border-top:1px solid #cfcfcf;margin-top:18px;padding-top:16px" if dia else ""
        partes.append(
            f'<div style="{separador}">{_etiqueta("Dirección", _TINTA_TENUE)}'
            f'<p style="margin:6px 0 0;font:700 17px/1.35 {_SANS};letter-spacing:-0.2px;color:{_TINTA}">{html.escape(direccion)}</p>'
            + (f'<p style="margin:4px 0 0;font:400 14px/1.4 {_SANS};color:{_TINTA_TENUE}">{piso_depto}</p>' if piso_depto else "")
            + '</div>'
        )
    contenido = "".join(partes)
    return _bloque(_titulo_seccion("Entrega") + _tabla(f'<tr><td style="padding:26px 24px">{contenido}</td></tr>', f"background:{_CREMA}"))


def _lista_precios(usd, cotizacion, grande=False):
    """Un precio por línea, cada uno con su aclaración al lado. El primero (U$D contado) manda."""
    filas = []
    for i, (etiqueta, monto) in enumerate(precios(usd, cotizacion)):
        principal = i == 0
        tamano = (36 if grande else 17) if principal else 14
        clase = ' class="total"' if principal and grande else ""
        filas.append(
            f'<tr><td valign="bottom" style="padding:{"0" if principal else "9px"} 0 0">'
            f'{_etiqueta(etiqueta, _BLANCO if principal else _TENUE)}</td>'
            f'<td valign="bottom" align="right"{clase} style="padding:{"0" if principal else "9px"} 0 0;white-space:nowrap;'
            f'font:{700 if principal else 500} {tamano}px/1 {_MONO};letter-spacing:{"-1.5px" if principal and grande else "0"};'
            f'color:{_BLANCO if principal else _TEXTO}">{monto}</td></tr>'
        )
        if principal:
            filas.append(f'<tr><td colspan="2" style="padding:{"16px" if grande else "12px"} 0 0;border-bottom:1px solid {_BORDE};'
                         f'font-size:0;line-height:0">&nbsp;</td></tr>')
    return _tabla("".join(filas))


def _fila_item(item, cotizacion, agregado=False):
    cantidad = int(item.get("cantidad") or 1)
    meta = []
    if item.get("color") and item["color"] != "Color único":
        meta.append(html.escape(item["color"]))
    meta.append(f"Cantidad {cantidad}")
    if item.get("usd_unitario") is not None and cantidad > 1:
        meta.append(f"{_usd(item['usd_unitario'])} c/u")
    lista = (f'<div style="margin-top:16px;padding:16px;background:{_BG};border:1px solid {_BORDE}">'
             f'{_lista_precios(item["usd_subtotal"], cotizacion)}</div>'
             if item.get("usd_subtotal") is not None else "")
    marca = (f'<p style="margin:0 0 10px"><span style="display:inline-block;padding:5px 8px;background:{_CORAL};'
             f'font:700 10px/1 {_MONO};letter-spacing:2px;text-transform:uppercase;color:{_FONDO}">+ Agregado</span></p>'
             if agregado else "")
    return (
        f'<tr><td style="padding:20px;border-bottom:1px solid {_BORDE}{";border-left:3px solid " + _CORAL if agregado else ""}">'
        f'{marca}<p style="margin:0;font:600 16px/1.35 {_SANS};color:{_BLANCO};word-break:break-word">{html.escape(item.get("nombre") or "")}</p>'
        f'<p style="margin:6px 0 0;font:500 11px/1.4 {_MONO};letter-spacing:1px;text-transform:uppercase;color:{_TENUE}">'
        f'{" · ".join(meta)}</p>{lista}</td></tr>'
    )


def _totales(pedido, items, cotizacion):
    if pedido.get("total_usd") is None:
        return ""
    total = float(pedido.get("total_usd") or 0)
    descuento = float(pedido.get("descuento_usd") or 0)
    filas = ""
    if descuento:
        subtotal = sum(float(i.get("usd_subtotal") or 0) for i in items) or total + descuento
        for etiqueta, valor, color in (("Subtotal", _usd(subtotal), _TENUE), ("Descuento", f"-{_usd(descuento)}", _CORAL)):
            fila = (f'<tr><td>{_etiqueta(etiqueta, color)}</td>'
                    f'<td align="right" style="font:600 14px/1 {_MONO};color:{color}">{valor}</td></tr>')
            filas += f'<tr><td style="padding:18px 20px 0">{_tabla(fila)}</td></tr>'
    aviso = (f'<p style="margin:16px 0 0;font:400 12px/1.5 {_SANS};color:#7a7a7a">Pesos calculados con el dólar a '
             f'{_pesos(cotizacion)}. Si pagás en pesos, el monto puede variar según la cotización del día de la entrega.</p>'
             if cotizacion else "")
    return (filas + f'<tr><td style="padding:22px 20px">'
            f'<div style="border-top:2px solid {_CORAL};padding-top:16px">'
            f'<p style="margin:0 0 14px">{_etiqueta("Total", _CORAL)}</p>'
            f'{_lista_precios(total, cotizacion, grande=True)}{aviso}</div></td></tr>')


def _clave_item(item):
    return (item.get("nombre"), item.get("color"))


def _compra(pedido, items, cotizacion, agregados=()):
    nuevos = {_clave_item(item) for item in agregados}
    filas = ("".join(_fila_item(item, cotizacion, _clave_item(item) in nuevos) for item in items)
             + _totales(pedido, items, cotizacion))
    return _bloque(_titulo_seccion("Tu compra") + _tabla(filas, f"background:{_PANEL};border:1px solid {_BORDE}"))


def _tarjeta_garantia(g, url):
    lineas = []
    if g["como"]:
        lineas.append(f'<p style="margin:0 0 10px;font:400 14px/1.55 {_SANS};color:{_TEXTO}">{html.escape(g["como"])}</p>')
    if g["cubre"]:
        lineas.append(f'<p style="margin:0 0 8px;font:400 14px/1.55 {_SANS};color:{_TENUE}">'
                      f'<b style="color:{_VERDE};font-weight:600">&#10003;&nbsp;Cubre</b>&nbsp; {html.escape(g["cubre"])}</p>')
    if g["no_cubre"]:
        lineas.append(f'<p style="margin:0 0 8px;font:400 14px/1.55 {_SANS};color:{_TENUE}">'
                      f'<b style="color:{_CORAL};font-weight:600">&#10005;&nbsp;No cubre</b>&nbsp; {html.escape(g["no_cubre"])}</p>')
    pie = _tabla(
        f'<tr><td valign="middle" style="border-top:1px solid {_BORDE};padding-top:16px">'
        f'<a href="{url}" style="font:600 17px/1.2 {_SANS};color:{_BLANCO}">Garantía {html.escape(g["titulo"])}</a></td>'
        f'<td valign="middle" align="right" width="34" style="border-top:1px solid {_BORDE};padding-top:16px">'
        f'<a href="{url}">{_flecha()}</a></td></tr>'
    )
    tarjeta = _tabla(
        f'<tr><td style="padding:22px 22px 0">'
        + _cifra(html.escape(g["numero"]), html.escape(g["unidad"]), _BLANCO, _CORAL, 68)
        + f'<p style="margin:14px 0 0">{_etiqueta(html.escape(g["desde"].rstrip(".")))}</p>'
        f'<div style="margin-top:16px">{"".join(lineas)}</div></td></tr>'
        f'<tr><td style="padding:8px 22px 18px">{pie}</td></tr>',
        f"background:{_PANEL};border:1px solid {_BORDE}",
    )
    return f'<tr><td style="padding:0 0 12px">{tarjeta}</td></tr>'


def _garantias(resumen, url_garantias):
    if not resumen:
        return ""
    url = html.escape(url_garantias, quote=True)
    return _bloque(
        _titulo_seccion("Garantías")
        + f'<p style="margin:-6px 0 18px;font:400 15px/1.55 {_SANS};color:{_TENUE}">El resumen de la garantía de lo que '
        f'compraste. Guardá este mail: te sirve para cualquier reclamo.</p>'
        + _tabla("".join(_tarjeta_garantia(g, url) for g in resumen))
        + f'<p style="margin:6px 0 0"><a href="{url}" style="font:600 14px/1.4 {_SANS};color:{_CORAL}">'
        f'Leé las condiciones completas en la web &#8599;</a></p>'
    )


def _boton(url, texto="Ver mi pedido en la web"):
    return _bloque(_tabla(
        f'<tr><td align="center" style="background:{_CORAL}">'
        f'<a href="{html.escape(url, quote=True)}" style="display:block;padding:19px 24px;'
        f'font:800 16px/1 {_SANS};letter-spacing:-0.2px;color:{_FONDO}">{texto} &#8599;</a></td></tr>'
    ), padding_top=44)


def _sticker(cierre="Cualquier duda con tu pedido, escribime y lo vemos."):
    """El sticker 'Hola, soy Vlad' de la home, como firma."""
    return (
        f'<tr><td class="px" align="center" style="padding:56px 32px 0">'
        f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" '
        f'style="max-width:360px;border-collapse:separate;border:1px solid #ff7770;border-radius:10px;'
        f'border-bottom:10px solid {_STICKER_ROJO};background:{_STICKER_PAPEL}">'
        f'<tr><td align="center" style="background:{_STICKER_ROJO};border-radius:9px 9px 0 0;padding:12px 16px">'
        f'<p style="margin:0;font:900 26px/1 {_SANS};letter-spacing:6px;color:{_STICKER_PAPEL}">HOLA</p></td></tr>'
        f'<tr><td align="center" style="padding:14px 18px 6px">'
        f'<p style="margin:0;font:500 19px/1 {_MANO};color:{_STICKER_SOY}">soy</p>'
        f'<p style="margin:2px 0 0;font:700 54px/1 {_MANO};color:{_STICKER_TINTA}">Vlad</p></td></tr>'
        f'<tr><td align="center" style="border-top:3px solid {_STICKER_ROJO};padding:10px 16px 12px">'
        f'<p style="margin:0;font:500 20px/1.1 {_MANO};color:{_STICKER_TINTA}">vendo tecnología desde el año 2009.</p>'
        f'</td></tr></table>'
        f'<p style="margin:28px 0 0;font:italic 25px/1.25 {_SERIF};color:{_BLANCO}">Gracias por confiar en mí.</p>'
        f'<p style="margin:8px 0 0;font:400 15px/1.6 {_SANS};color:{_TENUE}">{cierre}</p>'
        f'</td></tr>'
    )


def _pie(url_sitio, motivo="se registró un pedido a tu nombre", aclaracion=" No es válido como factura."):
    dominio = html.escape(url_sitio.split("://")[-1])
    return (
        f'<tr><td class="px" style="padding:48px 32px 32px">'
        f'<div style="border-top:1px solid {_BORDE};padding-top:20px">'
        f'<p style="margin:0;font:800 15px/1 {_SANS};letter-spacing:-0.5px;color:{_BLANCO}">'
        f'The Tech Room Arg<span style="color:{_CORAL}">.</span></p>'
        f'<p style="margin:10px 0 0;font:400 12px/1.6 {_SANS};color:#7a7a7a">Te llegó este mail porque {motivo} '
        f'en <a href="{html.escape(url_sitio, quote=True)}" style="color:{_TENUE};text-decoration:underline">'
        f'{dominio}</a>.{aclaracion}</p></div></td></tr>'
    )


def asunto(pedido, correccion=False):
    titulo = "Corrección de Pedido" if correccion else "Pedido confirmado"
    return f"{titulo} #{numero_pedido(pedido)} — The Tech Room Arg"


def html_pedido_confirmado(cliente, pedido, url_sitio=URL_SITIO, cotizacion=None, agregados=None):
    """El mail del pedido. Con `agregados` es una Corrección de Pedido: `pedido` es el pedido
    completo ya actualizado y `agregados` lo que se le sumó (va marcado)."""
    correccion = bool(agregados)
    url_sitio = (url_sitio or URL_SITIO).rstrip("/")
    cotizacion = cotizacion or cotizacion_catalogo()
    items = _items(pedido)
    dia = _fecha(pedido.get("fecha_entrega"))
    numero = numero_pedido(pedido)
    preheader = f"Corrección de pedido #{numero}" if correccion else f"Pedido #{numero} confirmado"
    if pedido.get("total_usd") is not None:
        preheader += f" · {'nuevo total ' if correccion else ''}{_usd(pedido['total_usd'])}"
    if dia:
        preheader += f" · entrega el {_fecha_larga(dia)}"
    cuerpo = "".join((
        _encabezado(numero),
        _hero(_primer_nombre(cliente), dia, correccion),
        _entrega(pedido, dia),
        _compra(pedido, items, cotizacion, agregados or ()),
        _garantias(garantias_resumidas(items), f"{url_sitio}/#ttra-garantias"),
        _boton(f"{url_sitio}/perfil"),
        _sticker(),
        _pie(url_sitio),
    ))
    titulo = "Corrección de pedido" if correccion else "Pedido confirmado"
    return _documento(titulo, preheader, cuerpo)


def _documento(titulo, preheader, cuerpo):
    return f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="dark"><meta name="supported-color-schemes" content="dark">
<title>{titulo}</title><style>{_ESTILOS}</style></head>
<body style="margin:0;padding:0;background:{_FONDO};-webkit-text-size-adjust:100%">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent">{html.escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;background:{_FONDO}">
<tr><td align="center" style="padding:20px 10px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border-collapse:collapse;max-width:600px;background:{_BG};border:1px solid #2a2a2a">
{cuerpo}
</table>
</td></tr></table>
</body></html>"""


# ── Pedido cancelado ────────────────────────────────────────────────────────

def _hero_cancelado(nombre, dia):
    saludo = f"Hola, {html.escape(nombre)}." if nombre else "Hola."
    cuando = f' para el <b style="color:{_BLANCO};font-weight:600">{_fecha_larga(dia)}</b>' if dia else ""
    return _bloque(
        f'<p style="margin:0 0 22px;font:600 11px/1 {_MONO};letter-spacing:2px;text-transform:uppercase;color:{_CORAL}">'
        f'&#9679;&nbsp;&nbsp;Pedido cancelado</p>'
        f'<p class="titulo" style="margin:0;font:800 58px/0.95 {_SANS};letter-spacing:-2.6px;color:{_BLANCO}">'
        f'Tu pedido fue cancelado<span style="color:{_CORAL}">.</span></p>'
        f'<p style="margin:26px 0 0;font:italic 27px/1.15 {_SERIF};color:{_TEXTO}">{saludo}</p>'
        f'<p style="margin:10px 0 0;font:400 16px/1.6 {_SANS};color:{_TENUE}">Cancelé tu pedido{cuando}. '
        f'Abajo tenés el detalle de lo que se canceló. Si fue un error o tenés alguna duda, escribime y lo vemos.</p>',
        padding_top=44,
    )


def _cancelado(pedido, items):
    """Lo que se canceló, apagado: sin los 5 precios, con el total tachado."""
    filas = []
    for item in items:
        meta = []
        if item.get("color") and item["color"] != "Color único":
            meta.append(html.escape(item["color"]))
        meta.append(f"Cantidad {int(item.get('cantidad') or 1)}")
        filas.append(
            f'<tr><td style="padding:18px 20px;border-bottom:1px solid {_BORDE}">'
            f'<p style="margin:0;font:600 16px/1.35 {_SANS};color:{_TEXTO};word-break:break-word">{html.escape(item.get("nombre") or "")}</p>'
            f'<p style="margin:6px 0 0;font:500 11px/1.4 {_MONO};letter-spacing:1px;text-transform:uppercase;color:{_TENUE}">'
            f'{" · ".join(meta)}</p></td></tr>'
        )
    if pedido.get("total_usd") is not None:
        total = _tabla(
            f'<tr><td valign="bottom">{_etiqueta("Total cancelado", _CORAL)}</td>'
            f'<td valign="bottom" align="right" style="white-space:nowrap;font:700 22px/1 {_MONO};color:{_TENUE};'
            f'text-decoration:line-through">{_usd(pedido["total_usd"])}</td></tr>'
        )
        filas.append(f'<tr><td style="padding:20px"><div style="border-top:2px solid {_CORAL};padding-top:16px">{total}</div></td></tr>')
    return _bloque(_titulo_seccion("Lo que se canceló") + _tabla("".join(filas), f"background:{_PANEL};border:1px solid {_BORDE}"))


def asunto_cancelado(pedido):
    return f"Pedido cancelado #{numero_pedido(pedido)} — The Tech Room Arg"


def html_pedido_cancelado(cliente, pedido, url_sitio=URL_SITIO):
    url_sitio = (url_sitio or URL_SITIO).rstrip("/")
    dia = _fecha(pedido.get("fecha_entrega"))
    numero = numero_pedido(pedido)
    preheader = f"Pedido #{numero} cancelado" + (f" · era para el {_fecha_larga(dia)}" if dia else "")
    cuerpo = "".join((
        _encabezado(numero),
        _hero_cancelado(_primer_nombre(cliente), dia),
        _cancelado(pedido, _items(pedido)),
        _boton(url_sitio, "Ir a la tienda"),
        _sticker("Cualquier duda, escribime y lo vemos."),
        _pie(url_sitio),
    ))
    return _documento("Pedido cancelado", preheader, cuerpo)


def notificar_cancelacion(client, pedido, url_sitio=None):
    """Le avisa al cliente que se canceló su pedido. Nunca levanta: un mail caído no frena el borrado."""
    try:
        filas = client.table("clientes").select("*").eq("id", pedido.get("cliente_id")).execute().data
        cliente = filas[0] if filas else {}
        email = (cliente.get("email") or "").strip()
        if not email:
            logger.info("Pedido %s cancelado sin mail de cliente: no se notifica", pedido.get("id"))
            return False
        url = url_sitio or os.environ.get("PUBLIC_APP_URL") or URL_SITIO
        enviar_email(email, asunto_cancelado(pedido), html_pedido_cancelado(cliente, pedido, url))
        return True
    except Exception:
        logger.exception("No se pudo mandar el mail de cancelación del pedido %s", pedido.get("id"))
        return False


def _pedido_en_base(client, carga):
    if not carga.get("id"):
        return None
    try:
        filas = client.table("pedidos").select("*").eq("id", carga["id"]).execute().data
    except Exception:
        logger.exception("No se pudo leer el pedido %s", carga.get("id"))
        return None
    return filas[0] if filas else None


def _es_correccion(pedido, carga):
    """La carga se sumó a un pedido que ya existía (mismo día de entrega, sin entregar)."""
    if not pedido or not pedido.get("detalle") or not carga.get("detalle"):
        return False
    if len(pedido["detalle"]) != len(carga["detalle"]):
        return True
    cantidades = lambda detalle: sorted((str(i.get("nombre")), str(i.get("color")), int(i.get("cantidad") or 0)) for i in detalle)
    return cantidades(pedido["detalle"]) != cantidades(carga["detalle"])


def notificar_pedido(client, cliente_id, carga, url_sitio=None):
    """Manda el mail de lo que se acaba de cargar. Nunca levanta: un mail caído no rompe el pedido.

    Si la carga se sumó a un pedido pendiente del mismo día, va como Corrección de Pedido
    con el pedido completo; si no, como Pedido confirmado con lo cargado.
    """
    try:
        filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
        cliente = filas[0] if filas else {}
        email = (cliente.get("email") or "").strip()
        if not email:
            logger.info("Pedido %s sin mail de cliente: no se notifica", carga.get("id"))
            return False
        url = url_sitio or os.environ.get("PUBLIC_APP_URL") or URL_SITIO
        pedido = _pedido_en_base(client, carga)
        if _es_correccion(pedido, carga):
            enviar_email(email, asunto(pedido, correccion=True),
                         html_pedido_confirmado(cliente, pedido, url, agregados=carga["detalle"]))
        else:
            enviar_email(email, asunto(carga), html_pedido_confirmado(cliente, carga, url))
        return True
    except Exception:
        logger.exception("No se pudo mandar el mail del pedido %s", carga.get("id"))
        return False
