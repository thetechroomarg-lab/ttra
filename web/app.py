import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from web import auth, buscador, catalogo, leads
from web.chat import responder
from web.reglas import WHATSAPP

# Interruptor: False = buscador gratis (sin IA). True = IA (Claude, tu API key).
# Para volver a la IA, cambiá esto a True y reiniciá el servidor.
USAR_IA = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web")

load_dotenv(Path(__file__).parent / ".env")

BASE = Path(__file__).parent
PRODUCTOS_PATH = BASE / "productos.json"

# Tope de gasto por chat/cliente (USD). Al superarlo, se lo deriva al WhatsApp.
LIMITE_USD = 0.25
_gasto = {}  # sesion -> USD acumulado

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret-cambiar-en-produccion"),
)


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
def chat(entrada: ChatIn):
    productos = _cargar_productos()
    if not productos:
        logger.warning("productos.json vacío o ausente")
        return {"respuesta": "Estoy actualizando los precios, escribime al WhatsApp "
                             f"{WHATSAPP} 🙌"}

    # Modo GRATIS (sin IA): buscador determinístico, costo cero.
    if not USAR_IA:
        texto, genero, datos = buscador.responder_sin_ia(entrada.mensaje, entrada.sesion, productos)
        if datos:
            try:
                leads.guardar_lead(entrada.sesion, datos,
                                   fecha=datetime.now().strftime("%Y-%m-%d %H:%M"))
            except Exception:
                logger.exception("No se pudo guardar el lead")
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
        if datos:
            try:
                leads.guardar_lead(entrada.sesion, datos,
                                   fecha=datetime.now().strftime("%Y-%m-%d %H:%M"))
            except Exception:
                logger.exception("No se pudo guardar el lead")
        genero = (datos or {}).get("genero", "")
    except Exception:
        logger.exception("Error al responder")
        texto = ("Tengo un problema técnico en este momento 😅. Escribime directo al "
                 f"WhatsApp {WHATSAPP} y te atiendo enseguida.")
        genero = ""
    return {"respuesta": texto, "genero": genero}


class RegistroIn(BaseModel):
    nombre: str
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


def _sesion_activa(request: Request):
    return bool(request.session.get("usuario_email"))


@app.post("/registro")
def registro(entrada: RegistroIn, request: Request):
    conn = auth.get_conn()
    try:
        auth.crear_usuario(
            conn, entrada.nombre, entrada.email, entrada.password,
            datetime.now().strftime("%Y-%m-%d %H:%M"),
        )
    except auth.EmailDuplicadoError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        conn.close()
    request.session["usuario_email"] = entrada.email.strip().lower()
    request.session["usuario_nombre"] = entrada.nombre
    return {"ok": True}


@app.post("/login")
def login(entrada: LoginIn, request: Request):
    conn = auth.get_conn()
    usuario = auth.verificar_usuario(conn, entrada.email, entrada.password)
    conn.close()
    if usuario is None:
        return JSONResponse({"error": "Usuario o contraseña incorrectos"}, status_code=401)
    request.session["usuario_email"] = usuario["email"]
    request.session["usuario_nombre"] = usuario["nombre"]
    return {"ok": True}


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/catalogo")
def pagina_catalogo(request: Request):
    if not _sesion_activa(request):
        return RedirectResponse("/login.html")
    return FileResponse(str(BASE / "static" / "catalogo.html"))


@app.get("/api/catalogo")
def api_catalogo(request: Request):
    if not _sesion_activa(request):
        return JSONResponse({"error": "No autenticado"}, status_code=401)
    productos = _cargar_productos()
    if not productos:
        return {"secciones": {s: [] for s in catalogo.SECCIONES},
                "mensaje": "Estamos actualizando los precios"}
    return {"secciones": catalogo.secciones_catalogo(productos)}


app.mount("/", StaticFiles(directory=str(BASE / "static"), html=True), name="static")
