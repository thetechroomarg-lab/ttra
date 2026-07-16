import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from web import leads
from web.chat import responder
from web.reglas import WHATSAPP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web")

load_dotenv(Path(__file__).parent / ".env")

BASE = Path(__file__).parent
PRODUCTOS_PATH = BASE / "productos.json"

# Tope de gasto por chat/cliente (USD). Al superarlo, se lo deriva al WhatsApp.
LIMITE_USD = 0.25
_gasto = {}  # sesion -> USD acumulado

app = FastAPI()


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
    except Exception:
        logger.exception("Error al responder")
        texto = ("Tengo un problema técnico en este momento 😅. Escribime directo al "
                 f"WhatsApp {WHATSAPP} y te atiendo enseguida.")
    return {"respuesta": texto}


app.mount("/", StaticFiles(directory=str(BASE / "static"), html=True), name="static")
