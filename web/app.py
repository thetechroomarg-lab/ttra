import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from web.chat import responder

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
        return {"respuesta": "Estoy actualizando los precios, escribime al WhatsApp "
                             "https://wa.me/543512145217 🙌"}
    try:
        texto = responder(entrada.mensaje, entrada.historial, productos, _cliente())
    except Exception:
        texto = ("Tengo un problema técnico en este momento 😅. Escribime directo al "
                 "WhatsApp https://wa.me/543512145217 y te atiendo enseguida.")
    return {"respuesta": texto}


app.mount("/", StaticFiles(directory=str(BASE / "static"), html=True), name="static")
