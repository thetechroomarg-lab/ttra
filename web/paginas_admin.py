"""Paginas HTML del panel de admin de clientes.

Extraido de app.py: el codigo de las paginas es identico, solo cambio el
decorador de @app.get a @router.get.
"""

import html
import json
from datetime import date, datetime
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from web import entregas
from web.ui_helpers import (
    CADETE_SLUG,
    _ADMIN_CLIENTES_ESTILO,
    _ADMIN_CLIENTES_PWA_HEAD,
    _ADMIN_CLIENTES_PWA_SCRIPT,
    _ICONO_OJO,
    _ICONO_TACHO,
    _clientes_admin_activo,
    _formatear_entero_ar,
    _formatear_fecha_ar,
    _json_para_script,
    _query_maps,
    _ranking_productos_consultados,
)

def get_client():
    """Resuelve el cliente de Supabase a traves de web.app en cada llamada.

    Indirecto a proposito: el acceso a datos sigue centralizado en app.py, asi
    que un reemplazo de app.get_client (tests, o cualquier swap en runtime)
    tambien aplica a estas paginas.
    """
    from web import app as _app

    return _app.get_client()


router = APIRouter()


@router.get("/admin/clientes", response_class=HTMLResponse)
def admin_clientes(request: Request):
    return _admin_clientes_pagina(request, mostrar_clientes=False)


@router.get("/admin/clientes/lista", response_class=HTMLResponse)
def admin_clientes_lista(request: Request):
    return _admin_clientes_pagina(request, mostrar_clientes=True)


def _admin_clientes_pagina(request: Request, mostrar_clientes: bool):
    if not _clientes_admin_activo(request):
        return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Clientes — Ingresar</title>{_ADMIN_CLIENTES_PWA_HEAD}{_ADMIN_CLIENTES_ESTILO}</head><body>
<div class="tarjeta">
  <h1>Panel de clientes</h1>
  <p id="err" class="error" style="display:none"></p>
  <input id="pass" type="password" placeholder="Contraseña" autofocus>
  <button id="btn">Ingresar</button>
</div>
<div class="modal-series" id="modal-series" hidden><div class="modal-series-contenido" role="dialog" aria-modal="true" aria-labelledby="series-titulo"><h2 id="series-titulo">Fotos de números de serie</h2><p>Sacá o seleccioná todas las fotos antes de enviar el recibo.</p><div id="series-fotos" class="series-fotos"></div><div class="series-acciones"><button id="series-agregar" type="button">Agregar foto</button><button id="series-cancelar" type="button">Cancelar</button><button id="series-enviar" type="button">Enviar recibo</button></div></div></div>
<script>
document.getElementById("btn").addEventListener("click", async () => {{
  const r = await fetch("/admin/clientes/login", {{
    method: "POST", headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{password: document.getElementById("pass").value}})
  }});
  if (r.ok) {{ location.reload(); return; }}
  const err = document.getElementById("err");
  err.textContent = "Contraseña incorrecta";
  err.style.display = "block";
}});
document.getElementById("pass").addEventListener("keydown", (e) => {{
  if (e.key === "Enter") document.getElementById("btn").click();
}});
</script>
{_ADMIN_CLIENTES_PWA_SCRIPT}
</body></html>"""

    client = get_client()
    filas_clientes = client.table("clientes").select("*").execute().data
    clientes = [
        {
            "id": c.get("id") or "",
            "nombre": f"{c.get('nombre') or ''} {c.get('apellido') or ''}".strip(),
            "celular": c.get("celular") or "",
            "email": c.get("email") or "",
            "provincia": c.get("provincia") or "Sin especificar",
            "fecha": c.get("creado_en") or "",
            "tiene_cuenta": bool(c.get("auth_id")),
            "tipo_cliente": "mayorista" if c.get("tipo_cliente") == "mayorista" else "minorista",
            "direccion": c.get("direccion") or "",
        }
        for c in filas_clientes
    ]
    clientes.sort(key=lambda r: r.get("fecha", ""), reverse=True)
    clientes_por_id = {cliente["id"]: cliente for cliente in clientes}
    fecha_hoy = entregas.ahora_argentina().date().isoformat()
    pedidos = [] if mostrar_clientes else client.table("pedidos").select("*").execute().data
    tareas = [] if mostrar_clientes else client.table("tareas_entrega").select("*").execute().data
    tareas_hoy = [
        tarea for tarea in tareas
        if tarea.get("fecha_entrega") == fecha_hoy and not tarea.get("completada_en")
    ]
    tareas_hoy.sort(key=lambda tarea: int(tarea.get("orden") or 0))
    pedidos_hoy = [
        pedido for pedido in pedidos
        if pedido.get("fecha_entrega") == fecha_hoy and not pedido.get("recibo_enviado_en")
    ]
    fecha_historial = request.query_params.get("fecha_pedidos") or fecha_hoy
    try:
        fecha_historial = date.fromisoformat(fecha_historial).isoformat()
    except ValueError:
        fecha_historial = fecha_hoy
    pedidos_historial = [
        pedido for pedido in pedidos
        if pedido.get("fecha_entrega") == fecha_historial
        and (pedido.get("recibo_enviado_en") or fecha_historial != fecha_hoy)
    ]
    tareas_historial = [
        tarea for tarea in tareas
        if tarea.get("fecha_entrega") == fecha_historial
        and (tarea.get("completada_en") or fecha_historial != fecha_hoy)
    ]

    def _descripcion_pedido(pedido):
        detalle = pedido.get("detalle") or []
        if detalle:
            return " | ".join(
                f"{item.get('nombre', '')} x{item.get('cantidad', 0)}"
                f" · Proveedor: {item.get('proveedor') or 'Proveedor no identificado'}"
                for item in detalle
            )
        return " | ".join(pedido.get("productos") or [])

    def _boton_recibo(pedido):
        pedido_id = html.escape(pedido.get("id", ""))
        if not pedido.get("detalle") or pedido.get("total_usd") is None:
            return ('<button class="btn-enviar-recibo" type="button" '
                    f'data-id="{pedido_id}" disabled title="Falta detalle histórico">Enviar recibo</button>')
        return (f'<button class="btn-enviar-recibo" type="button" '
                f'data-id="{pedido_id}">Enviar recibo</button>')

    def _control_derivar(entidad_id, tipo, derivado):
        if derivado:
            return f'<button class="btn-quitar-derivacion" type="button" data-id="{entidad_id}" data-tipo="{tipo}">Derivado a Alejo</button>'
        return f'<button class="btn-derivar-entrega" type="button" data-id="{entidad_id}" data-tipo="{tipo}">Derivar a Alejo</button>'

    def _controles_entrega(pedido):
        pedido_id = html.escape(pedido.get("id", ""))
        fecha = html.escape(pedido.get("fecha_entrega", ""))
        direccion = (pedido.get("direccion_entrega") or "").strip()
        boton_direcciones = (
            f'<button class="btn-direcciones" type="button" '
            f'data-maps="https://www.google.com/maps/search/?{html.escape(urlencode({"api": 1, "query": _query_maps(direccion, pedido.get("lat"), pedido.get("lng"))}))}">Vamos</button>'
            f'<button class="btn-editar-direccion" type="button" data-id="{pedido_id}" data-direccion="{html.escape(direccion)}">Editar dirección</button>'
            if direccion else f'<button class="btn-agregar-direccion" type="button" data-id="{pedido_id}">Agregar dirección</button>'
        )
        return (
            '<div class="pedido-acciones">'
            f'{boton_direcciones}'
            f'{_boton_recibo(pedido)}'
            f'<button class="btn-editar-entrega" type="button" data-id="{pedido_id}" data-fecha="{fecha}" data-tipo="pedido">Editar fecha</button>'
            f'{_control_derivar(pedido_id, "pedido", pedido.get("asignado_a") == CADETE_SLUG)}'
            f'<button class="btn-eliminar-entrega" type="button" data-id="{pedido_id}">Eliminar entrega</button>'
            '</div>'
        )

    def _acciones_tarea(tarea):
        tarea_id = html.escape(tarea.get("id", ""))
        fecha = html.escape(tarea.get("fecha_entrega", ""))
        direccion = (tarea.get("direccion") or "").strip()
        boton_direcciones = (
            f'<button class="btn-direcciones" type="button" '
            f'data-maps="https://www.google.com/maps/search/?{html.escape(urlencode({"api": 1, "query": direccion}))}">Vamos</button>'
            f'<button class="btn-editar-direccion-tarea" type="button" data-id="{tarea_id}" data-direccion="{html.escape(direccion)}">Editar dirección</button>'
            if direccion else f'<button class="btn-agregar-direccion-tarea" type="button" data-id="{tarea_id}">Agregar dirección</button>'
        )
        return (
            '<div class="pedido-acciones">'
            f'{boton_direcciones}'
            f'<button class="btn-completar-tarea" type="button" data-id="{tarea_id}">Completado</button>'
            f'<button class="btn-editar-tarea" type="button" data-id="{tarea_id}" data-fecha="{fecha}" data-tipo="tarea">Editar fecha</button>'
            f'{_control_derivar(tarea_id, "tarea", tarea.get("asignado_a") == CADETE_SLUG)}'
            f'<button class="btn-eliminar-tarea" type="button" data-id="{tarea_id}">Eliminar tarea</button>'
            '</div>'
        )

    def _tarjeta_tarea(tarea):
        tarea_id = html.escape(tarea.get("id", ""))
        nombre_cliente = tarea.get("cliente_nombre") or clientes_por_id.get(tarea.get("cliente_id"), {}).get("nombre", "")
        detalle_cliente = f'<br><span>Cliente: {html.escape(nombre_cliente)}</span>' if nombre_cliente else ""
        return (
            f'<div class="pedido-hoy" data-tipo-entrega="tarea" data-entrega-id="{tarea_id}"><button class="arrastrar-entrega" draggable="true" type="button" aria-label="Arrastrar tarea">≡</button><div class="pedido-hoy-detalle">'
            f'<strong>Tarea: {html.escape(tarea.get("titulo") or "")}</strong>'
            f'{detalle_cliente}<br><span>{html.escape(tarea.get("nota") or "")}</span></div>'
            f'{_acciones_tarea(tarea)}</div>'
        )

    def _acciones_recibo_historial(pedido):
        if not pedido.get("recibo_enviado_en"):
            return ""
        pedido_id = html.escape(pedido.get("id", ""))
        ojo = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
               'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z"/><circle cx="12" cy="12" r="3"/></svg>')
        reenvio = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                   'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 0 1-15.5 6.2"/><path d="M3 12A9 9 0 0 1 18.5 5.8"/><path d="M3 17v-5h5"/><path d="M21 7v5h-5"/></svg>')
        tacho = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>')
        return (f'<span class="acciones-recibo"><a class="btn-ver-recibo-pdf" href="/admin/pedidos/{pedido_id}/recibo.pdf" target="_blank" title="Ver PDF" aria-label="Ver PDF del recibo">{ojo}</a>'
                f'<button class="btn-reenviar-recibo" type="button" data-id="{pedido_id}" title="Reenviar recibo" aria-label="Reenviar recibo">{reenvio}</button>'
                f'<button class="btn-eliminar-historial" type="button" data-id="{pedido_id}" title="Eliminar del historial" aria-label="Eliminar del historial">{tacho}</button></span>')

    def _tarjeta_pedido(pedido):
        return (
            f'<div class="pedido-hoy" data-pedido-id="{html.escape(pedido.get("id", ""))}" data-tipo-entrega="pedido" data-entrega-id="{html.escape(pedido.get("id", ""))}"><button class="arrastrar-entrega" draggable="true" type="button" aria-label="Arrastrar pedido">≡</button><div class="pedido-hoy-detalle"><strong>{html.escape(clientes_por_id.get(pedido.get("cliente_id"), {}).get("nombre", "Cliente"))}</strong> · '
            f'{html.escape(clientes_por_id.get(pedido.get("cliente_id"), {}).get("celular", "—"))}<br><span>{html.escape(_descripcion_pedido(pedido))} · U$D {_formatear_entero_ar(pedido.get("total_usd"))}</span></div>'
            f'{_controles_entrega(pedido)}</div>'
        )

    entregas_pendientes = [
        ("pedido", pedido, pedido.get("orden_entrega")) for pedido in pedidos_hoy
    ] + [
        ("tarea", tarea, tarea.get("orden")) for tarea in tareas_hoy
    ]
    if entregas_pendientes and all(orden is not None for _, _, orden in entregas_pendientes):
        entregas_pendientes.sort(key=lambda entrega: int(entrega[2]))
    tarjetas_pendientes_hoy = [
        _tarjeta_pedido(entrega) if tipo == "pedido" else _tarjeta_tarea(entrega)
        for tipo, entrega, _ in entregas_pendientes
    ]
    if tarjetas_pendientes_hoy:
        pedidos_hoy_html = "".join(tarjetas_pendientes_hoy)
    else:
        pedidos_hoy_html = '<p class="vacio">No hay pedidos pendientes para hoy.</p>'
    if pedidos_historial or tareas_historial:
        def _pedido_historial_html(pedido):
            cliente_pedido = clientes_por_id.get(pedido.get("cliente_id"), {})
            nombre_cliente = (
                f"{cliente_pedido.get('nombre', '')} {cliente_pedido.get('apellido', '')}".strip()
                or "Cliente"
            )
            descripcion = _descripcion_pedido(pedido)
            busqueda = html.escape(f"{nombre_cliente} {descripcion}".lower())
            if pedido.get("recibo_enviado_en"):
                estado = "Recibo enviado originalmente: " + html.escape(pedido.get("recibo_emitido_en") or pedido.get("recibo_enviado_en", ""))
                acciones = _acciones_recibo_historial(pedido)
            else:
                estado = "Pendiente de recibo" if pedido.get("detalle") and pedido.get("total_usd") is not None else "Sin detalle histórico"
                acciones = _controles_entrega(pedido)
            observaciones = (pedido.get("observaciones_cadete") or "").strip()
            detalle_obs = (
                f'<br><span class="observacion-cadete">Observaciones: {html.escape(observaciones)}</span>'
                if observaciones else ""
            )
            return (
                f'<div class="pedido-historico" data-busqueda-historial="{busqueda}"><strong>{html.escape(nombre_cliente)}</strong> · '
                f'{html.escape(descripcion)} · U$D {_formatear_entero_ar(pedido.get("total_usd"))}<br><span class="estado-recibo">'
                f'{estado}</span>{detalle_obs}{acciones}</div>'
            )

        def _tarea_historial_html(tarea):
            nombre_cliente = tarea.get("cliente_nombre") or clientes_por_id.get(tarea.get("cliente_id"), {}).get("nombre", "")
            titulo = tarea.get("titulo") or "Tarea sin título"
            nota = tarea.get("nota") or ""
            tarea_id = html.escape(tarea.get("id", ""))
            busqueda = html.escape(f"{nombre_cliente} {titulo} {nota}".lower())
            detalle_cliente = f" · {html.escape(nombre_cliente)}" if nombre_cliente else ""
            detalle_nota = f" · {html.escape(nota)}" if nota else ""
            tacho = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
                     'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>')
            if tarea.get("completada_en"):
                estado = f'Completada el {html.escape(tarea.get("completada_en"))}'
                titulo_tarjeta = "Tarea completada"
                acciones = f'<button class="btn-eliminar-historial-tarea" type="button" data-id="{tarea_id}" title="Eliminar del historial" aria-label="Eliminar del historial">{tacho}</button>'
            else:
                estado = "Pendiente"
                titulo_tarjeta = "Tarea"
                acciones = _acciones_tarea(tarea)
            observaciones = (tarea.get("observaciones_cadete") or "").strip()
            detalle_obs = (
                f'<br><span class="observacion-cadete">Observaciones: {html.escape(observaciones)}</span>'
                if observaciones else ""
            )
            return (
                f'<div class="pedido-historico" data-busqueda-historial="{busqueda}"><strong>{titulo_tarjeta}: {html.escape(titulo)}</strong>'
                f'{detalle_cliente}{detalle_nota}<br><span class="estado-recibo">{estado}</span>'
                f'{detalle_obs}{acciones}</div>'
            )

        pedidos_historial_html = "".join(
            [_pedido_historial_html(pedido) for pedido in pedidos_historial]
            + [_tarea_historial_html(tarea) for tarea in tareas_historial]
        )
    else:
        pedidos_historial_html = '<p class="vacio">No hay pedidos para esta fecha.</p>'

    clientes_tarea_json = _json_para_script(
        [
            {"id": cliente["id"], "nombre": cliente["nombre"], "direccion": cliente.get("direccion") or ""}
            for cliente in sorted(clientes, key=lambda cliente: cliente["nombre"].casefold())
        ]
    )
    pendientes_hoy_seccion_html = (
        f'<section class="pedidos-hoy"><div class="pedidos-hoy-header"><h2>Pedidos pendientes para hoy ({len(pedidos_hoy) + len(tareas_hoy)})</h2>'
        f'<button id="tarea-cerrar" class="tarea-cerrar" type="button" hidden aria-label="Cerrar formulario de tarea" title="Cerrar">✕</button></div>'
        f'<form id="form-tarea-entrega" class="form-tarea-entrega"><button id="tarea-toggle" class="tarea-toggle" type="button">+ Nueva tarea</button>'
        f'<div id="tarea-campos" class="tarea-campos" hidden><input id="tarea-titulo" required maxlength="200" placeholder="Nueva tarea">'
        f'<input id="tarea-fecha" type="date" required value="{fecha_hoy}" title="Fecha de la tarea">'
        f'<div class="tarea-direccion-wrap"><input id="tarea-cliente-busqueda" required maxlength="200" placeholder="Cliente" autocomplete="off"><input type="hidden" id="tarea-cliente"><ul id="tarea-cliente-sugerencias" class="tarea-direccion-sugerencias" role="listbox" aria-label="Clientes" hidden></ul></div>'
        f'<input id="tarea-nota" maxlength="1000" placeholder="Nota opcional"><div class="tarea-direccion-wrap"><input id="tarea-direccion" maxlength="500" placeholder="Agregar dirección" autocomplete="street-address"><ul id="tarea-direccion-sugerencias" class="tarea-direccion-sugerencias" role="listbox" aria-label="Sugerencias de dirección" hidden></ul></div>'
        f'<label class="tarea-enviar-alejo"><input type="checkbox" id="tarea-enviar-alejo"> Enviar a Alejo</label>'
        f'<button type="submit">Agregar tarea</button></div></form>'
        f'{pedidos_hoy_html}</section>'
        if fecha_historial == fecha_hoy else ""
    )

    if not mostrar_clientes:
        return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Pedidos y recibos</title>{_ADMIN_CLIENTES_PWA_HEAD}{_ADMIN_CLIENTES_ESTILO}</head><body>
<div class="panel">
  <div class="panel-header">
    <h1>Pedidos y recibos</h1>
    <div class="panel-header-acciones"><a class="btn-clientes" href="/admin/clientes/lista">Clientes</a><button id="salir">Cerrar sesión</button></div>
  </div>
  <section class="historial-pedidos"><h2>Historial de pedidos</h2><input id="filtro-historial-pedidos" type="search" placeholder="Buscar por cliente o producto"><label for="fecha-historial-pedidos">Fecha de consulta</label><input id="fecha-historial-pedidos" type="date" value="{fecha_historial}">{pedidos_historial_html}</section>
  {pendientes_hoy_seccion_html}
</div>
<div class="modal-series" id="modal-series" hidden><div class="modal-series-contenido" role="dialog" aria-modal="true" aria-labelledby="series-titulo"><h2 id="series-titulo">Fotos de números de serie</h2><p>Sacá o seleccioná todas las fotos antes de enviar el recibo.</p><div id="series-fotos" class="series-fotos"></div><div class="series-acciones"><button id="series-agregar" type="button">Agregar foto</button><button id="series-cancelar" type="button">Cancelar</button><button id="series-enviar" type="button">Enviar recibo</button></div></div></div>
<div class="modal-direccion" id="modal-direccion" hidden><div class="modal-direccion-contenido" role="dialog" aria-modal="true" aria-labelledby="direccion-titulo"><h2 id="direccion-titulo">Dirección de entrega</h2><div class="tarea-direccion-wrap"><input id="direccion-entrega-admin" type="text" maxlength="500" placeholder="Ej.: Av. Colón 123, Córdoba" autocomplete="off"><ul id="direccion-entrega-admin-sugerencias" class="tarea-direccion-sugerencias" role="listbox" aria-label="Sugerencias de dirección" hidden></ul></div><div class="direccion-acciones"><button id="direccion-cancelar" type="button">Cancelar</button><button id="direccion-guardar" type="button">Guardar dirección</button></div></div></div>
<div class="modal-fecha-entrega" id="modal-fecha-entrega" hidden><div class="modal-fecha-contenido" role="dialog" aria-modal="true" aria-labelledby="fecha-entrega-titulo"><h2 id="fecha-entrega-titulo">Editar fecha de entrega</h2><input id="fecha-entrega-admin" type="date"><div class="fecha-entrega-acciones"><button id="fecha-entrega-cancelar" type="button">Cancelar</button><button id="fecha-entrega-guardar" type="button">Guardar fecha</button></div></div></div>
<script>
document.getElementById("salir").addEventListener("click", async () => {{
  await fetch("/admin/clientes/logout", {{ method: "POST" }});
  location.reload();
}});
async function comprimirFotoSerie(archivo) {{
  const imagen = await createImageBitmap(archivo);
  const escala = Math.min(1, 1600 / Math.max(imagen.width, imagen.height));
  const lienzo = document.createElement("canvas");
  lienzo.width = Math.round(imagen.width * escala); lienzo.height = Math.round(imagen.height * escala);
  lienzo.getContext("2d").drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
  const blob = await new Promise((ok) => lienzo.toBlob(ok, "image/jpeg", .75));
  return new File([blob], "numero-serie.jpg", {{ type:"image/jpeg" }});
}}
let pedidoReciboActivo = null;
let fotosSerie = [];
const modalSeries = document.getElementById("modal-series");
const vistaFotosSerie = document.getElementById("series-fotos");
function renderFotosSerie() {{
  vistaFotosSerie.innerHTML = fotosSerie.map((foto, indice) => `<div class="serie-foto"><img src="${{URL.createObjectURL(foto)}}" alt="Foto de número de serie ${{indice + 1}}"><button type="button" data-indice="${{indice}}" aria-label="Quitar foto">×</button></div>`).join("");
  vistaFotosSerie.querySelectorAll("button").forEach((boton) => boton.addEventListener("click", () => {{ fotosSerie.splice(Number(boton.dataset.indice), 1); renderFotosSerie(); }}));
}}
function agregarFotoSerie() {{
  const selector = Object.assign(document.createElement("input"), {{ type:"file", accept:"image/*", capture:"environment" }});
  selector.addEventListener("change", async () => {{ if (selector.files?.[0]) {{ fotosSerie.push(await comprimirFotoSerie(selector.files[0])); renderFotosSerie(); }} }});
  selector.click();
}}
document.querySelectorAll(".btn-enviar-recibo").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    pedidoReciboActivo = btn; fotosSerie = []; renderFotosSerie(); modalSeries.hidden = false;
  }});
}});
document.getElementById("series-agregar").addEventListener("click", agregarFotoSerie);
document.getElementById("series-cancelar").addEventListener("click", () => {{ modalSeries.hidden = true; }});
document.getElementById("series-enviar").addEventListener("click", async () => {{
  if (!pedidoReciboActivo) return;
  const boton = document.getElementById("series-enviar"); boton.disabled = true; boton.textContent = "Enviando...";
  const adjuntos = new FormData(); fotosSerie.forEach((foto) => adjuntos.append("fotos", foto));
  const r = await fetch(`/admin/pedidos/${{pedidoReciboActivo.dataset.id}}/recibo`, {{ method:"POST", body:adjuntos }});
  const respuesta = await r.json().catch(() => ({{}}));
  if (!r.ok) {{ alert(respuesta.error || "No se pudo enviar el recibo."); boton.disabled = false; boton.textContent = "Enviar recibo"; return; }}
  location.reload();
}});
document.querySelectorAll(".btn-reenviar-recibo").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Reenviar el recibo original por email?")) return;
    btn.disabled = true;
    const r = await fetch(`/admin/pedidos/${{btn.dataset.id}}/recibo`, {{ method: "POST" }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo reenviar el recibo."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
let pedidoDireccionActivo = null;
let tareaDireccionActiva = null;
const modalDireccion = document.getElementById("modal-direccion");
const campoDireccion = document.getElementById("direccion-entrega-admin");
document.querySelectorAll(".btn-agregar-direccion").forEach((btn) => {{
  btn.addEventListener("click", () => {{
    pedidoDireccionActivo = btn.dataset.id;
    tareaDireccionActiva = null;
    campoDireccion.value = "";
    modalDireccion.hidden = false;
    document.getElementById("direccion-entrega-admin-sugerencias").hidden = true;
    campoDireccion.focus();
  }});
}});
document.querySelectorAll(".btn-agregar-direccion-tarea").forEach((btn) => {{
  btn.addEventListener("click", () => {{
    tareaDireccionActiva = btn.dataset.id;
    pedidoDireccionActivo = null;
    campoDireccion.value = "";
    modalDireccion.hidden = false;
    document.getElementById("direccion-entrega-admin-sugerencias").hidden = true;
    campoDireccion.focus();
  }});
}});
document.querySelectorAll(".btn-direcciones").forEach((btn) => {{
  btn.addEventListener("click", () => {{ window.open(btn.dataset.maps, "_blank", "noopener"); }});
}});
document.querySelectorAll(".btn-editar-direccion").forEach((btn) => {{
  btn.addEventListener("click", () => {{
    pedidoDireccionActivo = btn.dataset.id;
    tareaDireccionActiva = null;
    campoDireccion.value = btn.dataset.direccion || "";
    modalDireccion.hidden = false;
    document.getElementById("direccion-entrega-admin-sugerencias").hidden = true;
    campoDireccion.focus();
  }});
}});
document.querySelectorAll(".btn-editar-direccion-tarea").forEach((btn) => {{
  btn.addEventListener("click", () => {{
    tareaDireccionActiva = btn.dataset.id;
    pedidoDireccionActivo = null;
    campoDireccion.value = btn.dataset.direccion || "";
    modalDireccion.hidden = false;
    document.getElementById("direccion-entrega-admin-sugerencias").hidden = true;
    campoDireccion.focus();
  }});
}});
document.getElementById("direccion-cancelar").addEventListener("click", () => {{
  pedidoDireccionActivo = null;
  tareaDireccionActiva = null;
  modalDireccion.hidden = true;
}});
document.getElementById("direccion-guardar").addEventListener("click", async () => {{
  const direccion = campoDireccion.value.trim();
  if (!direccion) {{ campoDireccion.focus(); return; }}
  const boton = document.getElementById("direccion-guardar");
  boton.disabled = true;
  const destino = tareaDireccionActiva
    ? `/admin/tareas-entrega/${{tareaDireccionActiva}}/direccion`
    : `/admin/pedidos/${{pedidoDireccionActivo}}/direccion`;
  const r = await fetch(destino, {{
    method: "PUT", headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{direccion_entrega: direccion}}),
  }});
  const datos = await r.json().catch(() => ({{}}));
  if (!r.ok) {{ alert(datos.error || "No se pudo guardar la dirección."); boton.disabled = false; return; }}
  location.reload();
}});
let fechaEntregaActiva = null;
const modalFechaEntrega = document.getElementById("modal-fecha-entrega");
const campoFechaEntrega = document.getElementById("fecha-entrega-admin");
document.querySelectorAll(".btn-editar-entrega, .btn-editar-tarea").forEach((btn) => {{
  btn.addEventListener("click", () => {{
    fechaEntregaActiva = {{ tipo: btn.dataset.tipo, id: btn.dataset.id, fecha: btn.dataset.fecha }};
    campoFechaEntrega.value = btn.dataset.fecha;
    modalFechaEntrega.hidden = false;
    campoFechaEntrega.focus();
  }});
}});
document.getElementById("fecha-entrega-cancelar").addEventListener("click", () => {{
  fechaEntregaActiva = null;
  modalFechaEntrega.hidden = true;
}});
document.getElementById("fecha-entrega-guardar").addEventListener("click", async () => {{
  const fecha = campoFechaEntrega.value;
  if (!fecha) {{ campoFechaEntrega.focus(); return; }}
  if (!fechaEntregaActiva || fecha === fechaEntregaActiva.fecha) {{ modalFechaEntrega.hidden = true; return; }}
  const boton = document.getElementById("fecha-entrega-guardar");
  boton.disabled = true;
  const tabla = fechaEntregaActiva.tipo === "tarea" ? "tareas-entrega" : "pedidos";
  const r = await fetch(`/admin/${{tabla}}/${{fechaEntregaActiva.id}}/fecha-entrega`, {{
    method: "PUT", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{fecha_entrega: fecha}}),
  }});
  const datos = await r.json().catch(() => ({{}}));
  if (!r.ok) {{
    alert(datos.error || "No se pudo editar la fecha de entrega.");
    boton.disabled = false;
    return;
  }}
  location.reload();
}});
document.querySelectorAll(".btn-eliminar-entrega").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Eliminar esta entrega? Esta acción no se puede deshacer.")) return;
    btn.disabled = true;
    const r = await fetch(`/admin/pedidos/${{btn.dataset.id}}`, {{ method: "DELETE" }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo eliminar la entrega."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-eliminar-tarea").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Eliminar esta tarea? Esta acción no se puede deshacer.")) return;
    btn.disabled = true;
    const r = await fetch(`/admin/tareas-entrega/${{btn.dataset.id}}`, {{ method: "DELETE" }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo eliminar la tarea."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-eliminar-historial").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("Este pedido ya tiene un recibo emitido y enviado al cliente. ¿Eliminarlo del historial de todas formas? Esta acción no se puede deshacer.")) return;
    btn.disabled = true;
    const r = await fetch(`/admin/pedidos/${{btn.dataset.id}}`, {{ method: "DELETE" }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo eliminar el pedido."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-eliminar-historial-tarea").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Eliminar esta tarea del historial? Esta acción no se puede deshacer.")) return;
    btn.disabled = true;
    const r = await fetch(`/admin/tareas-entrega/${{btn.dataset.id}}`, {{ method: "DELETE" }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo eliminar la tarea."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.getElementById("fecha-historial-pedidos").addEventListener("change", (e) => {{
  const url = new URL(location.href);
  url.searchParams.set("fecha_pedidos", e.target.value);
  location.href = url.toString();
}});
const filtroHistorialPedidos = document.getElementById("filtro-historial-pedidos");
function filtrarHistorialPedidos() {{
  const texto = filtroHistorialPedidos.value.trim().toLowerCase();
  document.querySelectorAll("[data-busqueda-historial]").forEach((pedido) => {{
    pedido.hidden = Boolean(texto && !pedido.dataset.busquedaHistorial.includes(texto));
  }});
}}
filtroHistorialPedidos.addEventListener("input", filtrarHistorialPedidos);
let apiPlacesAdmin;
async function cargarApiPlacesAdmin() {{
  if (apiPlacesAdmin !== undefined) return apiPlacesAdmin;
  apiPlacesAdmin = fetch("/api/configuracion-publica")
    .then((respuesta) => respuesta.ok ? respuesta.json() : {{}})
    .then(async (configuracion) => {{
      if (!configuracion.google_maps_api_key) return null;
      await new Promise((resolver, rechazar) => {{
        const script = document.createElement("script");
        script.src = `https://maps.googleapis.com/maps/api/js?key=${{encodeURIComponent(configuracion.google_maps_api_key)}}&libraries=places&v=weekly`;
        script.async = true;
        script.onload = resolver;
        script.onerror = rechazar;
        document.head.append(script);
      }});
      return google.maps.importLibrary("places");
    }})
    .catch((error) => {{ console.error("No se pudo cargar Google Places", error); return null; }});
  return apiPlacesAdmin;
}}
function activarAutocompleteDireccion(input, lista) {{
  if (!input || !lista) return;
  let temporizador;
  function ocultar() {{ lista.replaceChildren(); lista.hidden = true; }}
  async function mostrar(texto) {{
    const places = await cargarApiPlacesAdmin();
    if (!places || texto !== input.value.trim()) return;
    const {{ AutocompleteSuggestion }} = places;
    const {{ suggestions }} = await AutocompleteSuggestion.fetchAutocompleteSuggestions({{
      input: texto,
      includedRegionCodes: ["ar"],
    }}).catch((error) => {{ console.error("Autocomplete de direccion fallo", error); return {{ suggestions: [] }}; }});
    if (texto !== input.value.trim() || !suggestions?.length) {{ ocultar(); return; }}
    lista.replaceChildren(...suggestions.slice(0, 5).map(({{ placePrediction }}) => {{
      const item = document.createElement("li");
      const boton = document.createElement("button");
      boton.type = "button";
      boton.textContent = placePrediction.text.text;
      boton.addEventListener("click", async () => {{
        const place = placePrediction.toPlace();
        await place.fetchFields({{ fields: ["formattedAddress"] }});
        input.value = place.formattedAddress || placePrediction.text.text;
        ocultar();
      }});
      item.append(boton);
      return item;
    }}));
    lista.hidden = false;
  }}
  input.addEventListener("input", () => {{
    clearTimeout(temporizador);
    const texto = input.value.trim();
    if (texto.length < 3) {{ ocultar(); return; }}
    temporizador = setTimeout(() => {{ mostrar(texto).catch(ocultar); }}, 250);
  }});
  document.addEventListener("pointerdown", (evento) => {{
    if (lista.hidden) return;
    if (evento.target === input || lista.contains(evento.target)) return;
    ocultar();
  }});
}}
activarAutocompleteDireccion(document.getElementById("tarea-direccion"), document.getElementById("tarea-direccion-sugerencias"));
activarAutocompleteDireccion(document.getElementById("direccion-entrega-admin"), document.getElementById("direccion-entrega-admin-sugerencias"));
const CLIENTES_TAREA = {clientes_tarea_json};
const busquedaClienteTarea = document.getElementById("tarea-cliente-busqueda");
const idClienteTarea = document.getElementById("tarea-cliente");
const sugerenciasClienteTarea = document.getElementById("tarea-cliente-sugerencias");
function ocultarSugerenciasClienteTarea() {{
  sugerenciasClienteTarea.replaceChildren();
  sugerenciasClienteTarea.hidden = true;
}}
busquedaClienteTarea?.addEventListener("input", () => {{
  idClienteTarea.value = "";
  const texto = busquedaClienteTarea.value.trim().toLowerCase();
  if (!texto) {{ ocultarSugerenciasClienteTarea(); return; }}
  const coincidencias = CLIENTES_TAREA.filter((cliente) => cliente.nombre.toLowerCase().includes(texto)).slice(0, 8);
  if (!coincidencias.length) {{ ocultarSugerenciasClienteTarea(); return; }}
  sugerenciasClienteTarea.replaceChildren(...coincidencias.map((cliente) => {{
    const item = document.createElement("li");
    const boton = document.createElement("button");
    boton.type = "button";
    boton.textContent = cliente.nombre;
    boton.addEventListener("click", () => {{
      busquedaClienteTarea.value = cliente.nombre;
      idClienteTarea.value = cliente.id;
      if (cliente.direccion) document.getElementById("tarea-direccion").value = cliente.direccion;
      ocultarSugerenciasClienteTarea();
    }});
    item.append(boton);
    return item;
  }}));
  sugerenciasClienteTarea.hidden = false;
}});
document.addEventListener("pointerdown", (evento) => {{
  if (!sugerenciasClienteTarea || sugerenciasClienteTarea.hidden) return;
  if (evento.target.closest("#tarea-cliente-busqueda, #tarea-cliente-sugerencias")) return;
  ocultarSugerenciasClienteTarea();
}});
const listaEntregas = document.querySelector(".pedidos-hoy");
async function guardarOrdenEntregas() {{
  const items = Array.from(listaEntregas.querySelectorAll(".pedido-hoy[data-tipo-entrega]")).map((entrega) => ({{
    tipo: entrega.dataset.tipoEntrega,
    id: entrega.dataset.entregaId,
  }}));
  const respuesta = await fetch("/admin/entregas/orden", {{
    method: "PUT", headers: {{ "Content-Type": "application/json" }}, body: JSON.stringify({{ items }}),
  }});
  if (!respuesta.ok) {{ alert("No se pudo guardar el orden. Recargá la página e intentá nuevamente."); }}
}}
document.querySelectorAll(".arrastrar-entrega").forEach((tirador) => {{
  tirador.addEventListener("pointerdown", (evento) => {{
    if (evento.pointerType === "mouse") return;
    const entrega = tirador.closest(".pedido-hoy[data-tipo-entrega]");
    if (!entrega || !listaEntregas) return;
    evento.preventDefault();
    entrega.classList.add("arrastrando");
    tirador.setPointerCapture(evento.pointerId);
    const mover = (movimiento) => {{
      const destino = document.elementFromPoint(movimiento.clientX, movimiento.clientY)?.closest(".pedido-hoy[data-tipo-entrega]");
      if (!destino || destino === entrega || !listaEntregas.contains(destino)) return;
      const mitad = destino.getBoundingClientRect().top + destino.offsetHeight / 2;
      listaEntregas.insertBefore(entrega, movimiento.clientY < mitad ? destino : destino.nextSibling);
    }};
    const soltar = async () => {{
      entrega.classList.remove("arrastrando");
      document.removeEventListener("pointermove", mover);
      document.removeEventListener("pointerup", soltar);
      document.removeEventListener("pointercancel", soltar);
      await guardarOrdenEntregas();
    }};
      document.addEventListener("pointermove", mover);
      document.addEventListener("pointerup", soltar);
      document.addEventListener("pointercancel", soltar);
    }});
}});
let entregaNativaArrastrada = null;
document.querySelectorAll(".arrastrar-entrega").forEach((tirador) => {{
  tirador.addEventListener("dragstart", (evento) => {{
    entregaNativaArrastrada = tirador.closest(".pedido-hoy[data-tipo-entrega]");
    if (!entregaNativaArrastrada) return;
    entregaNativaArrastrada.classList.add("arrastrando");
    evento.dataTransfer.effectAllowed = "move";
  }});
  tirador.addEventListener("dragend", () => {{
    entregaNativaArrastrada?.classList.remove("arrastrando");
    entregaNativaArrastrada = null;
  }});
}});
document.querySelectorAll(".pedido-hoy[data-tipo-entrega]").forEach((destino) => {{
  destino.addEventListener("dragover", (evento) => {{
    if (!entregaNativaArrastrada || entregaNativaArrastrada === destino) return;
    evento.preventDefault();
    const mitad = destino.getBoundingClientRect().top + destino.offsetHeight / 2;
    listaEntregas.insertBefore(entregaNativaArrastrada, evento.clientY < mitad ? destino : destino.nextSibling);
  }});
  destino.addEventListener("drop", async (evento) => {{
    if (!entregaNativaArrastrada) return;
    evento.preventDefault();
    entregaNativaArrastrada.classList.remove("arrastrando");
    entregaNativaArrastrada = null;
    await guardarOrdenEntregas();
  }});
}});
document.getElementById("tarea-toggle")?.addEventListener("click", (e) => {{
  e.currentTarget.hidden = true;
  document.getElementById("tarea-campos").hidden = false;
  document.getElementById("tarea-cerrar").hidden = false;
  document.getElementById("tarea-titulo").focus();
}});
document.getElementById("tarea-cerrar")?.addEventListener("click", () => {{
  document.getElementById("form-tarea-entrega").reset();
  document.getElementById("tarea-cliente").value = "";
  document.getElementById("tarea-campos").hidden = true;
  document.getElementById("tarea-cerrar").hidden = true;
  document.getElementById("tarea-toggle").hidden = false;
}});
document.getElementById("form-tarea-entrega")?.addEventListener("submit", async (e) => {{
  e.preventDefault();
  const r = await fetch("/admin/tareas-entrega", {{ method:"POST", headers:{{"Content-Type":"application/json"}}, body:JSON.stringify({{fecha_entrega:document.getElementById("tarea-fecha").value, titulo:document.getElementById("tarea-titulo").value, cliente_id:document.getElementById("tarea-cliente").value || null, cliente_nombre:document.getElementById("tarea-cliente-busqueda").value, nota:document.getElementById("tarea-nota").value, direccion:document.getElementById("tarea-direccion").value, enviar_a_alejo:document.getElementById("tarea-enviar-alejo").checked}}) }});
  if (!r.ok) {{ alert("No se pudo crear la tarea."); return; }}
  location.href = `/admin/clientes?fecha_pedidos=${{document.getElementById("tarea-fecha").value}}`;
}});
document.querySelectorAll(".btn-completar-tarea").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    btn.disabled = true;
    const r = await fetch(`/admin/tareas-entrega/${{btn.dataset.id}}/completar`, {{ method:"POST" }});
    if (!r.ok) {{ alert("No se pudo completar la tarea."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
function _rutaDerivar(tipo, id) {{
  return tipo === "pedido" ? `/admin/pedidos/${{id}}/derivar` : `/admin/tareas-entrega/${{id}}/derivar`;
}}
document.querySelectorAll(".btn-derivar-entrega").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    const observaciones = prompt("Dejale una observación a Alejo (opcional)", "");
    if (observaciones === null) return;
    btn.disabled = true;
    const r = await fetch(_rutaDerivar(btn.dataset.tipo, btn.dataset.id), {{
      method: "PUT", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{derivado: true, observaciones}}),
    }});
    if (!r.ok) {{ alert("No se pudo derivar la entrega."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-quitar-derivacion").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm(btn.dataset.tipo === "pedido" ? "¿Quitar pedido a Alejo?" : "¿Quitar tarea a Alejo?")) return;
    btn.disabled = true;
    const r = await fetch(_rutaDerivar(btn.dataset.tipo, btn.dataset.id), {{
      method: "PUT", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{derivado: false}}),
    }});
    if (!r.ok) {{ alert("No se pudo quitar la derivación."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
</script>
{_ADMIN_CLIENTES_PWA_SCRIPT}
</body></html>"""

    provincias = sorted({c["provincia"] for c in clientes}, key=str.casefold)
    opciones_provincia_html = "".join(
        f'<option value="{html.escape(provincia)}">{html.escape(provincia)}</option>'
        for provincia in provincias
    )
    if not clientes:
        filas_html = '<tr><td colspan="7" class="vacio">Todavía no hay clientes registrados.</td></tr>'
    else:
        def _celda_cuenta(c):
            if not c.get("tiene_cuenta"):
                return (
                    '<div class="cuenta-cliente-acciones">'
                    '<span class="tipo-cliente tipo-cliente-sin-cuenta">'
                    'El cliente todavía no tiene una cuenta</span>'
                    '<button class="btn-mayorista" disabled>Habilitar mayorista</button>'
                    '</div>'
                )
            id_seguro = html.escape(c.get("id", ""))
            mayorista = c.get("tipo_cliente") == "mayorista"
            etiqueta = "Mayorista" if mayorista else "Minorista"
            clase_etiqueta = "tipo-cliente-mayorista" if mayorista else "tipo-cliente-minorista"
            texto_boton = "Quitar mayorista" if mayorista else "Habilitar mayorista"
            clase_boton = "btn-mayorista-activo" if mayorista else ""
            return (
                '<div class="cuenta-cliente-acciones">'
                f'<span class="tipo-cliente {clase_etiqueta}">{etiqueta}</span>'
                f'<button class="btn-mayorista {clase_boton}" data-id="{id_seguro}" '
                f'data-habilitado="{str(not mayorista).lower()}">{texto_boton}</button>'
                f'<button class="btn-reset" data-id="{id_seguro}">Resetear contraseña</button>'
                f'<button class="btn-eliminar" data-id="{id_seguro}" title="Eliminar cuenta" '
                f'aria-label="Eliminar cuenta">{_ICONO_TACHO}</button>'
                '</div>'
            )

        filas_html = "".join(
            f'<tr class="cliente-fila" data-busqueda="{html.escape(" ".join((c.get("nombre", ""), c.get("celular", ""), c.get("email", ""), c.get("provincia", ""))).lower())}" data-provincia="{html.escape(c.get("provincia", ""))}"><td class="col-check"><input class="cliente-check" type="checkbox" '
            f'value="{html.escape(c.get("id", ""))}" aria-label="Seleccionar cliente"></td>'
            f"<td>{html.escape(c.get('nombre', ''))}</td>"
            f"<td>{html.escape(c.get('celular', ''))}</td>"
            f"<td>{html.escape(c.get('email', '')) or '—'}</td>"
            f"<td>{html.escape(c.get('provincia', ''))}</td>"
            f'<td><a class="btn-historial" href="/admin/clientes/{html.escape(c.get("id", ""))}/historial" '
            f'title="Ver historial de pedidos" aria-label="Ver historial de pedidos">{_ICONO_OJO}</a></td>'
            f"<td>{_celda_cuenta(c)}</td></tr>"
            for c in clientes
        )
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Clientes</title>{_ADMIN_CLIENTES_PWA_HEAD}{_ADMIN_CLIENTES_ESTILO}</head><body>
<div class="panel">
  <div class="panel-header">
    <h1>Clientes ({len(clientes)})</h1>
    <div class="panel-header-acciones"><a class="btn-clientes" href="/admin/clientes">Pedidos y recibos</a><button id="salir">Cerrar sesión</button></div>
  </div>
  <div class="filtros-clientes">
    <input id="filtro-clientes" type="search" placeholder="Buscar por nombre, email, celular o provincia">
    <select id="filtro-provincia"><option value="">Todas las provincias</option>{opciones_provincia_html}</select>
    <select id="ordenar-clientes"><option value="fecha-desc">Ordenar: más recientes</option><option value="nombre-asc">Nombre: A a Z</option><option value="nombre-desc">Nombre: Z a A</option><option value="celular-asc">Celular</option><option value="provincia-asc">Provincia: A a Z</option></select>
  </div>
  <div class="acciones-masivas" id="acciones-masivas">
    <span id="seleccionados-texto">0 clientes seleccionados</span>
    <button id="btn-mail-masivo" type="button">Enviar mail</button>
    <button id="btn-eliminar-masivo" type="button">Eliminar seleccionados</button>
  </div>
  <div class="tabla-scroll"><table id="tabla-clientes">
    <thead><tr><th class="col-check"><input id="seleccionar-todos" type="checkbox" aria-label="Seleccionar todos"></th><th><button class="ordenar-columna" data-sort="nombre" data-sort-index="1">Nombre</button></th><th><button class="ordenar-columna" data-sort="celular" data-sort-index="2">Celular</button></th><th><button class="ordenar-columna" data-sort="email" data-sort-index="3">Email</button></th><th><button class="ordenar-columna" data-sort="provincia" data-sort-index="4">Provincia</button></th><th>Historial</th><th>Cuenta</th></tr></thead>
    <tbody>{filas_html}</tbody>
  </table></div>
  <div class="paginacion-clientes" id="paginacion-clientes" hidden></div>
</div>
<div class="modal-mail" id="modal-mail" hidden>
  <div class="modal-mail-contenido" role="dialog" aria-modal="true" aria-labelledby="modal-mail-titulo">
    <h2 id="modal-mail-titulo">Enviar mail</h2>
    <p id="modal-mail-ayuda"></p>
    <div class="mail-editor-toolbar" aria-label="Formato del mensaje">
      <button type="button" data-mail-formato="bold" aria-label="Negrita"><strong>B</strong></button>
      <button type="button" data-mail-formato="italic" aria-label="Cursiva"><em>I</em></button>
      <button type="button" data-mail-formato="insertUnorderedList" aria-label="Lista">Lista</button>
      <button type="button" id="mail-agregar-link">Enlace</button>
    </div>
    <div id="mail-mensaje" class="mail-editor" contenteditable="true" role="textbox" aria-multiline="true" data-placeholder="Escribí el mensaje para los clientes seleccionados"></div>
    <div class="modal-mail-acciones"><button id="mail-cancelar" type="button">Cancelar</button><button id="mail-enviar" type="button">Enviar</button></div>
  </div>
</div>
<script>
document.getElementById("salir").addEventListener("click", async () => {{
  await fetch("/admin/clientes/logout", {{ method: "POST" }});
  location.reload();
}});
document.querySelectorAll(".btn-reset").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Generar una contraseña nueva para este cliente y mandársela por mail?")) return;
    btn.disabled = true;
    btn.textContent = "Enviando...";
    const r = await fetch(`/admin/clientes/${{btn.dataset.id}}/resetear-password`, {{ method: "POST" }});
    const datos = await r.json();
    if (r.ok) {{
      alert("Listo, le llegó un mail con la contraseña nueva.");
      btn.textContent = "Resetear contraseña";
    }} else {{
      alert(datos.error || "No se pudo resetear la contraseña");
      btn.textContent = "Resetear contraseña";
    }}
    btn.disabled = false;
  }});
}});
document.querySelectorAll(".btn-eliminar").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Eliminar esta cuenta definitivamente? También se borrarán sus pedidos e historial. Esta acción no se puede deshacer.")) return;
    btn.disabled = true;
    const r = await fetch(`/admin/clientes/${{btn.dataset.id}}/eliminar`, {{ method: "POST" }});
    const datos = await r.json();
    if (r.ok) {{ location.reload(); return; }}
    alert(datos.error || "No se pudo eliminar la cuenta");
    btn.disabled = false;
  }});
}});
document.querySelectorAll(".btn-mayorista").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    const habilitado = btn.dataset.habilitado === "true";
    const accion = habilitado ? "habilitar" : "quitar";
    if (!confirm(`¿${{accion.charAt(0).toUpperCase() + accion.slice(1)}} acceso mayorista a este cliente?`)) return;
    btn.disabled = true;
    const r = await fetch(`/admin/clientes/${{btn.dataset.id}}/mayorista`, {{
      method: "POST", headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify({{habilitado}}),
    }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || datos.detail || "No se pudo actualizar el acceso mayorista."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-enviar-recibo").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Enviar el recibo por email a este cliente?")) return;
    btn.disabled = true;
    btn.textContent = "Enviando...";
    const r = await fetch(`/admin/pedidos/${{btn.dataset.id}}/recibo`, {{ method: "POST" }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo enviar el recibo."); btn.disabled = false; btn.textContent = "Enviar recibo"; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-reenviar-recibo").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Reenviar el recibo original por email?")) return;
    btn.disabled = true;
    const r = await fetch(`/admin/pedidos/${{btn.dataset.id}}/recibo`, {{ method: "POST" }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo reenviar el recibo."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-editar-entrega").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    const fecha = prompt("Nueva fecha de entrega (AAAA-MM-DD)", btn.dataset.fecha);
    if (!fecha || fecha === btn.dataset.fecha) return;
    btn.disabled = true;
    const r = await fetch(`/admin/pedidos/${{btn.dataset.id}}/fecha-entrega`, {{
      method: "PUT", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{fecha_entrega: fecha}}),
    }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo editar la fecha de entrega."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-eliminar-entrega").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Eliminar esta entrega? Esta acción no se puede deshacer.")) return;
    btn.disabled = true;
    const r = await fetch(`/admin/pedidos/${{btn.dataset.id}}`, {{ method: "DELETE" }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo eliminar la entrega."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
function _rutaDerivar(tipo, id) {{
  return tipo === "pedido" ? `/admin/pedidos/${{id}}/derivar` : `/admin/tareas-entrega/${{id}}/derivar`;
}}
document.querySelectorAll(".btn-derivar-entrega").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    const observaciones = prompt("Dejale una observación a Alejo (opcional)", "");
    if (observaciones === null) return;
    btn.disabled = true;
    const r = await fetch(_rutaDerivar(btn.dataset.tipo, btn.dataset.id), {{
      method: "PUT", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{derivado: true, observaciones}}),
    }});
    if (!r.ok) {{ alert("No se pudo derivar la entrega."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-quitar-derivacion").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm(btn.dataset.tipo === "pedido" ? "¿Quitar pedido a Alejo?" : "¿Quitar tarea a Alejo?")) return;
    btn.disabled = true;
    const r = await fetch(_rutaDerivar(btn.dataset.tipo, btn.dataset.id), {{
      method: "PUT", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{derivado: false}}),
    }});
    if (!r.ok) {{ alert("No se pudo quitar la derivación."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
const checksClientes = Array.from(document.querySelectorAll(".cliente-check"));
const seleccionarTodos = document.getElementById("seleccionar-todos");
const accionesMasivas = document.getElementById("acciones-masivas");
const seleccionadosTexto = document.getElementById("seleccionados-texto");
const modalMail = document.getElementById("modal-mail");
const mailMensaje = document.getElementById("mail-mensaje");
const filtroClientes = document.getElementById("filtro-clientes");
const filtroProvincia = document.getElementById("filtro-provincia");
const ordenarClientesSelect = document.getElementById("ordenar-clientes");

function idsSeleccionados() {{ return checksClientes.filter((chk) => chk.checked).map((chk) => chk.value); }}
function actualizarSeleccion() {{
  const cantidad = idsSeleccionados().length;
  seleccionadosTexto.textContent = `${{cantidad}} cliente${{cantidad === 1 ? "" : "s"}} seleccionado${{cantidad === 1 ? "" : "s"}}`;
  accionesMasivas.classList.toggle("visible", cantidad > 0);
  seleccionarTodos.checked = checksClientes.length > 0 && cantidad === checksClientes.length;
  seleccionarTodos.indeterminate = cantidad > 0 && cantidad < checksClientes.length;
}}
checksClientes.forEach((chk) => chk.addEventListener("change", actualizarSeleccion));
seleccionarTodos.addEventListener("change", () => {{ checksClientes.forEach((chk) => {{ chk.checked = seleccionarTodos.checked; }}); actualizarSeleccion(); }});

const CLIENTES_POR_PAGINA = 50;
let paginaClientesActual = 1;
const contenedorPaginacionClientes = document.getElementById("paginacion-clientes");

function filasClientesQueCoincidenConFiltro() {{
  const texto = filtroClientes.value.trim().toLowerCase();
  const provincia = filtroProvincia.value;
  return Array.from(document.querySelectorAll("#tabla-clientes tbody .cliente-fila")).filter((fila) =>
    !((texto && !fila.dataset.busqueda.includes(texto)) || (provincia && fila.dataset.provincia !== provincia))
  );
}}

function renderizarPaginacionClientes(total, totalPaginas) {{
  if (!contenedorPaginacionClientes) return;
  if (totalPaginas <= 1) {{ contenedorPaginacionClientes.innerHTML = ""; contenedorPaginacionClientes.hidden = true; return; }}
  contenedorPaginacionClientes.hidden = false;
  const desde = (paginaClientesActual - 1) * CLIENTES_POR_PAGINA + 1;
  const hasta = Math.min(paginaClientesActual * CLIENTES_POR_PAGINA, total);
  contenedorPaginacionClientes.innerHTML =
    `<button type="button" id="pagina-clientes-anterior" ${{paginaClientesActual === 1 ? "disabled" : ""}}>Anterior</button>` +
    `<span>${{desde}}–${{hasta}} de ${{total}} · página ${{paginaClientesActual}} de ${{totalPaginas}}</span>` +
    `<button type="button" id="pagina-clientes-siguiente" ${{paginaClientesActual === totalPaginas ? "disabled" : ""}}>Siguiente</button>`;
  document.getElementById("pagina-clientes-anterior").addEventListener("click", () => {{
    if (paginaClientesActual <= 1) return;
    paginaClientesActual -= 1;
    actualizarVistaClientes();
    document.getElementById("tabla-clientes").scrollIntoView({{ behavior: "smooth", block: "start" }});
  }});
  document.getElementById("pagina-clientes-siguiente").addEventListener("click", () => {{
    if (paginaClientesActual >= totalPaginas) return;
    paginaClientesActual += 1;
    actualizarVistaClientes();
    document.getElementById("tabla-clientes").scrollIntoView({{ behavior: "smooth", block: "start" }});
  }});
}}

function actualizarVistaClientes() {{
  const coincidentes = filasClientesQueCoincidenConFiltro();
  const totalPaginas = Math.max(1, Math.ceil(coincidentes.length / CLIENTES_POR_PAGINA));
  if (paginaClientesActual > totalPaginas) paginaClientesActual = totalPaginas;
  const inicio = (paginaClientesActual - 1) * CLIENTES_POR_PAGINA;
  const fin = inicio + CLIENTES_POR_PAGINA;
  const coincidentesEnPagina = new Set(coincidentes.slice(inicio, fin));
  document.querySelectorAll("#tabla-clientes tbody .cliente-fila").forEach((fila) => {{
    fila.hidden = !coincidentesEnPagina.has(fila);
  }});
  renderizarPaginacionClientes(coincidentes.length, totalPaginas);
}}

function filtrarClientes() {{
  paginaClientesActual = 1;
  actualizarVistaClientes();
}}
filtroClientes.addEventListener("input", filtrarClientes);
filtroProvincia.addEventListener("change", filtrarClientes);

const columnasOrden = {{ nombre: 1, celular: 2, email: 3, provincia: 4 }};
function ordenarFilasClientes(campo, ascendente) {{
  const indice = columnasOrden[campo];
  const filas = Array.from(document.querySelectorAll("#tabla-clientes tbody .cliente-fila"));
  filas.sort((a, b) => a.cells[indice].textContent.trim().localeCompare(
    b.cells[indice].textContent.trim(), "es", {{ numeric: true, sensitivity: "base" }}
  ) * (ascendente ? 1 : -1));
  const cuerpo = document.querySelector("#tabla-clientes tbody");
  filas.forEach((fila) => cuerpo.appendChild(fila));
  paginaClientesActual = 1;
  actualizarVistaClientes();
}}
ordenarClientesSelect.addEventListener("change", () => {{
  const [campo, direccion] = ordenarClientesSelect.value.split("-");
  if (campo === "fecha") return;
  ordenarFilasClientes(campo, direccion === "asc");
}});

document.querySelectorAll(".ordenar-columna").forEach((btn) => {{
  btn.addEventListener("click", () => {{
    const ascendente = btn.dataset.orden !== "asc";
    document.querySelectorAll(".ordenar-columna").forEach((otro) => {{ otro.dataset.orden = ""; }});
    btn.dataset.orden = ascendente ? "asc" : "desc";
    ordenarFilasClientes(btn.dataset.sort, ascendente);
  }});
}});
actualizarVistaClientes();

document.getElementById("btn-mail-masivo").addEventListener("click", () => {{
  document.getElementById("modal-mail-ayuda").textContent = `El asunto será: Novedades de The Tech Room Arg. Se enviará a ${{idsSeleccionados().length}} cliente(s). Cada email comenzará con el nombre del cliente y terminará con “Saludos, Vlad.”.`;
  mailMensaje.innerHTML = "";
  modalMail.hidden = false;
  mailMensaje.focus();
}});
document.querySelectorAll("[data-mail-formato]").forEach((boton) => {{
  boton.addEventListener("click", () => {{
    mailMensaje.focus();
    document.execCommand(boton.dataset.mailFormato, false);
  }});
}});
document.getElementById("mail-agregar-link").addEventListener("click", () => {{
  const url = prompt("Pegá el enlace (https://...)");
  if (!url) return;
  mailMensaje.focus();
  document.execCommand("createLink", false, url);
}});
document.getElementById("mail-cancelar").addEventListener("click", () => {{ modalMail.hidden = true; }});
document.getElementById("mail-enviar").addEventListener("click", async () => {{
  const mensaje = mailMensaje.innerHTML.trim();
  if (!mailMensaje.textContent.trim()) {{ alert("Escribí un mensaje antes de enviar."); return; }}
  const boton = document.getElementById("mail-enviar");
  boton.disabled = true;
  const r = await fetch("/admin/clientes/acciones/enviar-mail", {{
    method: "POST", headers: {{"Content-Type": "application/json"}},
    body: JSON.stringify({{cliente_ids: idsSeleccionados(), mensaje}}),
  }});
  const datos = await r.json();
  boton.disabled = false;
  if (!r.ok) {{ alert(datos.error || "No se pudo enviar el mail."); return; }}
  modalMail.hidden = true;
  alert(`Mail enviado a ${{datos.enviados}} cliente(s). Fallidos: ${{datos.fallidos}}.`);
}});
document.getElementById("btn-eliminar-masivo").addEventListener("click", async () => {{
  const ids = idsSeleccionados();
  if (!confirm(`¿Eliminar definitivamente ${{ids.length}} cuenta(s)? También se borrarán sus pedidos e historial. Esta acción no se puede deshacer.`)) return;
  const r = await fetch("/admin/clientes/acciones/eliminar", {{
    method: "POST", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{cliente_ids: ids}}),
  }});
  const datos = await r.json();
  if (!r.ok) {{ alert(datos.error || "No se pudieron eliminar las cuentas."); return; }}
  location.reload();
}});
</script>
{_ADMIN_CLIENTES_PWA_SCRIPT}
</body></html>"""

@router.get("/admin/clientes/{cliente_id}/historial", response_class=HTMLResponse)
def admin_clientes_historial(cliente_id: str, request: Request):
    if not _clientes_admin_activo(request):
        return RedirectResponse("/admin/clientes")

    client = get_client()
    filas_cliente = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    cliente = filas_cliente[0]
    nombre_cliente = f"{cliente.get('nombre', '')} {cliente.get('apellido', '')}".strip()

    filas_pedidos = client.table("pedidos").select("*").eq("cliente_id", cliente_id).execute().data
    filas_pedidos.sort(key=lambda p: p.get("fecha", ""), reverse=True)
    try:
        filas_interacciones = client.table("interacciones_cliente").select("*").eq("cliente_id", cliente_id).execute().data
    except Exception:
        filas_interacciones = []
    filas_interacciones.sort(
        key=lambda i: ((i.get("fecha", "") or "")[:10], i.get("fecha", "") or ""),
        reverse=True,
    )
    ranking_consultados = _ranking_productos_consultados(filas_interacciones)

    def _tipo_evento_label(tipo):
        return {
            "view_item": "view item",
            "select_product": "view item",
            "view_product": "view item",
        }.get(tipo, tipo or "Interacción")

    def _detalle_interaccion(fila):
        producto = (fila.get("producto_nombre") or "").strip()
        return html.escape(producto) if producto else "—"

    if not filas_pedidos:
        filas_pedidos_html = '<tr><td colspan="5" class="vacio">Este cliente todavía no tiene pedidos confirmados.</td></tr>'
    else:
        def _fila_pedido(fila):
            fecha, dia, hora = _formatear_fecha_ar(fila.get("fecha", ""))
            productos_fila = [p for p in (fila.get("productos") or []) if p]
            detalle = html.escape(" | ".join(productos_fila)) or "—"
            return (
                f'<tr data-campaign-item="{detalle}" data-campaign-source="pedido" '
                f'data-campaign-products="{html.escape(json.dumps(productos_fila))}">'
                f'<td class="col-check"><input type="checkbox" class="chk-mailing" '
                f'aria-label="Seleccionar pedido confirmado"></td>'
                f"<td>{fecha}</td><td>{dia}</td><td>{hora}</td><td>{detalle}</td></tr>"
            )

        filas_pedidos_html = "".join(_fila_pedido(fila) for fila in filas_pedidos)

    if not filas_interacciones:
        filas_interacciones_html = '<tr><td colspan="6" class="vacio">Este cliente todavía no tiene historial de vistas registrado.</td></tr>'
    else:
        def _fila_interaccion(fila):
            fecha, dia, hora = _formatear_fecha_ar(fila.get("fecha", ""))
            evento = html.escape(_tipo_evento_label(fila.get('tipo_evento', '')))
            detalle = _detalle_interaccion(fila)
            productos_fila = [fila.get("producto_nombre")] if fila.get("producto_nombre") else []
            return (
                f'<tr data-campaign-item="{evento} — {detalle}" data-campaign-source="vista" '
                f'data-campaign-products="{html.escape(json.dumps(productos_fila))}">'
                f'<td class="col-check"><input type="checkbox" class="chk-mailing" '
                f'aria-label="Seleccionar interacción"></td>'
                f"<td>{fecha}</td><td>{dia}</td><td>{hora}</td>"
                f"<td>{evento}</td><td>{detalle}</td></tr>"
            )

        filas_interacciones_html = "".join(_fila_interaccion(fila) for fila in filas_interacciones)

    if not ranking_consultados:
        filas_consultados_html = '<tr><td colspan="4" class="vacio">Todavía no hay productos consultados para ordenar.</td></tr>'
    else:
        def _fila_consultado(fila):
            fecha, dia, hora = _formatear_fecha_ar(fila.get("ultima_fecha", ""))
            producto = html.escape(fila.get("producto", "")) or "—"
            return (
                f'<tr data-campaign-item="{producto}" data-campaign-source="ranking" '
                f'data-campaign-products="{html.escape(json.dumps([fila.get("producto", "")]))}">'
                f'<td class="col-check"><input type="checkbox" class="chk-mailing" '
                f'aria-label="Seleccionar producto consultado"></td>'
                f"<td>{producto}</td><td>{fila.get('vistas', 0)}</td><td>{fecha} {hora}</td></tr>"
            )

        filas_consultados_html = "".join(_fila_consultado(fila) for fila in ranking_consultados)

    email_cliente = html.escape(cliente.get("email", "") or "")

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Historial — {html.escape(nombre_cliente)}</title>{_ADMIN_CLIENTES_PWA_HEAD}{_ADMIN_CLIENTES_ESTILO}</head><body>
<div class="panel">
  <div class="panel-header">
    <h1>Historial de {html.escape(nombre_cliente) or "cliente"}</h1>
    <a class="volver" href="/admin/clientes/lista">← Volver</a>
  </div>
  <section class="subseccion">
    <h2>Pedidos confirmados</h2>
    <p>Acá ves todo lo que el cliente cargó al carrito y confirmó.</p>
    <p class="scroll-hint">Deslizá para ver todas las columnas →</p>
    <div class="tabla-scroll tabla-historial"><table>
      <thead><tr><th class="col-check"></th><th>Fecha</th><th>Día</th><th>Hora</th><th>Productos</th></tr></thead>
      <tbody>{filas_pedidos_html}</tbody>
    </table></div>
  </section>
  <section class="subseccion">
    <h2>Productos más consultados</h2>
    <p>Ranking por cantidad de vistas de este cliente, ordenado de mayor a menor para decidir mejor el mailing.</p>
    <p class="scroll-hint">Deslizá para ver todas las columnas →</p>
    <div class="tabla-scroll tabla-historial"><table>
      <thead><tr><th class="col-check"></th><th>Producto</th><th>Vistas</th><th>Última vista</th></tr></thead>
      <tbody>{filas_consultados_html}</tbody>
    </table></div>
  </section>
  <section class="subseccion">
    <h2>Historial de vistas</h2>
    <p>Acá ves todas las interacciones de navegación, vistas e íconos que tocó el cliente.</p>
    <p class="scroll-hint">Deslizá para ver todas las columnas →</p>
    <div class="tabla-scroll tabla-historial"><table>
      <thead><tr><th class="col-check"></th><th>Fecha</th><th>Día</th><th>Hora</th><th>Evento</th><th>Detalle</th></tr></thead>
      <tbody>{filas_interacciones_html}</tbody>
    </table></div>
  </section>
  <div class="acciones-mailing">
    <button id="btn-preparar-mailing" {'disabled' if not email_cliente else ''}>Enviar mailing</button>
    <span id="mailing-ayuda">{'Seleccioná productos o vistas y se envía una oferta por mail si siguen disponibles en catálogo.' if email_cliente else 'Este cliente no tiene email disponible para mailing.'}</span>
  </div>
</div>
<script>
const btnMailing = document.getElementById("btn-preparar-mailing");
const checksMailing = [...document.querySelectorAll(".chk-mailing")];
const emailCliente = {_json_para_script(cliente.get("email", "") or "")};
const nombreCliente = {_json_para_script(nombre_cliente or "cliente")};
const clienteId = {_json_para_script(cliente.get("id", ""))};

function filasSeleccionadas() {{
  return checksMailing
    .filter((chk) => chk.checked)
    .map((chk) => chk.closest("tr"))
    .filter(Boolean);
}}

function actualizarEstadoMailing() {{
  if (!btnMailing || !emailCliente) return;
  btnMailing.disabled = filasSeleccionadas().length === 0;
}}

function productosSeleccionados() {{
  const productos = [];
  const vistos = new Set();
  for (const fila of filasSeleccionadas()) {{
    let lista = [];
    try {{
      lista = JSON.parse(fila.dataset.campaignProducts || "[]");
    }} catch {{
      lista = [];
    }}
    for (const producto of lista) {{
      if (!producto || vistos.has(producto)) continue;
      vistos.add(producto);
      productos.push(producto);
    }}
  }}
  return productos;
}}

checksMailing.forEach((chk) => chk.addEventListener("change", actualizarEstadoMailing));
actualizarEstadoMailing();

if (btnMailing) {{
  btnMailing.addEventListener("click", async () => {{
    const productos = productosSeleccionados();
    if (!emailCliente || productos.length === 0) return;
    btnMailing.disabled = true;
    const ayudaPrev = document.getElementById("mailing-ayuda").textContent;
    document.getElementById("mailing-ayuda").textContent = "Enviando mailing...";
    try {{
      const r = await fetch(`/admin/clientes/${{clienteId}}/mailing-oferta`, {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{ productos }}),
      }});
      const datos = await r.json();
      if (!r.ok) {{
        document.getElementById("mailing-ayuda").textContent = datos.error || "No se pudo enviar el mailing.";
        return;
      }}
      const omitidos = (datos.omitidos || []).length
        ? ` Omitidos por falta de stock/catálogo: ${{datos.omitidos.join(", ")}}.`
        : "";
      document.getElementById("mailing-ayuda").textContent =
        `Mail enviado a ${{emailCliente}} con ${{datos.enviados}} producto(s).${{omitidos}}`;
    }} catch {{
      document.getElementById("mailing-ayuda").textContent = "No se pudo enviar el mailing.";
    }} finally {{
      actualizarEstadoMailing();
      if (!filasSeleccionadas().length) btnMailing.disabled = true;
    }}
  }});
}}
</script>
{_ADMIN_CLIENTES_PWA_SCRIPT}
</body></html>"""
