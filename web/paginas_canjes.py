"""Pestaña "Canjes" del panel de admin (/admin/clientes#canjes).

Devuelve solo el fragmento (filtros + tarjetas): el panel lo pide por fetch,
igual que la pestaña Borrados. Los modales y los handlers viven en
ui/admin_secciones.html y ui/admin_canjes.js.html.
"""
import html

from web import canjes
from web.ui_helpers import _formatear_fecha_ar


def _tarjeta(canje, cliente):
    fecha, _dia, hora = _formatear_fecha_ar(canje.get("creado_en"))
    nombre = f"{cliente.get('nombre') or ''} {cliente.get('apellido') or ''}".strip() or "Cliente"
    equipo = f"{canje['modelo']} {canje['capacidad']}"
    estado = canje.get("estado") or "pendiente"
    valor = f"{int(canje['valor_usd']):,}".replace(",", ".")
    ident = html.escape(canje["id"])
    rotulos = canjes.ROTULOS_FOTOS
    # Una miniatura por foto guardada (una solicitud vieja puede tener menos que las actuales).
    fotos = "".join(
        f'<button type="button" class="canje-foto" data-src="/admin/canjes/{ident}/foto/{i}" '
        f'data-rotulo="{html.escape(rotulos[i] if i < len(rotulos) else f"Foto {i + 1}")}">'
        f'<img loading="lazy" src="/admin/canjes/{ident}/foto/{i}" '
        f'alt="{html.escape(rotulos[i] if i < len(rotulos) else f"Foto {i + 1}")}">'
        f'<span>{html.escape(rotulos[i] if i < len(rotulos) else f"Foto {i + 1}")}</span></button>'
        for i in range(len(canje.get("fotos") or []))
    )
    if estado == "pendiente":
        pie = ('<div class="canje-acciones"><button type="button" class="canje-rechazar">Rechazar</button>'
               '<button type="button" class="canje-aprobar">Aprobar</button></div>')
    elif estado == "aprobado":
        pie = f'<p class="canje-codigo">{html.escape(canje.get("codigo") or "")}</p>'
    else:
        motivo = html.escape(canje.get("motivo_rechazo") or "")
        pie = f'<p class="canje-datos">Motivo: {motivo}</p>' if motivo else ""
    etiqueta = {"pendiente": "Pendiente", "aprobado": "Aprobado", "rechazado": "Rechazado"}.get(estado, estado)
    return (
        f'<article class="canje" data-id="{ident}" data-estado="{html.escape(estado)}" '
        f'data-cliente="{html.escape(nombre)}" data-valor="{int(canje["valor_usd"])}" '
        f'data-equipo="{html.escape(equipo)}"{"" if estado == "pendiente" else " hidden"}>'
        f'<div class="canje-cabecera"><div><h3>{html.escape(equipo)}</h3>'
        f'<p class="canje-datos">{html.escape(nombre)} · {html.escape(cliente.get("celular") or "sin celular")} · '
        f'{html.escape(cliente.get("email") or "sin email")}<br>{fecha} {hora}</p>'
        f'<span class="canje-estado {html.escape(estado)}">{etiqueta}</span></div>'
        f'<span class="canje-valor">US$ {valor}</span></div>'
        f'<div class="canje-fotos">{fotos}</div>{pie}</article>'
    )


def html_fragmento(solicitudes, clientes):
    pendientes = sum(1 for c in solicitudes if c.get("estado") == "pendiente")
    tarjetas = "".join(_tarjeta(c, clientes.get(c["cliente_id"], {})) for c in solicitudes)
    return (
        '<div class="canjes-filtros">'
        f'<button type="button" data-estado="pendiente" aria-pressed="true">Pendientes ({pendientes})</button>'
        '<button type="button" data-estado="aprobado" aria-pressed="false">Aprobados</button>'
        '<button type="button" data-estado="rechazado" aria-pressed="false">Rechazados</button></div>'
        f'{tarjetas}'
        f'<p class="canjes-vacio" id="canjes-vacio"{" hidden" if pendientes else ""}>No hay solicitudes en esta lista.</p>'
    )
