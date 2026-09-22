import hashlib
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
from decimal import Decimal
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

from web import buscador, catalogo, cuentas, domicilios, entregas, interacciones, mayoristas, pedidos, recibos
from web.email_util import EnvioEmailError, enviar_email
from web.productos import resolver_proveedor
from web.slugs import slug as slug_producto
from web.supabase_client import get_client
from web.ui_helpers import (
    CADETE_SLUG,
    _ADMIN_CLIENTES_ESTILO,
    _ADMIN_CLIENTES_PWA_HEAD,
    _ADMIN_CLIENTES_PWA_SCRIPT,
    _CADETE_ESTILO,
    _CADETE_PWA_HEAD,
    _DIAS_SEMANA,
    _ICONO_OJO,
    _ICONO_TACHO,
    _cadete_activo,
    _clientes_admin_activo,
    _formatear_entero_ar,
    _formatear_fecha_ar,
    _json_para_script,
    _leer_ui,
    _link_whatsapp_cliente,
    _puede_operar_entrega,
    _query_maps,
    _ranking_productos_consultados,
)
from web.chat import responder
from web.reglas import WHATSAPP

# Interruptor: False = buscador gratis (sin IA). True = IA (Claude, tu API key).
# Para volver a la IA, cambiá esto a True y reiniciá el servidor.
USAR_IA = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web")
# httpx/httpcore loguean cada request salvo Supabase en INFO, incluyendo la
# URL completa — y las consultas por email/celular (ej. login, reseteo de
# password) van como query string ahí (".../clientes?email=eq.juan@x.com").
# Con el nivel de arriba eso terminaba en los logs de Railway en texto plano.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

load_dotenv(Path(__file__).parent / ".env")

BASE = Path(__file__).parent
_UI_DIR = BASE / "ui"


def _leer_ui(nombre):
    """Lee un fragmento estatico de HTML/CSS desde web/ui/.

    Vive fuera de web/static/ (que se sirve publico) y fuera de app.py para que
    el modulo no cargue con decenas de KB de CSS inline. Lo que devuelve es
    identico al literal que habia antes: se inyecta igual en los f-strings.
    """
    return (_UI_DIR / nombre).read_text(encoding="utf-8")


# En producción (Railway) apunta a un volumen persistente vía la variable de
# entorno PRODUCTOS_PATH; en local, cae al archivo de siempre junto al código.
PRODUCTOS_PATH = Path(os.environ.get("PRODUCTOS_PATH", str(BASE / "productos.json")))
# No se sirve al navegador: se genera junto al catálogo para enriquecer el
# detalle administrativo de cada pedido sin exponer proveedores al público.
PROVEEDORES_PATH = Path(os.environ.get("PROVEEDORES_PATH", str(BASE / "proveedores.json")))
COSTOS_PATH = Path(os.environ.get(
    "COSTOS_PATH", str(PRODUCTOS_PATH.with_name("costos.json"))
))
CATALOGO_MANIFEST_PATH = Path(os.environ.get(
    "CATALOGO_MANIFEST_PATH",
    str(PRODUCTOS_PATH.with_name("catalogo-manifest.json")),
))
_CAMPOS_PRIVADOS_CATALOGO = frozenset({"costo", "margen", "proveedor", "capacidad"})
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
ADMIN_CLIENTES_PASSWORD = os.environ.get("ADMIN_CLIENTES_PASSWORD")
if not ADMIN_CLIENTES_PASSWORD:
    # Sin fallback: esta contraseña es la única puerta al panel con datos de
    # clientes (nombre/celular/email/historial) y a poder resetear passwords
    # ajenas — un valor por defecto adivinable ahí es un agujero de seguridad,
    # no una comodidad de desarrollo. Mejor que el server no arranque.
    raise RuntimeError("ADMIN_CLIENTES_PASSWORD no configurado — no se puede iniciar el servidor")
CADETE_PASSWORD = os.environ.get("CADETE_PASSWORD")
if not CADETE_PASSWORD:
    # Mismo criterio que ADMIN_CLIENTES_PASSWORD: el panel de Alejo expone
    # nombre/celular/dirección de clientes con pedidos derivados — un default
    # hardcodeado en el repo (visible en el historial de git) es un agujero
    # de seguridad, no una comodidad. Antes de este cambio el valor por
    # defecto era "Alejo2026"; hay que setearlo como CADETE_PASSWORD en
    # Railway (y en .env local) antes de deployar esto, o el server no arranca.
    raise RuntimeError("CADETE_PASSWORD no configurado — no se puede iniciar el servidor")

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


def _cargar_costos():
    """Load the private wholesale cost index without exposing its failures."""
    try:
        if not COSTOS_PATH.exists():
            return {}
        costos = json.loads(COSTOS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.exception("No se pudo cargar el índice privado de costos")
        return {}
    return costos if isinstance(costos, dict) else {}


def _cargar_snapshot_mayorista():
    """Load exactly one committed product/cost generation, or fail closed."""
    try:
        manifiesto_antes = CATALOGO_MANIFEST_PATH.read_bytes()
        manifiesto = json.loads(manifiesto_antes)
        if (
            not isinstance(manifiesto, dict)
            or manifiesto.get("version") != 1
            or not isinstance(manifiesto.get("generacion"), str)
            or not manifiesto["generacion"].strip()
        ):
            return [], {}

        productos_bytes = PRODUCTOS_PATH.read_bytes()
        costos_bytes = COSTOS_PATH.read_bytes()
        manifiesto_despues = CATALOGO_MANIFEST_PATH.read_bytes()
        if manifiesto_antes != manifiesto_despues:
            return [], {}

        productos_hash = manifiesto.get("productos_sha256")
        costos_hash = manifiesto.get("costos_sha256")
        if (
            not isinstance(productos_hash, str)
            or not isinstance(costos_hash, str)
            or not secrets.compare_digest(
                hashlib.sha256(productos_bytes).hexdigest(), productos_hash
            )
            or not secrets.compare_digest(
                hashlib.sha256(costos_bytes).hexdigest(), costos_hash
            )
        ):
            return [], {}

        productos = json.loads(productos_bytes)
        costos = json.loads(costos_bytes)
        if not isinstance(productos, list) or not isinstance(costos, dict):
            return [], {}
        return productos, costos
    except (OSError, json.JSONDecodeError, UnicodeError, TypeError, ValueError):
        logger.exception("No se pudo cargar un snapshot mayorista consistente")
        return [], {}


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


class ClienteMayoristaIn(BaseModel):
    habilitado: bool


class DerivarEntregaIn(BaseModel):
    derivado: bool
    observaciones: str | None = None


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

    descuento_total = {"usd": Decimal("0"), "pesos": Decimal("0"), "transferencia": Decimal("0")}
    cantidad_total = 0
    for item in items_norm:
        if item["nombre"] not in productos_aplicables:
            continue
        producto = disponibles[item["nombre"]]
        try:
            usd = pedidos.decimal_monetario(producto.get("usd"))
            pesos = pedidos.decimal_monetario(producto.get("pesos"))
            transferencia = pedidos.decimal_monetario(producto.get("transferencia"))
        except ValueError:
            continue
        if usd <= 0:
            continue
        qty = item["cantidad"]
        cantidad_total += qty
        try:
            descuento_usd_unit = min(
                pedidos.decimal_monetario(
                    descuento_row.get("descuento_usd") or _DESCUENTO_MAILING_USD
                ),
                usd,
            )
        except ValueError:
            continue
        descuento_total["usd"] += descuento_usd_unit * qty
        descuento_total["pesos"] += round(descuento_usd_unit * (pesos / usd)) * qty
        descuento_total["transferencia"] += round(descuento_usd_unit * (transferencia / usd)) * qty

    if cantidad_total == 0:
        return None

    return {
        "codigo": descuento_row["code"],
        "productos": sorted(productos_aplicables),
        "cantidad": cantidad_total,
        "descuento_usd_por_item": pedidos.numero_monetario_db(
            descuento_row.get("descuento_usd") or _DESCUENTO_MAILING_USD
        ),
        "descuento": {
            moneda: pedidos.numero_monetario_db(valor)
            for moneda, valor in descuento_total.items()
        },
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


_LOGIN_MAX_INTENTOS = 8
_LOGIN_VENTANA_SEG = 15 * 60
_intentos_login_fallidos: dict[tuple[str, str], list[float]] = {}


def _ip_cliente(request: Request):
    adelante = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if adelante:
        return adelante
    return request.client.host if request.client else "desconocido"


def _login_bloqueado(request: Request, ruta: str):
    clave = (_ip_cliente(request), ruta)
    ahora = time.time()
    intentos = [t for t in _intentos_login_fallidos.get(clave, []) if ahora - t < _LOGIN_VENTANA_SEG]
    _intentos_login_fallidos[clave] = intentos
    return len(intentos) >= _LOGIN_MAX_INTENTOS


def _registrar_login_fallido(request: Request, ruta: str):
    clave = (_ip_cliente(request), ruta)
    _intentos_login_fallidos.setdefault(clave, []).append(time.time())


def _limpiar_login_fallido(request: Request, ruta: str):
    _intentos_login_fallidos.pop((_ip_cliente(request), ruta), None)


@app.post("/admin/clientes/login")
def admin_clientes_login(entrada: ClientesLoginIn, request: Request):
    if _login_bloqueado(request, "clientes"):
        return JSONResponse({"error": "Demasiados intentos. Probá de nuevo en unos minutos."}, status_code=429)
    if not secrets.compare_digest(entrada.password, ADMIN_CLIENTES_PASSWORD):
        _registrar_login_fallido(request, "clientes")
        return JSONResponse({"error": "Contraseña incorrecta"}, status_code=401)
    _limpiar_login_fallido(request, "clientes")
    request.session["clientes_admin_ok"] = True
    return {"ok": True}


@app.post("/admin/clientes/logout")
def admin_clientes_logout(request: Request):
    request.session.pop("clientes_admin_ok", None)
    return {"ok": True}


@app.post("/admin/cadete/login")
def admin_cadete_login(entrada: ClientesLoginIn, request: Request):
    if _login_bloqueado(request, "cadete"):
        return JSONResponse({"error": "Demasiados intentos. Probá de nuevo en unos minutos."}, status_code=429)
    if not secrets.compare_digest(entrada.password, CADETE_PASSWORD):
        _registrar_login_fallido(request, "cadete")
        return JSONResponse({"error": "Contraseña incorrecta"}, status_code=401)
    _limpiar_login_fallido(request, "cadete")
    request.session["cadete_ok"] = True
    return {"ok": True}


@app.post("/admin/cadete/logout")
def admin_cadete_logout(request: Request):
    request.session.pop("cadete_ok", None)
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


@app.post("/admin/clientes/{cliente_id}/mayorista")
def admin_clientes_actualizar_mayorista(
    cliente_id: str, entrada: ClienteMayoristaIn, request: Request,
):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    filas_cliente = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas_cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    if entrada.habilitado and not filas_cliente[0].get("auth_id"):
        raise HTTPException(status_code=400, detail="El contacto no tiene una cuenta habilitable")
    tipo_cliente = "mayorista" if entrada.habilitado else "minorista"
    actualizacion = {"tipo_cliente": tipo_cliente}
    if not entrada.habilitado:
        actualizacion["condiciones_mayorista_aceptadas_en"] = None
    client.table("clientes").update(actualizacion).eq("id", cliente_id).execute()
    return {"ok": True, "tipo_cliente": tipo_cliente}


@app.post("/admin/pedidos/{pedido_id}/recibo")
async def admin_pedido_enviar_recibo(pedido_id: str, request: Request):
    if not (_clientes_admin_activo(request) or _cadete_activo(request)):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    client = get_client()
    filas_pedido = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas_pedido:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedido = filas_pedido[0]
    if not _puede_operar_entrega(request, pedido):
        raise HTTPException(status_code=403, detail="Esta entrega no está asignada a tu usuario")
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
    enviado_por_cadete = _cadete_activo(request)
    pedido_para_mail = {
        **pedido, "recibo_id": recibo_id, "recibo_emitido_en": emitido_en,
        "entregado_por_cadete": enviado_por_cadete,
    }
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
    actualizacion_pedido = {
        "recibo_id": recibo_id,
        "recibo_emitido_en": emitido_en,
        "recibo_enviado_en": ahora_recibo,
        "fotos_series": fotos_guardadas,
    }
    if enviado_por_cadete:
        observacion_previa = (pedido.get("observaciones_cadete") or "").strip()
        if "Entregado por Alejo" not in observacion_previa:
            actualizacion_pedido["observaciones_cadete"] = (
                f"{observacion_previa} · Entregado por Alejo" if observacion_previa else "Entregado por Alejo"
            )
    client.table("pedidos").update(actualizacion_pedido).eq("id", pedido_id).execute()
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






from web import paginas_admin, paginas_cadete  # noqa: E402  (necesita app creado)
app.include_router(paginas_admin.router)
app.include_router(paginas_cadete.router)



class RegistroIn(BaseModel):
    nombre: str
    apellido: str
    celular: str
    email: EmailStr
    password: str = Field(min_length=8)
    provincia: str = Field(min_length=2, max_length=80)
    direccion: str = Field(min_length=3, max_length=500)
    lat: float | None = None
    lng: float | None = None


class LoginIn(BaseModel):
    email: str
    password: str


class CompletarSignupIn(BaseModel):
    access_token: str | None = None
    token_hash: str | None = None
    type: str | None = None


def _sesion_activa(request: Request):
    return bool(request.session.get("cliente_id"))


def _tipo_cliente_sesion(request: Request) -> str:
    """Resolve the persisted price tier; anonymous and failed lookups are retail."""
    if not _sesion_activa(request):
        return "minorista"
    try:
        filas = (get_client().table("clientes").select("tipo_cliente")
                 .eq("id", request.session["cliente_id"]).execute().data)
    except Exception:
        logger.exception("No se pudo resolver el tipo de cliente de la sesión")
        return "minorista"
    if filas and filas[0].get("tipo_cliente") == "mayorista":
        return "mayorista"
    return "minorista"


def _catalogo_autorizado(request: Request) -> tuple[list[dict], str]:
    """Return the product list and price tier authorized for this request."""
    tipo_cliente = _tipo_cliente_sesion(request)
    if tipo_cliente == "mayorista":
        productos_crudos, costos = _cargar_snapshot_mayorista()
    else:
        productos_crudos, costos = _cargar_productos(), None
    productos = [
        {campo: valor for campo, valor in producto.items()
         if campo not in _CAMPOS_PRIVADOS_CATALOGO}
        for producto in productos_crudos
    ]
    request.state.productos_publicos_autorizados = productos
    if tipo_cliente == "mayorista":
        return mayoristas.catalogo_mayorista(productos, costos), tipo_cliente
    return productos, tipo_cliente


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
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
    try:
        domicilios.crear(
            client, cliente["id"], "Principal", entrada.direccion,
            lat=entrada.lat, lng=entrada.lng, predeterminado=True,
        )
    except Exception:
        logger.exception("No se pudo guardar el domicilio inicial del registro")
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
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
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
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
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
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    tipo_cliente = _tipo_cliente_sesion(request)
    return {**cliente, "tipo_cliente": tipo_cliente, "modo_precio": tipo_cliente}


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
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
    return cliente


class DomicilioIn(BaseModel):
    alias: str = Field(min_length=1, max_length=80)
    direccion: str = Field(min_length=3, max_length=500)
    lat: float | None = None
    lng: float | None = None


@app.get("/api/domicilios")
def api_domicilios_listar(request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        return domicilios.listar(get_client(), request.session["cliente_id"])
    except Exception:
        logger.exception("No se pudieron obtener los domicilios")
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)


@app.post("/api/domicilios")
def api_domicilios_crear(entrada: DomicilioIn, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        domicilio = domicilios.crear(
            get_client(), request.session["cliente_id"], entrada.alias, entrada.direccion,
            lat=entrada.lat, lng=entrada.lng,
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo guardar el domicilio")
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
    return domicilio


@app.put("/api/domicilios/{domicilio_id}")
def api_domicilios_actualizar(domicilio_id: str, entrada: DomicilioIn, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        domicilio = domicilios.actualizar(
            get_client(), request.session["cliente_id"], domicilio_id, entrada.alias, entrada.direccion,
            lat=entrada.lat, lng=entrada.lng,
        )
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo actualizar el domicilio")
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
    return domicilio


@app.delete("/api/domicilios/{domicilio_id}")
def api_domicilios_eliminar(domicilio_id: str, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        domicilios.eliminar(get_client(), request.session["cliente_id"], domicilio_id)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo eliminar el domicilio")
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
    return {"ok": True}


@app.post("/api/domicilios/{domicilio_id}/predeterminado")
def api_domicilios_predeterminado(domicilio_id: str, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        domicilios.marcar_predeterminado(get_client(), request.session["cliente_id"], domicilio_id)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo marcar el domicilio como predeterminado")
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
    return {"ok": True}


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
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
    return {"ok": True}


@app.post("/api/me/condiciones-mayorista")
def api_aceptar_condiciones_mayorista(request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    if _tipo_cliente_sesion(request) != "mayorista":
        raise HTTPException(status_code=403, detail="Solo aplica a cuentas mayoristas")
    aceptadas_en = datetime.now(timezone.utc).isoformat()
    try:
        client = get_client()
        client.table("clientes").update(
            {"condiciones_mayorista_aceptadas_en": aceptadas_en}
        ).eq("id", request.session["cliente_id"]).execute()
    except Exception:
        logger.exception("No se pudo guardar la aceptación de condiciones mayoristas")
        return JSONResponse({"error": "No pude conectar, probá de nuevo en un momento"}, status_code=503)
    return {"ok": True, "condiciones_mayorista_aceptadas_en": aceptadas_en}


@app.get("/perfil")
def pagina_perfil(request: Request):
    if not _sesion_activa(request) or _debe_cambiar_password(request):
        return RedirectResponse("/login.html")
    return FileResponse(str(BASE / "static" / "perfil.html"))


class DetallePedidoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=300)
    color: str | None = Field(default=None, max_length=100)
    cantidad: int = Field(ge=1, le=100)
    usd_unitario: Decimal = Field(ge=0)
    usd_subtotal: Decimal = Field(ge=0)


class PedidoIn(BaseModel):
    productos: list[str] = Field(min_length=1)
    fecha_entrega: date | None = None
    direccion_entrega: str | None = Field(default=None, max_length=500)
    detalle: list[DetallePedidoIn] = Field(default_factory=list)
    total_usd: Decimal | None = Field(default=None, ge=0)
    descuento_usd: Decimal = Field(default=0, ge=0)
    codigo_descuento: str | None = Field(default=None, max_length=100)
    codigo_promo: str | None = Field(default=None, max_length=100)
    lat: float | None = None
    lng: float | None = None


class EditarFechaEntregaIn(BaseModel):
    fecha_entrega: date


class EditarDireccionEntregaIn(BaseModel):
    direccion_entrega: str = Field(max_length=500)


class TareaEntregaIn(BaseModel):
    fecha_entrega: date
    titulo: str = Field(min_length=1, max_length=200)
    cliente_id: str | None = Field(default=None, max_length=36)
    cliente_nombre: str | None = Field(default=None, max_length=200)
    nota: str | None = Field(default=None, max_length=1000)
    direccion: str | None = Field(default=None, max_length=500)
    enviar_a_alejo: bool = False
    derivar_a_vlad: bool = False


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
    client = get_client()
    catalogo_autorizado, modo_precio = _catalogo_autorizado(request)
    if not entrada.detalle:
        if modo_precio == "mayorista":
            return JSONResponse(
                {
                    "error": "Los precios cambiaron. Recargá el catálogo e intentá de nuevo.",
                    "conflicto": "catalogo",
                },
                status_code=409,
            )
        pedidos.guardar_pedido(
            client,
            cliente_id,
            entrada.productos,
            entrada.fecha_entrega,
            modo_precio=modo_precio,
            descuento_mayorista_usd=0,
        )
        return {"ok": True}
    if entrada.detalle and not (entrada.direccion_entrega or "").strip():
        return JSONResponse({"error": "Especificá dirección de entrega"}, status_code=400)

    error_precios = JSONResponse(
        {
            "error": "Los precios cambiaron. Recargá el catálogo e intentá de nuevo.",
            "conflicto": "catalogo",
        },
        status_code=409,
    )
    nombres_autorizados = [
        producto.get("nombre")
        for producto in catalogo_autorizado
        if producto.get("nombre")
    ]
    productos_publicos = getattr(
        request.state, "productos_publicos_autorizados", catalogo_autorizado
    )
    nombres_publicos = [
        producto.get("nombre")
        for producto in productos_publicos
        if producto.get("nombre")
    ]
    if (
        len(nombres_autorizados) != len(set(nombres_autorizados))
        or len(nombres_publicos) != len(set(nombres_publicos))
    ):
        return error_precios
    por_nombre = {
        producto.get("nombre"): producto
        for producto in catalogo_autorizado
        if producto.get("nombre")
    }
    publicos_por_nombre = {
        producto.get("nombre"): producto
        for producto in productos_publicos
        if producto.get("nombre")
    }
    proveedores = _cargar_proveedores()
    detalle = []
    productos_pedido = []
    total_bruto_usd = Decimal("0")
    descuento_mayorista_usd = Decimal("0")
    cantidad_total = 0
    for item in entrada.detalle:
        producto = por_nombre.get(item.nombre)
        if not producto or producto.get("usd") is None:
            return error_precios
        try:
            precio_autorizado = pedidos.decimal_monetario(producto.get("usd"))
        except ValueError:
            return error_precios
        if precio_autorizado < 0 or item.usd_unitario != precio_autorizado:
            return error_precios

        colores = producto.get("colores")
        if isinstance(colores, list) and colores:
            if item.color not in colores:
                return error_precios
            color = item.color
        else:
            if item.color not in (None, "Color único"):
                return error_precios
            color = None

        subtotal_autorizado = precio_autorizado * item.cantidad
        if item.usd_subtotal != subtotal_autorizado:
            return error_precios
        total_bruto_usd += subtotal_autorizado
        cantidad_total += item.cantidad
        if modo_precio == "mayorista":
            producto_publico = publicos_por_nombre.get(item.nombre)
            if not producto_publico or producto_publico.get("usd") is None:
                return error_precios
            try:
                precio_publico = pedidos.decimal_monetario(
                    producto_publico.get("usd")
                )
            except ValueError:
                return error_precios
            if precio_publico < precio_autorizado:
                return error_precios
            descuento_mayorista_usd += (
                precio_publico - precio_autorizado
            ) * item.cantidad
        detalle.append({
            "nombre": item.nombre,
            "color": color,
            "cantidad": item.cantidad,
            "usd_unitario": pedidos.numero_monetario_db(precio_autorizado),
            "usd_subtotal": pedidos.numero_monetario_db(subtotal_autorizado),
            "proveedor": resolver_proveedor(proveedores, item.nombre),
        })
        etiqueta = f"{item.nombre} ({color})" if color else item.nombre
        if etiqueta not in productos_pedido:
            productos_pedido.append(etiqueta)

    descuento_cantidad_usd = Decimal("0")
    if modo_precio == "minorista":
        if cantidad_total > 5:
            descuento_cantidad_usd = Decimal("7.5") * cantidad_total
        elif cantidad_total > 1:
            descuento_cantidad_usd = Decimal("5") * cantidad_total

    fila_descuento = None
    descuento_mailing_usd = Decimal("0")
    codigo_descuento = (entrada.codigo_descuento or "").strip().upper()
    if codigo_descuento and modo_precio == "minorista":
        fila_descuento = _descuento_codigo_row(client, cliente_id, codigo_descuento)
        descuento = (
            _resolver_descuento_codigo(catalogo_autorizado, fila_descuento, entrada.detalle)
            if fila_descuento
            else None
        )
        if not descuento:
            return JSONResponse(
                {
                    "error": "El código de descuento ya no es válido para este pedido.",
                    "conflicto": "codigo_descuento",
                },
                status_code=409,
            )
        descuento_mailing_usd = pedidos.decimal_monetario(
            descuento["descuento"]["usd"]
        )

    descuento_usd = min(
        descuento_cantidad_usd + descuento_mailing_usd,
        total_bruto_usd,
    )
    total_usd = total_bruto_usd - descuento_usd
    if entrada.total_usd != total_usd:
        return error_precios
    codigo_promo = (entrada.codigo_promo or "").strip().upper()
    if fila_descuento or codigo_promo:
        parametros = {
            "p_cliente_id": cliente_id,
            "p_codigo": fila_descuento["code"] if fila_descuento else None,
            "p_productos": productos_pedido,
            "p_detalle": detalle,
            "p_total_usd": pedidos.numero_monetario_db(total_usd),
            "p_descuento_usd": pedidos.numero_monetario_db(descuento_usd),
            "p_descuento_mailing_usd": pedidos.numero_monetario_db(
                descuento_mailing_usd
            ),
            "p_fecha_entrega": entrada.fecha_entrega.isoformat(),
            "p_direccion_entrega": (
                (entrada.direccion_entrega or "").strip() or None
            ),
            "p_modo_precio": modo_precio,
            "p_descuento_mayorista_usd": pedidos.numero_monetario_db(
                descuento_mayorista_usd
            ),
            "p_origen": "whatsapp",
            "p_codigo_promo": codigo_promo or None,
        }
        try:
            resultado = client.rpc(
                "guardar_pedido_con_descuento_mailing", parametros
            ).execute().data
        except Exception:
            logger.exception(
                "No se pudo guardar atomicamente el pedido con promociones"
            )
            return JSONResponse(
                {"error": "No pude confirmar las promociones y guardar el pedido."},
                status_code=503,
            )
        if not isinstance(resultado, dict):
            return JSONResponse(
                {"error": "No pude confirmar las promociones y guardar el pedido."},
                status_code=503,
            )
        if not resultado.get("ok"):
            if resultado.get("error") == "codigo_promo_no_disponible":
                return JSONResponse(
                    {
                        "error": "El código de regalo ya no está disponible para este pedido.",
                        "conflicto": "codigo_promo",
                    },
                    status_code=409,
                )
            return JSONResponse(
                {
                    "error": "El código de descuento ya no es válido para este pedido.",
                    "conflicto": "codigo_descuento",
                },
                status_code=409,
            )
        if not isinstance(resultado.get("pedido"), dict):
            return JSONResponse(
                {"error": "No pude confirmar las promociones y guardar el pedido."},
                status_code=503,
            )
        # La función guardar_pedido_con_descuento_mailing (RPC en Supabase) no
        # conoce lat/lng: se completan acá con un update aparte para no tener
        # que tocar esa función en la base.
        if entrada.lat is not None and entrada.lng is not None:
            pedido_id_rpc = resultado["pedido"].get("id")
            if pedido_id_rpc:
                try:
                    client.table("pedidos").update(
                        {"lat": entrada.lat, "lng": entrada.lng}
                    ).eq("id", pedido_id_rpc).execute()
                except Exception:
                    logger.exception("No se pudo guardar lat/lng del pedido %s", pedido_id_rpc)
    else:
        pedidos.guardar_pedido(
            client,
            cliente_id,
            productos_pedido,
            entrada.fecha_entrega,
            direccion_entrega=(entrada.direccion_entrega or "").strip() or None,
            detalle=detalle,
            total_usd=pedidos.numero_monetario_db(total_usd),
            descuento_usd=pedidos.numero_monetario_db(descuento_usd),
            modo_precio=modo_precio,
            descuento_mayorista_usd=pedidos.numero_monetario_db(
                descuento_mayorista_usd
            ),
            lat=entrada.lat,
            lng=entrada.lng,
        )
    return {"ok": True}


@app.put("/admin/pedidos/{pedido_id}/fecha-entrega")
def admin_pedido_editar_fecha(pedido_id: str, entrada: EditarFechaEntregaIn, request: Request):
    if not (_clientes_admin_activo(request) or _cadete_activo(request)):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    client = get_client()
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    if not _puede_operar_entrega(request, filas[0]):
        raise HTTPException(status_code=403, detail="Esta entrega no está asignada a tu usuario")
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


@app.put("/admin/pedidos/{pedido_id}/derivar")
def admin_pedido_derivar(pedido_id: str, entrada: DerivarEntregaIn, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    asignado_a = CADETE_SLUG if entrada.derivado else None
    observaciones = ((entrada.observaciones or "").strip() or None) if entrada.derivado else None
    client.table("pedidos").update({
        "asignado_a": asignado_a, "observaciones_cadete": observaciones,
    }).eq("id", pedido_id).execute()
    return {"ok": True, "pedido_id": pedido_id, "asignado_a": asignado_a}


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
    es_admin = _clientes_admin_activo(request)
    es_cadete = _cadete_activo(request)
    if not (es_admin or es_cadete):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    client = get_client()
    existentes = client.table("tareas_entrega").select("orden").eq(
        "fecha_entrega", entrada.fecha_entrega.isoformat()
    ).execute().data
    orden = max((int(t.get("orden") or 0) for t in existentes), default=0) + 1
    # El admin decide con el checkbox "Enviar a Alejo" si la tarea le queda
    # asignada o no. El cadete crea notas propias asignadas a él por default,
    # salvo que tilde "Derivar a Vlad" al crearla (se la manda directo, sin
    # el paso extra de derivarla después).
    if es_admin:
        asignado_a = CADETE_SLUG if entrada.enviar_a_alejo else None
    else:
        asignado_a = None if entrada.derivar_a_vlad else CADETE_SLUG
    tarea = {
        "id": str(uuid.uuid4()),
        "fecha_entrega": entrada.fecha_entrega.isoformat(),
        "titulo": entrada.titulo.strip(),
        "cliente_id": (entrada.cliente_id or "").strip() or None,
        "cliente_nombre": (entrada.cliente_nombre or "").strip() or None,
        "nota": (entrada.nota or "").strip() or None,
        "direccion": (entrada.direccion or "").strip() or None,
        "orden": orden,
        "asignado_a": asignado_a,
    }
    client.table("tareas_entrega").insert(tarea).execute()
    return {"ok": True, "tarea": tarea}


@app.post("/admin/tareas-entrega/{tarea_id}/completar")
def admin_completar_tarea_entrega(tarea_id: str, request: Request):
    if not (_clientes_admin_activo(request) or _cadete_activo(request)):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    client = get_client()
    filas = client.table("tareas_entrega").select("*").eq("id", tarea_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if not _puede_operar_entrega(request, filas[0]):
        raise HTTPException(status_code=403, detail="Esta tarea no está asignada a tu usuario")
    completada_en = datetime.now(timezone.utc).isoformat()
    actualizacion_tarea = {"completada_en": completada_en}
    if _cadete_activo(request):
        observacion_previa = (filas[0].get("observaciones_cadete") or "").strip()
        if "Entregado por Alejo" not in observacion_previa:
            actualizacion_tarea["observaciones_cadete"] = (
                f"{observacion_previa} · Entregado por Alejo" if observacion_previa else "Entregado por Alejo"
            )
    client.table("tareas_entrega").update(actualizacion_tarea).eq("id", tarea_id).execute()
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


@app.put("/admin/tareas-entrega/{tarea_id}/derivar")
def admin_tarea_derivar(tarea_id: str, entrada: DerivarEntregaIn, request: Request):
    es_admin = _clientes_admin_activo(request)
    es_cadete = _cadete_activo(request)
    if not (es_admin or es_cadete):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    client = get_client()
    filas = client.table("tareas_entrega").select("*").eq("id", tarea_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if not es_admin:
        # El cadete solo puede devolverle a Vlad una nota que ya es suya
        # (nunca auto-asignarse una tarea ajena ni tocar sus observaciones).
        if entrada.derivado or filas[0].get("asignado_a") != CADETE_SLUG:
            raise HTTPException(status_code=403, detail="No podés derivar esta tarea")
        client.table("tareas_entrega").update({"asignado_a": None}).eq("id", tarea_id).execute()
        return {"ok": True, "tarea_id": tarea_id, "asignado_a": None}
    asignado_a = CADETE_SLUG if entrada.derivado else None
    observaciones = ((entrada.observaciones or "").strip() or None) if entrada.derivado else None
    client.table("tareas_entrega").update({
        "asignado_a": asignado_a, "observaciones_cadete": observaciones,
    }).eq("id", tarea_id).execute()
    return {"ok": True, "tarea_id": tarea_id, "asignado_a": asignado_a}


@app.put("/admin/tareas-entrega/{tarea_id}/fecha-entrega")
def admin_tarea_editar_fecha(tarea_id: str, entrada: EditarFechaEntregaIn, request: Request):
    if not (_clientes_admin_activo(request) or _cadete_activo(request)):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    client = get_client()
    filas = client.table("tareas_entrega").select("*").eq("id", tarea_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if not _puede_operar_entrega(request, filas[0]):
        raise HTTPException(status_code=403, detail="Esta tarea no está asignada a tu usuario")
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
    return JSONResponse(
        {"error": "Este endpoint fue retirado; el código se consume al guardar el pedido."},
        status_code=410,
    )


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
    return JSONResponse(
        {"error": "Este endpoint fue retirado; el regalo se consume al guardar el pedido."},
        status_code=410,
    )


@app.get("/catalogo")
def pagina_catalogo(request: Request):
    if _sesion_activa(request) and _debe_cambiar_password(request):
        return RedirectResponse("/login.html")
    return FileResponse(str(BASE / "static" / "catalogo.html"))


@app.get("/preventa")
def pagina_preventa(request: Request):
    if not _sesion_activa(request) or _debe_cambiar_password(request):
        return RedirectResponse("/login.html")
    return FileResponse(str(BASE / "static" / "preventa.html"))


@app.get("/api/catalogo")
def api_catalogo(request: Request):
    productos, modo_precio = _catalogo_autorizado(request)
    if not productos:
        return {"secciones": {s: [] for s in catalogo.SECCIONES},
                "mensaje": "Estoy actualizando los precios",
                "modo_precio": modo_precio}
    return {"secciones": catalogo.secciones_catalogo(productos), "modo_precio": modo_precio}


_PRODUCTO_PUBLICO_ESTILO = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>document.documentElement.setAttribute('data-modo','classic');
try { if (localStorage.getItem('ttra_classic_theme') === 'light')
  document.documentElement.setAttribute('data-classic-theme','light'); } catch {}</script>
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="/theme.css">
<link rel="stylesheet" href="/classic.css">
<link rel="stylesheet" href="/classic-editorial.css">
<link rel="stylesheet" href="/site-pages.css">
"""

_PRODUCTO_PUBLICO_HEADER = (
    '<header class="ttra-page-header"><a class="ttra-page-brand" href="/" '
    'aria-label="The Tech Room Arg, volver al inicio">THE<br>TECH<br>ROOM<br>ARG<span>.</span></a>'
    '<nav class="ttra-page-actions" aria-label="Navegación">'
    '<a class="ttra-page-link" href="/catalogo">Explorar catálogo</a></nav></header>'
)
_PRODUCTO_PUBLICO_FOOTER = (
    '<footer class="ttra-page-footer"><div class="ttra-page-footer-brand">'
    'THE<br>TECH<br>ROOM<br>ARG<span>.</span></div>'
    '<p>© The Tech Room Arg · Córdoba</p></footer>'
)


@app.get("/p/{slug_url}", response_class=HTMLResponse)
def pagina_producto_publico(slug_url: str):
    productos_publicos, _costos = _cargar_productos(), None
    producto = next(
        (p for p in productos_publicos if slug_producto(p.get("nombre", "")) == slug_url),
        None,
    )
    if producto is None:
        return HTMLResponse(
            f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
            f"<title>Producto no encontrado</title>{_PRODUCTO_PUBLICO_ESTILO}</head>"
            f"<body class='ttra-page'>{_PRODUCTO_PUBLICO_HEADER}"
            f"<main class='ttra-product-main'><div class='ttra-product-art' aria-hidden='true'><span>THE TECH ROOM ARG.</span></div>"
            f"<div class='ttra-product-copy'><p class='ttra-page-eyebrow'>PRODUCTO NO DISPONIBLE</p>"
            f"<h1>No encontré ese producto</h1>"
            f"<p class='colores'>Puede que ya no esté disponible. Escribime por WhatsApp y te confirmo.</p>"
            f"<a class='ttra-product-cta' href='{WHATSAPP}'>Escribir por WhatsApp</a>"
            f"</div></main>{_PRODUCTO_PUBLICO_FOOTER}</body></html>",
            status_code=404,
        )
    nombre = html.escape(producto.get("nombre", ""))
    colores = producto.get("colores") or []
    colores_html = f"<p class='colores'>{html.escape(', '.join(colores))}</p>" if colores else ""
    usd = producto.get("usd")
    pesos = producto.get("pesos")
    transferencia = producto.get("transferencia")
    mensaje_wa = urlencode({"text": f"Hola! Te consulto por: {producto.get('nombre', '')}"})
    link_wa = f"{WHATSAPP}?{mensaje_wa}"
    return HTMLResponse(
        f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<title>{nombre} — The Tech Room Arg</title>{_PRODUCTO_PUBLICO_ESTILO}</head>"
        f"<body class='ttra-page'>{_PRODUCTO_PUBLICO_HEADER}"
        f"<main class='ttra-product-main'><div class='ttra-product-art' aria-hidden='true'><span>THE TECH ROOM ARG.</span></div>"
        f"<div class='ttra-product-copy'><p class='ttra-page-eyebrow'>PRODUCTO / THE TECH ROOM ARG</p>"
        f"<h1>{nombre}</h1>{colores_html}"
        f"<div class='ttra-product-prices'>"
        f"<p><strong>U$D {usd}</strong></p>"
        f"<p>$ {pesos} pesos contado</p>"
        f"<p>$ {transferencia} pesos transferencia</p>"
        f"</div>"
        f"<a class='ttra-product-cta' href='{link_wa}'>Consultar por WhatsApp</a>"
        f"<a class='ttra-product-secondary' href='/login'>Ver todo el catálogo</a>"
        f"</div></main>{_PRODUCTO_PUBLICO_FOOTER}</body></html>"
    )


@app.get("/api/recomendados")
def api_recomendados(request: Request, limit: int = 16):
    productos_autorizados, _modo_precio = _catalogo_autorizado(request)
    if not productos_autorizados:
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
    ranking = interacciones.recomendar_nombres(
        productos_autorizados, filas_interacciones, limite=limite
    )
    por_nombre = {
        producto["nombre"]: producto
        for producto in productos_autorizados
        if producto.get("nombre")
    }
    return {
        "productos": [
            {
                **por_nombre[candidato["nombre"]],
                "motivo_recomendacion": candidato["motivo_recomendacion"],
            }
            for candidato in ranking
            if candidato["nombre"] in por_nombre
        ]
    }


# Fallback para instalaciones antiguas o una actualización incompleta. La fuente
# normal es la cotización publicada atómicamente con el catálogo.
COTIZACION_DOLAR = 1565


def _cargar_cotizacion_catalogo():
    try:
        manifiesto = json.loads(CATALOGO_MANIFEST_PATH.read_text(encoding="utf-8"))
        cotizacion = manifiesto.get("cotizacion")
        if (
            isinstance(cotizacion, bool)
            or not isinstance(cotizacion, (int, float))
            or not math.isfinite(cotizacion)
            or cotizacion <= 0
        ):
            return COTIZACION_DOLAR
        return cotizacion
    except (OSError, json.JSONDecodeError, UnicodeError, TypeError, ValueError):
        logger.warning("No se pudo cargar la cotización del catálogo")
        return COTIZACION_DOLAR


@app.get("/api/cotizacion")
def api_cotizacion():
    return {"valor": _cargar_cotizacion_catalogo()}


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
    if not secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
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
