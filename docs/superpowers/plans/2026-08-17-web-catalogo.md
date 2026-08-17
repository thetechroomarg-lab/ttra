# Web de catálogo con login — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar a la web existente (`web/app.py`) un catálogo público con login
(usuario/contraseña) y 5 secciones (Celulares, Accesorios Celulares, Tablets, Notebooks
y Macbooks, Gaming), con tema oscuro/chic y un carrousel de marcas.

**Architecture:** Todo vive en el mismo proceso FastAPI que ya sirve el chat. Autenticación
con sesión de cookie firmada (`SessionMiddleware`) + usuarios en SQLite con password
hasheado. El catálogo se arma desde el mismo `productos.json` que ya usa el chat, con una
capa de mapeo nueva (`web/catalogo.py`) que no toca el pipeline de precios existente.

**Tech Stack:** FastAPI, Starlette `SessionMiddleware`, SQLite (stdlib `sqlite3`),
`passlib[bcrypt]`, `itsdangerous`, pytest + `fastapi.testclient.TestClient`.

**Spec:** `docs/superpowers/specs/2026-08-17-web-catalogo-design.md`

## Global Constraints

- Login v1 es **solo usuario/contraseña** — Gmail queda fuera de esta implementación.
- Login inválido devuelve **siempre** el mismo mensaje genérico ("usuario o contraseña
  incorrectos"); nunca debe distinguir si el email existe o no.
- No se modifica `bands.py` ni `consolidate.py` — el mapeo de secciones del catálogo es
  una capa nueva, separada del pipeline de precios.
- Si `productos.json` no existe o está vacío, el catálogo debe mostrar un mensaje de
  "actualizando precios" en vez de romper (mismo criterio que ya usa `/chat`).
- El carrousel de marcas es **texto estilizado**, no logos reales (decisión ya tomada).
- Tema oscuro (grafito/negro + acento dorado/cobre) en login y catálogo.

---

## Task 1: Dependencias de autenticación

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: `passlib.hash.bcrypt` y `starlette.middleware.sessions.SessionMiddleware`
  disponibles para las tareas siguientes.

- [ ] **Step 1: Agregar las dependencias**

Agregar al final de `requirements.txt`:

```
passlib[bcrypt]==1.7.4
itsdangerous==2.2.0
```

- [ ] **Step 2: Instalar en el venv del proyecto**

Run: `./.venv/bin/pip install -r requirements.txt`
Expected: instala `passlib`, `bcrypt` e `itsdangerous` sin errores.

- [ ] **Step 3: Verificar que se puede importar**

Run: `./.venv/bin/python -c "from passlib.hash import bcrypt; from starlette.middleware.sessions import SessionMiddleware; print('ok')"`
Expected: imprime `ok`.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: agregar passlib e itsdangerous para login"
```

---

## Task 2: Módulo de autenticación (`web/auth.py`)

**Files:**
- Create: `web/auth.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Consumes: nada (módulo independiente, usa solo `sqlite3` y `passlib`).
- Produces:
  - `get_conn(db_path=None) -> sqlite3.Connection` — abre (y crea si no existe) la
    tabla `usuarios`. `db_path` es un `pathlib.Path` o `str`; si es `None` usa el
    módulo-level `DB_PATH`.
  - `class EmailDuplicadoError(Exception)`
  - `crear_usuario(conn, nombre: str, email: str, password: str, creado: str) -> None`
    — lanza `EmailDuplicadoError` si el email ya existe (comparación case-insensitive).
  - `verificar_usuario(conn, email: str, password: str) -> dict | None` — devuelve
    `{"id": int, "nombre": str, "email": str}` si las credenciales son correctas,
    `None` si no.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_auth.py`:

```python
import pytest

from web import auth


@pytest.fixture
def conn(tmp_path):
    c = auth.get_conn(tmp_path / "test_usuarios.db")
    yield c
    c.close()


def test_crear_y_verificar_usuario(conn):
    auth.crear_usuario(conn, "Juan Perez", "Juan@Ejemplo.com", "clave123", "2026-08-17 10:00")
    usuario = auth.verificar_usuario(conn, "juan@ejemplo.com", "clave123")
    assert usuario is not None
    assert usuario["nombre"] == "Juan Perez"
    assert usuario["email"] == "juan@ejemplo.com"


def test_verificar_con_password_incorrecta_devuelve_none(conn):
    auth.crear_usuario(conn, "Juan Perez", "juan@ejemplo.com", "clave123", "2026-08-17 10:00")
    assert auth.verificar_usuario(conn, "juan@ejemplo.com", "clave-mala") is None


def test_verificar_email_inexistente_devuelve_none(conn):
    assert auth.verificar_usuario(conn, "nadie@ejemplo.com", "clave123") is None


def test_crear_usuario_email_duplicado_lanza_error(conn):
    auth.crear_usuario(conn, "Juan Perez", "juan@ejemplo.com", "clave123", "2026-08-17 10:00")
    with pytest.raises(auth.EmailDuplicadoError):
        auth.crear_usuario(conn, "Otro Nombre", "JUAN@ejemplo.com", "otra-clave", "2026-08-17 11:00")
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `./.venv/bin/pytest tests/test_auth.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.auth'` (o similar).

- [ ] **Step 3: Implementar `web/auth.py`**

```python
import sqlite3
from pathlib import Path

from passlib.hash import bcrypt

DB_PATH = Path(__file__).parent / "usuarios.db"


class EmailDuplicadoError(Exception):
    pass


def get_conn(db_path=None):
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            creado TEXT NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def crear_usuario(conn, nombre, email, password, creado):
    email = email.strip().lower()
    existente = conn.execute(
        "SELECT 1 FROM usuarios WHERE email = ?", (email,)
    ).fetchone()
    if existente:
        raise EmailDuplicadoError(f"Ya existe una cuenta con el email {email}")
    password_hash = bcrypt.hash(password)
    conn.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, creado) VALUES (?, ?, ?, ?)",
        (nombre, email, password_hash, creado),
    )
    conn.commit()


def verificar_usuario(conn, email, password):
    email = email.strip().lower()
    fila = conn.execute(
        "SELECT id, nombre, email, password_hash FROM usuarios WHERE email = ?",
        (email,),
    ).fetchone()
    if fila is None:
        return None
    id_, nombre, email_db, password_hash = fila
    if not bcrypt.verify(password, password_hash):
        return None
    return {"id": id_, "nombre": nombre, "email": email_db}
```

- [ ] **Step 4: Correr el test para confirmar que pasa**

Run: `./.venv/bin/pytest tests/test_auth.py -v`
Expected: 4 PASSED.

- [ ] **Step 5: Commit**

```bash
git add web/auth.py tests/test_auth.py
git commit -m "feat: modulo de autenticacion con SQLite y bcrypt"
```

---

## Task 3: Rutas de login/registro/logout en `web/app.py`

**Files:**
- Modify: `web/app.py`
- Modify: `web/.env.example`
- Test: `tests/test_app_auth.py`

**Interfaces:**
- Consumes: `web.auth.get_conn`, `web.auth.crear_usuario`, `web.auth.verificar_usuario`,
  `web.auth.EmailDuplicadoError` (Task 2).
- Produces:
  - `POST /registro` — body `{"nombre": str, "email": str, "password": str}` →
    `{"ok": true}` (201) o `{"error": str}` (400) si el email ya existe. Setea la sesión.
  - `POST /login` — body `{"email": str, "password": str}` → `{"ok": true}` (200) o
    `{"error": "Usuario o contraseña incorrectos"}` (401). Setea la sesión.
  - `POST /logout` — limpia la sesión → `{"ok": true}`.
  - Helper `_sesion_activa(request: Request) -> bool` usado por Task 5.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_app_auth.py`:

```python
from fastapi.testclient import TestClient

import web.app as appmod
from web import auth


def _cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    return TestClient(appmod.app)


def test_registro_exitoso_crea_sesion(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    r = c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_registro_email_duplicado_devuelve_400(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    r = c.post("/registro", json={"nombre": "Otro", "email": "juan@x.com", "password": "otra"})
    assert r.status_code == 400
    assert "error" in r.json()


def test_login_correcto(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    r = c.post("/login", json={"email": "juan@x.com", "password": "clave123"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_login_incorrecto_devuelve_mensaje_generico(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    r = c.post("/login", json={"email": "nadie@x.com", "password": "loquesea"})
    assert r.status_code == 401
    assert r.json()["error"] == "Usuario o contraseña incorrectos"


def test_logout_limpia_sesion(tmp_path, monkeypatch):
    c = _cliente(tmp_path, monkeypatch)
    c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    r = c.post("/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `./.venv/bin/pytest tests/test_app_auth.py -v`
Expected: FAIL (404 en `/registro`, `/login`, `/logout` — rutas no existen todavía).

- [ ] **Step 3: Agregar `SESSION_SECRET` al ejemplo de entorno**

Agregar una línea a `web/.env.example`:

```
SESSION_SECRET=cambiame-por-una-clave-larga-y-aleatoria
```

- [ ] **Step 4: Implementar las rutas en `web/app.py`**

Modificar los imports (líneas 1-14) agregando `Request`, `JSONResponse`,
`SessionMiddleware` y `web.auth`:

```python
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from web import auth, buscador, leads
from web.chat import responder
from web.reglas import WHATSAPP
```

Después de `app = FastAPI()` (línea 32), agregar el middleware de sesión:

```python
app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SESSION_SECRET", "dev-secret-cambiar-en-produccion"),
)
```

Antes de la línea `app.mount("/", StaticFiles(...), name="static")` (la última línea del
archivo), agregar:

```python
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
```

- [ ] **Step 5: Correr el test para confirmar que pasa**

Run: `./.venv/bin/pytest tests/test_app_auth.py -v`
Expected: 5 PASSED.

- [ ] **Step 6: Correr toda la suite para confirmar que no rompió nada**

Run: `./.venv/bin/pytest -q`
Expected: todos los tests existentes siguen en PASSED.

- [ ] **Step 7: Commit**

```bash
git add web/app.py web/.env.example tests/test_app_auth.py
git commit -m "feat: rutas de registro, login y logout con sesion"
```

---

## Task 4: Mapeo de secciones del catálogo (`web/catalogo.py`)

**Files:**
- Create: `web/catalogo.py`
- Test: `tests/test_catalogo.py`

**Interfaces:**
- Consumes: lista de productos con forma `{"nombre": str, "categoria": str, ...}` (la
  misma forma que ya produce `web/productos.json`).
- Produces:
  - `SECCIONES = ["Celulares", "Accesorios Celulares", "Tablets", "Notebooks y Macbooks", "Gaming"]`
  - `secciones_catalogo(productos: list[dict]) -> dict[str, list[dict]]` — devuelve un
    dict con las 5 claves de `SECCIONES`, cada una con la lista de productos que le
    corresponden (nunca falta ninguna clave, aunque esté vacía).

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_catalogo.py`:

```python
from web.catalogo import SECCIONES, secciones_catalogo


def _prod(nombre, categoria):
    return {"nombre": nombre, "categoria": categoria}


def test_todas_las_secciones_estan_presentes_aunque_vacias():
    resultado = secciones_catalogo([])
    assert set(resultado.keys()) == set(SECCIONES)
    assert all(resultado[s] == [] for s in SECCIONES)


def test_categorias_conocidas_van_a_su_seccion():
    productos = [
        _prod("iPhone 15", "Apple - iPhone"),
        _prod("Galaxy A17", "Samsung"),
        _prod("MacBook Air M2", "Mac"),
        _prod("HP 15-EF0022", "Notebook"),
        _prod("iPad 9na", "Apple - iPad"),
        _prod("AirPods Pro", "Apple - AirPods"),
        _prod("Apple Watch SE", "Apple - Watch"),
    ]
    resultado = secciones_catalogo(productos)
    assert [p["nombre"] for p in resultado["Celulares"]] == ["iPhone 15", "Galaxy A17"]
    assert [p["nombre"] for p in resultado["Notebooks y Macbooks"]] == ["MacBook Air M2", "HP 15-EF0022"]
    assert [p["nombre"] for p in resultado["Tablets"]] == ["iPad 9na"]
    assert [p["nombre"] for p in resultado["Accesorios Celulares"]] == ["AirPods Pro", "Apple Watch SE"]


def test_otros_oppo_va_a_celulares():
    resultado = secciones_catalogo([_prod("Oppo Reno 14F DARK SIDE 5g 256/12gb", "Otros")])
    assert resultado["Celulares"][0]["nombre"].startswith("Oppo")


def test_otros_playstation_va_a_gaming():
    resultado = secciones_catalogo([_prod("PlayStation 5 Slim 825GB Digital", "Otros")])
    assert resultado["Gaming"][0]["nombre"] == "PlayStation 5 Slim 825GB Digital"


def test_otros_cargador_va_a_accesorios_por_defecto():
    resultado = secciones_catalogo([_prod("CARGADOR APPLE 35W CERTIFICADO USB C", "Otros")])
    assert resultado["Accesorios Celulares"][0]["nombre"] == "CARGADOR APPLE 35W CERTIFICADO USB C"


def test_otros_drone_va_a_accesorios_por_defecto():
    resultado = secciones_catalogo([_prod("Drone DJI Flip Plegable Ultraliviano 4K 48MP", "Otros")])
    assert resultado["Accesorios Celulares"][0]["nombre"].startswith("Drone")
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `./.venv/bin/pytest tests/test_catalogo.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.catalogo'`.

- [ ] **Step 3: Implementar `web/catalogo.py`**

```python
import re

SECCIONES = [
    "Celulares",
    "Accesorios Celulares",
    "Tablets",
    "Notebooks y Macbooks",
    "Gaming",
]

_CELULARES_CATEGORIAS = {
    "Apple - iPhone", "Apple - iPhone Usado", "Samsung", "Xiaomi", "Motorola", "Realme",
}
_NOTEBOOK_CATEGORIAS = {"Mac", "Notebook"}
_TABLET_CATEGORIAS = {"Apple - iPad"}
_ACCESORIO_CATEGORIAS = {"Apple - AirPods", "Apple - Watch"}

# Teléfonos de marcas que hoy caen en la categoría "Otros" del pipeline de precios.
_CELULAR_OTROS = re.compile(
    r"(?i)\boppo\b|\bnokia\b|\binfinix\b|\bhonor\b|\bitel\b|\bxiaomi\b|\bredmi\b|"
    r"\bpoco\b|\bsamsung\b|\bgalaxy\b|\bmotorola\b|\bmoto\b|\brealme\b|\bcelular\b|"
    r"\bhot\s*\d"
)

# Consolas y accesorios de gaming que también caen en "Otros".
_GAMING_OTROS = re.compile(
    r"(?i)playstation|\bps5\b|nintendo|\bswitch\b|\br36s\b|volante|logitech"
)


def _seccion_de(producto):
    categoria = producto.get("categoria", "")
    if categoria in _CELULARES_CATEGORIAS:
        return "Celulares"
    if categoria in _NOTEBOOK_CATEGORIAS:
        return "Notebooks y Macbooks"
    if categoria in _TABLET_CATEGORIAS:
        return "Tablets"
    if categoria in _ACCESORIO_CATEGORIAS:
        return "Accesorios Celulares"
    nombre = producto.get("nombre", "")
    if _CELULAR_OTROS.search(nombre):
        return "Celulares"
    if _GAMING_OTROS.search(nombre):
        return "Gaming"
    return "Accesorios Celulares"


def secciones_catalogo(productos):
    resultado = {seccion: [] for seccion in SECCIONES}
    for producto in productos:
        resultado[_seccion_de(producto)].append(producto)
    return resultado
```

- [ ] **Step 4: Correr el test para confirmar que pasa**

Run: `./.venv/bin/pytest tests/test_catalogo.py -v`
Expected: 6 PASSED.

- [ ] **Step 5: Commit**

```bash
git add web/catalogo.py tests/test_catalogo.py
git commit -m "feat: mapeo de productos a las 5 secciones del catalogo"
```

---

## Task 5: Rutas protegidas `/catalogo` y `/api/catalogo`

**Files:**
- Modify: `web/app.py`
- Test: `tests/test_app_catalogo.py`

**Interfaces:**
- Consumes: `_sesion_activa` (Task 3), `web.catalogo.secciones_catalogo` (Task 4),
  `_cargar_productos` (ya existe en `web/app.py`).
- Produces:
  - `GET /catalogo` — si no hay sesión activa, redirige (302) a `/login.html`; si hay
    sesión, devuelve el archivo `web/static/catalogo.html`.
  - `GET /api/catalogo` — sin sesión: `{"error": "No autenticado"}` (401). Con sesión y
    sin `productos.json`: `{"secciones": {}, "mensaje": "Estamos actualizando los precios"}`.
    Con sesión y productos: `{"secciones": {...5 claves...}}`.

- [ ] **Step 1: Escribir el test que falla**

Crear `tests/test_app_catalogo.py`:

```python
from fastapi.testclient import TestClient

import web.app as appmod
from web import auth


def _cliente_autenticado(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    c = TestClient(appmod.app)
    c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    return c


def test_api_catalogo_sin_sesion_devuelve_401(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    c = TestClient(appmod.app)
    r = c.get("/api/catalogo")
    assert r.status_code == 401


def test_pagina_catalogo_sin_sesion_redirige_a_login(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    c = TestClient(appmod.app, follow_redirects=False)
    r = c.get("/catalogo")
    assert r.status_code in (302, 307)
    assert "login" in r.headers["location"]


def test_api_catalogo_con_sesion_y_sin_productos(tmp_path, monkeypatch):
    c = _cliente_autenticado(tmp_path, monkeypatch)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [])
    r = c.get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["mensaje"] == "Estamos actualizando los precios"


def test_api_catalogo_con_sesion_y_productos(tmp_path, monkeypatch):
    c = _cliente_autenticado(tmp_path, monkeypatch)
    monkeypatch.setattr(
        appmod, "_cargar_productos",
        lambda: [{"nombre": "iPhone 15", "categoria": "Apple - iPhone"}],
    )
    r = c.get("/api/catalogo")
    assert r.status_code == 200
    secciones = r.json()["secciones"]
    assert secciones["Celulares"][0]["nombre"] == "iPhone 15"
    assert secciones["Gaming"] == []
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `./.venv/bin/pytest tests/test_app_catalogo.py -v`
Expected: FAIL (404 en `/catalogo` y `/api/catalogo`).

- [ ] **Step 3: Implementar las rutas**

Agregar el import de `catalogo` y `FileResponse`/`RedirectResponse` en `web/app.py`:

```python
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from web import auth, buscador, catalogo, leads
```

Agregar las rutas, justo antes de `app.mount("/", StaticFiles(...), name="static")`:

```python
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
```

- [ ] **Step 4: Correr el test para confirmar que pasa**

Run: `./.venv/bin/pytest tests/test_app_catalogo.py -v`
Expected: 4 PASSED.

- [ ] **Step 5: Correr toda la suite**

Run: `./.venv/bin/pytest -q`
Expected: todos PASSED.

- [ ] **Step 6: Commit**

```bash
git add web/app.py tests/test_app_catalogo.py
git commit -m "feat: rutas protegidas /catalogo y /api/catalogo"
```

---

## Task 6: Página de login/registro (frontend)

**Files:**
- Create: `web/static/login.html`
- Create: `web/static/login.css`
- Create: `web/static/login.js`

**Interfaces:**
- Consumes: `POST /login`, `POST /registro` (Task 3).
- Produces: página en `/login.html` que, tras un login/registro exitoso, redirige a
  `/catalogo`.

- [ ] **Step 1: Crear `web/static/login.html`**

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>THE TECH ROOM ARG — Ingresar</title>
  <link rel="stylesheet" href="login.css">
</head>
<body>
  <main class="tarjeta">
    <h1>THE TECH ROOM ARG</h1>
    <p class="subtitulo">Tu catálogo, a un clic.</p>

    <div class="tabs">
      <button type="button" class="tab activa" data-tab="login">Ingresar</button>
      <button type="button" class="tab" data-tab="registro">Crear cuenta</button>
    </div>

    <form id="form-login" class="form">
      <input type="email" id="login-email" placeholder="Email" autocomplete="email" required>
      <input type="password" id="login-password" placeholder="Contraseña" autocomplete="current-password" required>
      <button type="submit">Ingresar</button>
      <p class="error" id="login-error"></p>
    </form>

    <form id="form-registro" class="form oculto">
      <input type="text" id="registro-nombre" placeholder="Nombre" autocomplete="name" required>
      <input type="email" id="registro-email" placeholder="Email" autocomplete="email" required>
      <input type="password" id="registro-password" placeholder="Contraseña" autocomplete="new-password" required>
      <button type="submit">Crear cuenta</button>
      <p class="error" id="registro-error"></p>
    </form>
  </main>
  <script src="login.js"></script>
</body>
</html>
```

- [ ] **Step 2: Crear `web/static/login.css`**

```css
* { box-sizing: border-box; }
body {
  margin: 0; min-height: 100vh; display: flex; align-items: center; justify-content: center;
  font-family: system-ui, sans-serif; background: #0c0c0e; color: #eae6df;
}
.tarjeta {
  width: min(360px, 90vw); padding: 32px 28px; background: #16161a; border-radius: 16px;
  border: 1px solid #2a2a30; box-shadow: 0 20px 60px rgba(0, 0, 0, .5);
}
h1 { margin: 0 0 4px; font-size: 20px; letter-spacing: .04em; color: #d4af6a; }
.subtitulo { margin: 0 0 20px; font-size: 13px; color: #8a8a92; }
.tabs { display: flex; gap: 6px; margin-bottom: 18px; background: #0c0c0e; border-radius: 10px; padding: 4px; }
.tab {
  flex: 1; padding: 8px; border: none; border-radius: 8px; background: transparent;
  color: #8a8a92; font-size: 13px; cursor: pointer;
}
.tab.activa { background: #d4af6a; color: #0c0c0e; font-weight: 600; }
.form { display: flex; flex-direction: column; gap: 10px; }
.form.oculto { display: none; }
input {
  padding: 12px 14px; border-radius: 8px; border: 1px solid #2a2a30; background: #0c0c0e;
  color: #eae6df; font-size: 14px;
}
input:focus { outline: none; border-color: #d4af6a; }
button[type="submit"] {
  margin-top: 4px; padding: 12px; border: none; border-radius: 8px; background: #d4af6a;
  color: #0c0c0e; font-size: 14px; font-weight: 600; cursor: pointer;
}
.error { min-height: 16px; margin: 0; font-size: 12px; color: #e06666; }
```

- [ ] **Step 3: Crear `web/static/login.js`**

```javascript
const tabs = document.querySelectorAll(".tab");
const formLogin = document.getElementById("form-login");
const formRegistro = document.getElementById("form-registro");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("activa"));
    tab.classList.add("activa");
    const esLogin = tab.dataset.tab === "login";
    formLogin.classList.toggle("oculto", !esLogin);
    formRegistro.classList.toggle("oculto", esLogin);
  });
});

async function enviar(url, body, errorEl) {
  errorEl.textContent = "";
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const datos = await r.json();
  if (!r.ok) {
    errorEl.textContent = datos.error || "Ocurrió un error, probá de nuevo.";
    return;
  }
  window.location.href = "/catalogo";
}

formLogin.addEventListener("submit", (e) => {
  e.preventDefault();
  enviar(
    "/login",
    {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    },
    document.getElementById("login-error"),
  );
});

formRegistro.addEventListener("submit", (e) => {
  e.preventDefault();
  enviar(
    "/registro",
    {
      nombre: document.getElementById("registro-nombre").value,
      email: document.getElementById("registro-email").value,
      password: document.getElementById("registro-password").value,
    },
    document.getElementById("registro-error"),
  );
});
```

- [ ] **Step 4: Verificación manual**

Run: `./.venv/bin/uvicorn web.app:app --reload --port 8000`
Abrir `http://localhost:8000/login.html`, crear una cuenta nueva y confirmar que
redirige a `/catalogo`. Cerrar el navegador, volver a `/login.html` y entrar con las
mismas credenciales.
Expected: ambos flujos redirigen a `/catalogo`; un email duplicado en "Crear cuenta"
muestra el error debajo del formulario; una contraseña incorrecta en "Ingresar" muestra
"Usuario o contraseña incorrectos".

- [ ] **Step 5: Commit**

```bash
git add web/static/login.html web/static/login.css web/static/login.js
git commit -m "feat: pagina de login y registro con tema oscuro"
```

---

## Task 7: Página de catálogo con carrousel y 5 secciones (frontend)

**Files:**
- Create: `web/static/catalogo.html`
- Create: `web/static/catalogo.css`
- Create: `web/static/catalogo.js`

**Interfaces:**
- Consumes: `GET /api/catalogo` (Task 5), `web.catalogo.SECCIONES` (los 5 nombres de
  sección, ya fijados en Task 4: `Celulares`, `Accesorios Celulares`, `Tablets`,
  `Notebooks y Macbooks`, `Gaming`).
- Produces: página en `/catalogo` con carrousel de marcas arriba y las 5 secciones
  navegables por tabs debajo.

- [ ] **Step 1: Crear `web/static/catalogo.html`**

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>THE TECH ROOM ARG — Catálogo</title>
  <link rel="stylesheet" href="catalogo.css">
</head>
<body>
  <header>
    <h1>THE TECH ROOM ARG</h1>
    <button id="btn-logout" type="button">Salir</button>
  </header>

  <div class="carrousel-wrap">
    <div class="carrousel" id="carrousel"></div>
  </div>

  <nav class="tabs" id="tabs"></nav>
  <main id="secciones"></main>

  <script src="catalogo.js"></script>
</body>
</html>
```

- [ ] **Step 2: Crear `web/static/catalogo.css`**

```css
* { box-sizing: border-box; }
body {
  margin: 0; font-family: system-ui, sans-serif; background: #0c0c0e; color: #eae6df;
  min-height: 100vh;
}
header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; background: #16161a; border-bottom: 1px solid #2a2a30;
}
header h1 { margin: 0; font-size: 18px; letter-spacing: .04em; color: #d4af6a; }
#btn-logout {
  padding: 8px 14px; border: 1px solid #2a2a30; border-radius: 8px; background: transparent;
  color: #eae6df; cursor: pointer;
}

.carrousel-wrap { overflow: hidden; background: #16161a; border-bottom: 1px solid #2a2a30; }
.carrousel {
  display: flex; gap: 48px; white-space: nowrap; padding: 14px 0;
  animation: desplazar 25s linear infinite;
  width: max-content;
}
.carrousel span {
  font-size: 15px; letter-spacing: .12em; text-transform: uppercase; color: #8a8a92;
}
@keyframes desplazar {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

.tabs {
  display: flex; gap: 8px; padding: 16px 20px 0; flex-wrap: wrap;
}
.tabs button {
  padding: 10px 16px; border: 1px solid #2a2a30; border-radius: 999px; background: #16161a;
  color: #8a8a92; font-size: 13px; cursor: pointer;
}
.tabs button.activa { background: #d4af6a; color: #0c0c0e; border-color: #d4af6a; font-weight: 600; }

main { padding: 20px; }
.grilla { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.card {
  background: #16161a; border: 1px solid #2a2a30; border-radius: 12px; padding: 16px;
}
.card h3 { margin: 0 0 8px; font-size: 15px; color: #eae6df; }
.card .precios { font-size: 13px; color: #8a8a92; line-height: 1.6; }
.card .precios strong { color: #d4af6a; }
.mensaje-vacio { color: #8a8a92; padding: 40px; text-align: center; }
```

- [ ] **Step 3: Crear `web/static/catalogo.js`**

```javascript
const MARCAS = [
  "Apple", "Samsung", "Xiaomi", "Motorola", "Realme", "Oppo", "Honor",
  "Infinix", "Nokia", "PlayStation", "Nintendo", "JBL", "Logitech",
];

const SECCIONES = [
  "Celulares", "Accesorios Celulares", "Tablets", "Notebooks y Macbooks", "Gaming",
];

function pintarCarrousel() {
  const el = document.getElementById("carrousel");
  const marcas = [...MARCAS, ...MARCAS]; // duplicado para el loop visual
  el.innerHTML = marcas.map((m) => `<span>${m}</span>`).join("");
}

function pintarTabs(activa) {
  const el = document.getElementById("tabs");
  el.innerHTML = SECCIONES.map(
    (s) => `<button data-seccion="${s}" class="${s === activa ? "activa" : ""}">${s}</button>`
  ).join("");
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => pintarSeccion(btn.dataset.seccion));
  });
}

let SECCIONES_DATA = {};

function pintarSeccion(nombre) {
  pintarTabs(nombre);
  const el = document.getElementById("secciones");
  const productos = SECCIONES_DATA[nombre] || [];
  if (productos.length === 0) {
    el.innerHTML = `<p class="mensaje-vacio">Todavía no hay productos cargados en ${nombre}.</p>`;
    return;
  }
  el.innerHTML = `<div class="grilla">${productos.map(tarjetaProducto).join("")}</div>`;
}

function tarjetaProducto(p) {
  return `
    <div class="card">
      <h3>${p.nombre}</h3>
      <p class="precios">
        <strong>U$D ${p.usd ?? "-"}</strong><br>
        $ ${p.pesos ?? "-"} contado<br>
        $ ${p.transferencia ?? "-"} transferencia
      </p>
    </div>
  `;
}

async function cargarCatalogo() {
  const r = await fetch("/api/catalogo");
  if (r.status === 401) {
    window.location.href = "/login.html";
    return;
  }
  const datos = await r.json();
  SECCIONES_DATA = datos.secciones || {};
  if (datos.mensaje) {
    document.getElementById("secciones").innerHTML =
      `<p class="mensaje-vacio">${datos.mensaje}</p>`;
    pintarTabs(null);
    return;
  }
  pintarSeccion(SECCIONES[0]);
}

document.getElementById("btn-logout").addEventListener("click", async () => {
  await fetch("/logout", { method: "POST" });
  window.location.href = "/login.html";
});

pintarCarrousel();
cargarCatalogo();
```

- [ ] **Step 4: Verificación manual**

Con el servidor corriendo (`./.venv/bin/uvicorn web.app:app --reload --port 8000`) y ya
logueado desde la Task 6, ir a `http://localhost:8000/catalogo`.
Expected: el carrousel de marcas se desplaza solo en loop; las 5 tabs aparecen; al
hacer click en cada una se muestran los productos de `productos.json` que correspondan
(o el mensaje de sección vacía si no hay ninguno); "Salir" cierra la sesión y vuelve a
`/login.html`; entrar directo a `http://localhost:8000/catalogo` sin sesión iniciada
(en una ventana de incógnito) redirige a `/login.html`.

- [ ] **Step 5: Commit**

```bash
git add web/static/catalogo.html web/static/catalogo.css web/static/catalogo.js
git commit -m "feat: pagina de catalogo con carrousel de marcas y 5 secciones"
```

---

## Self-Review Notes

- **Cobertura de la spec:** login user/pass (Task 2-3, 6), registro (Task 2-3, 6), 5
  secciones desde `productos.json` (Task 4-5, 7), reglas de "Otros" (Task 4), rutas
  protegidas (Task 5), fallback sin productos (Task 5), carrousel de marcas en texto
  (Task 7), tema oscuro/chic (Task 6-7), tests de todo lo anterior (Task 2-5) — todo
  cubierto. Gmail y logos reales quedan explícitamente fuera de alcance (Global
  Constraints).
- **Consistencia de tipos:** `secciones_catalogo` devuelve siempre las 5 claves de
  `SECCIONES` (Task 4), y tanto `/api/catalogo` (Task 5) como `catalogo.js` (Task 7)
  asumen esa forma exacta — sin claves faltantes que rompan el frontend.
- **No placeholders:** cada paso tiene código completo, sin "TODO" ni "similar a la
  tarea anterior".
