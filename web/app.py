import html
import json
import logging
import math
import os
import posixpath
import re
import secrets
import string
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.sessions import SessionMiddleware

from web import buscador, catalogo, cuentas, interacciones, pedidos
from web.email_util import EnvioEmailError, enviar_email
from web.supabase_client import get_client
from web.chat import responder
from web.reglas import WHATSAPP

# Interruptor: False = buscador gratis (sin IA). True = IA (Claude, tu API key).
# Para volver a la IA, cambiá esto a True y reiniciá el servidor.
USAR_IA = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web")

load_dotenv(Path(__file__).parent / ".env")

BASE = Path(__file__).parent
# En producción (Railway) apunta a un volumen persistente vía la variable de
# entorno PRODUCTOS_PATH; en local, cae al archivo de siempre junto al código.
PRODUCTOS_PATH = Path(os.environ.get("PRODUCTOS_PATH", str(BASE / "productos.json")))
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
ADMIN_CLIENTES_PASSWORD = os.environ.get("ADMIN_CLIENTES_PASSWORD")
if not ADMIN_CLIENTES_PASSWORD:
    # Sin fallback: esta contraseña es la única puerta al panel con datos de
    # clientes (nombre/celular/email/historial) y a poder resetear passwords
    # ajenas — un valor por defecto adivinable ahí es un agujero de seguridad,
    # no una comodidad de desarrollo. Mejor que el server no arranque.
    raise RuntimeError("ADMIN_CLIENTES_PASSWORD no configurado — no se puede iniciar el servidor")

# Tope de gasto por chat/cliente (USD). Al superarlo, se lo deriva al WhatsApp.
LIMITE_USD = 0.25
_gasto = {}  # sesion -> USD acumulado

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def _manejar_error_validacion(request: Request, exc: RequestValidationError):
    # El detalle default de FastAPI/Pydantic incluye "input" con el valor
    # crudo que falló la validación — si ese campo es una contraseña, la
    # devuelve en texto plano en la respuesta. Acá la reemplazamos por un
    # mensaje propio (mismo formato {"error": ...} que usa el resto de la
    # app) sin exponer ningún valor de entrada.
    campos = {".".join(str(p) for p in err["loc"] if p != "body") for err in exc.errors()}
    if "password" in campos:
        mensaje = "La contraseña tiene que tener al menos 8 caracteres."
    else:
        mensaje = "Revisá los datos ingresados e intentá de nuevo."
    return JSONResponse(status_code=422, content={"error": mensaje})


def _public_app_base_url(request: Request):
    base_publica = (os.environ.get("PUBLIC_APP_URL") or "").strip()
    if base_publica:
        return base_publica.rstrip("/")
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if forwarded_host:
        forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip() or "https"
        return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


def _public_login_url(request: Request):
    return f"{_public_app_base_url(request)}/login.html"


def _public_producto_mailing_url(request: Request, nombre_producto: str, codigo: str):
    query = urlencode({
        "producto": nombre_producto,
        "agregar": "1",
        "codigo": codigo,
    })
    return f"{_public_app_base_url(request)}/?{query}"


@app.middleware("http")
async def sin_cache_estaticos(request: Request, call_next):
    """Evita que el navegador se quede con una versión vieja de JS/CSS
    cacheada tras un simple F5 (cada refresh revalida contra el archivo
    real en disco)."""
    response = await call_next(request)
    if request.url.path.endswith((".js", ".css")):
        response.headers["Cache-Control"] = "no-cache"
    return response


_RUTAS_HTML_PUBLICAS = {"/login.html", "/index.html"}


def _normalizar_ruta(path):
    """Normaliza un path de request al MISMO criterio que usa StaticFiles
    para resolver qué archivo termina sirviendo: colapsa barras repetidas
    (incluida la excepción POSIX de "//" inicial, que posixpath.normpath por
    sí solo NO colapsa) y después resuelve segmentos "." y ".." con
    posixpath.normpath — esto último es imprescindible porque uvicorn ya
    decodifica %2e/%2f antes de que la app vea el path, así que
    "/foo/%2e%2e/" llega literalmente como "/foo/../" y hay que resolverlo
    como "/", no compararlo tal cual contra un sufijo .html."""
    ruta = re.sub(r"/+", "/", path)
    ruta = posixpath.normpath(ruta)
    if not ruta.startswith("/"):
        ruta = "/" + ruta
    return ruta.lower()


@app.middleware("http")
async def gate_paginas_html(request: Request, call_next):
    """El StaticFiles mount de más abajo serviría cualquier .html (incluido
    index.html o catalogo.html) sin pasar por el chequeo de sesión que sí
    tiene GET "/". Esto cierra ese agujero: cualquier .html estático, salvo
    login.html (la página de login/registro, que tiene que ser pública),
    requiere sesión activa — usando la MISMA normalización de path que
    aplica StaticFiles, no una comparación contra el path crudo (ver
    _normalizar_ruta). El mount además se registra con html=False (más
    abajo) para que ninguna variante que resuelva a un directorio sirva
    index.html automáticamente sin pasar por esta gate."""
    ruta_cruda = request.url.path
    ruta = _normalizar_ruta(ruta_cruda)

    if ruta == "/" and ruta_cruda != "/":
        # "//", "///", "/./", "/foo/../", etc.: StaticFiles las resolvería
        # igual que "/", que ya está gateada por la ruta explícita
        # @app.get("/") — canonicalizamos ahí en vez de dejar que el mount
        # decida.
        return RedirectResponse("/")

    if ruta.endswith(".html") and ruta not in _RUTAS_HTML_PUBLICAS and not _sesion_activa(request):
        return RedirectResponse("/")

    # Con una contraseña temporal pendiente de cambio, ninguna pantalla del
    # catálogo es accesible todavía — todo redirige a login.html, que es
    # quien muestra el form obligatorio de "elegí tu contraseña nueva".
    if (ruta.endswith(".html") and ruta != "/login.html"
            and _sesion_activa(request) and _debe_cambiar_password(request)):
        return RedirectResponse("/login.html")

    return await call_next(request)


# SessionMiddleware se registra DESPUÉS de los middlewares de arriba a propósito:
# FastAPI hace add_middleware(insert al frente de la pila), así que lo último
# que se registra queda más "afuera" y corre primero en cada request — acá
# necesitamos que request.session ya exista cuando gate_paginas_html se ejecuta.
_session_secret = os.environ.get("SESSION_SECRET")
if not _session_secret:
    # Sin fallback: esta clave firma la cookie de sesión de todos los
    # clientes y del panel de admin — un valor fijo en el código deja
    # cualquier sesión (incluida la de admin) forjable por cualquiera que
    # lea el repo. Mejor que el server no arranque sin una clave propia.
    raise RuntimeError("SESSION_SECRET no configurado — no se puede iniciar el servidor")
_session_https_only_raw = (os.environ.get("SESSION_HTTPS_ONLY") or "").strip().lower()
if _session_https_only_raw in {"1", "true", "yes", "on"}:
    _session_https_only = True
elif _session_https_only_raw in {"0", "false", "no", "off"}:
    _session_https_only = False
else:
    _public_app_url = (os.environ.get("PUBLIC_APP_URL") or "").strip().lower()
    _session_https_only = bool(
        os.environ.get("RAILWAY_ENVIRONMENT")
        or os.environ.get("RAILWAY_PROJECT_ID")
        or _public_app_url.startswith("https://")
    )
app.add_middleware(SessionMiddleware, secret_key=_session_secret, https_only=_session_https_only)


def _cargar_productos():
    if not PRODUCTOS_PATH.exists():
        return []
    return json.loads(PRODUCTOS_PATH.read_text(encoding="utf-8"))


def _cliente():
    import anthropic
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


class ChatIn(BaseModel):
    mensaje: str
    historial: list[dict] = []
    sesion: str = "anon"


@app.post("/chat")
def chat(entrada: ChatIn, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    if _debe_cambiar_password(request):
        raise HTTPException(status_code=403, detail="Tenés que elegir una contraseña nueva antes de seguir")
    productos = _cargar_productos()
    if not productos:
        logger.warning("productos.json vacío o ausente")
        return {"respuesta": "Estoy actualizando los precios, escribime al WhatsApp "
                             f"{WHATSAPP} 🙌"}

    # Modo GRATIS (sin IA): buscador determinístico, costo cero.
    if not USAR_IA:
        texto, genero, datos = buscador.responder_sin_ia(entrada.mensaje, entrada.sesion, productos)
        return {"respuesta": texto, "genero": genero}

    # Tope de gasto por sesión: si ya lo superó, no llamamos a la IA (costo 0).
    if _gasto.get(entrada.sesion, 0.0) >= LIMITE_USD:
        logger.info("Sesión %s alcanzó el tope de USD %.2f", entrada.sesion, LIMITE_USD)
        return {"respuesta": "¡Gracias por tu interés! 😊 Para seguir con tu consulta y "
                             f"cerrar la compra, escribime directo por WhatsApp 👉 {WHATSAPP}"}
    try:
        texto, costo, datos = responder(entrada.mensaje, entrada.historial,
                                        productos, _cliente())
        _gasto[entrada.sesion] = _gasto.get(entrada.sesion, 0.0) + costo
        logger.info("Sesión %s: acumulado USD %.4f / %.2f",
                    entrada.sesion, _gasto[entrada.sesion], LIMITE_USD)
        genero = (datos or {}).get("genero", "")
    except Exception:
        logger.exception("Error al responder")
        texto = ("Tengo un problema técnico en este momento 😅. Escribime directo al "
                 f"WhatsApp {WHATSAPP} y te atiendo enseguida.")
        genero = ""
    return {"respuesta": texto, "genero": genero}


# --- Panel simple para ver el registro de clientes ---

class ClientesLoginIn(BaseModel):
    password: str


class MailingOfertaIn(BaseModel):
    productos: list[str]


class DescuentoItemIn(BaseModel):
    nombre: str
    cantidad: int = Field(ge=1)


class DescuentoCodigoIn(BaseModel):
    codigo: str
    items: list[DescuentoItemIn]


_DESCUENTO_MAILING_USD = 5


def _clientes_admin_activo(request: Request):
    return bool(request.session.get("clientes_admin_ok"))


def _formatear_entero_ar(valor):
    if valor is None:
        return "—"
    return f"{int(valor):,}".replace(",", ".")


def _precios_mail_producto(producto):
    usd = producto.get("usd")
    pesos = producto.get("pesos")
    transferencia = producto.get("transferencia")
    if usd in (None, "") or pesos in (None, "") or transferencia in (None, ""):
        return None

    usd = int(usd)
    pesos = int(pesos)
    transferencia = int(transferencia)
    usd_promo = max(usd - _DESCUENTO_MAILING_USD, 0)
    banco_usa_promo = math.ceil(usd_promo / 0.975)
    usdt_promo = math.ceil(usd_promo / 0.99)

    if usd > 0:
        pesos_promo = max(round(usd_promo * (pesos / usd)), 0)
        transferencia_promo = max(round(usd_promo * (transferencia / usd)), 0)
    else:
        pesos_promo = pesos
        transferencia_promo = transferencia

    return {
        "usd_promo": usd_promo,
        "banco_usa_promo": banco_usa_promo,
        "usdt_promo": usdt_promo,
        "pesos_promo": pesos_promo,
        "transferencia_promo": transferencia_promo,
    }


def _generar_codigo_descuento(client):
    alfabeto = string.ascii_uppercase + string.digits
    for _ in range(12):
        codigo = "TTRA-" + "".join(secrets.choice(alfabeto) for _ in range(8))
        existe = client.table("codigos_descuento").select("*").eq("code", codigo).execute().data
        if not existe:
            return codigo
    raise RuntimeError("No se pudo generar un código de descuento único")


def _descuento_codigo_row(client, cliente_id, codigo):
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return None
    filas = (
        client.table("codigos_descuento")
        .select("*")
        .eq("cliente_id", cliente_id)
        .eq("code", codigo)
        .execute()
        .data
    )
    if not filas:
        return None
    fila = filas[0]
    if not fila.get("activo") or fila.get("usado_en"):
        return None
    return fila


def _resolver_descuento_codigo(productos_catalogo, descuento_row, items):
    disponibles = {p.get("nombre", "").strip(): p for p in productos_catalogo if p.get("nombre")}
    elegibles = set(descuento_row.get("productos") or [])
    items_norm = []
    vistos = set()
    for item in items:
        nombre = (item.nombre or "").strip()
        if not nombre:
            continue
        items_norm.append({"nombre": nombre, "cantidad": int(item.cantidad)})
        vistos.add(nombre)

    productos_aplicables = [nombre for nombre in elegibles if nombre in disponibles and nombre in vistos]
    if not productos_aplicables:
        return None

    descuento_total = {"usd": 0, "pesos": 0, "transferencia": 0}
    cantidad_total = 0
    for item in items_norm:
        if item["nombre"] not in productos_aplicables:
            continue
        producto = disponibles[item["nombre"]]
        usd = int(producto.get("usd") or 0)
        pesos = int(producto.get("pesos") or 0)
        transferencia = int(producto.get("transferencia") or 0)
        if usd <= 0:
            continue
        qty = item["cantidad"]
        cantidad_total += qty
        descuento_usd_unit = min(int(descuento_row.get("descuento_usd") or _DESCUENTO_MAILING_USD), usd)
        descuento_total["usd"] += descuento_usd_unit * qty
        descuento_total["pesos"] += round(descuento_usd_unit * (pesos / usd)) * qty
        descuento_total["transferencia"] += round(descuento_usd_unit * (transferencia / usd)) * qty

    if cantidad_total == 0:
        return None

    return {
        "codigo": descuento_row["code"],
        "productos": sorted(productos_aplicables),
        "cantidad": cantidad_total,
        "descuento_usd_por_item": int(descuento_row.get("descuento_usd") or _DESCUENTO_MAILING_USD),
        "descuento": descuento_total,
    }


def _validar_descuento_codigo(cliente_id, entrada: DescuentoCodigoIn):
    fila = _descuento_codigo_row(get_client(), cliente_id, entrada.codigo)
    if not fila:
        return None
    return _resolver_descuento_codigo(_cargar_productos(), fila, entrada.items)


def _mensaje_error_codigos_descuento(exc: Exception):
    texto = str(exc).lower()
    if "codigos_descuento" in texto or "relation" in texto or "does not exist" in texto:
        return (
            "Falta crear la tabla codigos_descuento en Supabase antes de enviar este mailing."
        )
    return "No se pudo guardar el código de descuento del mailing."


@app.post("/admin/clientes/login")
def admin_clientes_login(entrada: ClientesLoginIn, request: Request):
    if entrada.password != ADMIN_CLIENTES_PASSWORD:
        return JSONResponse({"error": "Contraseña incorrecta"}, status_code=401)
    request.session["clientes_admin_ok"] = True
    return {"ok": True}


@app.post("/admin/clientes/logout")
def admin_clientes_logout(request: Request):
    request.session.pop("clientes_admin_ok", None)
    return {"ok": True}


@app.post("/admin/clientes/{cliente_id}/resetear-password")
def admin_clientes_resetear_password(cliente_id: str, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    try:
        client = get_client()
        resultado = cuentas.resetear_password_cliente(client, cliente_id)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        return JSONResponse({"error": "Supabase no está disponible en este momento"}, status_code=503)
    try:
        enviar_email(
            resultado["email"],
            "Tu nueva contraseña — The Tech Room Arg",
            f"<p>Se generó una nueva contraseña para tu cuenta:</p>"
            f"<p style='font-size:18px;font-weight:bold'>{html.escape(resultado['password'])}</p>"
            f"<p>Usala para ingresar en thetechroomarg.com y, si querés, cambiala después "
            f"desde tu cuenta.</p>",
        )
    except EnvioEmailError:
        return JSONResponse(
            {"error": "La contraseña se reseteó pero no se pudo enviar el mail"}, status_code=502
        )
    return {"ok": True}


@app.post("/admin/clientes/{cliente_id}/mailing-oferta")
def admin_clientes_mailing_oferta(cliente_id: str, entrada: MailingOfertaIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")

    client = get_client()
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    cliente = filas[0]
    email_cliente = (cliente.get("email") or "").strip()
    if not email_cliente:
        return JSONResponse({"error": "Este cliente no tiene email cargado"}, status_code=400)

    productos_catalogo = _cargar_productos()
    disponibles = {p.get("nombre", "").strip(): p for p in productos_catalogo if p.get("nombre")}
    pedidos = []
    vistos = set()
    for nombre in entrada.productos:
        nombre = (nombre or "").strip()
        if not nombre or nombre in vistos:
            continue
        vistos.add(nombre)
        pedidos.append(nombre)

    if not pedidos:
        return JSONResponse({"error": "Seleccioná al menos un producto"}, status_code=400)

    productos_disponibles = [nombre for nombre in pedidos if nombre in disponibles]
    productos_no_disponibles = [nombre for nombre in pedidos if nombre not in disponibles]

    if not productos_disponibles:
        return JSONResponse(
            {"error": "Ninguno de los productos seleccionados sigue disponible en el catálogo"},
            status_code=400,
        )

    nombre_cliente = f"{cliente.get('nombre', '')} {cliente.get('apellido', '')}".strip() or "cliente"
    productos_oferta = []
    productos_oferta_detalle = []
    for nombre in productos_disponibles:
        precios = _precios_mail_producto(disponibles[nombre])
        if not precios:
            continue
        productos_oferta.append(nombre)
        productos_oferta_detalle.append((nombre, precios))

    if not productos_oferta_detalle:
        return JSONResponse(
            {"error": "Los productos seleccionados no tienen precios válidos para armar la oferta"},
            status_code=400,
        )

    try:
        codigo = _generar_codigo_descuento(client)
        client.table("codigos_descuento").insert({
            "cliente_id": cliente_id,
            "code": codigo,
            "productos": productos_oferta,
            "descuento_usd": _DESCUENTO_MAILING_USD,
            "activo": False,
        }).execute()
    except Exception as e:
        logger.exception("No se pudo crear el código de descuento para mailing")
        return JSONResponse({"error": _mensaje_error_codigos_descuento(e)}, status_code=503)

    bloques_producto = []
    for nombre, precios in productos_oferta_detalle:
        link_producto = _public_producto_mailing_url(request, nombre, codigo)
        bloques_producto.append(
            "<li>"
            f"<strong>{html.escape(nombre)}</strong><br>"
            f"Promo especial: U$D {_DESCUENTO_MAILING_USD} de descuento.<br>"
            f"USD billete: U$D {precios['usd_promo']}<br>"
            f"Dólar banco USA: U$D {precios['banco_usa_promo']}<br>"
            f"USDT: U$D {precios['usdt_promo']}<br>"
            f"Pesos contado: $ {_formatear_entero_ar(precios['pesos_promo'])}<br>"
            f"Transferencia en pesos: $ {_formatear_entero_ar(precios['transferencia_promo'])}<br>"
            f'<a href="{html.escape(link_producto)}" '
            "style=\"display:inline-block;margin-top:8px;padding:10px 14px;background:#c8102e;"
            "color:#fff;text-decoration:none;border-radius:8px;font-weight:700\">"
            "Abrir este producto en el carrito con mi descuento"
            "</a>"
            "</li>"
        )

    items_html = "".join(bloques_producto)
    html_mail = (
        f"<p>Hola {html.escape(nombre_cliente)},</p>"
        f"<p>Estuve viendo que miraste estos productos en The Tech Room Arg y te ofrezco "
        f"un descuento de U$D {_DESCUENTO_MAILING_USD} por producto si avanzás hoy:</p>"
        f"<ul>{items_html}</ul>"
        f"<p>Tu código de descuento es: <strong>{html.escape(codigo)}</strong></p>"
        f"<p>Podés cargarlo directamente en el checkout del carrito y se van a descontar "
        f"U$D {_DESCUENTO_MAILING_USD} por cada producto incluido en este mail.</p>"
        f"<p>Si te interesa alguno, respondé este mail y te armo la propuesta.</p>"
        f"<p>Saludos,<br>The Tech Room Arg</p>"
    )
    try:
        enviar_email(
            email_cliente,
            "Descuento especial en productos que viste — The Tech Room Arg",
            html_mail,
        )
    except EnvioEmailError as e:
        return JSONResponse({"error": str(e)}, status_code=502)

    try:
        client.table("codigos_descuento").update({"activo": True}).eq("code", codigo).execute()
    except Exception as e:
        logger.exception("Se envió el mailing pero no se pudo activar el código de descuento")
        return JSONResponse(
            {"error": "El mail salió, pero no se pudo activar el código de descuento en Supabase."},
            status_code=503,
        )

    return {
        "ok": True,
        "codigo": codigo,
        "enviados": len(productos_oferta),
        "omitidos": productos_no_disponibles,
    }


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


_ADMIN_CLIENTES_ESTILO = """
<style>
  body { font-family: 'Segoe UI', system-ui, sans-serif; background:#111318; margin:0;
         min-height:100vh; display:flex; align-items:center; justify-content:center; padding:20px; box-sizing:border-box; }
  .tarjeta { background:#1b1e24; border-radius:14px; padding:28px 24px; width:100%; max-width:340px;
             box-shadow:0 10px 30px rgba(0,0,0,0.5); box-sizing:border-box; border:1px solid #2a2e37; }
  .tarjeta h1 { margin:0 0 16px; color:#f2f4f8; font-size:20px; }
  .tarjeta input { width:100%; height:42px; padding:0 12px; font-size:15px; box-sizing:border-box;
                   border:2px solid #333844; border-radius:10px; margin-bottom:10px;
                   background:#12141a; color:#f2f4f8; }
  .tarjeta button { width:100%; height:44px; border:none; border-radius:10px; background:#c8102e;
                    color:#fff; font-size:15px; font-weight:800; cursor:pointer; }
  .error { color:#ff6b6b; font-size:13px; margin:0 0 10px; }
  .panel { background:#1b1e24; border-radius:14px; padding:20px; max-width:1000px; width:100%;
           margin:20px auto; box-shadow:0 10px 30px rgba(0,0,0,0.5); box-sizing:border-box;
           border:1px solid #2a2e37; }
  .panel-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }
  .panel-header h1 { color:#f2f4f8; font-size:20px; margin:0; }
  .panel-header button { border:none; background:#3a3f4b; color:#f2f4f8; border-radius:8px;
                          padding:8px 14px; cursor:pointer; font-weight:700; }
  table { width:100%; border-collapse:collapse; font-size:14px; color:#dfe2e8; }
  th, td { text-align:left; padding:8px 10px; border-bottom:1px solid #2a2e37; }
  th { color:#f2f4f8; }
  .vacio { color:#9aa0ab; text-align:center; padding:30px; }
  .btn-historial { display:inline-flex; color:#dfe2e8; }
  .btn-historial:hover { color:#fff; }
  .panel-header a.volver { color:#dfe2e8; text-decoration:none; font-weight:700; font-size:14px; }
  .panel-header a.volver:hover { color:#fff; }
  .subseccion { margin-top:22px; }
  .subseccion h2 { color:#f2f4f8; font-size:17px; margin:0 0 10px; }
  .subseccion p { margin:0 0 12px; color:#9aa0ab; font-size:13px; }
  .acciones-mailing { display:flex; align-items:center; gap:10px; margin-top:16px; flex-wrap:wrap; }
  .acciones-mailing button { border:none; background:#c8102e; color:#fff; border-radius:8px;
                             padding:10px 14px; cursor:pointer; font-weight:700; }
  .acciones-mailing button[disabled] { opacity:.45; cursor:not-allowed; }
  .acciones-mailing span { color:#9aa0ab; font-size:13px; }
  .col-check { width:40px; text-align:center; }
  .col-check input { width:16px; height:16px; accent-color:#c8102e; cursor:pointer; }
</style>
"""


@app.get("/admin/clientes", response_class=HTMLResponse)
def admin_clientes(request: Request):
    if not _clientes_admin_activo(request):
        return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Clientes — Ingresar</title>{_ADMIN_CLIENTES_ESTILO}</head><body>
<div class="tarjeta">
  <h1>Panel de clientes</h1>
  <p id="err" class="error" style="display:none"></p>
  <input id="pass" type="password" placeholder="Contraseña" autofocus>
  <button id="btn">Ingresar</button>
</div>
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
</body></html>"""

    client = get_client()
    filas_clientes = client.table("clientes").select("*").execute().data
    clientes = [
        {
            "id": c.get("id", ""),
            "nombre": f"{c.get('nombre', '')} {c.get('apellido', '')}".strip(),
            "celular": c.get("celular", ""),
            "fecha": c.get("creado_en", ""),
            "tiene_cuenta": bool(c.get("auth_id")),
        }
        for c in filas_clientes
    ]
    clientes.sort(key=lambda r: r.get("fecha", ""), reverse=True)
    if not clientes:
        filas_html = '<tr><td colspan="5" class="vacio">Todavía no hay clientes registrados.</td></tr>'
    else:
        def _celda_cuenta(c):
            if not c.get("tiene_cuenta"):
                return "—"
            id_seguro = html.escape(c.get("id", ""))
            return f'<button class="btn-reset" data-id="{id_seguro}">Resetear contraseña</button>'

        filas_html = "".join(
            f"<tr><td>{html.escape(c.get('nombre', ''))}</td>"
            f"<td>{html.escape(c.get('celular', ''))}</td>"
            f"<td>{html.escape(c.get('fecha', ''))}</td>"
            f'<td><a class="btn-historial" href="/admin/clientes/{html.escape(c.get("id", ""))}/historial" '
            f'title="Ver historial de pedidos" aria-label="Ver historial de pedidos">{_ICONO_OJO}</a></td>'
            f"<td>{_celda_cuenta(c)}</td></tr>"
            for c in clientes
        )
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Clientes</title>{_ADMIN_CLIENTES_ESTILO}</head><body>
<div class="panel">
  <div class="panel-header">
    <h1>Clientes ({len(clientes)})</h1>
    <button id="salir">Cerrar sesión</button>
  </div>
  <table>
    <thead><tr><th>Nombre</th><th>Celular</th><th>Fecha</th><th>Historial</th><th>Cuenta</th></tr></thead>
    <tbody>{filas_html}</tbody>
  </table>
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
</script>
</body></html>"""


@app.get("/admin/clientes/{cliente_id}/historial", response_class=HTMLResponse)
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
<title>Historial — {html.escape(nombre_cliente)}</title>{_ADMIN_CLIENTES_ESTILO}</head><body>
<div class="panel">
  <div class="panel-header">
    <h1>Historial de {html.escape(nombre_cliente) or "cliente"}</h1>
    <a class="volver" href="/admin/clientes">← Volver</a>
  </div>
  <section class="subseccion">
    <h2>Pedidos confirmados</h2>
    <p>Acá ves todo lo que el cliente cargó al carrito y confirmó.</p>
    <table>
      <thead><tr><th class="col-check"></th><th>Fecha</th><th>Día</th><th>Hora</th><th>Productos</th></tr></thead>
      <tbody>{filas_pedidos_html}</tbody>
    </table>
  </section>
  <section class="subseccion">
    <h2>Productos más consultados</h2>
    <p>Ranking por cantidad de vistas de este cliente, ordenado de mayor a menor para decidir mejor el mailing.</p>
    <table>
      <thead><tr><th class="col-check"></th><th>Producto</th><th>Vistas</th><th>Última vista</th></tr></thead>
      <tbody>{filas_consultados_html}</tbody>
    </table>
  </section>
  <section class="subseccion">
    <h2>Historial de vistas</h2>
    <p>Acá ves todas las interacciones de navegación, vistas e íconos que tocó el cliente.</p>
    <table>
      <thead><tr><th class="col-check"></th><th>Fecha</th><th>Día</th><th>Hora</th><th>Evento</th><th>Detalle</th></tr></thead>
      <tbody>{filas_interacciones_html}</tbody>
    </table>
  </section>
  <div class="acciones-mailing">
    <button id="btn-preparar-mailing" {'disabled' if not email_cliente else ''}>Enviar mailing</button>
    <span id="mailing-ayuda">{'Seleccioná productos o vistas y se envía una oferta por mail si siguen disponibles en catálogo.' if email_cliente else 'Este cliente no tiene email disponible para mailing.'}</span>
  </div>
</div>
<script>
const btnMailing = document.getElementById("btn-preparar-mailing");
const checksMailing = [...document.querySelectorAll(".chk-mailing")];
const emailCliente = {json.dumps(cliente.get("email", "") or "")};
const nombreCliente = {json.dumps(nombre_cliente or "cliente")};
const clienteId = {json.dumps(cliente.get("id", ""))};

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
</body></html>"""


class RegistroIn(BaseModel):
    nombre: str
    apellido: str
    celular: str
    email: EmailStr
    password: str = Field(min_length=8)


class LoginIn(BaseModel):
    email: str
    password: str


class CompletarSignupIn(BaseModel):
    access_token: str | None = None
    token_hash: str | None = None
    type: str | None = None


def _sesion_activa(request: Request):
    return bool(request.session.get("cliente_id"))


def _debe_cambiar_password(request: Request):
    return bool(request.session.get("debe_cambiar_password"))


def _anon_id_request(request: Request):
    return (request.headers.get("X-TTRA-ANON-ID") or "").strip() or None


def _sesion_desde_auth_user(request: Request, auth_id: str):
    filas = get_client().table("clientes").select("*").eq("auth_id", auth_id).execute().data
    if not filas:
        return None
    cliente = filas[0]
    request.session["cliente_id"] = cliente["id"]
    request.session["cliente_nombre"] = cliente["nombre"]
    request.session["debe_cambiar_password"] = bool(cliente.get("debe_cambiar_password"))
    return cliente


def _vincular_interacciones_anonimas(client, request: Request, cliente_id: str):
    anon_id = _anon_id_request(request)
    if not anon_id:
        return
    try:
        interacciones.vincular_interacciones_anonimas(client, anon_id, cliente_id)
    except Exception:
        logger.exception("No se pudieron vincular interacciones anónimas para %s", cliente_id)


@app.get("/login")
def pagina_login():
    return FileResponse(str(BASE / "static" / "login.html"))


@app.get("/registro")
def pagina_registro():
    return FileResponse(str(BASE / "static" / "login.html"))


@app.post("/registro")
def registro(entrada: RegistroIn, request: Request):
    try:
        client = get_client()
        cliente = cuentas.registrar_cliente(
            client, entrada.nombre, entrada.apellido, entrada.celular,
            entrada.email, entrada.password,
            email_redirect_to=_public_login_url(request),
        )
    except (cuentas.CelularDuplicadoError, cuentas.EmailDuplicadoError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo completar el registro (¿Supabase no disponible?)")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    if cliente["requiere_confirmacion_email"]:
        _vincular_interacciones_anonimas(client, request, cliente["id"])
        request.session.clear()
        return {
            "ok": True,
            "requiere_confirmacion_email": True,
            "email_redirect_to": _public_login_url(request),
        }
    request.session["cliente_id"] = cliente["id"]
    request.session["cliente_nombre"] = cliente["nombre"]
    request.session["debe_cambiar_password"] = False
    _vincular_interacciones_anonimas(client, request, cliente["id"])
    return {"ok": True, "requiere_confirmacion_email": False}


@app.post("/login")
def login(entrada: LoginIn, request: Request):
    try:
        client_datos = get_client()
        cliente = cuentas.login_cliente(get_client(), client_datos, entrada.email, entrada.password)
    except cuentas.EmailNoConfirmadoError as e:
        return JSONResponse({"error": str(e)}, status_code=403)
    except Exception:
        logger.exception("No se pudo completar el login (¿Supabase no disponible?)")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    if cliente is None:
        return JSONResponse({"error": "Usuario o contraseña incorrectos"}, status_code=401)
    request.session["cliente_id"] = cliente["id"]
    request.session["cliente_nombre"] = cliente["nombre"]
    request.session["debe_cambiar_password"] = cliente["debe_cambiar_password"]
    _vincular_interacciones_anonimas(client_datos, request, cliente["id"])
    return {"ok": True, "debe_cambiar_password": cliente["debe_cambiar_password"]}


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.post("/auth/completar-signup")
def auth_completar_signup(entrada: CompletarSignupIn, request: Request):
    client = get_client()
    auth_user = None
    try:
        if entrada.access_token:
            auth_user = client.auth.get_user(entrada.access_token).user
        elif entrada.token_hash and entrada.type:
            auth_resp = client.auth.verify_otp({
                "token_hash": entrada.token_hash,
                "type": entrada.type,
            })
            auth_user = getattr(auth_resp, "user", None)
        else:
            return JSONResponse({"error": "Faltan datos de verificación"}, status_code=400)
    except Exception:
        logger.exception("No se pudo completar la verificación del signup")
        return JSONResponse({"error": "No se pudo validar el link de verificación"}, status_code=400)

    if not auth_user:
        return JSONResponse({"error": "No se pudo validar el usuario verificado"}, status_code=400)

    cliente = _sesion_desde_auth_user(request, auth_user.id)
    if not cliente:
        return JSONResponse({"error": "La cuenta fue verificada pero no existe el cliente asociado"}, status_code=404)

    _vincular_interacciones_anonimas(client, request, cliente["id"])
    return {"ok": True, "debe_cambiar_password": bool(cliente.get("debe_cambiar_password"))}


class CambiarPasswordObligatorioIn(BaseModel):
    password: str = Field(min_length=8)


@app.post("/cambiar-password-obligatorio")
def cambiar_password_obligatorio(entrada: CambiarPasswordObligatorioIn, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        cuentas.cambiar_password_obligatorio(get_client(), request.session["cliente_id"], entrada.password)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo cambiar la contraseña obligatoria (¿Supabase no disponible?)")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    request.session["debe_cambiar_password"] = False
    return {"ok": True}


@app.get("/api/me")
def api_me(request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        cliente = cuentas.obtener_cliente(get_client(), request.session["cliente_id"])
    except Exception:
        logger.exception("No se pudo obtener el perfil del cliente")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return cliente


class ActualizarMeIn(BaseModel):
    nombre: str
    apellido: str
    celular: str


@app.put("/api/me")
def api_me_actualizar(entrada: ActualizarMeIn, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        cliente = cuentas.actualizar_cliente(
            get_client(), request.session["cliente_id"],
            entrada.nombre, entrada.apellido, entrada.celular,
        )
    except (cuentas.CelularDuplicadoError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo actualizar el perfil del cliente")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    return cliente


class CambiarPasswordPropioIn(BaseModel):
    password_actual: str
    password_nueva: str = Field(min_length=8)


@app.post("/api/me/password")
def api_me_password(entrada: CambiarPasswordPropioIn, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        cuentas.cambiar_password_propio(
            get_client(), get_client(), request.session["cliente_id"],
            entrada.password_actual, entrada.password_nueva,
        )
    except cuentas.PasswordActualIncorrectaError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo cambiar la contraseña del cliente")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    return {"ok": True}


@app.get("/perfil")
def pagina_perfil(request: Request):
    if not _sesion_activa(request) or _debe_cambiar_password(request):
        return RedirectResponse("/login.html")
    return FileResponse(str(BASE / "static" / "perfil.html"))


class PedidoIn(BaseModel):
    productos: list[str]


class InteraccionIn(BaseModel):
    tipo_evento: str
    producto_nombre: str | None = None
    categoria: str | None = None
    marca: str | None = None
    session_id: str | None = None
    metadata: dict = Field(default_factory=dict)


_EVENTOS_INTERACCION_PERMITIDOS = {"view_item", "select_product", "view_product"}


@app.post("/api/interacciones")
def api_interacciones(entrada: InteraccionIn, request: Request):
    if entrada.tipo_evento not in _EVENTOS_INTERACCION_PERMITIDOS:
        return {"ok": True}
    tipo_evento = (
        "view_item"
        if entrada.tipo_evento in {"select_product", "view_product"}
        else entrada.tipo_evento
    )
    anon_id = _anon_id_request(request)
    cliente_id = request.session.get("cliente_id")
    if not cliente_id and not anon_id:
        return {"ok": True}
    try:
        interacciones.guardar_interaccion(
            get_client(),
            tipo_evento,
            cliente_id=cliente_id,
            anon_id=anon_id,
            session_id=entrada.session_id,
            producto_nombre=entrada.producto_nombre,
            categoria=None,
            marca=None,
            metadata={},
        )
    except Exception:
        logger.exception("No se pudo guardar interacción %s", tipo_evento)
    return {"ok": True}


@app.post("/api/pedidos")
def api_pedidos(entrada: PedidoIn, request: Request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=401, detail="Sesión requerida")
    if _debe_cambiar_password(request):
        raise HTTPException(status_code=403, detail="Tenés que elegir una contraseña nueva antes de seguir")
    pedidos.guardar_pedido(get_client(), cliente_id, entrada.productos)
    return {"ok": True}


@app.post("/api/descuentos/validar")
def api_descuentos_validar(entrada: DescuentoCodigoIn, request: Request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=401, detail="Sesión requerida")
    if _debe_cambiar_password(request):
        raise HTTPException(status_code=403, detail="Tenés que elegir una contraseña nueva antes de seguir")
    descuento = _validar_descuento_codigo(cliente_id, entrada)
    if not descuento:
        return JSONResponse({"error": "Código inválido o sin productos aplicables para este carrito"}, status_code=400)
    return {"ok": True, **descuento}


@app.post("/api/descuentos/consumir")
def api_descuentos_consumir(entrada: DescuentoCodigoIn, request: Request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=401, detail="Sesión requerida")
    if _debe_cambiar_password(request):
        raise HTTPException(status_code=403, detail="Tenés que elegir una contraseña nueva antes de seguir")
    client = get_client()
    fila = _descuento_codigo_row(client, cliente_id, entrada.codigo)
    if not fila:
        return JSONResponse({"error": "Código inválido o ya utilizado"}, status_code=400)
    descuento = _resolver_descuento_codigo(_cargar_productos(), fila, entrada.items)
    if not descuento:
        return JSONResponse({"error": "El código no aplica a los productos actuales del carrito"}, status_code=400)
    client.table("codigos_descuento").update({"usado_en": datetime.utcnow().isoformat()}).eq("code", fila["code"]).execute()
    return {"ok": True, **descuento}


@app.get("/catalogo")
def pagina_catalogo(request: Request):
    if not _sesion_activa(request) or _debe_cambiar_password(request):
        return RedirectResponse("/login.html")
    return FileResponse(str(BASE / "static" / "catalogo.html"))


@app.get("/api/catalogo")
def api_catalogo():
    productos = _cargar_productos()
    if not productos:
        return {"secciones": {s: [] for s in catalogo.SECCIONES},
                "mensaje": "Estamos actualizando los precios"}
    return {"secciones": catalogo.secciones_catalogo(productos)}


@app.get("/api/recomendados")
def api_recomendados(request: Request, limit: int = 16):
    productos = _cargar_productos()
    if not productos:
        return {"productos": []}

    filas_interacciones = []
    cliente_id = request.session.get("cliente_id")
    anon_id = _anon_id_request(request)
    if cliente_id or anon_id:
        try:
            query = get_client().table("interacciones_cliente").select("*")
            if cliente_id:
                filas_interacciones = query.eq("cliente_id", cliente_id).execute().data
            else:
                filas_interacciones = query.eq("anon_id", anon_id).execute().data
        except Exception:
            logger.exception("No se pudieron cargar interacciones para recomendaciones")

    limite = max(1, min(limit, 24))
    return {
        "productos": interacciones.recomendar_productos(
            productos, filas_interacciones, limite=limite
        )
    }


# Cotización del dólar en Córdoba usada como referencia en el sitio (a mano,
# actualizar acá cuando cambie — es la misma fuente única que usa el catálogo).
COTIZACION_DOLAR = 1560


@app.get("/api/cotizacion")
def api_cotizacion():
    return {"valor": COTIZACION_DOLAR}


NOTICIAS_RSS_URL = (
    "https://news.google.com/rss/search?q=politica%20OR%20economia%20OR%20finanzas"
    "&hl=es-419&gl=AR&ceid=AR:es-419"
)
NOTICIAS_TTL_SEG = 600  # 10 minutos: evita golpear Google News en cada visita
_noticias_cache = {"titulares": [], "actualizado": 0.0}


def _separar_titulo_y_fuente(titulo_crudo, link):
    # Google News agrega " - Nombre del medio" al final de cada título.
    m = re.match(r"^(.*)\s+-\s+([^-]+)$", titulo_crudo.strip())
    if not m:
        return {"titulo": titulo_crudo.strip(), "fuente": "", "link": link}
    return {"titulo": m.group(1).strip(), "fuente": m.group(2).strip(), "link": link}


@app.get("/api/noticias")
def api_noticias():
    ahora = time.time()
    if ahora - _noticias_cache["actualizado"] < NOTICIAS_TTL_SEG and _noticias_cache["titulares"]:
        return {"titulares": _noticias_cache["titulares"]}
    try:
        r = httpx.get(NOTICIAS_RSS_URL, timeout=6, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        raiz = ET.fromstring(r.text)
        titulares = [
            _separar_titulo_y_fuente(item.findtext("title", ""), item.findtext("link", ""))
            for item in raiz.findall(".//item")
        ]
        titulares = [t for t in titulares if t["titulo"]][:12]
        if titulares:
            _noticias_cache["titulares"] = titulares
            _noticias_cache["actualizado"] = ahora
    except Exception:
        logger.exception("No se pudieron obtener las noticias")
    return {"titulares": _noticias_cache["titulares"]}


@app.post("/admin/productos")
async def admin_subir_productos(request: Request, x_admin_token: str = Header(default="")):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=503, detail="ADMIN_TOKEN no configurado en el servidor")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Token inválido")
    try:
        productos = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body inválido: se espera JSON")
    if not isinstance(productos, list):
        raise HTTPException(status_code=400, detail="Se espera una lista de productos")
    PRODUCTOS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PRODUCTOS_PATH.write_text(json.dumps(productos, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "productos": len(productos)}


@app.get("/")
def pagina_inicio(request: Request):
    if _sesion_activa(request) and _debe_cambiar_password(request):
        return FileResponse(str(BASE / "static" / "login.html"))
    return FileResponse(str(BASE / "static" / "index.html"))


# html=False a propósito: con html=True, StaticFiles resuelve cualquier
# path que apunte a un directorio (incluida la raíz) sirviendo su
# index.html automáticamente, sin pasar por gate_paginas_html ni por la
# ruta explícita GET "/" — es la causa raíz del bypass que encontramos.
# GET "/" ya tiene su propia ruta explícita arriba; los .html reales
# (index.html, catalogo.html, login.html) se siguen sirviendo igual porque
# StaticFiles los sirve por nombre de archivo exacto, con o sin html=True.
app.mount("/", StaticFiles(directory=str(BASE / "static"), html=False), name="static")
