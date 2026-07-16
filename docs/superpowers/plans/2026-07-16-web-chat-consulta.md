# Web de consulta (chat) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Una web local con un chat donde el cliente consulta por texto o voz, la IA (Claude API) entiende el pedido, busca en `productos.json` y responde en formato WhatsApp con los 3 precios, sin mostrar proveedor.

**Architecture:** Pipeline genera `productos.json` (sin proveedor) → backend FastAPI local guarda la API key y expone `POST /chat` que consulta a Claude con los productos + reglas → frontend HTML/JS de una sola página con entrada de texto y micrófono (Web Speech API).

**Tech Stack:** Python 3 (venv del proyecto), FastAPI + uvicorn, Anthropic SDK, HTML/CSS/JS plano, pytest.

## Global Constraints

- **Nunca** incluir el proveedor (sigla az/em/fr/va/ba) en `productos.json` ni en las respuestas al cliente.
- Respuestas **siempre en formato WhatsApp**: cordial, con emojis, cerrando con una pregunta.
- Mostrar **siempre los 3 precios**: 🇺🇸 U$D · 🇦🇷 pesos · 🏦 transferencia (pesos ÷ 0,97, redondeado).
- El bot **no inventa precios**: solo usa los de `productos.json`.
- Si el producto no está: **una sola** recomendación de lo más parecido, sin insistir.
- El bot habla **solo de productos/precios**; otra cosa → redirige amable al catálogo.
- Cierre de venta: derivar al WhatsApp `https://wa.me/543512145217`.
- La API key va en un `.env` local, **fuera de git**.
- Todo el código nuevo vive en la carpeta `web/`.

---

## Task 1: Generador de `productos.json`

**Files:**
- Create: `web/__init__.py` (vacío)
- Create: `web/productos.py`
- Test: `tests/test_productos.py`

**Interfaces:**
- Consumes: `consolidate.consolidar(items)`, `bands.calcular_precio(costo)`, `imagelink.google_image_link(nombre)`.
- Produces: `generar_productos(items: list[dict], cotizacion: float) -> list[dict]` donde cada dict es `{"nombre": str, "categoria": str, "usd": int, "pesos": int, "transferencia": int, "link_imagen": str}` (SIN `proveedor`). Y `escribir_productos_json(items, cotizacion, ruta)` que vuelca el array a un archivo JSON UTF-8.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_productos.py
import json
from web.productos import generar_productos, escribir_productos_json


def test_genera_productos_sin_proveedor_y_con_3_precios():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 630, "proveedor": "fr"},
        {"nombre": "iphone 13 128gb", "costo": 610, "proveedor": "az"},
    ]
    prods = generar_productos(items, cotizacion=1540)
    assert len(prods) == 1                      # se consolida al más barato
    p = prods[0]
    assert "proveedor" not in p                 # NUNCA el proveedor
    assert p["usd"] == 660                      # 610 + banda 50, redondeo a 5
    assert p["pesos"] == 660 * 1540
    assert p["transferencia"] == round(p["pesos"] / 0.97)
    assert p["link_imagen"].startswith("https://www.google.com/search?tbm=isch")
    assert p["categoria"]                       # tiene alguna categoría no vacía


def test_escribir_productos_json(tmp_path):
    items = [{"nombre": "Moto G15 128GB", "costo": 150, "proveedor": "va"}]
    ruta = tmp_path / "productos.json"
    escribir_productos_json(items, 1540, str(ruta))
    data = json.loads(ruta.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) == 1
    assert "proveedor" not in data[0]
    assert data[0]["nombre"] == "Moto G15 128GB"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/python -m pytest tests/test_productos.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'web'"

- [ ] **Step 3: Write minimal implementation**

```python
# web/__init__.py  (archivo vacío)
```

```python
# web/productos.py
import json

from consolidate import consolidar
from bands import calcular_precio
from imagelink import google_image_link


def _categoria(nombre):
    l = nombre.lower()
    if "iphone" in l:
        return "Apple - iPhone" if "usad" not in l else "Apple - iPhone Usado"
    if "ipad" in l:
        return "Apple - iPad"
    if "airpod" in l:
        return "Apple - AirPods"
    if "watch" in l:
        return "Apple - Watch"
    if "macbook" in l or "mac mini" in l or "macmini" in l or "imac" in l:
        return "Mac"
    if "notebook" in l or "laptop" in l:
        return "Notebook"
    if "samsung" in l or "galaxy" in l:
        return "Samsung"
    if any(b in l for b in ("xiaomi", "poco", "redmi")):
        return "Xiaomi"
    if l.startswith("moto") or "motorola" in l:
        return "Motorola"
    if "realme" in l:
        return "Realme"
    return "Otros"


def generar_productos(items, cotizacion):
    consolidados = consolidar(items)["lista"]
    productos = []
    for fila in consolidados:
        usd = calcular_precio(fila["costo"])
        pesos = round(usd * cotizacion)
        transferencia = round(pesos / 0.97)
        productos.append({
            "nombre": fila["nombre"],
            "categoria": _categoria(fila["nombre"]),
            "usd": usd,
            "pesos": pesos,
            "transferencia": transferencia,
            "link_imagen": google_image_link(fila["nombre"]),
        })
    return productos


def escribir_productos_json(items, cotizacion, ruta):
    productos = generar_productos(items, cotizacion)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(productos, f, ensure_ascii=False, indent=2)
    return productos
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/python -m pytest tests/test_productos.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add web/__init__.py web/productos.py tests/test_productos.py
git commit -m "feat: generador de productos.json para la web (sin proveedor)"
```

---

## Task 2: Backend FastAPI con endpoint `/chat`

**Files:**
- Create: `web/reglas.py` (el system prompt / reglas del bot)
- Create: `web/chat.py` (lógica de respuesta, con cliente Claude inyectable)
- Create: `web/app.py` (FastAPI: sirve frontend + `POST /chat`)
- Create: `web/.env.example`
- Modify: `requirements.txt` (agregar fastapi, uvicorn, anthropic, python-dotenv)
- Modify: `.gitignore` (agregar `web/.env` y `web/productos.json`)
- Test: `tests/test_chat.py`

**Interfaces:**
- Consumes: `productos.json` (Task 1).
- Produces:
  - `web/reglas.py`: `construir_system(productos: list[dict]) -> str` — arma el prompt de sistema con las reglas + el catálogo en JSON.
  - `web/chat.py`: `responder(mensaje: str, historial: list[dict], productos: list[dict], client) -> str` — llama a `client.messages.create(...)` y devuelve el texto. `client` se inyecta para poder testear sin API real. `historial` es lista de `{"role": "user"|"assistant", "content": str}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_chat.py
from web.reglas import construir_system
from web.chat import responder


class _FakeContent:
    def __init__(self, text): self.text = text


class _FakeResp:
    def __init__(self, text): self.content = [_FakeContent(text)]


class _FakeMessages:
    def __init__(self, parent): self.parent = parent
    def create(self, **kwargs):
        self.parent.ultimo_kwargs = kwargs
        return _FakeResp("iPhone 13 128GB\n🇺🇸 U$D 660 · 🇦🇷 $ 1.016.400 · 🏦 $ 1.047.835")


class FakeClient:
    def __init__(self): self.messages = _FakeMessages(self)


def test_system_incluye_reglas_y_catalogo_sin_proveedor():
    productos = [{"nombre": "iPhone 13 128GB", "categoria": "Apple - iPhone",
                  "usd": 660, "pesos": 1016400, "transferencia": 1047835,
                  "link_imagen": "x"}]
    system = construir_system(productos)
    assert "WhatsApp" in system
    assert "proveedor" in system.lower()          # la regla de NO mostrar proveedor
    assert "iPhone 13 128GB" in system            # el catálogo está embebido
    assert "wa.me/543512145217" in system


def test_responder_llama_al_cliente_y_devuelve_texto():
    productos = [{"nombre": "iPhone 13 128GB", "categoria": "Apple - iPhone",
                  "usd": 660, "pesos": 1016400, "transferencia": 1047835,
                  "link_imagen": "x"}]
    client = FakeClient()
    out = responder("tenes iphone 13?", [], productos, client)
    assert "U$D 660" in out
    # se le pasó el mensaje del usuario al modelo
    msgs = client.ultimo_kwargs["messages"]
    assert msgs[-1] == {"role": "user", "content": "tenes iphone 13?"}
    # el system prompt viaja aparte
    assert "system" in client.ultimo_kwargs
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/python -m pytest tests/test_chat.py -v`
Expected: FAIL con "ModuleNotFoundError: No module named 'web.reglas'"

- [ ] **Step 3: Write minimal implementation**

```python
# web/reglas.py
import json

WHATSAPP = "https://wa.me/543512145217"


def construir_system(productos):
    catalogo = json.dumps(productos, ensure_ascii=False)
    return f"""Sos el asistente de ventas de THE TECH ROOM ARG (electrónica, Córdoba, Argentina).
Respondés a clientes por un chat web. Reglas ESTRICTAS:

- Respondé SIEMPRE en formato WhatsApp: cordial, con emojis, cerrando con una pregunta.
- Mostrá SIEMPRE los 3 precios de cada producto exactamente como están en el catálogo:
  🇺🇸 U$D {{usd}} · 🇦🇷 $ {{pesos}} · 🏦 $ {{transferencia}} (transferencia en pesos).
  Formateá los números en pesos con puntos de miles (ej. 1.016.400).
- NUNCA muestres ni menciones proveedores, fuentes ni de dónde sacás los productos.
- Usá SOLO los productos del catálogo de abajo. NUNCA inventes un producto ni un precio.
- Si el cliente pide algo que NO está en el catálogo, recomendá UNA SOLA vez lo más
  parecido que haya, sin insistir. Si no hay nada parecido, decilo amablemente.
- Hablá solo de productos y precios. Si preguntan otra cosa, redirigí amable al catálogo.
- Cuando el cliente quiera avanzar con la compra, derivalo al WhatsApp: {WHATSAPP}

CATÁLOGO (JSON):
{catalogo}
"""


# web/chat.py
MODELO = "claude-sonnet-5"


def responder(mensaje, historial, productos, client):
    from web.reglas import construir_system
    system = construir_system(productos)
    mensajes = list(historial) + [{"role": "user", "content": mensaje}]
    resp = client.messages.create(
        model=MODELO,
        max_tokens=1024,
        system=system,
        messages=mensajes,
    )
    return resp.content[0].text
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/python -m pytest tests/test_chat.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Crear app FastAPI, deps y config**

```python
# web/app.py
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
```

```
# web/.env.example
ANTHROPIC_API_KEY=sk-ant-tu-key-aca
```

Agregar a `requirements.txt` (mantener las líneas existentes):
```
fastapi
uvicorn
anthropic
python-dotenv
```

Agregar a `.gitignore` (crear el archivo si no existe):
```
web/.env
web/productos.json
```

Instalar dependencias:
```bash
cd "/Users/toraba/TTRA Project" && ./.venv/bin/pip install fastapi uvicorn anthropic python-dotenv
```

- [ ] **Step 6: Commit**

```bash
git add web/reglas.py web/chat.py web/app.py web/.env.example requirements.txt .gitignore tests/test_chat.py
git commit -m "feat: backend FastAPI con endpoint /chat (Claude API inyectable)"
```

---

## Task 3: Frontend — página de chat con texto y voz

**Files:**
- Create: `web/static/index.html`
- Create: `web/static/styles.css`
- Create: `web/static/chat.js`

**Interfaces:**
- Consumes: `POST /chat` con body `{mensaje, historial}` → `{respuesta}`.
- Produces: página servida en `/` por FastAPI.

- [ ] **Step 1: Crear la página HTML**

```html
<!-- web/static/index.html -->
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>THE TECH ROOM ARG — Consultas</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <header><h1>🤖 THE TECH ROOM ARG</h1><p>Consultá precios — escribí o usá el micrófono 🎤</p></header>
  <main id="chat"></main>
  <form id="form">
    <button type="button" id="mic" title="Hablar">🎤</button>
    <input id="entrada" autocomplete="off" placeholder="Escribí tu consulta…" />
    <button type="submit">Enviar</button>
  </form>
  <script src="chat.js"></script>
</body>
</html>
```

- [ ] **Step 2: Crear estilos**

```css
/* web/static/styles.css */
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; background: #0b141a; color: #e9edef;
       display: flex; flex-direction: column; height: 100vh; }
header { background: #202c33; padding: 12px 16px; }
header h1 { margin: 0; font-size: 18px; }
header p { margin: 4px 0 0; font-size: 13px; color: #8696a0; }
#chat { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 8px; }
.msg { max-width: 80%; padding: 8px 12px; border-radius: 10px; white-space: pre-wrap; line-height: 1.35; }
.user { align-self: flex-end; background: #005c4b; }
.bot { align-self: flex-start; background: #202c33; }
form { display: flex; gap: 8px; padding: 12px; background: #202c33; }
input { flex: 1; padding: 10px; border-radius: 8px; border: none; font-size: 15px; }
button { padding: 10px 14px; border: none; border-radius: 8px; background: #00a884; color: #fff;
         font-size: 15px; cursor: pointer; }
#mic.grabando { background: #e53935; }
```

- [ ] **Step 3: Crear la lógica del chat (texto + voz)**

```javascript
// web/static/chat.js
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const entrada = document.getElementById("entrada");
const mic = document.getElementById("mic");
const historial = [];

function burbuja(texto, quien) {
  const div = document.createElement("div");
  div.className = "msg " + quien;
  div.textContent = texto;
  chat.appendChild(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

async function enviar(mensaje) {
  burbuja(mensaje, "user");
  historial.push({ role: "user", content: mensaje });
  const cargando = burbuja("…", "bot");
  try {
    const r = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje, historial: historial.slice(0, -1) }),
    });
    const data = await r.json();
    cargando.textContent = data.respuesta;
    historial.push({ role: "assistant", content: data.respuesta });
  } catch (e) {
    cargando.textContent = "Error de conexión. Probá de nuevo 🙏";
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const t = entrada.value.trim();
  if (!t) return;
  entrada.value = "";
  enviar(t);
});

// --- Voz (Web Speech API) ---
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
  const rec = new SR();
  rec.lang = "es-AR";
  rec.interimResults = false;
  mic.addEventListener("click", () => { mic.classList.add("grabando"); rec.start(); });
  rec.addEventListener("result", (ev) => { entrada.value = ev.results[0][0].transcript; });
  rec.addEventListener("end", () => { mic.classList.remove("grabando"); });
} else {
  mic.style.display = "none";  // navegador sin soporte de voz
}

burbuja("¡Hola! 😊 Soy el asistente de THE TECH ROOM ARG. ¿Qué estás buscando?", "bot");
```

- [ ] **Step 4: Verificación manual**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/python -c "import pathlib; assert (pathlib.Path('web/static/index.html')).exists() and (pathlib.Path('web/static/chat.js')).exists()"`
Expected: sin error (los archivos existen)

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html web/static/styles.css web/static/chat.js
git commit -m "feat: frontend del chat con entrada de texto y voz"
```

---

## Task 4: Integración, script de datos y README

**Files:**
- Create: `web/generar_datos.py` (genera `web/productos.json` desde un `entrada.json` + cotización)
- Create: `web/README.md` (cómo correrlo)
- Test: `tests/test_generar_datos.py`

**Interfaces:**
- Consumes: `web/productos.py` (Task 1), un `entrada.json` con `{"items": [...]}`.
- Produces: `web/productos.json` en disco; instrucciones de arranque.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_generar_datos.py
import json
import subprocess
import sys
from pathlib import Path


def test_genera_productos_json_desde_entrada(tmp_path):
    entrada = tmp_path / "entrada.json"
    entrada.write_text(json.dumps({"items": [
        {"nombre": "iPhone 13 128GB", "costo": 610, "proveedor": "az"}
    ]}), encoding="utf-8")
    salida = tmp_path / "productos.json"
    proj = Path(__file__).resolve().parents[1]
    r = subprocess.run(
        [sys.executable, "web/generar_datos.py", str(entrada), "1540", str(salida)],
        cwd=str(proj), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    data = json.loads(salida.read_text(encoding="utf-8"))
    assert data[0]["nombre"] == "iPhone 13 128GB"
    assert "proveedor" not in data[0]
    assert data[0]["usd"] == 660
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/python -m pytest tests/test_generar_datos.py -v`
Expected: FAIL (returncode != 0, el script no existe)

- [ ] **Step 3: Write minimal implementation**

```python
# web/generar_datos.py
import json
import sys

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__file__)))
from web.productos import escribir_productos_json


def main():
    if len(sys.argv) != 4:
        print("uso: python web/generar_datos.py <entrada.json> <cotizacion> <salida.json>")
        sys.exit(1)
    entrada, cotiz, salida = sys.argv[1], float(sys.argv[2]), sys.argv[3]
    with open(entrada, encoding="utf-8") as f:
        items = json.load(f)["items"]
    prods = escribir_productos_json(items, cotiz, salida)
    print(f"OK: {len(prods)} productos -> {salida}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/python -m pytest tests/test_generar_datos.py -v`
Expected: PASS (1 passed)

- [ ] **Step 5: Crear README**

```markdown
<!-- web/README.md -->
# Web de consulta (chat) — THE TECH ROOM ARG

Chat local que responde consultas de clientes usando el listado de precios.

## Configuración (una vez)

1. Instalar dependencias:
   ```bash
   ./.venv/bin/pip install -r requirements.txt
   ```
2. Copiar `web/.env.example` a `web/.env` y pegar la API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

## Cada vez que actualizás precios

Generar el `productos.json` desde el `entrada.json` del pipeline + la cotización del día:
```bash
./.venv/bin/python web/generar_datos.py entrada.json 1540 web/productos.json
```

## Levantar el chat

```bash
./.venv/bin/uvicorn web.app:app --reload --port 8000
```
Abrir en el navegador: http://localhost:8000
(El micrófono funciona en Chrome/Edge.)
```

- [ ] **Step 6: Commit**

```bash
git add web/generar_datos.py web/README.md tests/test_generar_datos.py
git commit -m "feat: script de datos y README para correr la web"
```

---

## Verificación final (manual, con la API key real)

1. Generar datos: `./.venv/bin/python web/generar_datos.py entrada.json 1540 web/productos.json`
2. Levantar: `./.venv/bin/uvicorn web.app:app --reload --port 8000`
3. Abrir http://localhost:8000, preguntar "tenés iphone 13?" y verificar: respuesta WhatsApp, 3 precios, sin proveedor.
4. Probar el micrófono en Chrome.
5. Preguntar por algo inexistente y verificar que recomienda una sola alternativa.
