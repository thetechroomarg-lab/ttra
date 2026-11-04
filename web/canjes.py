"""Plan Canje: solicitudes de iPhone usado como parte de pago.

El cliente (con cuenta) sube las fotos y elige modelo y capacidad de la tabla
(canje_tabla.json). Vlad ve la solicitud en /admin/canjes y la aprueba o la
rechaza. Al aprobar se emite un código de descuento de una sola vez por el
valor de la tabla: queda reservado/consumido como cualquier otro código (ver
cupones.py) y no vuelve a existir después de usarse.
"""
import html
import json
import math
import secrets
import string
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .mail_pedido import (
    URL_SITIO, _BLANCO, _BORDE, _CORAL, _MONO, _SANS, _TENUE, _TEXTO,
    _bloque, _boton, _documento, _etiqueta, _logo, _pie, _sticker, _tabla,
)

TABLA_PATH = Path(__file__).parent / "canje_tabla.json"
BUCKET = "recibos-series"
# Las siete fotos que pide la página, en el orden en que se muestran.
ROTULOS_FOTOS = (
    "Frente", "Reverso", "Lado izquierdo", "Lado derecho",
    "Borde superior", "Borde inferior", "Captura de batería",
)


class CanjeError(Exception):
    pass


def cargar_tabla():
    return json.loads(TABLA_PATH.read_text(encoding="utf-8"))


def buscar_equipo(equipo_id):
    return next((fila for fila in cargar_tabla() if fila["id"] == equipo_id), None)


def toma_como(canje):
    """Capacidad de la tabla cuyo precio se paga (1 TB y 2 TB se toman como 512 GB), o ''."""
    equipo = buscar_equipo(canje.get("equipo_id")) or {}
    return equipo.get("toma_como") or ""


def _ahora():
    return datetime.now(timezone.utc).isoformat()


def crear_solicitud(client, cliente_id, equipo, rutas_fotos, canje_id=None):
    fila = {
        "id": canje_id or str(uuid.uuid4()),
        "cliente_id": cliente_id,
        "equipo_id": equipo["id"],
        "modelo": equipo["modelo"],
        "capacidad": equipo["capacidad"],
        "valor_usd": int(equipo["valor_usd"]),
        "fotos": list(rutas_fotos),
        "estado": "pendiente",
        "codigo": None,
        "motivo_rechazo": None,
        "creado_en": _ahora(),
        "resuelto_en": None,
    }
    client.table("canjes").insert(fila).execute()
    return fila


def obtener(client, canje_id):
    filas = client.table("canjes").select("*").eq("id", canje_id).execute().data
    return filas[0] if filas else None


def listar(client):
    filas = client.table("canjes").select("*").execute().data or []
    return sorted(filas, key=lambda f: f.get("creado_en") or "", reverse=True)


def _codigo_unico(client):
    alfabeto = string.ascii_uppercase + string.digits
    for _ in range(12):
        codigo = "CANJE-" + "".join(secrets.choice(alfabeto) for _ in range(8))
        if not client.table("codigos_descuento").select("*").eq("code", codigo).execute().data:
            return codigo
    raise RuntimeError("No se pudo generar un código de canje único")


def aprobar(client, canje_id):
    """Pendiente -> aprobado, con un código de una sola vez por el valor de la
    tabla. Devuelve (canje, codigo). Solo se aprueba una vez."""
    canje = obtener(client, canje_id)
    if canje is None:
        raise CanjeError("No encontré la solicitud")
    if canje.get("estado") != "pendiente":
        raise CanjeError("Esta solicitud ya está resuelta")
    valor = int(canje["valor_usd"])
    codigo = _codigo_unico(client)
    client.table("codigos_descuento").insert({
        "cliente_id": canje["cliente_id"],
        "code": codigo,
        # Sin lista de productos + tope: vale para cualquier producto, por el
        # valor del equipo en total (igual que el premio de fidelidad).
        "productos": [],
        "descuento_usd": math.ceil(valor),
        "tope_total_usd": valor,
        "activo": True,
    }).execute()
    # Condicional: dos clics seguidos no emiten dos códigos.
    ganado = (
        client.table("canjes")
        .update({"estado": "aprobado", "codigo": codigo, "resuelto_en": _ahora()})
        .eq("id", canje_id).eq("estado", "pendiente").execute().data
    )
    if not ganado:
        client.table("codigos_descuento").delete().eq("code", codigo).execute()
        raise CanjeError("Esta solicitud ya está resuelta")
    return {**canje, "estado": "aprobado", "codigo": codigo}, codigo


def rechazar(client, canje_id, motivo=""):
    canje = obtener(client, canje_id)
    if canje is None:
        raise CanjeError("No encontré la solicitud")
    ganado = (
        client.table("canjes")
        .update({"estado": "rechazado", "motivo_rechazo": (motivo or "").strip()[:500] or None,
                 "resuelto_en": _ahora()})
        .eq("id", canje_id).eq("estado", "pendiente").execute().data
    )
    if not ganado:
        raise CanjeError("Esta solicitud ya está resuelta")
    return {**canje, "estado": "rechazado"}


def codigos_aprobados_de(client, cliente_id):
    """Códigos de canje del cliente (aprobados); cupones.disponible decide si
    todavía se pueden usar."""
    filas = client.table("canjes").select("*").eq("cliente_id", cliente_id).eq("estado", "aprobado").execute().data
    return [f["codigo"] for f in (filas or []) if f.get("codigo")]


# ---- Mails (mismo molde Classic oscuro que mail_pedido / mail_cuenta) ----

def _encabezado(etiqueta, valor):
    fila = (f'<tr><td valign="middle">{_logo()}</td>'
            f'<td valign="middle" align="right">{_etiqueta(etiqueta)}'
            f'<p style="margin:6px 0 0;font:700 17px/1 {_MONO};letter-spacing:0.5px;color:{_BLANCO}">{html.escape(valor)}</p></td></tr>')
    return f'<tr><td class="px" style="padding:24px 32px;border-bottom:1px solid {_BORDE}">{_tabla(fila)}</td></tr>'


def _titulo(kicker, titulo):
    return _bloque(
        f'<p style="margin:0 0 22px;font:600 11px/1 {_MONO};letter-spacing:2px;text-transform:uppercase;color:{_CORAL}">'
        f'&#9679;&nbsp;&nbsp;{html.escape(kicker)}</p>'
        f'<p class="titulo" style="margin:0;font:800 46px/1 {_SANS};letter-spacing:-2px;color:{_BLANCO}">'
        f'{html.escape(titulo)}<span style="color:{_CORAL}">.</span></p>',
        padding_top=44,
    )


def _renglones(pares):
    filas = "".join(
        f'<tr><td style="padding:10px 0;border-bottom:1px solid {_BORDE};font:600 11px/1.4 {_MONO};'
        f'letter-spacing:2px;text-transform:uppercase;color:{_TENUE}">{html.escape(k)}</td>'
        f'<td align="right" style="padding:10px 0;border-bottom:1px solid {_BORDE};font:600 15px/1.4 {_SANS};'
        f'color:{_TEXTO}">{html.escape(v)}</td></tr>'
        for k, v in pares
    )
    return _bloque(_tabla(filas), padding_top=32)


def _nombre(cliente):
    return f"{cliente.get('nombre') or ''} {cliente.get('apellido') or ''}".strip() or "Cliente"


def asunto_aviso(canje, cliente):
    return f"Plan Canje: {canje['modelo']} {canje['capacidad']} de {_nombre(cliente)}"


def html_aviso_vlad(canje, cliente, url_sitio=URL_SITIO):
    url_sitio = (url_sitio or URL_SITIO).rstrip("/")
    cuerpo = "".join((
        _encabezado("Plan Canje", "Solicitud"),
        _titulo("Nueva solicitud", f"{canje['modelo']} {canje['capacidad']}"),
        _renglones([
            ("Cliente", _nombre(cliente)),
            ("Celular", cliente.get("celular") or "—"),
            ("Email", cliente.get("email") or "—"),
            ("Valor de tabla", f"US$ {int(canje['valor_usd']):,}".replace(",", ".")
             + (f" (precio de {toma_como(canje)})" if toma_como(canje) else "")),
            ("Fotos adjuntas", " · ".join(ROTULOS_FOTOS)),
        ]),
        _boton(f"{url_sitio}/admin/canjes", "Aprobar o rechazar"),
    ))
    return _documento("Plan Canje", "Nueva solicitud con fotos adjuntas", cuerpo)


def asunto_resultado(canje):
    return ("Aprobé tu iPhone para el Plan Canje" if canje["estado"] == "aprobado"
            else "Sobre tu iPhone del Plan Canje")


def html_resultado_cliente(canje, cliente, url_sitio=URL_SITIO):
    url_sitio = (url_sitio or URL_SITIO).rstrip("/")
    nombre = (cliente.get("nombre") or "").strip()
    saludo = f"Hola, {html.escape(nombre)}." if nombre else "Hola."
    if canje["estado"] == "aprobado":
        valor = f"US$ {int(canje['valor_usd']):,}".replace(",", ".")
        cuerpo = "".join((
            _encabezado("Plan Canje", "Aprobado"),
            _titulo("Aprobado", "Tomo tu iPhone"),
            _bloque(
                f'<p style="margin:0;font:400 16px/1.6 {_SANS};color:{_TENUE}">{saludo} Aprobé tu '
                f'{html.escape(canje["modelo"])} {html.escape(canje["capacidad"])}. Tenés un código de '
                f'<strong style="color:{_BLANCO}">{valor}</strong> de descuento para tu próxima compra. '
                f'Sirve una sola vez y se aplica solo cuando abrís el carrito.</p>'
                f'<p style="margin:22px 0 0;font:700 24px/1.2 {_MONO};letter-spacing:1px;color:{_BLANCO}">'
                f'{html.escape(canje["codigo"])}</p>', padding_top=28),
            _boton(f"{url_sitio}/catalogo", "Elegir mi equipo"),
            _sticker("Cualquier duda, escribime y lo vemos."),
            _pie(url_sitio, "aprobé tu equipo del Plan Canje", ""),
        ))
        return _documento("Plan Canje aprobado", f"Tenés {valor} de descuento", cuerpo)
    motivo = (canje.get("motivo_rechazo") or "").strip()
    texto = (f'{saludo} Revisé las fotos de tu {html.escape(canje["modelo"])} {html.escape(canje["capacidad"])} '
             f'y esta vez no lo puedo tomar.')
    if motivo:
        texto += f' Motivo: {html.escape(motivo)}.'
    cuerpo = "".join((
        _encabezado("Plan Canje", "Resuelto"),
        _titulo("Plan Canje", "No lo puedo tomar"),
        _bloque(f'<p style="margin:0;font:400 16px/1.6 {_SANS};color:{_TENUE}">{texto}</p>', padding_top=28),
        _sticker("Si querés, escribime y lo charlamos."),
        _pie(url_sitio, "revisé tu equipo del Plan Canje", ""),
    ))
    return _documento("Plan Canje", "Sobre tu iPhone del Plan Canje", cuerpo)
