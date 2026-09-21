"""Pagina HTML del panel de entregas del cadete.

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
    _ADMIN_CLIENTES_PWA_SCRIPT,
    _CADETE_ESTILO,
    _CADETE_PWA_HEAD,
    _DIAS_SEMANA,
    _cadete_activo,
    _formatear_entero_ar,
    _link_whatsapp_cliente,
    _query_maps,
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


@router.get("/admin/cadete", response_class=HTMLResponse)
def admin_cadete(request: Request):
    if not _cadete_activo(request):
        return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Entregas — Ingresar</title>{_CADETE_PWA_HEAD}{_CADETE_ESTILO}</head><body>
<div class="tarjeta">
  <h1>Panel de entregas</h1>
  <p id="err" class="error" style="display:none"></p>
  <input id="pass" type="password" placeholder="Contraseña" autofocus>
  <button id="btn">Ingresar</button>
</div>
<script>
document.getElementById("btn").addEventListener("click", async () => {{
  const r = await fetch("/admin/cadete/login", {{
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
    fecha_hoy = entregas.ahora_argentina().date().isoformat()
    fecha_param = request.query_params.get("fecha", "")
    try:
        date.fromisoformat(fecha_param)
        fecha_consulta = fecha_param
    except ValueError:
        fecha_consulta = fecha_hoy

    def _label_fecha_entrega(fecha_iso):
        try:
            momento = datetime.fromisoformat(fecha_iso)
        except ValueError:
            return fecha_iso
        return f"{momento.strftime('%d/%m')} · {_DIAS_SEMANA[momento.weekday()]}"

    filas_clientes = client.table("clientes").select("*").execute().data
    clientes_por_id = {c.get("id"): c for c in filas_clientes}
    pedidos = client.table("pedidos").select("*").eq("asignado_a", CADETE_SLUG).execute().data
    tareas = client.table("tareas_entrega").select("*").eq("asignado_a", CADETE_SLUG).execute().data
    pedidos_hoy = [
        pedido for pedido in pedidos
        if pedido.get("fecha_entrega") == fecha_consulta and not pedido.get("recibo_enviado_en")
    ]
    tareas_hoy = [
        tarea for tarea in tareas
        if tarea.get("fecha_entrega") == fecha_consulta and not tarea.get("completada_en")
    ]

    def _descripcion_pedido(pedido):
        detalle = pedido.get("detalle") or []
        if detalle:
            return " | ".join(
                f"{item.get('nombre', '')} x{item.get('cantidad', 0)}"
                for item in detalle
            )
        return " | ".join(pedido.get("productos") or [])

    def _boton_vamos(direccion, lat=None, lng=None):
        if not direccion:
            return '<span style="color:#9aa0ab">Sin dirección cargada</span>'
        return (
            f'<button class="btn-direcciones" type="button" '
            f'data-maps="https://www.google.com/maps/search/?{html.escape(urlencode({"api": 1, "query": _query_maps(direccion, lat, lng)}))}">Vamos</button>'
        )

    def _boton_whatsapp_cliente(celular):
        link = _link_whatsapp_cliente(celular)
        if not link:
            return ""
        return f'<a class="btn-whatsapp-cliente" href="{html.escape(link)}" target="_blank" rel="noopener">WhatsApp</a>'

    def _tarjeta_pedido_cadete(pedido):
        pedido_id = html.escape(pedido.get("id", ""))
        cliente = clientes_por_id.get(pedido.get("cliente_id"), {})
        nombre_cliente = f"{cliente.get('nombre', '')} {cliente.get('apellido', '')}".strip() or "Cliente"
        direccion = (pedido.get("direccion_entrega") or "").strip()
        if not pedido.get("detalle") or pedido.get("total_usd") is None:
            boton_recibo = (f'<button class="btn-enviar-recibo" type="button" data-id="{pedido_id}" '
                             'disabled title="Falta detalle histórico">Enviar recibo</button>')
        else:
            boton_recibo = f'<button class="btn-enviar-recibo" type="button" data-id="{pedido_id}">Enviar recibo</button>'
        observaciones = (pedido.get("observaciones_cadete") or "").strip()
        detalle_obs = (
            f'<br><span class="observacion-cadete">Observaciones: {html.escape(observaciones)}</span>'
            if observaciones else ""
        )
        fecha = html.escape(pedido.get("fecha_entrega", ""))
        boton_fecha = (
            f'<button class="btn-editar-entrega" type="button" data-id="{pedido_id}" data-fecha="{fecha}" '
            'data-tipo="pedido">Editar fecha</button>'
        )
        return (
            f'<div class="pedido-hoy"><div class="pedido-hoy-detalle"><strong>{html.escape(nombre_cliente)}</strong> · '
            f'{html.escape(cliente.get("celular") or "—")}<br><span>{html.escape(_descripcion_pedido(pedido))}</span>'
            f'{detalle_obs}<br><span class="total-cadete">Total a cobrar: U$D {_formatear_entero_ar(pedido.get("total_usd"))}</span></div>'
            f'<div class="pedido-acciones">{_boton_vamos(direccion, pedido.get("lat"), pedido.get("lng"))}{_boton_whatsapp_cliente(cliente.get("celular"))}{boton_recibo}{boton_fecha}</div></div>'
        )

    def _tarjeta_tarea_cadete(tarea):
        tarea_id = html.escape(tarea.get("id", ""))
        direccion = (tarea.get("direccion") or "").strip()
        cliente_tarea = clientes_por_id.get(tarea.get("cliente_id"), {})
        nombre_cliente = tarea.get("cliente_nombre") or ""
        detalle_cliente = f'<br><span>Cliente: {html.escape(nombre_cliente)}</span>' if nombre_cliente else ""
        observaciones = (tarea.get("observaciones_cadete") or "").strip()
        detalle_obs = (
            f'<br><span class="observacion-cadete">Observaciones: {html.escape(observaciones)}</span>'
            if observaciones else ""
        )
        fecha = html.escape(tarea.get("fecha_entrega", ""))
        boton_fecha = (
            f'<button class="btn-editar-entrega" type="button" data-id="{tarea_id}" data-fecha="{fecha}" '
            'data-tipo="tarea">Editar fecha</button>'
        )
        boton_derivar_vlad = (
            f'<button class="btn-derivar-vlad" type="button" data-id="{tarea_id}">Derivar a Vlad</button>'
        )
        return (
            f'<div class="pedido-hoy"><div class="pedido-hoy-detalle">'
            f'<strong>Tarea: {html.escape(tarea.get("titulo") or "")}</strong>'
            f'{detalle_cliente}<br><span>{html.escape(tarea.get("nota") or "")}</span>{detalle_obs}</div>'
            f'<div class="pedido-acciones">{_boton_vamos(direccion)}{_boton_whatsapp_cliente(cliente_tarea.get("celular"))}'
            f'<button class="btn-completar-tarea" type="button" data-id="{tarea_id}">Completado</button>{boton_fecha}{boton_derivar_vlad}</div></div>'
        )

    tarjetas = (
        [_tarjeta_pedido_cadete(pedido) for pedido in pedidos_hoy]
        + [_tarjeta_tarea_cadete(tarea) for tarea in tareas_hoy]
    )
    entregas_html = "".join(tarjetas) if tarjetas else (
        '<p class="vacio">No tenés entregas asignadas para hoy.</p>' if fecha_consulta == fecha_hoy
        else '<p class="vacio">No tenés entregas asignadas para ese día.</p>'
    )

    seccion_proximos = ""
    if fecha_consulta == fecha_hoy:
        pedidos_proximos = [
            pedido for pedido in pedidos
            if pedido.get("fecha_entrega", "") > fecha_hoy and not pedido.get("recibo_enviado_en")
        ]
        tareas_proximas = [
            tarea for tarea in tareas
            if tarea.get("fecha_entrega", "") > fecha_hoy and not tarea.get("completada_en")
        ]
        fechas_proximas = sorted({
            pedido.get("fecha_entrega") for pedido in pedidos_proximos
        } | {
            tarea.get("fecha_entrega") for tarea in tareas_proximas
        })
        proximos_html = "".join(
            f'<div class="proximos-dia"><h3>{html.escape(_label_fecha_entrega(fecha))}</h3>'
            + "".join(_tarjeta_pedido_cadete(pedido) for pedido in pedidos_proximos if pedido.get("fecha_entrega") == fecha)
            + "".join(_tarjeta_tarea_cadete(tarea) for tarea in tareas_proximas if tarea.get("fecha_entrega") == fecha)
            + "</div>"
            for fecha in fechas_proximas
        )
        total_proximos = len(pedidos_proximos) + len(tareas_proximas)
        if total_proximos:
            seccion_proximos = (
                f'<section class="pedidos-hoy proximos-dias"><div class="pedidos-hoy-header">'
                f'<h2>Próximos días ({total_proximos})</h2></div>{proximos_html}</section>'
            )

    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Entregas asignadas</title>{_CADETE_PWA_HEAD}{_CADETE_ESTILO}</head><body>
<div class="panel">
  <div class="panel-header">
    <h1>Entregas asignadas</h1>
    <div class="panel-header-acciones"><button id="salir">Cerrar sesión</button></div>
  </div>
  <div class="selector-fecha-cadete">
    <label for="fecha-cadete">Ver entregas del día</label>
    <input id="fecha-cadete" type="date" value="{fecha_consulta}">
  </div>
  <form id="form-nota-cadete" class="form-tarea-entrega">
    <button id="nota-toggle" class="tarea-toggle" type="button">+ Nueva nota</button>
    <button id="nota-cerrar" class="tarea-cerrar" type="button" hidden aria-label="Cerrar formulario de nota" title="Cerrar">✕</button>
    <div id="nota-campos" class="nota-campos" hidden>
      <input id="nota-titulo" required maxlength="200" placeholder="Nota">
      <input id="nota-fecha" type="date" required value="{fecha_consulta}" title="Fecha de la nota">
      <input id="nota-detalle" maxlength="1000" placeholder="Detalle opcional">
      <div class="tarea-direccion-wrap"><input id="nota-direccion" maxlength="500" placeholder="Agregar dirección (opcional)" autocomplete="off"><ul id="nota-direccion-sugerencias" class="tarea-direccion-sugerencias" role="listbox" aria-label="Sugerencias de dirección" hidden></ul></div>
      <label class="nota-derivar-vlad-label"><input type="checkbox" id="nota-derivar-vlad"> Derivar a Vlad</label>
      <button type="submit">Agregar nota</button>
    </div>
  </form>
  <section class="pedidos-hoy"><div class="pedidos-hoy-header"><h2>Pendientes para {'hoy' if fecha_consulta == fecha_hoy else html.escape(_label_fecha_entrega(fecha_consulta))} ({len(pedidos_hoy) + len(tareas_hoy)})</h2></div>{entregas_html}</section>
  {seccion_proximos}
</div>
<div class="modal-series" id="modal-series" hidden><div class="modal-series-contenido" role="dialog" aria-modal="true" aria-labelledby="series-titulo"><h2 id="series-titulo">Fotos de números de serie</h2><p>Sacá o seleccioná todas las fotos antes de enviar el recibo.</p><div id="series-fotos" class="series-fotos"></div><div class="series-acciones"><button id="series-agregar" type="button">Agregar foto</button><button id="series-cancelar" type="button">Cancelar</button><button id="series-enviar" type="button">Enviar recibo</button></div></div></div>
<script>
document.getElementById("salir").addEventListener("click", async () => {{
  await fetch("/admin/cadete/logout", {{ method: "POST" }});
  location.reload();
}});
document.getElementById("fecha-cadete").addEventListener("change", (e) => {{
  location.href = `/admin/cadete?fecha=${{e.target.value}}`;
}});
document.getElementById("nota-toggle").addEventListener("click", (e) => {{
  e.currentTarget.hidden = true;
  document.getElementById("nota-campos").hidden = false;
  document.getElementById("nota-cerrar").hidden = false;
  document.getElementById("nota-titulo").focus();
}});
document.getElementById("nota-cerrar").addEventListener("click", () => {{
  document.getElementById("form-nota-cadete").reset();
  document.getElementById("nota-campos").hidden = true;
  document.getElementById("nota-cerrar").hidden = true;
  document.getElementById("nota-toggle").hidden = false;
}});
document.getElementById("form-nota-cadete").addEventListener("submit", async (e) => {{
  e.preventDefault();
  const r = await fetch("/admin/tareas-entrega", {{
    method:"POST", headers:{{"Content-Type":"application/json"}},
    body:JSON.stringify({{
      fecha_entrega:document.getElementById("nota-fecha").value,
      titulo:document.getElementById("nota-titulo").value,
      nota:document.getElementById("nota-detalle").value,
      direccion:document.getElementById("nota-direccion").value,
      derivar_a_vlad:document.getElementById("nota-derivar-vlad").checked,
    }}),
  }});
  if (!r.ok) {{ alert("No se pudo crear la nota."); return; }}
  location.href = `/admin/cadete?fecha=${{document.getElementById("nota-fecha").value}}`;
}});
document.querySelectorAll(".btn-direcciones").forEach((btn) => {{
  btn.addEventListener("click", () => {{ window.open(btn.dataset.maps, "_blank", "noopener"); }});
}});
document.querySelectorAll(".btn-completar-tarea").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    btn.disabled = true;
    const r = await fetch(`/admin/tareas-entrega/${{btn.dataset.id}}/completar`, {{ method:"POST" }});
    if (!r.ok) {{ alert("No se pudo completar la tarea."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-derivar-vlad").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    if (!confirm("¿Devolverle esta nota a Vlad?")) return;
    btn.disabled = true;
    const r = await fetch(`/admin/tareas-entrega/${{btn.dataset.id}}/derivar`, {{
      method:"PUT", headers:{{"Content-Type":"application/json"}}, body:JSON.stringify({{derivado:false}}),
    }});
    if (!r.ok) {{ alert("No se pudo derivar la nota."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
document.querySelectorAll(".btn-editar-entrega").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    const fecha = prompt("Nueva fecha de entrega (AAAA-MM-DD)", btn.dataset.fecha);
    if (!fecha || fecha === btn.dataset.fecha) return;
    btn.disabled = true;
    const ruta = btn.dataset.tipo === "pedido"
      ? `/admin/pedidos/${{btn.dataset.id}}/fecha-entrega`
      : `/admin/tareas-entrega/${{btn.dataset.id}}/fecha-entrega`;
    const r = await fetch(ruta, {{
      method: "PUT", headers: {{"Content-Type": "application/json"}}, body: JSON.stringify({{fecha_entrega: fecha}}),
    }});
    const datos = await r.json().catch(() => ({{}}));
    if (!r.ok) {{ alert(datos.error || "No se pudo editar la fecha de entrega."); btn.disabled = false; return; }}
    location.reload();
  }});
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
  if (!r.ok) {{ alert(respuesta.error || "No se pudo enviar el recibo."); boton.disabled = false; boton.textContent = "Enviar recibo"; modalSeries.hidden = true; return; }}
  location.reload();
}});
let apiPlacesCadete;
async function cargarApiPlacesCadete() {{
  if (apiPlacesCadete !== undefined) return apiPlacesCadete;
  apiPlacesCadete = fetch("/api/configuracion-publica")
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
  return apiPlacesCadete;
}}
function activarAutocompleteDireccionCadete(input, lista) {{
  if (!input || !lista) return;
  let temporizador;
  function ocultar() {{ lista.replaceChildren(); lista.hidden = true; }}
  async function mostrar(texto) {{
    const places = await cargarApiPlacesCadete();
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
activarAutocompleteDireccionCadete(document.getElementById("nota-direccion"), document.getElementById("nota-direccion-sugerencias"));
</script>
{_ADMIN_CLIENTES_PWA_SCRIPT}
</body></html>"""
