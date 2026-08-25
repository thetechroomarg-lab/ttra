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
import uuid
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Literal
from urllib.parse import urlencode, urlparse

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.sessions import SessionMiddleware

from web import buscador, catalogo, cuentas, entregas, interacciones, pedidos, recibos
from web.email_util import EnvioEmailError, enviar_email
from web.productos import resolver_proveedor
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
# No se sirve al navegador: se genera junto al catálogo para enriquecer el
# detalle administrativo de cada pedido sin exponer proveedores al público.
PROVEEDORES_PATH = Path(os.environ.get("PROVEEDORES_PATH", str(BASE / "proveedores.json")))
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


@app.get("/api/configuracion-publica")
async def configuracion_publica():
    """Configuración que el navegador necesita para servicios públicos.

    La clave de Maps se entrega al navegador porque la API de JavaScript la
    requiere allí. Su seguridad depende de las restricciones configuradas en
    Google Cloud, no de ocultarla en el código cliente.
    """
    return {"google_maps_api_key": os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()}


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
    url = f"{_public_app_base_url(request)}/login.html"
    if request.query_params.get("modo") == "fallout":
        return f"{url}?modo=fallout"
    return url


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


def _cargar_proveedores():
    if not PROVEEDORES_PATH.exists():
        return {}
    return json.loads(PROVEEDORES_PATH.read_text(encoding="utf-8"))


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


class ClientesSeleccionadosIn(BaseModel):
    cliente_ids: list[str] = Field(min_length=1, max_length=100)


class MailingMasivoIn(ClientesSeleccionadosIn):
    mensaje: str = Field(min_length=1, max_length=5000)


def _nuevo_recibo_id(client):
    return client.rpc("siguiente_numero_recibo").execute().data


def _descargar_fotos_series(client, pedido):
    fotos = []
    for ruta in pedido.get("fotos_series") or []:
        try:
            contenido = client.storage.from_("recibos-series").download(ruta)
        except Exception:
            continue
        if contenido:
            fotos.append(contenido)
    return fotos


class DescuentoItemIn(BaseModel):
    nombre: str
    cantidad: int = Field(ge=1)


class DescuentoCodigoIn(BaseModel):
    codigo: str
    items: list[DescuentoItemIn]


class CodigoPromoIn(BaseModel):
    codigo: str


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


def _codigo_promo_row(client, codigo):
    codigo = (codigo or "").strip().upper()
    if not codigo:
        return None
    filas = client.table("codigos_promo").select("*").eq("code", codigo).execute().data
    if not filas:
        return None
    fila = filas[0]
    if not fila.get("activo"):
        return None
    if int(fila.get("usos_actuales") or 0) >= int(fila.get("usos_maximos") or 0):
        return None
    return fila


def _mensaje_error_codigos_descuento(exc: Exception):
    texto = str(exc).lower()
    if "codigos_descuento" in texto or "relation" in texto or "does not exist" in texto:
        return (
            "Falta crear la tabla codigos_descuento en Supabase antes de enviar este mailing."
        )
    return "No se pudo guardar el código de descuento del mailing."


class _SanitizadorHtmlMailing(HTMLParser):
    """Conserva solo el formato seguro que puede escribirse desde el admin."""

    _ETIQUETAS = {"p", "div", "br", "strong", "b", "em", "i", "ul", "ol", "li", "a"}
    _PELIGROSAS = {"script", "style", "iframe", "object", "embed"}
    _NORMALIZADAS = {"b": "strong", "i": "em", "div": "p"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.partes = []
        self.abiertas = []
        self._bloqueadas = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in self._PELIGROSAS:
            self._bloqueadas += 1
            return
        if self._bloqueadas or tag not in self._ETIQUETAS:
            return
        tag = self._NORMALIZADAS.get(tag, tag)
        if tag == "br":
            self.partes.append("<br>")
            return
        if tag == "a":
            href = dict(attrs).get("href", "").strip()
            esquema = urlparse(href).scheme.lower()
            if esquema not in {"http", "https", "mailto"}:
                self.partes.append("<a>")
            else:
                self.partes.append(f'<a href="{html.escape(href, quote=True)}">')
        else:
            self.partes.append(f"<{tag}>")
        self.abiertas.append(tag)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self._PELIGROSAS:
            self._bloqueadas = max(0, self._bloqueadas - 1)
            return
        if self._bloqueadas or tag not in self._ETIQUETAS or tag == "br":
            return
        tag = self._NORMALIZADAS.get(tag, tag)
        if tag in self.abiertas:
            while self.abiertas:
                abierta = self.abiertas.pop()
                self.partes.append(f"</{abierta}>")
                if abierta == tag:
                    break

    def handle_data(self, data):
        if not self._bloqueadas:
            self.partes.append(html.escape(data))

    def resultado(self):
        while self.abiertas:
            self.partes.append(f"</{self.abiertas.pop()}>")
        return "".join(self.partes).strip()


def _sanitizar_html_mailing(mensaje: str):
    sanitizador = _SanitizadorHtmlMailing()
    sanitizador.feed(mensaje)
    sanitizador.close()
    return sanitizador.resultado()


def _primer_nombre_cliente(cliente):
    nombre = str(cliente.get("nombre") or "").strip().split()
    return nombre[0] if nombre else "cliente"


def _html_mailing_para_cliente(mensaje_html: str, cliente):
    primer_nombre = html.escape(_primer_nombre_cliente(cliente))
    contenido = mensaje_html.replace("{primer nombre}", primer_nombre)
    return f"<p>Hola {primer_nombre},</p>{contenido}<p>Saludos,<br>Vlad.</p>"


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


def _clientes_seleccionados(client, cliente_ids: list[str]):
    ids = list(dict.fromkeys(cliente_id for cliente_id in cliente_ids if cliente_id))
    clientes_por_id = {
        cliente.get("id"): cliente
        for cliente in client.table("clientes").select("*").execute().data
    }
    if any(cliente_id not in clientes_por_id for cliente_id in ids):
        raise ValueError("Uno o más clientes ya no existen")
    return [clientes_por_id[cliente_id] for cliente_id in ids]


@app.post("/admin/clientes/acciones/enviar-mail")
def admin_clientes_enviar_mail_masivo(entrada: MailingMasivoIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    try:
        clientes = _clientes_seleccionados(get_client(), entrada.cliente_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    mensaje_html = _sanitizar_html_mailing(entrada.mensaje)
    if not re.sub(r"<[^>]+>", "", mensaje_html).strip():
        raise HTTPException(status_code=422, detail="El mensaje no puede estar vacío")
    enviados = 0
    fallidos = 0
    for cliente in clientes:
        try:
            enviar_email(
                cliente["email"],
                "Novedades de The Tech Room Arg",
                _html_mailing_para_cliente(mensaje_html, cliente),
            )
            enviados += 1
        except EnvioEmailError:
            logger.exception("No se pudo enviar mail masivo a %s", cliente.get("id"))
            fallidos += 1
    return {"ok": True, "enviados": enviados, "fallidos": fallidos}


@app.post("/admin/clientes/acciones/eliminar")
def admin_clientes_eliminar_masivo(entrada: ClientesSeleccionadosIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    try:
        clientes = _clientes_seleccionados(client, entrada.cliente_ids)
        for cliente in clientes:
            cuentas.eliminar_cliente(client, cliente["id"])
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception:
        logger.exception("No se pudo completar la eliminación masiva de clientes")
        return JSONResponse({"error": "No se pudieron eliminar todas las cuentas"}, status_code=503)
    return {"ok": True, "eliminados": len(clientes)}


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


@app.post("/admin/clientes/{cliente_id}/eliminar")
def admin_clientes_eliminar(cliente_id: str, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    try:
        cuentas.eliminar_cliente(get_client(), cliente_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception:
        logger.exception("No se pudo eliminar el cliente %s", cliente_id)
        return JSONResponse({"error": "No se pudo eliminar la cuenta en este momento"}, status_code=503)
    return {"ok": True}


@app.post("/admin/pedidos/{pedido_id}/recibo")
async def admin_pedido_enviar_recibo(pedido_id: str, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    filas_pedido = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas_pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedido = filas_pedido[0]
    if not pedido.get("detalle") or pedido.get("total_usd") is None:
        return JSONResponse(
            {"error": "Este pedido histórico no tiene el detalle necesario para emitir un recibo"},
            status_code=400,
        )
    filas_cliente = client.table("clientes").select("*").eq("id", pedido.get("cliente_id")).execute().data
    if not filas_cliente or not (filas_cliente[0].get("email") or "").strip():
        return JSONResponse({"error": "El cliente no tiene un email disponible"}, status_code=400)
    cliente = filas_cliente[0]
    recibo_id = pedido.get("recibo_id") or _nuevo_recibo_id(client)
    ahora_recibo = datetime.now(timezone.utc).isoformat()
    emitido_en = pedido.get("recibo_emitido_en") or pedido.get("recibo_enviado_en") or ahora_recibo
    pedido_para_mail = {**pedido, "recibo_id": recibo_id, "recibo_emitido_en": emitido_en}
    try:
        formulario = await request.form() if request.headers.get("content-type", "").startswith("multipart/") else {}
        adjuntos_fotos = []
        fotos_pdf = []
        fotos_guardadas = list(pedido.get("fotos_series") or [])
        for foto in formulario.getlist("fotos")[:10] if formulario else []:
            if not getattr(foto, "filename", None):
                continue
            contenido = await foto.read()
            if not contenido or len(contenido) > 2_500_000:
                return JSONResponse({"error": "Cada foto comprimida debe pesar menos de 2,5 MB"}, status_code=400)
            nombre = f"serie-{uuid.uuid4().hex}.jpg"
            ruta = f"pedidos/{pedido_id}/{nombre}"
            client.storage.from_("recibos-series").upload(ruta, contenido, {"content-type": "image/jpeg"})
            fotos_guardadas.append(ruta)
            fotos_pdf.append(contenido)
            adjuntos_fotos.append({"filename": nombre, "content": contenido})
        pdf_adjunto = recibos.pdf_recibo(cliente, pedido_para_mail, fotos=fotos_pdf)
        enviar_email(
            cliente["email"],
            f"Recibo {recibo_id} — The Tech Room Arg",
            recibos.html_recibo(cliente, pedido_para_mail),
            [{"filename": f"recibo-{recibo_id}.pdf", "content": pdf_adjunto}, *adjuntos_fotos],
        )
    except EnvioEmailError as e:
        return JSONResponse({"error": str(e)}, status_code=502)
    client.table("pedidos").update({
        "recibo_id": recibo_id,
        "recibo_emitido_en": emitido_en,
        "recibo_enviado_en": ahora_recibo,
        "fotos_series": fotos_guardadas,
    }).eq("id", pedido_id).execute()
    return {"ok": True, "recibo_id": recibo_id, "reenviado": bool(pedido.get("recibo_enviado_en"))}


@app.get("/admin/pedidos/{pedido_id}/recibo.pdf")
def admin_pedido_pdf_recibo(pedido_id: str, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedido = filas[0]
    if not pedido.get("recibo_enviado_en"):
        return JSONResponse({"error": "Este pedido todavía no tiene un recibo emitido"}, status_code=400)
    if not pedido.get("detalle") or pedido.get("total_usd") is None:
        return JSONResponse({"error": "Este pedido no tiene el detalle necesario para el recibo"}, status_code=400)
    emitido_en = pedido.get("recibo_emitido_en") or pedido["recibo_enviado_en"]
    if not pedido.get("recibo_emitido_en"):
        client.table("pedidos").update({"recibo_emitido_en": emitido_en}).eq("id", pedido_id).execute()
    clientes = client.table("clientes").select("*").eq("id", pedido.get("cliente_id")).execute().data
    if not clientes:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    contenido = recibos.pdf_recibo(
        clientes[0],
        {**pedido, "recibo_emitido_en": emitido_en},
        fotos=_descargar_fotos_series(client, pedido),
    )
    nombre = f"recibo-{pedido.get('recibo_id') or pedido_id}.pdf"
    return Response(contenido, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{nombre}"'})


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
  .panel-header-acciones { display:flex; align-items:center; gap:10px; }
  .btn-clientes { background:#3a3f4b; border-radius:8px; color:#f2f4f8; font-size:14px; font-weight:700; padding:8px 14px; text-decoration:none; }
  .btn-clientes:hover { background:#4a5160; }
  table { width:100%; border-collapse:collapse; font-size:14px; color:#dfe2e8; }
  th, td { text-align:left; padding:8px 10px; border-bottom:1px solid #2a2e37; }
  th { color:#f2f4f8; }
  .vacio { color:#9aa0ab; text-align:center; padding:30px; }
  .btn-historial { display:inline-flex; color:#dfe2e8; }
  .btn-historial:hover { color:#fff; }
  .btn-eliminar { background:#8d1627; border:1px solid #c8102e; color:#fff; }
  .btn-eliminar:hover { background:#c8102e; }
  .acciones-masivas { display:none; align-items:center; gap:10px; margin:0 0 14px; flex-wrap:wrap; }
  .acciones-masivas.visible { display:flex; }
  .acciones-masivas span { color:#9aa0ab; font-size:13px; }
  .acciones-masivas button { border:none; border-radius:8px; padding:9px 12px; color:#fff; cursor:pointer; font-weight:700; }
  #btn-mail-masivo { background:#3a3f4b; }
  #btn-eliminar-masivo { background:#8d1627; border:1px solid #c8102e; }
  .filtros-clientes { display:flex; gap:8px; margin:0 0 14px; flex-wrap:wrap; }
  .filtros-clientes input, .filtros-clientes select { min-height:38px; box-sizing:border-box; border:1px solid #4a5160; border-radius:8px; background:#12141a; color:#f2f4f8; padding:0 10px; font:inherit; }
  #filtro-clientes { flex:1 1 240px; }
  .pedidos-hoy { margin:0 0 20px; padding:14px; border:1px solid #4a5160; border-radius:10px; }
  .pedidos-hoy h2 { margin:0 0 10px; color:#f2f4f8; font-size:17px; }
  .form-tarea-entrega { display:grid; gap:8px; grid-template-columns:1.2fr 1.2fr 1.5fr 1.5fr auto; margin:0 0 12px; }
  .tarea-direccion-wrap { position:relative; min-width:0; }
  .form-tarea-entrega input, .form-tarea-entrega select { box-sizing:border-box; min-width:0; min-height:38px; border:1px solid #4a5160; border-radius:8px; background:#12141a; color:#f2f4f8; padding:0 10px; font:inherit; }
  .tarea-direccion-wrap input { width:100%; }
  .form-tarea-entrega input::placeholder { color:#9aa0ab; }
  .form-tarea-entrega button { border:0; border-radius:8px; background:#c8102e; color:#fff; cursor:pointer; font:inherit; font-weight:700; min-height:38px; padding:0 14px; }
  .tarea-direccion-sugerencias { position:absolute; z-index:50; top:calc(100% + 4px); left:0; right:0; max-height:180px; overflow-y:auto; margin:0; padding:0; list-style:none; border:1px solid #4a5160; border-radius:8px; background:#12141a; box-shadow:0 8px 18px rgba(0,0,0,.28); }
  .tarea-direccion-sugerencias[hidden] { display:none; }
  .tarea-direccion-sugerencias button { display:block; width:100%; min-height:38px; padding:8px 10px; border:0; border-radius:0; border-bottom:1px solid #2a2e37; background:#12141a; color:#f2f4f8; text-align:left; font-weight:400; }
  .tarea-direccion-sugerencias li:last-child button { border-bottom:0; }
  .tarea-direccion-sugerencias button:hover, .tarea-direccion-sugerencias button:focus-visible { background:#272c36; outline:0; }
  .pedido-hoy { display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 0; border-top:1px solid #2a2e37; color:#dfe2e8; font-size:14px; }
  .pedido-hoy strong { color:#f2f4f8; }
  .pedido-hoy-detalle { min-width:0; }
  .pedido-hoy.arrastrando { opacity:.5; }
  .arrastrar-entrega { flex:0 0 auto; width:32px; min-height:36px; border:1px solid #4a5160; border-radius:8px; background:#252a33; color:#f2f4f8; cursor:grab; font:700 20px/1 sans-serif; touch-action:none; }
  .arrastrar-entrega:active { cursor:grabbing; }
  .pedido-hoy-detalle span { color:#9aa0ab; }
  .pedido-acciones { display:flex; align-items:center; gap:7px; flex:0 0 auto; flex-wrap:wrap; justify-content:flex-end; }
  .btn-enviar-recibo { flex:0 0 auto; border:0; border-radius:8px; padding:9px 12px; background:#c8102e; color:#fff; cursor:pointer; font-weight:700; }
  .btn-direcciones, .btn-agregar-direccion, .btn-agregar-direccion-tarea { border:1px solid #4a5160; border-radius:8px; padding:8px 10px; background:#252a33; color:#f2f4f8; cursor:pointer; font-weight:700; text-decoration:none; }
  .btn-enviar-recibo:disabled { opacity:.55; cursor:not-allowed; }
  .btn-editar-entrega, .btn-eliminar-entrega, .btn-completar-tarea, .btn-editar-tarea, .btn-eliminar-tarea { border:1px solid #4a5160; border-radius:8px; padding:8px 10px; background:#252a33; color:#f2f4f8; cursor:pointer; font-weight:700; }
  .btn-completar-tarea { background:#c8102e; border:0; color:#fff; }
  .btn-eliminar-entrega, .btn-eliminar-tarea { border-color:#8d1627; color:#ff9baa; }
  .historial-pedidos { margin:0 0 20px; padding:14px; border:1px solid #4a5160; border-radius:10px; }
  .historial-pedidos h2 { margin:0 0 10px; color:#f2f4f8; font-size:17px; }
  .historial-pedidos label { color:#dfe2e8; font-size:13px; font-weight:700; }
  .historial-pedidos input { margin-left:8px; min-height:34px; border:1px solid #4a5160; border-radius:8px; padding:0 8px; background:#12141a; color:#f2f4f8; font:inherit; }
  #filtro-historial-pedidos { box-sizing:border-box; display:block; margin:0 0 10px; min-height:38px; width:100%; }
  #fecha-historial-pedidos { color-scheme:dark; }
  #fecha-historial-pedidos::-webkit-calendar-picker-indicator { filter:none; opacity:.9; cursor:pointer; }
  .pedido-historico { padding:10px 0; border-top:1px solid #2a2e37; color:#dfe2e8; font-size:14px; }
  .estado-recibo { display:inline-block; margin-top:4px; color:#9aa0ab; font-size:12px; }
  .acciones-recibo { display:inline-flex; gap:8px; margin-left:8px; vertical-align:middle; }
  .btn-ver-recibo-pdf, .btn-reenviar-recibo, .btn-eliminar-historial { display:inline-flex; align-items:center; justify-content:center; width:30px; height:30px; border:1px solid #4a5160; border-radius:7px; background:#252a33; color:#f2f4f8; cursor:pointer; text-decoration:none; }
  .btn-eliminar-historial { border-color:#8d1627; color:#ff9baa; }
  .ordenar-columna { appearance:none; border:0; background:transparent; color:#f2f4f8; font:inherit; font-weight:700; cursor:pointer; padding:0; }
  .ordenar-columna:hover { color:#fff; text-decoration:underline; }
  .modal-mail { position:fixed; inset:0; z-index:20; background:rgba(0,0,0,.7); align-items:center; justify-content:center; padding:20px; }
  .modal-mail[hidden] { display:none; }
  .modal-series { position:fixed; inset:0; z-index:30; background:rgba(0,0,0,.7); align-items:center; justify-content:center; padding:20px; }
  .modal-series[hidden] { display:none; }
  .modal-series-contenido { width:min(520px,100%); background:#1b1e24; border:1px solid #333844; border-radius:12px; padding:20px; box-sizing:border-box; }
  .modal-series h2 { color:#f2f4f8; font-size:18px; margin:0 0 8px; }
  .modal-series p { color:#9aa0ab; font-size:13px; }
  .series-fotos { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:12px 0; }
  .serie-foto { position:relative; }
  .serie-foto img { border-radius:8px; display:block; height:90px; object-fit:cover; width:100%; }
  .serie-foto button { position:absolute; right:4px; top:4px; border:0; border-radius:50%; background:#c8102e; color:#fff; cursor:pointer; width:24px; height:24px; }
  .series-acciones { display:flex; gap:8px; }
  .series-acciones button { border:0; border-radius:8px; color:#fff; cursor:pointer; font-weight:700; min-height:42px; padding:0 12px; }
  #series-agregar, #series-cancelar { background:#3a3f4b; }
  #series-enviar { background:#c8102e; margin-left:auto; }
  .modal-direccion { position:fixed; inset:0; z-index:30; background:rgba(0,0,0,.7); align-items:center; justify-content:center; padding:20px; }
  .modal-direccion[hidden] { display:none; }
  .modal-fecha-entrega { position:fixed; inset:0; z-index:30; background:rgba(0,0,0,.7); align-items:center; justify-content:center; padding:20px; }
  .modal-fecha-entrega[hidden] { display:none; }
  .modal-series, .modal-direccion { display:flex; }
  .modal-fecha-entrega { display:flex; }
  .modal-direccion-contenido { width:min(520px,100%); background:#1b1e24; border:1px solid #333844; border-radius:12px; padding:20px; box-sizing:border-box; }
  .modal-fecha-contenido { width:min(420px,100%); background:#1b1e24; border:1px solid #333844; border-radius:12px; padding:20px; box-sizing:border-box; }
  .modal-direccion h2 { color:#f2f4f8; font-size:18px; margin:0 0 12px; }
  .modal-fecha-entrega h2 { color:#f2f4f8; font-size:18px; margin:0 0 12px; }
  .modal-direccion input { box-sizing:border-box; width:100%; min-height:42px; border:1px solid #4a5160; border-radius:8px; padding:0 10px; background:#12141a; color:#f2f4f8; font:inherit; }
  .modal-fecha-entrega input { box-sizing:border-box; width:100%; min-height:42px; border:1px solid #4a5160; border-radius:8px; padding:0 10px; background:#12141a; color:#f2f4f8; color-scheme:dark; font:inherit; }
  .direccion-acciones { display:flex; gap:8px; margin-top:12px; }
  .fecha-entrega-acciones { display:flex; gap:8px; margin-top:12px; }
  .direccion-acciones button { border:0; border-radius:8px; color:#fff; cursor:pointer; font-weight:700; min-height:42px; padding:0 12px; }
  .fecha-entrega-acciones button { border:0; border-radius:8px; color:#fff; cursor:pointer; font-weight:700; min-height:42px; padding:0 12px; }
  #direccion-cancelar { background:#3a3f4b; }
  #direccion-guardar { background:#c8102e; margin-left:auto; }
  #fecha-entrega-cancelar { background:#3a3f4b; }
  #fecha-entrega-guardar { background:#c8102e; margin-left:auto; }
  .modal-mail-contenido { width:min(520px, 100%); background:#1b1e24; border:1px solid #333844; border-radius:12px; padding:20px; box-sizing:border-box; }
  .modal-mail h2 { margin:0 0 8px; color:#f2f4f8; font-size:18px; }
  .modal-mail p { margin:0 0 12px; color:#9aa0ab; font-size:13px; }
  .mail-editor-toolbar { display:flex; gap:6px; flex-wrap:wrap; margin:0 0 8px; }
  .mail-editor-toolbar button { align-items:center; background:#252a33; border:1px solid #4a5160; border-radius:6px; color:#f2f4f8; cursor:pointer; display:inline-flex; font:inherit; font-weight:700; justify-content:center; min-height:32px; padding:4px 9px; }
  .mail-editor-toolbar button:hover { border-color:#dfe2e8; }
  .mail-editor { width:100%; min-height:160px; resize:vertical; overflow:auto; box-sizing:border-box; border:1px solid #4a5160; border-radius:8px; padding:10px; color:#f2f4f8; background:#12141a; font:inherit; line-height:1.45; }
  .mail-editor:empty::before { color:#7d8491; content:attr(data-placeholder); pointer-events:none; }
  .mail-editor:focus { border-color:#dfe2e8; outline:0; }
  .mail-editor p { color:inherit; font-size:inherit; margin:0 0 10px; }
  .mail-editor ul, .mail-editor ol { margin:0 0 10px; padding-left:22px; }
  .modal-mail-acciones { display:flex; justify-content:flex-end; gap:8px; margin-top:12px; }
  .modal-mail-acciones button { border:0; border-radius:8px; padding:9px 12px; cursor:pointer; font-weight:700; }
  #mail-cancelar { background:#3a3f4b; color:#fff; }
  #mail-enviar { background:#c8102e; color:#fff; }
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
  .tabla-scroll { width:100%; max-width:100%; overflow-x:auto; -webkit-overflow-scrolling:touch; }
  @media (max-width: 640px) {
    body { align-items:flex-start; padding:12px; }
    .panel { margin:0; padding:16px; border-radius:12px; }
    .panel-header { align-items:stretch; flex-direction:column; gap:10px; }
    .panel-header-acciones { align-items:stretch; flex-direction:column; }
    .panel-header button, .panel-header a.volver { box-sizing:border-box; text-align:center; width:100%; }
    .panel-header .btn-clientes { box-sizing:border-box; text-align:center; width:100%; }
    .historial-pedidos input { box-sizing:border-box; display:block; margin:8px 0 0; max-width:100%; width:100%; }
    .filtros-clientes { flex-direction:column; }
    .filtros-clientes input, .filtros-clientes select { min-width:0; width:100%; }
    #filtro-clientes { flex:0 1 auto; min-height:38px; }
    .pedido-hoy { align-items:stretch; flex-direction:column; }
    .arrastrar-entrega { align-self:flex-start; min-height:42px; width:44px; }
    .form-tarea-entrega { grid-template-columns:1fr; }
    .form-tarea-entrega button { min-height:44px; }
    .pedido-hoy-detalle, .pedido-historico { overflow-wrap:anywhere; word-break:break-word; }
    .pedido-acciones { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); grid-template-areas:"recibo direcciones" "editar eliminar"; justify-content:stretch; width:100%; }
    .pedido-acciones > * { box-sizing:border-box; flex:1 1 140px; min-height:42px; }
    .pedido-acciones .btn-direcciones, .pedido-acciones .btn-agregar-direccion { align-items:center; display:flex; justify-content:center; }
    .pedido-acciones .btn-agregar-direccion-tarea { align-items:center; display:flex; justify-content:center; }
    .pedido-acciones .btn-enviar-recibo { grid-area:recibo; }
    .pedido-acciones .btn-completar-tarea { grid-area:recibo; }
    .pedido-acciones .btn-direcciones { grid-area:direcciones; }
    .pedido-acciones .btn-agregar-direccion { grid-area:direcciones; }
    .pedido-acciones .btn-agregar-direccion-tarea { grid-area:direcciones; }
    .pedido-acciones .btn-editar-entrega { grid-area:editar; }
    .pedido-acciones .btn-editar-tarea { grid-area:editar; }
    .pedido-acciones .btn-eliminar-entrega { grid-area:eliminar; }
    .pedido-acciones .btn-eliminar-tarea { grid-area:eliminar; }
    .acciones-recibo { margin:8px 0 0; }
    .tabla-scroll { overflow:visible; }
    #tabla-clientes { min-width:0; font-size:13px; }
    #tabla-clientes thead { display:none; }
    #tabla-clientes, #tabla-clientes tbody, #tabla-clientes tr, #tabla-clientes td { box-sizing:border-box; display:block; width:100%; }
    #tabla-clientes tr[hidden] { display:none !important; }
    #tabla-clientes tbody { display:grid; gap:12px; }
    #tabla-clientes tr { background:#12141a; border:1px solid #2a2e37; border-radius:10px; padding:4px 12px; }
    #tabla-clientes td { align-items:flex-start; border-bottom:1px solid #2a2e37; display:flex; gap:12px; justify-content:space-between; min-height:42px; padding:10px 0; white-space:normal; overflow-wrap:anywhere; vertical-align:top; }
    #tabla-clientes td::before { color:#9aa0ab; content:""; flex:0 0 82px; font-size:12px; font-weight:700; }
    #tabla-clientes td:nth-child(1)::before { content:"Seleccionar"; }
    #tabla-clientes td:nth-child(2)::before { content:"Nombre"; }
    #tabla-clientes td:nth-child(3)::before { content:"Celular"; }
    #tabla-clientes td:nth-child(4)::before { content:"Provincia"; }
    #tabla-clientes td:nth-child(5)::before { content:"Historial"; }
    #tabla-clientes td:nth-child(6)::before { content:"Cuenta"; }
    #tabla-clientes td:nth-child(7)::before { content:"Acciones"; }
    #tabla-clientes td:last-child { border-bottom:0; }
    #tabla-clientes .col-check { justify-content:flex-start; text-align:left; }
    #tabla-clientes .col-check::before { display:none; }
    #tabla-clientes .btn-reset, #tabla-clientes .btn-eliminar { border-radius:8px; box-sizing:border-box; min-height:36px; padding:8px 10px; width:100%; }
    .acciones-mailing { align-items:stretch; flex-direction:column; }
    .acciones-mailing button { width:100%; min-height:44px; }
    .modal-mail { align-items:flex-end; padding:12px; }
    .modal-mail-contenido { max-height:calc(100vh - 24px); overflow-y:auto; padding:16px; }
    .modal-mail-acciones { flex-direction:column-reverse; }
    .modal-mail-acciones button { min-height:44px; width:100%; }
  }
</style>
"""

_ADMIN_CLIENTES_PWA_HEAD = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="manifest" href="/admin-clientes.webmanifest">
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


@app.get("/admin/clientes", response_class=HTMLResponse)
def admin_clientes(request: Request):
    return _admin_clientes_pagina(request, mostrar_clientes=False)


@app.get("/admin/clientes/lista", response_class=HTMLResponse)
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
            "id": c.get("id", ""),
            "nombre": f"{c.get('nombre', '')} {c.get('apellido', '')}".strip(),
            "celular": c.get("celular", ""),
            "email": c.get("email", ""),
            "provincia": c.get("provincia") or "Sin especificar",
            "fecha": c.get("creado_en", ""),
            "tiene_cuenta": bool(c.get("auth_id")),
            "direccion": c.get("direccion"),
        }
        for c in filas_clientes
    ]
    clientes.sort(key=lambda r: r.get("fecha", ""), reverse=True)
    clientes_por_id = {cliente["id"]: cliente for cliente in clientes}
    fecha_hoy = entregas.ahora_argentina().date().isoformat()
    pedidos = client.table("pedidos").select("*").execute().data
    tareas = client.table("tareas_entrega").select("*").execute().data
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
        if pedido.get("fecha_entrega") == fecha_historial and pedido.get("recibo_enviado_en")
    ]
    tareas_historial = [
        tarea for tarea in tareas
        if tarea.get("fecha_entrega") == fecha_historial and tarea.get("completada_en")
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

    def _controles_entrega(pedido):
        pedido_id = html.escape(pedido.get("id", ""))
        fecha = html.escape(pedido.get("fecha_entrega", ""))
        direccion = (pedido.get("direccion_entrega") or "").strip()
        boton_direcciones = (
            f'<a class="btn-direcciones" target="_blank" rel="noopener" '
            f'href="https://www.google.com/maps/search/?{html.escape(urlencode({"api": 1, "query": direccion}))}">Vamos</a>'
            if direccion else f'<button class="btn-agregar-direccion" type="button" data-id="{pedido_id}">Agregar dirección</button>'
        )
        return (
            '<div class="pedido-acciones">'
            f'{boton_direcciones}'
            f'{_boton_recibo(pedido)}'
            f'<button class="btn-editar-entrega" type="button" data-id="{pedido_id}" data-fecha="{fecha}" data-tipo="pedido">Editar fecha</button>'
            f'<button class="btn-eliminar-entrega" type="button" data-id="{pedido_id}">Eliminar entrega</button>'
            '</div>'
        )

    def _tarjeta_tarea(tarea):
        tarea_id = html.escape(tarea.get("id", ""))
        fecha = html.escape(tarea.get("fecha_entrega", ""))
        direccion = (tarea.get("direccion") or "").strip()
        nombre_cliente = clientes_por_id.get(tarea.get("cliente_id"), {}).get("nombre", "")
        detalle_cliente = f'<br><span>Cliente: {html.escape(nombre_cliente)}</span>' if nombre_cliente else ""
        boton_direcciones = (
            f'<a class="btn-direcciones" target="_blank" rel="noopener" '
            f'href="https://www.google.com/maps/search/?{html.escape(urlencode({"api": 1, "query": direccion}))}">Vamos</a>'
            if direccion else f'<button class="btn-agregar-direccion-tarea" type="button" data-id="{tarea_id}">Agregar dirección</button>'
        )
        return (
            f'<div class="pedido-hoy" data-tipo-entrega="tarea" data-entrega-id="{tarea_id}"><button class="arrastrar-entrega" draggable="true" type="button" aria-label="Arrastrar tarea">≡</button><div class="pedido-hoy-detalle">'
            f'<strong>Tarea: {html.escape(tarea.get("titulo") or "")}</strong>'
            f'{detalle_cliente}<br><span>{html.escape(tarea.get("nota") or "")}</span></div>'
            '<div class="pedido-acciones">'
            f'{boton_direcciones}'
            f'<button class="btn-completar-tarea" type="button" data-id="{tarea_id}">Completado</button>'
            f'<button class="btn-editar-tarea" type="button" data-id="{tarea_id}" data-fecha="{fecha}" data-tipo="tarea">Editar fecha</button>'
            f'<button class="btn-eliminar-tarea" type="button" data-id="{tarea_id}">Eliminar tarea</button>'
            '</div></div>'
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
            return (
                f'<div class="pedido-historico" data-busqueda-historial="{busqueda}"><strong>{html.escape(nombre_cliente)}</strong> · '
                f'{html.escape(descripcion)} · U$D {_formatear_entero_ar(pedido.get("total_usd"))}<br><span class="estado-recibo">'
                f'{("Recibo enviado originalmente: " + html.escape(pedido.get("recibo_emitido_en") or pedido.get("recibo_enviado_en", ""))) if pedido.get("recibo_enviado_en") else ("Pendiente de recibo" if pedido.get("detalle") and pedido.get("total_usd") is not None else "Sin detalle histórico")}</span>{_acciones_recibo_historial(pedido)}</div>'
            )

        def _tarea_historial_html(tarea):
            nombre_cliente = clientes_por_id.get(tarea.get("cliente_id"), {}).get("nombre", "")
            titulo = tarea.get("titulo") or "Tarea sin título"
            nota = tarea.get("nota") or ""
            busqueda = html.escape(f"{nombre_cliente} {titulo} {nota}".lower())
            detalle_cliente = f" · {html.escape(nombre_cliente)}" if nombre_cliente else ""
            detalle_nota = f" · {html.escape(nota)}" if nota else ""
            return (
                f'<div class="pedido-historico" data-busqueda-historial="{busqueda}"><strong>Tarea completada: {html.escape(titulo)}</strong>'
                f'{detalle_cliente}{detalle_nota}<br><span class="estado-recibo">Completada el {html.escape(tarea.get("completada_en") or "")}</span></div>'
            )

        pedidos_historial_html = "".join(
            [_pedido_historial_html(pedido) for pedido in pedidos_historial]
            + [_tarea_historial_html(tarea) for tarea in tareas_historial]
        )
    else:
        pedidos_historial_html = '<p class="vacio">No hay pedidos para esta fecha.</p>'

    clientes_tarea_json = json.dumps(
        [
            {"id": cliente["id"], "nombre": cliente["nombre"], "direccion": cliente.get("direccion") or ""}
            for cliente in sorted(clientes, key=lambda cliente: cliente["nombre"].casefold())
        ],
        ensure_ascii=False,
    )
    pendientes_hoy_seccion_html = (
        f'<section class="pedidos-hoy"><h2>Pedidos pendientes para hoy ({len(pedidos_hoy) + len(tareas_hoy)})</h2>'
        f'<form id="form-tarea-entrega" class="form-tarea-entrega"><input id="tarea-titulo" required maxlength="200" placeholder="Nueva tarea">'
        f'<div class="tarea-direccion-wrap"><input id="tarea-cliente-busqueda" maxlength="200" placeholder="Cliente opcional" autocomplete="off"><input type="hidden" id="tarea-cliente"><ul id="tarea-cliente-sugerencias" class="tarea-direccion-sugerencias" role="listbox" aria-label="Clientes" hidden></ul></div>'
        f'<input id="tarea-nota" maxlength="1000" placeholder="Nota opcional"><div class="tarea-direccion-wrap"><input id="tarea-direccion" maxlength="500" placeholder="Agregar dirección" autocomplete="street-address"><ul id="tarea-direccion-sugerencias" class="tarea-direccion-sugerencias" role="listbox" aria-label="Sugerencias de dirección" hidden></ul></div><button>Agregar tarea</button></form>'
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
<div class="modal-direccion" id="modal-direccion" hidden><div class="modal-direccion-contenido" role="dialog" aria-modal="true" aria-labelledby="direccion-titulo"><h2 id="direccion-titulo">Dirección de entrega</h2><input id="direccion-entrega-admin" type="text" maxlength="500" placeholder="Ej.: Av. Colón 123, Córdoba"><div class="direccion-acciones"><button id="direccion-cancelar" type="button">Cancelar</button><button id="direccion-guardar" type="button">Guardar dirección</button></div></div></div>
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
    campoDireccion.focus();
  }});
}});
document.querySelectorAll(".btn-agregar-direccion-tarea").forEach((btn) => {{
  btn.addEventListener("click", () => {{
    tareaDireccionActiva = btn.dataset.id;
    pedidoDireccionActivo = null;
    campoDireccion.value = "";
    modalDireccion.hidden = false;
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
const inputDireccionTarea = document.getElementById("tarea-direccion");
const sugerenciasDireccionTarea = document.getElementById("tarea-direccion-sugerencias");
let temporizadorDireccionTarea;
let apiPlacesAdmin;
function ocultarSugerenciasDireccionTarea() {{
  sugerenciasDireccionTarea.replaceChildren();
  sugerenciasDireccionTarea.hidden = true;
}}
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
async function mostrarSugerenciasDireccionTarea(texto) {{
  const places = await cargarApiPlacesAdmin();
  if (!places || texto !== inputDireccionTarea.value.trim()) return;
  const {{ AutocompleteSuggestion }} = places;
  const {{ suggestions }} = await AutocompleteSuggestion.fetchAutocompleteSuggestions({{
    input: texto,
    includedRegionCodes: ["ar"],
  }}).catch((error) => {{ console.error("Autocomplete de direccion fallo", error); return {{ suggestions: [] }}; }});
  if (texto !== inputDireccionTarea.value.trim() || !suggestions?.length) {{
    ocultarSugerenciasDireccionTarea();
    return;
  }}
  sugerenciasDireccionTarea.replaceChildren(...suggestions.slice(0, 5).map(({{ placePrediction }}) => {{
    const item = document.createElement("li");
    const boton = document.createElement("button");
    boton.type = "button";
    boton.textContent = placePrediction.text.text;
    boton.addEventListener("click", async () => {{
      const place = placePrediction.toPlace();
      await place.fetchFields({{ fields: ["formattedAddress"] }});
      inputDireccionTarea.value = place.formattedAddress || placePrediction.text.text;
      ocultarSugerenciasDireccionTarea();
    }});
    item.append(boton);
    return item;
  }}));
  sugerenciasDireccionTarea.hidden = false;
}}
inputDireccionTarea?.addEventListener("input", () => {{
  clearTimeout(temporizadorDireccionTarea);
  const texto = inputDireccionTarea.value.trim();
  if (texto.length < 3) {{ ocultarSugerenciasDireccionTarea(); return; }}
  temporizadorDireccionTarea = setTimeout(() => {{
    mostrarSugerenciasDireccionTarea(texto).catch(ocultarSugerenciasDireccionTarea);
  }}, 250);
}});
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
document.getElementById("form-tarea-entrega")?.addEventListener("submit", async (e) => {{
  e.preventDefault();
  const r = await fetch("/admin/tareas-entrega", {{ method:"POST", headers:{{"Content-Type":"application/json"}}, body:JSON.stringify({{fecha_entrega:"{fecha_hoy}", titulo:document.getElementById("tarea-titulo").value, cliente_id:document.getElementById("tarea-cliente").value || null, nota:document.getElementById("tarea-nota").value, direccion:document.getElementById("tarea-direccion").value}}) }});
  if (!r.ok) {{ alert("No se pudo crear la tarea."); return; }}
  location.reload();
}});
document.querySelectorAll(".btn-completar-tarea").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    btn.disabled = true;
    const r = await fetch(`/admin/tareas-entrega/${{btn.dataset.id}}/completar`, {{ method:"POST" }});
    if (!r.ok) {{ alert("No se pudo completar la tarea."); btn.disabled = false; return; }}
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
                return "—"
            id_seguro = html.escape(c.get("id", ""))
            return f'<button class="btn-reset" data-id="{id_seguro}">Resetear contraseña</button>'

        def _celda_eliminar(c):
            if not c.get("tiene_cuenta"):
                return "—"
            id_seguro = html.escape(c.get("id", ""))
            return f'<button class="btn-eliminar" data-id="{id_seguro}">Eliminar cuenta</button>'

        filas_html = "".join(
            f'<tr class="cliente-fila" data-busqueda="{html.escape(" ".join((c.get("nombre", ""), c.get("celular", ""), c.get("email", ""), c.get("provincia", ""))).lower())}" data-provincia="{html.escape(c.get("provincia", ""))}"><td class="col-check"><input class="cliente-check" type="checkbox" '
            f'value="{html.escape(c.get("id", ""))}" aria-label="Seleccionar cliente"></td>'
            f"<td>{html.escape(c.get('nombre', ''))}</td>"
            f"<td>{html.escape(c.get('celular', ''))}</td>"
            f"<td>{html.escape(c.get('provincia', ''))}</td>"
            f'<td><a class="btn-historial" href="/admin/clientes/{html.escape(c.get("id", ""))}/historial" '
            f'title="Ver historial de pedidos" aria-label="Ver historial de pedidos">{_ICONO_OJO}</a></td>'
            f"<td>{_celda_cuenta(c)}</td><td>{_celda_eliminar(c)}</td></tr>"
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
    <thead><tr><th class="col-check"><input id="seleccionar-todos" type="checkbox" aria-label="Seleccionar todos"></th><th><button class="ordenar-columna" data-sort="nombre" data-sort-index="1">Nombre</button></th><th><button class="ordenar-columna" data-sort="celular" data-sort-index="2">Celular</button></th><th><button class="ordenar-columna" data-sort="provincia" data-sort-index="3">Provincia</button></th><th>Historial</th><th>Cuenta</th><th>Acciones</th></tr></thead>
    <tbody>{filas_html}</tbody>
  </table></div>
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
    btn.textContent = "Eliminando...";
    const r = await fetch(`/admin/clientes/${{btn.dataset.id}}/eliminar`, {{ method: "POST" }});
    const datos = await r.json();
    if (r.ok) {{ location.reload(); return; }}
    alert(datos.error || "No se pudo eliminar la cuenta");
    btn.textContent = "Eliminar cuenta";
    btn.disabled = false;
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

function filtrarClientes() {{
  const texto = filtroClientes.value.trim().toLowerCase();
  const provincia = filtroProvincia.value;
  document.querySelectorAll("#tabla-clientes tbody .cliente-fila").forEach((fila) => {{
    fila.hidden = Boolean((texto && !fila.dataset.busqueda.includes(texto)) || (provincia && fila.dataset.provincia !== provincia));
  }});
}}
filtroClientes.addEventListener("input", filtrarClientes);
filtroProvincia.addEventListener("change", filtrarClientes);

const columnasOrden = {{ nombre: 1, celular: 2, provincia: 3 }};
function ordenarFilasClientes(campo, ascendente) {{
  const indice = columnasOrden[campo];
  const filas = Array.from(document.querySelectorAll("#tabla-clientes tbody .cliente-fila"));
  filas.sort((a, b) => a.cells[indice].textContent.trim().localeCompare(
    b.cells[indice].textContent.trim(), "es", {{ numeric: true, sensitivity: "base" }}
  ) * (ascendente ? 1 : -1));
  const cuerpo = document.querySelector("#tabla-clientes tbody");
  filas.forEach((fila) => cuerpo.appendChild(fila));
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
<title>Historial — {html.escape(nombre_cliente)}</title>{_ADMIN_CLIENTES_PWA_HEAD}{_ADMIN_CLIENTES_ESTILO}</head><body>
<div class="panel">
  <div class="panel-header">
    <h1>Historial de {html.escape(nombre_cliente) or "cliente"}</h1>
    <a class="volver" href="/admin/clientes/lista">← Volver</a>
  </div>
  <section class="subseccion">
    <h2>Pedidos confirmados</h2>
    <p>Acá ves todo lo que el cliente cargó al carrito y confirmó.</p>
    <div class="tabla-scroll"><table>
      <thead><tr><th class="col-check"></th><th>Fecha</th><th>Día</th><th>Hora</th><th>Productos</th></tr></thead>
      <tbody>{filas_pedidos_html}</tbody>
    </table></div>
  </section>
  <section class="subseccion">
    <h2>Productos más consultados</h2>
    <p>Ranking por cantidad de vistas de este cliente, ordenado de mayor a menor para decidir mejor el mailing.</p>
    <div class="tabla-scroll"><table>
      <thead><tr><th class="col-check"></th><th>Producto</th><th>Vistas</th><th>Última vista</th></tr></thead>
      <tbody>{filas_consultados_html}</tbody>
    </table></div>
  </section>
  <section class="subseccion">
    <h2>Historial de vistas</h2>
    <p>Acá ves todas las interacciones de navegación, vistas e íconos que tocó el cliente.</p>
    <div class="tabla-scroll"><table>
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
{_ADMIN_CLIENTES_PWA_SCRIPT}
</body></html>"""


class RegistroIn(BaseModel):
    nombre: str
    apellido: str
    celular: str
    email: EmailStr
    password: str = Field(min_length=8)
    provincia: str = Field(min_length=2, max_length=80)
    direccion: str | None = Field(default=None, max_length=500)


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
            entrada.email, entrada.password, entrada.provincia, entrada.direccion,
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
    direccion: str | None = Field(default=None, max_length=500)


class GuardarDireccionPerfilIn(BaseModel):
    direccion: str = Field(min_length=3, max_length=500)
    guardar_en_perfil: bool


@app.put("/api/me")
def api_me_actualizar(entrada: ActualizarMeIn, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        cliente = cuentas.actualizar_cliente(
            get_client(), request.session["cliente_id"],
            entrada.nombre, entrada.apellido, entrada.celular, entrada.direccion,
        )
    except (cuentas.CelularDuplicadoError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo actualizar el perfil del cliente")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    return cliente


@app.put("/api/me/direccion")
def api_me_guardar_direccion(entrada: GuardarDireccionPerfilIn, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        client = get_client()
        if entrada.guardar_en_perfil:
            client.table("clientes").update({"direccion": entrada.direccion.strip()}).eq(
                "id", request.session["cliente_id"]
            ).execute()
        cliente = cuentas.obtener_cliente(client, request.session["cliente_id"])
    except Exception:
        logger.exception("No se pudo guardar la preferencia de domicilio")
        return JSONResponse({"error": "No pudimos guardar el domicilio, probá de nuevo en un momento"}, status_code=503)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
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


class DetallePedidoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=300)
    color: str | None = Field(default=None, max_length=100)
    cantidad: int = Field(ge=1, le=100)
    usd_unitario: int = Field(ge=0)
    usd_subtotal: int = Field(ge=0)


class PedidoIn(BaseModel):
    productos: list[str] = Field(min_length=1)
    fecha_entrega: date | None = None
    direccion_entrega: str | None = Field(default=None, max_length=500)
    detalle: list[DetallePedidoIn] = Field(default_factory=list)
    total_usd: int | None = Field(default=None, ge=0)
    descuento_usd: int = Field(default=0, ge=0)


class EditarFechaEntregaIn(BaseModel):
    fecha_entrega: date


class EditarDireccionEntregaIn(BaseModel):
    direccion_entrega: str = Field(max_length=500)


class TareaEntregaIn(BaseModel):
    fecha_entrega: date
    titulo: str = Field(min_length=1, max_length=200)
    cliente_id: str | None = Field(default=None, max_length=36)
    nota: str | None = Field(default=None, max_length=1000)
    direccion: str | None = Field(default=None, max_length=500)


class OrdenEntregaItemIn(BaseModel):
    tipo: Literal["pedido", "tarea"]
    id: str = Field(min_length=1, max_length=100)


class ReordenarEntregasIn(BaseModel):
    items: list[OrdenEntregaItemIn]


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
    if not entrada.fecha_entrega:
        return JSONResponse({"error": "Elegí una fecha de entrega"}, status_code=400)
    if not entregas.fecha_entrega_valida(entrada.fecha_entrega):
        return JSONResponse({"error": "La fecha de entrega elegida ya no está disponible"}, status_code=400)
    if entrada.detalle and not (entrada.direccion_entrega or "").strip():
        return JSONResponse({"error": "Especificá dirección de entrega"}, status_code=400)
    proveedores = _cargar_proveedores()
    detalle = [
        {**item.model_dump(), "proveedor": resolver_proveedor(proveedores, item.nombre)}
        for item in entrada.detalle
    ]
    pedidos.guardar_pedido(
        get_client(),
        cliente_id,
        entrada.productos,
        entrada.fecha_entrega,
        direccion_entrega=(entrada.direccion_entrega or "").strip() or None,
        detalle=detalle,
        total_usd=entrada.total_usd,
        descuento_usd=entrada.descuento_usd,
    )
    return {"ok": True}


@app.put("/admin/pedidos/{pedido_id}/fecha-entrega")
def admin_pedido_editar_fecha(pedido_id: str, entrada: EditarFechaEntregaIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    if not entregas.fecha_entrega_valida(entrada.fecha_entrega):
        return JSONResponse({"error": "La fecha de entrega elegida no está disponible"}, status_code=400)
    client = get_client()
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if filas[0].get("recibo_enviado_en"):
        return JSONResponse({"error": "No se puede editar una entrega con recibo emitido"}, status_code=400)
    pedido = pedidos.editar_fecha_entrega(client, pedido_id, entrada.fecha_entrega)
    return {"ok": True, "pedido_id": pedido["id"], "fecha_entrega": pedido["fecha_entrega"]}


@app.delete("/admin/pedidos/{pedido_id}")
def admin_pedido_eliminar(pedido_id: str, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedidos.eliminar_pedido(client, pedido_id)
    return {"ok": True}


@app.put("/admin/pedidos/{pedido_id}/direccion")
def admin_pedido_agregar_direccion(pedido_id: str, entrada: EditarDireccionEntregaIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    direccion = entrada.direccion_entrega.strip()
    if not direccion:
        return JSONResponse({"error": "Ingresá una dirección de entrega"}, status_code=400)
    client = get_client()
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if filas[0].get("recibo_enviado_en"):
        return JSONResponse({"error": "No se puede editar una entrega con recibo emitido"}, status_code=400)
    client.table("pedidos").update({"direccion_entrega": direccion}).eq("id", pedido_id).execute()
    return {"ok": True, "pedido_id": pedido_id, "direccion_entrega": direccion}


@app.put("/admin/entregas/orden")
def admin_reordenar_entregas(entrada: ReordenarEntregasIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    fecha_hoy = entregas.ahora_argentina().date().isoformat()
    pedidos_hoy = [
        pedido for pedido in client.table("pedidos").select("*").execute().data
        if pedido.get("fecha_entrega") == fecha_hoy and not pedido.get("recibo_enviado_en")
    ]
    tareas_hoy = [
        tarea for tarea in client.table("tareas_entrega").select("*").eq("fecha_entrega", fecha_hoy).execute().data
        if not tarea.get("completada_en")
    ]
    esperados = {("pedido", pedido["id"]) for pedido in pedidos_hoy} | {("tarea", tarea["id"]) for tarea in tareas_hoy}
    recibidos = [(item.tipo, item.id) for item in entrada.items]
    if len(recibidos) != len(set(recibidos)) or set(recibidos) != esperados:
        return JSONResponse({"error": "Las entregas cambiaron. Recargá el listado."}, status_code=409)
    for orden, (tipo, entrega_id) in enumerate(recibidos, start=1):
        tabla, campo = ("pedidos", "orden_entrega") if tipo == "pedido" else ("tareas_entrega", "orden")
        client.table(tabla).update({campo: orden}).eq("id", entrega_id).execute()
    return {"ok": True}


@app.post("/admin/tareas-entrega")
def admin_crear_tarea_entrega(entrada: TareaEntregaIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    existentes = client.table("tareas_entrega").select("orden").eq(
        "fecha_entrega", entrada.fecha_entrega.isoformat()
    ).execute().data
    orden = max((int(t.get("orden") or 0) for t in existentes), default=0) + 1
    tarea = {
        "id": str(uuid.uuid4()),
        "fecha_entrega": entrada.fecha_entrega.isoformat(),
        "titulo": entrada.titulo.strip(),
        "cliente_id": (entrada.cliente_id or "").strip() or None,
        "nota": (entrada.nota or "").strip() or None,
        "direccion": (entrada.direccion or "").strip() or None,
        "orden": orden,
    }
    client.table("tareas_entrega").insert(tarea).execute()
    return {"ok": True, "tarea": tarea}


@app.post("/admin/tareas-entrega/{tarea_id}/completar")
def admin_completar_tarea_entrega(tarea_id: str, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    filas = client.table("tareas_entrega").select("*").eq("id", tarea_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    completada_en = datetime.now(timezone.utc).isoformat()
    client.table("tareas_entrega").update({"completada_en": completada_en}).eq("id", tarea_id).execute()
    return {"ok": True, "tarea_id": tarea_id, "completada_en": completada_en}


@app.put("/admin/tareas-entrega/{tarea_id}/direccion")
def admin_tarea_agregar_direccion(tarea_id: str, entrada: EditarDireccionEntregaIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    direccion = entrada.direccion_entrega.strip()
    if not direccion:
        return JSONResponse({"error": "Ingresá una dirección de entrega"}, status_code=400)
    client = get_client()
    filas = client.table("tareas_entrega").select("*").eq("id", tarea_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    client.table("tareas_entrega").update({"direccion": direccion}).eq("id", tarea_id).execute()
    return {"ok": True, "tarea_id": tarea_id, "direccion": direccion}


@app.put("/admin/tareas-entrega/{tarea_id}/fecha-entrega")
def admin_tarea_editar_fecha(tarea_id: str, entrada: EditarFechaEntregaIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    if not entregas.fecha_entrega_valida(entrada.fecha_entrega):
        return JSONResponse({"error": "La fecha de entrega elegida no está disponible"}, status_code=400)
    client = get_client()
    filas = client.table("tareas_entrega").select("*").eq("id", tarea_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    fecha_entrega = entrada.fecha_entrega.isoformat()
    existentes = client.table("tareas_entrega").select("orden").eq("fecha_entrega", fecha_entrega).execute().data
    orden = max((int(tarea.get("orden") or 0) for tarea in existentes), default=0) + 1
    client.table("tareas_entrega").update({
        "fecha_entrega": fecha_entrega,
        "orden": orden,
    }).eq("id", tarea_id).execute()
    return {"ok": True, "tarea_id": tarea_id, "fecha_entrega": fecha_entrega}


@app.delete("/admin/tareas-entrega/{tarea_id}")
def admin_tarea_eliminar(tarea_id: str, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    filas = client.table("tareas_entrega").select("*").eq("id", tarea_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    client.table("tareas_entrega").delete().eq("id", tarea_id).execute()
    return {"ok": True, "tarea_id": tarea_id}


@app.get("/api/entregas-disponibles")
def api_entregas_disponibles():
    ahora = entregas.ahora_argentina()
    opciones = entregas.opciones_entrega(ahora)
    return {"opciones": [{**opcion, "etiqueta": entregas.etiqueta_entrega(opcion["fecha"], ahora)} for opcion in opciones]}


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


@app.post("/api/codigos-promo/validar")
def api_codigos_promo_validar(entrada: CodigoPromoIn, request: Request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=401, detail="Sesión requerida")
    if _debe_cambiar_password(request):
        raise HTTPException(status_code=403, detail="Tenés que elegir una contraseña nueva antes de seguir")
    fila = _codigo_promo_row(get_client(), entrada.codigo)
    if not fila:
        return JSONResponse({"error": "Código inválido o ya alcanzó el límite de usos"}, status_code=400)
    return {"ok": True, "codigo": fila["code"], "producto_regalo": fila["producto_regalo"]}


@app.post("/api/codigos-promo/consumir")
def api_codigos_promo_consumir(entrada: CodigoPromoIn, request: Request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=401, detail="Sesión requerida")
    if _debe_cambiar_password(request):
        raise HTTPException(status_code=403, detail="Tenés que elegir una contraseña nueva antes de seguir")
    client = get_client()
    fila = _codigo_promo_row(client, entrada.codigo)
    if not fila:
        return JSONResponse({"error": "Código inválido o ya alcanzó el límite de usos"}, status_code=400)
    client.table("codigos_promo").update({"usos_actuales": int(fila.get("usos_actuales") or 0) + 1}).eq("code", fila["code"]).execute()
    return {"ok": True, "codigo": fila["code"], "producto_regalo": fila["producto_regalo"]}


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
