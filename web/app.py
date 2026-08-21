import html
import json
import logging
import os
import posixpath
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.sessions import SessionMiddleware

from web import buscador, catalogo, cuentas, pedidos
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
    logger.warning("ADMIN_CLIENTES_PASSWORD no configurado — usando clave de desarrollo, no apta para producción")
    ADMIN_CLIENTES_PASSWORD = "dev-cambiar-en-produccion"

# Tope de gasto por chat/cliente (USD). Al superarlo, se lo deriva al WhatsApp.
LIMITE_USD = 0.25
_gasto = {}  # sesion -> USD acumulado

app = FastAPI()


@app.middleware("http")
async def sin_cache_estaticos(request: Request, call_next):
    """Evita que el navegador se quede con una versión vieja de JS/CSS
    cacheada tras un simple F5 (cada refresh revalida contra el archivo
    real en disco)."""
    response = await call_next(request)
    if request.url.path.endswith((".js", ".css")):
        response.headers["Cache-Control"] = "no-cache"
    return response


_RUTAS_HTML_PUBLICAS = {"/login.html"}


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
    logger.warning("SESSION_SECRET no configurado — usando clave de desarrollo, no apta para producción")
    _session_secret = "dev-secret-cambiar-en-produccion"
app.add_middleware(SessionMiddleware, secret_key=_session_secret, https_only=True)


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


def _clientes_admin_activo(request: Request):
    return bool(request.session.get("clientes_admin_ok"))


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
    filas_pedidos = client.table("pedidos").select("*").execute().data
    pedidos_por_cliente = {}
    for p in filas_pedidos:
        pedidos_por_cliente.setdefault(p["cliente_id"], []).extend(p.get("productos", []))
    clientes = [
        {
            "id": c.get("id", ""),
            "nombre": f"{c.get('nombre', '')} {c.get('apellido', '')}".strip(),
            "celular": c.get("celular", ""),
            "productos": pedidos_por_cliente.get(c.get("id"), []),
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
            f"<td>{html.escape(' | '.join(c.get('productos', [])))}</td>"
            f"<td>{html.escape(c.get('fecha', ''))}</td>"
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
    <thead><tr><th>Nombre</th><th>Celular</th><th>Productos consultados</th><th>Fecha</th><th>Cuenta</th></tr></thead>
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


class RegistroIn(BaseModel):
    nombre: str
    apellido: str
    celular: str
    email: EmailStr
    password: str = Field(min_length=8)
    username: str = Field(min_length=3)


class LoginIn(BaseModel):
    email: str
    password: str


def _sesion_activa(request: Request):
    return bool(request.session.get("cliente_id"))


def _debe_cambiar_password(request: Request):
    return bool(request.session.get("debe_cambiar_password"))


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
            entrada.email, entrada.password, entrada.username,
        )
    except (cuentas.CelularDuplicadoError, cuentas.EmailDuplicadoError,
            cuentas.UsernameDuplicadoError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception:
        logger.exception("No se pudo completar el registro (¿Supabase no disponible?)")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    request.session["cliente_id"] = cliente["id"]
    request.session["cliente_nombre"] = cliente["nombre"]
    return {"ok": True}


@app.post("/login")
def login(entrada: LoginIn, request: Request):
    try:
        cliente = cuentas.login_cliente(get_client(), get_client(), entrada.email, entrada.password)
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
    return {"ok": True, "debe_cambiar_password": cliente["debe_cambiar_password"]}


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


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
    username: str = Field(min_length=3)


@app.put("/api/me")
def api_me_actualizar(entrada: ActualizarMeIn, request: Request):
    if not _sesion_activa(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    try:
        cliente = cuentas.actualizar_cliente(
            get_client(), request.session["cliente_id"],
            entrada.nombre, entrada.apellido, entrada.celular, entrada.username,
        )
    except (cuentas.CelularDuplicadoError, cuentas.UsernameDuplicadoError, ValueError) as e:
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


@app.post("/api/pedidos")
def api_pedidos(entrada: PedidoIn, request: Request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=401, detail="Sesión requerida")
    if _debe_cambiar_password(request):
        raise HTTPException(status_code=403, detail="Tenés que elegir una contraseña nueva antes de seguir")
    pedidos.guardar_pedido(get_client(), cliente_id, entrada.productos)
    return {"ok": True}


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
    if not _sesion_activa(request) or _debe_cambiar_password(request):
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
