"""Helpers de presentacion compartidos por los paneles HTML.

Viven aca y no en app.py para que los paneles (web/paginas_admin.py y
web/paginas_cadete.py) los puedan importar sin arrastrar el modulo entero.
El codigo es identico al que estaba inline en app.py.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Request

BASE = Path(__file__).parent
_UI_DIR = BASE / "ui"

# El slug del cadete: identifica a quien esta asignada una entrega.
CADETE_SLUG = "alejo"


def _leer_ui(nombre):
    """Lee un fragmento estatico de HTML/CSS desde web/ui/.

    Vive fuera de web/static/ (que se sirve publico) y fuera del codigo para
    que los modulos no carguen con decenas de KB de CSS inline. Lo que
    devuelve es identico al literal que habia antes.
    """
    return (_UI_DIR / nombre).read_text(encoding="utf-8")


def _clientes_admin_activo(request: Request):
    return bool(request.session.get("clientes_admin_ok"))


def _cadete_activo(request: Request):
    return bool(request.session.get("cadete_ok"))


def _puede_operar_entrega(request: Request, fila: dict):
    if _clientes_admin_activo(request):
        return True
    return _cadete_activo(request) and fila.get("asignado_a") == CADETE_SLUG


def _json_para_script(valor):
    # json.dumps no escapa "<", ">" ni "&", así que un dato de usuario (ej. un
    # nombre de cliente) que contenga "</script>" cerraría el bloque e
    # inyectaría HTML/JS arbitrario. Usar esto en vez de json.dumps() para
    # cualquier valor con datos de usuario embebido dentro de un <script>.
    return (
        json.dumps(valor, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def _formatear_entero_ar(valor):
    if valor is None:
        return "—"
    return f"{int(valor):,}".replace(",", ".")


def _query_maps(direccion, lat, lng):
    # Con coordenadas exactas (geolocalización del cliente al pedir, o el
    # punto elegido en el autocomplete) el link va directo a la casa puntual
    # — clave en barrios privados, donde la dirección de texto sola no
    # alcanza. Sin coordenadas, cae al texto de siempre.
    if lat is not None and lng is not None:
        return f"{lat},{lng}"
    return direccion


def _link_whatsapp_cliente(celular):
    digitos = re.sub(r"\D", "", celular or "")
    if not digitos:
        return None
    if not digitos.startswith("54"):
        digitos = "549" + digitos
    return f"https://wa.me/{digitos}"

_DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _formatear_fecha_ar(fecha_iso):
    """Las fechas se guardan en UTC (ver pedidos.py) — acá se muestran en
    hora de Argentina (UTC-3 fijo, sin horario de verano) para que
    coincidan con lo que el cliente realmente vivió al hacer el pedido."""
    if not fecha_iso:
        return "—", "—", "—"
    try:
        momento = datetime.fromisoformat(fecha_iso.replace("Z", "+00:00")) - timedelta(hours=3)
    except ValueError:
        return fecha_iso, "—", "—"
    return momento.strftime("%d/%m/%Y"), _DIAS_SEMANA[momento.weekday()], momento.strftime("%H:%M")


def _ranking_productos_consultados(filas_interacciones):
    conteos = {}
    ultima_fecha = {}
    for fila in filas_interacciones:
        tipo = (fila.get("tipo_evento") or "").strip()
        producto = (fila.get("producto_nombre") or "").strip()
        if tipo not in {"view_item", "select_product", "view_product"} or not producto:
            continue
        conteos[producto] = conteos.get(producto, 0) + 1
        fecha = fila.get("fecha", "") or ""
        if fecha > (ultima_fecha.get(producto) or ""):
            ultima_fecha[producto] = fecha
    ranking = [
        {"producto": producto, "vistas": vistas, "ultima_fecha": ultima_fecha.get(producto, "")}
        for producto, vistas in conteos.items()
    ]
    ranking.sort(key=lambda r: (-r["vistas"], -(0 if not r["ultima_fecha"] else 1), r["producto"].lower()))
    ranking.sort(key=lambda r: r["ultima_fecha"], reverse=True)
    ranking.sort(key=lambda r: r["vistas"], reverse=True)
    return ranking

_ICONO_OJO = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M1 12S5 5 12 5s11 7 11 7-4 7-11 7S1 12 1 12Z"/><circle cx="12" cy="12" r="3"/></svg>'
)

_ICONO_TACHO = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>'
    '<path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>'
)


_OPERACIONES_ESTILO = _leer_ui("operations_editorial.css.html")
_ADMIN_CLIENTES_ESTILO = _leer_ui("admin_clientes.css.html") + _OPERACIONES_ESTILO

# Alejo entra siempre desde el celular — a diferencia del panel de admin
# (pensado para escritorio, con overrides mobile en un @media), este es
# mobile-first sin media query: una sola columna y botones grandes siempre.
_CADETE_ESTILO = _leer_ui("cadete.css.html") + _OPERACIONES_ESTILO

_ADMIN_CLIENTES_PWA_HEAD = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/admin-clientes.webmanifest">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#111318">
"""

_CADETE_PWA_HEAD = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/admin-cadete.webmanifest">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#111318">
"""

_ADMIN_CLIENTES_PWA_SCRIPT = """
<script>
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {});
}
</script>
"""
