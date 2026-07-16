import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from web.chat import responder
from web.reglas import WHATSAPP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("web")

load_dotenv(Path(__file__).parent / ".env")

BASE = Path(__file__).parent
PRODUCTOS_PATH = BASE / "productos.json"

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


@app.post("/chat")
def chat(entrada: ChatIn):
    productos = _cargar_productos()
    if not productos:
        logger.warning("productos.json vacío o ausente")
        return {"respuesta": "Estoy actualizando los precios, escribime al WhatsApp "
                             f"{WHATSAPP} 🙌"}
    try:
        texto = responder(entrada.mensaje, entrada.historial, productos, _cliente())
    except Exception:
        logger.exception("Error al responder")
        texto = ("Tengo un problema técnico en este momento 😅. Escribime directo al "
                 f"WhatsApp {WHATSAPP} y te atiendo enseguida.")
    return {"respuesta": texto}


app.mount("/", StaticFiles(directory=str(BASE / "static"), html=True), name="static")
