"""Mail de cuenta creada: le llega al cliente cuando Vladimir le arma la cuenta a mano.

Sale tanto del alta desde /admin/clientes/lista como de la skill /pedido. Usa las
mismas piezas que el mail de pedido (mail_pedido.py): Classic oscuro, títulos
pesados con punto coral, la card crema destacada y el sticker "Hola, soy Vlad".
"""
import html

from .mail_pedido import (
    URL_SITIO, _BLANCO, _BORDE, _CORAL, _CREMA, _MONO, _SANS, _SERIF, _TENUE, _TEXTO,
    _TINTA, _TINTA_TENUE, _ROJO_CREMA, _bloque, _boton, _documento, _etiqueta, _logo,
    _pie, _sticker, _tabla,
)

ASUNTO = "Tu cuenta en The Tech Room Arg"


def _encabezado():
    fila = (f'<tr><td valign="middle">{_logo()}</td>'
            f'<td valign="middle" align="right">{_etiqueta("Cuenta")}'
            f'<p style="margin:6px 0 0;font:700 17px/1 {_MONO};letter-spacing:0.5px;color:{_BLANCO}">Nueva</p></td></tr>')
    return f'<tr><td class="px" style="padding:24px 32px;border-bottom:1px solid {_BORDE}">{_tabla(fila)}</td></tr>'


def _hero(nombre):
    saludo = f"¡Hola, {html.escape(nombre)}!" if nombre else "¡Hola!"
    return _bloque(
        f'<p style="margin:0 0 22px;font:600 11px/1 {_MONO};letter-spacing:2px;text-transform:uppercase;color:{_CORAL}">'
        f'&#9679;&nbsp;&nbsp;Cuenta creada</p>'
        f'<p class="titulo" style="margin:0;font:800 58px/0.95 {_SANS};letter-spacing:-2.6px;color:{_BLANCO}">'
        f'Ya tenés tu cuenta<span style="color:{_CORAL}">.</span></p>'
        f'<p style="margin:26px 0 0;font:italic 27px/1.15 {_SERIF};color:{_TEXTO}">{saludo}</p>'
        f'<p style="margin:10px 0 0;font:400 16px/1.6 {_SANS};color:{_TENUE}">Te creé una cuenta en la web para que '
        f'puedas seguir tus pedidos, ver tus garantías y comprar más rápido la próxima vez.</p>',
        padding_top=44,
    )


def _credenciales(email, password):
    """La card crema destacada, como la de entrega en el mail de pedido."""
    dato = lambda etiqueta, valor, mono: (
        f'<p style="margin:0;font:600 11px/1.4 {_MONO};letter-spacing:2px;text-transform:uppercase;'
        f'color:{_TINTA_TENUE}">{etiqueta}</p>'
        f'<p style="margin:6px 0 0;font:{"700 22px/1.2 " + _MONO + ";letter-spacing:1px" if mono else "700 18px/1.3 " + _SANS};'
        f'color:{_TINTA};word-break:break-all">{html.escape(valor)}</p>'
    )
    return _bloque(_tabla(
        f'<tr><td style="background:{_CREMA};padding:26px 24px">'
        f'{dato("Email", email, False)}'
        f'<div style="height:1px;background:#d9d9d9;margin:18px 0"></div>'
        f'{dato("Contraseña temporal", password, True)}'
        f'<p style="margin:18px 0 0;font:600 14px/1.5 {_SANS};color:{_ROJO_CREMA}">'
        f'Al entrar por primera vez te va a pedir que elijas una contraseña nueva.</p>'
        f'</td></tr>'
    ), padding_top=40)


def html_cuenta_creada(nombre, email, password, url_sitio=URL_SITIO):
    url_sitio = (url_sitio or URL_SITIO).rstrip("/")
    cuerpo = "".join((
        _encabezado(),
        _hero((nombre or "").split(" ")[0]),
        _credenciales(email, password),
        _boton(f"{url_sitio}/login.html", "Entrar a mi cuenta"),
        _sticker("Cualquier duda, escribime y lo vemos."),
        _pie(url_sitio, "se creó una cuenta a tu nombre", ""),
    ))
    return _documento("Cuenta creada", "Tu cuenta está lista · adentro tenés tu contraseña temporal", cuerpo)
