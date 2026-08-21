# Cuentas de cliente unificadas + Supabase — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar los dos sistemas actuales de datos de cliente (leads en `clientes.json`/`.csv`, cuentas de mayorista en `usuarios.db`) por un solo registro de cliente por persona, persistido en Supabase (Postgres + Supabase Auth), sin duplicados y sin depender del filesystem efímero de Railway.

**Architecture:** FastAPI (`web/app.py`) sigue siendo el único backend. Un módulo nuevo `web/supabase_client.py` crea el cliente de Supabase a partir de variables de entorno; `web/cuentas.py` contiene toda la lógica de registro/login/deduplicación (recibe el cliente de Supabase como parámetro, para poder testear con un doble de prueba sin llamadas de red reales). La sesión sigue usando la misma cookie firmada de Starlette que ya existe, solo cambia qué guarda (`cliente_id` en vez de `usuario_email`).

**Tech Stack:** FastAPI, Starlette `SessionMiddleware`, `supabase-py` (cliente oficial), Postgres (Supabase), pytest + `TestClient`.

**Spec:** [docs/superpowers/specs/2026-08-20-cuentas-clientes-supabase-design.md](../specs/2026-08-20-cuentas-clientes-supabase-design.md)

## Global Constraints

- Nombre, apellido, celular y email son obligatorios para crear una cuenta (spec, "Alcance v1").
- `celular` y `email` son únicos a nivel de base de datos — el error de duplicado lo tira Postgres/Supabase Auth, nunca una revisión manual en Python.
- El login/registro se hace con Supabase Auth (no bcrypt casero) — deja la puerta abierta a login con Google después sin cambiar el modelo de datos.
- Los leads migrados sin cuenta ("invitados") se identifican por `auth_id IS NULL`; si alguien se registra con el mismo celular, ese registro invitado se completa (`UPDATE`) en vez de crear una fila nueva. Esta es la única excepción al "UNIQUE bloquea todo".
- Si falla el guardado del perfil en `clientes` después de crear el usuario en Supabase Auth, se hace rollback (`auth.admin.delete_user`) — nunca queda una cuenta de auth sin perfil.
- Nunca se hace `git push origin web-ttra` (deploy a prod) sin permiso explícito de Vladimir para ese cambio puntual — regla vigente de toda la sesión, aplica también a correr la migración de datos reales.
- `web/leads.py` y `web/auth.py` se eliminan al final (Task 9) una vez que todo lo que dependía de ellos fue migrado — no se dejan como código muerto.

---

### Task 1: Cliente de Supabase — configuración base

**Files:**
- Create: `web/supabase_client.py`
- Create: `supabase/schema.sql`
- Modify: `requirements.txt`
- Test: `tests/test_supabase_client.py`

**Interfaces:**
- Produces: `get_client() -> supabase.Client` — lee `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` del entorno; usado por todos los tasks siguientes como punto único de entrada a Supabase.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_supabase_client.py
import pytest

from web import supabase_client


def test_get_client_sin_variables_de_entorno_da_error_claro(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        supabase_client.get_client()


def test_get_client_con_variables_crea_cliente(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://ejemplo.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "clave-de-prueba")
    cliente = supabase_client.get_client()
    assert cliente is not None
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_supabase_client.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.supabase_client'`

- [ ] **Step 3: Agregar la dependencia**

Agregar `supabase` a `requirements.txt` (después de `email-validator`), luego instalar:

Run: `pip install supabase` (o `pip install -r requirements.txt` tras editar el archivo)

- [ ] **Step 4: Implementar `web/supabase_client.py`**

```python
import os

from supabase import Client, create_client


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL y SUPABASE_SERVICE_KEY tienen que estar configuradas "
            "(en .env local o como variables de entorno en Railway)"
        )
    return create_client(url, key)
```

- [ ] **Step 5: Correr el test y confirmar que pasa**

Run: `pytest tests/test_supabase_client.py -v`
Expected: PASS

- [ ] **Step 6: Escribir el esquema SQL de referencia**

```sql
-- supabase/schema.sql
-- Correr esto una sola vez en el SQL Editor del proyecto de Supabase.

create extension if not exists pgcrypto;

create table if not exists clientes (
  id uuid primary key default gen_random_uuid(),
  auth_id uuid unique references auth.users(id) on delete set null,
  nombre text not null,
  apellido text not null,
  celular text not null unique,
  email text not null unique,
  tipo_cliente text not null default 'minorista',
  creado_en timestamptz not null default now(),
  actualizado_en timestamptz not null default now()
);

create table if not exists pedidos (
  id uuid primary key default gen_random_uuid(),
  cliente_id uuid not null references clientes(id) on delete cascade,
  productos jsonb not null,
  origen text not null default 'whatsapp',
  fecha timestamptz not null default now()
);

-- El backend siempre accede con la service_role key (bypassa RLS). No hay
-- llamadas a Supabase desde el browser, así que dejamos RLS activado sin
-- policies: cualquier acceso con la clave anon/pública queda bloqueado.
alter table clientes enable row level security;
alter table pedidos enable row level security;
```

- [ ] **Step 7: Commit**

```bash
git add web/supabase_client.py supabase/schema.sql requirements.txt tests/test_supabase_client.py
git commit -m "feat: cliente de Supabase y esquema de clientes/pedidos"
```

---

### Task 2: `web/cuentas.py` — registro, login y deduplicación

**Files:**
- Create: `web/cuentas.py`
- Create: `tests/fakes_supabase.py`
- Test: `tests/test_cuentas.py`

**Interfaces:**
- Consumes: nada de tasks anteriores (recibe el cliente de Supabase como parámetro — no importa `web.supabase_client` directamente, así queda testeable con un doble).
- Produces:
  - `normalizar_celular(celular: str) -> str`
  - `registrar_cliente(client, nombre, apellido, celular, email, password) -> dict` con claves `id, auth_id, nombre, apellido, celular, email` — `id` es el uuid propio de la fila en `clientes` (el que van a usar los tasks siguientes para la sesión y para `pedidos.cliente_id`).
  - `login_cliente(client, email, password) -> dict | None` — mismas claves que arriba.
  - `CelularDuplicadoError`, `EmailDuplicadoError` (excepciones)

- [ ] **Step 1: Escribir el doble de prueba de Supabase**

```python
# tests/fakes_supabase.py
"""Doble de prueba mínimo del cliente de supabase-py: solo implementa lo que
usa web/cuentas.py (auth.sign_up, auth.sign_in_with_password,
auth.admin.delete_user, table().select/insert/update().eq().execute())."""
import uuid


class _FakeAuthUser:
    def __init__(self, id_, email):
        self.id = id_
        self.email = email


class _FakeAuthResponse:
    def __init__(self, user):
        self.user = user


class _FakeAdminAuth:
    def __init__(self, usuarios_por_email):
        self._usuarios_por_email = usuarios_por_email

    def delete_user(self, user_id):
        for email, user in list(self._usuarios_por_email.items()):
            if user.id == user_id:
                del self._usuarios_por_email[email]


class FakeAuth:
    def __init__(self):
        self._usuarios_por_email = {}
        self._passwords = {}
        self.admin = _FakeAdminAuth(self._usuarios_por_email)

    def sign_up(self, credenciales):
        email = credenciales["email"].strip().lower()
        if email in self._usuarios_por_email:
            raise Exception("User already registered")
        user = _FakeAuthUser(id_=str(uuid.uuid4()), email=email)
        self._usuarios_por_email[email] = user
        self._passwords[email] = credenciales["password"]
        return _FakeAuthResponse(user)

    def sign_in_with_password(self, credenciales):
        email = credenciales["email"].strip().lower()
        user = self._usuarios_por_email.get(email)
        if not user or self._passwords.get(email) != credenciales["password"]:
            raise Exception("Invalid login credentials")
        return _FakeAuthResponse(user)


class _FakeExecuteResult:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, tabla, operacion, payload=None):
        self._tabla = tabla
        self._operacion = operacion
        self._payload = payload
        self._filtros = []

    def eq(self, campo, valor):
        self._filtros.append((campo, valor))
        return self

    def _filtrar(self, filas):
        for campo, valor in self._filtros:
            filas = [f for f in filas if f.get(campo) == valor]
        return filas

    def execute(self):
        if self._operacion == "select":
            return _FakeExecuteResult(self._filtrar(list(self._tabla._filas)))
        if self._operacion == "insert":
            fila = dict(self._payload)
            self._tabla._filas.append(fila)
            return _FakeExecuteResult([fila])
        if self._operacion == "update":
            objetivo = self._filtrar(self._tabla._filas)
            for fila in objetivo:
                fila.update(self._payload)
            return _FakeExecuteResult(objetivo)
        raise ValueError(self._operacion)


class _FakeTable:
    def __init__(self):
        self._filas = []

    def select(self, *_args, **_kwargs):
        return _FakeQuery(self, "select")

    def insert(self, payload):
        return _FakeQuery(self, "insert", payload)

    def update(self, payload):
        return _FakeQuery(self, "update", payload)


class FakeSupabaseClient:
    def __init__(self):
        self.auth = FakeAuth()
        self._tablas = {}

    def table(self, nombre):
        return self._tablas.setdefault(nombre, _FakeTable())
```

- [ ] **Step 2: Escribir los tests que fallan**

```python
# tests/test_cuentas.py
import pytest

from tests.fakes_supabase import FakeSupabaseClient
from web import cuentas


def test_registrar_cliente_exitoso():
    client = FakeSupabaseClient()
    cliente = cuentas.registrar_cliente(
        client, "Ana", "Gómez", "351 123-4567", "ana@x.com", "clave1234"
    )
    assert cliente["nombre"] == "Ana"
    assert cliente["apellido"] == "Gómez"
    assert cliente["celular"] == "3511234567"  # normalizado, sin espacios ni guiones
    assert cliente["email"] == "ana@x.com"
    assert cliente["id"]  # uuid propio asignado


def test_registrar_cliente_celular_duplicado_de_cuenta_ya_activa():
    client = FakeSupabaseClient()
    cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    with pytest.raises(cuentas.CelularDuplicadoError):
        cuentas.registrar_cliente(client, "Otra", "Persona", "3511234567", "otra@x.com", "clave1234")


def test_registrar_cliente_email_duplicado():
    client = FakeSupabaseClient()
    cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    with pytest.raises(cuentas.EmailDuplicadoError):
        cuentas.registrar_cliente(client, "Otra", "Persona", "3519999999", "ana@x.com", "clave1234")


def test_registrar_cliente_vincula_lead_invitado_por_celular():
    client = FakeSupabaseClient()
    # Simula un lead migrado sin cuenta: auth_id ausente.
    client.table("clientes").insert({
        "id": "id-lead-1", "auth_id": None, "nombre": "Ana", "apellido": "",
        "celular": "3511234567", "email": "",
    }).execute()

    cliente = cuentas.registrar_cliente(
        client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234"
    )
    assert cliente["id"] == "id-lead-1"  # se completó la fila existente, no se creó otra
    filas = client.table("clientes").select("*").eq("celular", "3511234567").execute().data
    assert len(filas) == 1
    assert filas[0]["auth_id"] == cliente["auth_id"]
    assert filas[0]["apellido"] == "Gómez"


def test_registrar_cliente_hace_rollback_si_falla_el_perfil():
    client = FakeSupabaseClient()

    def _insert_que_falla(_payload):
        raise Exception("boom: fila inválida")

    client.table("clientes").insert = _insert_que_falla
    with pytest.raises(cuentas.CelularDuplicadoError):
        cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    # El usuario de auth no debe quedar húmedo tras el rollback.
    assert "ana@x.com" not in client.auth._usuarios_por_email


def test_login_cliente_correcto():
    client = FakeSupabaseClient()
    cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    cliente = cuentas.login_cliente(client, "ana@x.com", "clave1234")
    assert cliente is not None
    assert cliente["nombre"] == "Ana"


def test_login_cliente_password_incorrecta():
    client = FakeSupabaseClient()
    cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    assert cuentas.login_cliente(client, "ana@x.com", "otraclave") is None


def test_login_cliente_sin_cuenta():
    client = FakeSupabaseClient()
    assert cuentas.login_cliente(client, "nadie@x.com", "loquesea") is None
```

- [ ] **Step 3: Correr los tests y confirmar que fallan**

Run: `pytest tests/test_cuentas.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.cuentas'`

- [ ] **Step 4: Implementar `web/cuentas.py`**

```python
import re
import uuid


class CelularDuplicadoError(Exception):
    pass


class EmailDuplicadoError(Exception):
    pass


def normalizar_celular(celular):
    return re.sub(r"\D", "", celular or "")


def registrar_cliente(client, nombre, apellido, celular, email, password):
    nombre = nombre.strip()
    apellido = apellido.strip()
    celular_norm = normalizar_celular(celular)
    email = email.strip().lower()
    if not celular_norm:
        raise ValueError("El celular ingresado no es válido")

    existentes = client.table("clientes").select("*").eq("celular", celular_norm).execute().data
    if any(f.get("auth_id") for f in existentes):
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}")
    lead_invitado = next((f for f in existentes if not f.get("auth_id")), None)

    try:
        auth_resp = client.auth.sign_up({"email": email, "password": password})
    except Exception:
        raise EmailDuplicadoError(f"Ya existe una cuenta con el email {email}")
    auth_id = auth_resp.user.id

    datos = {"auth_id": auth_id, "nombre": nombre, "apellido": apellido, "email": email}
    try:
        if lead_invitado:
            propio_id = lead_invitado["id"]
            client.table("clientes").update(datos).eq("celular", celular_norm).execute()
        else:
            propio_id = str(uuid.uuid4())
            datos.update({"id": propio_id, "celular": celular_norm})
            client.table("clientes").insert(datos).execute()
    except Exception:
        client.auth.admin.delete_user(auth_id)
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}")

    return {"id": propio_id, "auth_id": auth_id, "nombre": nombre,
            "apellido": apellido, "celular": celular_norm, "email": email}


def login_cliente(client, email, password):
    email = (email or "").strip().lower()
    try:
        auth_resp = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return None
    auth_id = auth_resp.user.id
    filas = client.table("clientes").select("*").eq("auth_id", auth_id).execute().data
    if not filas:
        return None
    perfil = filas[0]
    return {"id": perfil["id"], "auth_id": auth_id, "nombre": perfil["nombre"],
            "apellido": perfil["apellido"], "celular": perfil["celular"], "email": email}
```

- [ ] **Step 5: Correr los tests y confirmar que pasan**

Run: `pytest tests/test_cuentas.py -v`
Expected: PASS (8 tests)

- [ ] **Step 6: Commit**

```bash
git add web/cuentas.py tests/fakes_supabase.py tests/test_cuentas.py
git commit -m "feat: registro, login y deduplicación de clientes contra Supabase"
```

---

### Task 3: Wiring de `/registro`, `/login`, `/logout` en `web/app.py`

**Files:**
- Modify: `web/app.py:254-311` (bloque de `RegistroIn`/`LoginIn`/`_sesion_activa`/`/registro`/`/login`/`/logout`)
- Test: `tests/test_app_auth.py` (reemplaza el archivo existente por completo)

**Interfaces:**
- Consumes: `cuentas.registrar_cliente`, `cuentas.login_cliente`, `cuentas.CelularDuplicadoError`, `cuentas.EmailDuplicadoError` (Task 2); `supabase_client.get_client` (Task 1).
- Produces: `_sesion_activa(request) -> bool` (ahora chequea `request.session["cliente_id"]`) — lo usan los Tasks 4 y 7.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# tests/test_app_auth.py (reemplaza el archivo completo)
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    return TestClient(appmod.app)


def test_registro_exitoso_crea_sesion(monkeypatch):
    c = _cliente(monkeypatch)
    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_registro_celular_duplicado_devuelve_400(monkeypatch):
    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/registro", json={
        "nombre": "Otro", "apellido": "Nombre", "celular": "3511234567",
        "email": "otro@x.com", "password": "clave1234",
    })
    assert r.status_code == 400
    assert "error" in r.json()


def test_login_correcto(monkeypatch):
    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/login", json={"email": "juan@x.com", "password": "clave1234"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_login_incorrecto_devuelve_mensaje_generico(monkeypatch):
    c = _cliente(monkeypatch)
    r = c.post("/login", json={"email": "nadie@x.com", "password": "loquesea"})
    assert r.status_code == 401
    assert r.json()["error"] == "Usuario o contraseña incorrectos"


def test_logout_limpia_sesion(monkeypatch):
    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert c.get("/api/catalogo").status_code == 200  # pública, no requiere sesión


def test_registro_con_supabase_caido_da_mensaje_claro(monkeypatch):
    def _client_roto():
        raise Exception("connection refused")

    monkeypatch.setattr(appmod, "get_client", _client_roto)
    c = TestClient(appmod.app)
    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    assert r.status_code == 503
    assert "error" in r.json()
```

- [ ] **Step 2: Correr los tests y confirmar que fallan**

Run: `pytest tests/test_app_auth.py -v`
Expected: FAIL — el registro actual no acepta `apellido`/`celular` (los rechaza `RegistroIn` con 422), y `web.app` no tiene atributo `get_client` para monkeypatchear.

- [ ] **Step 3: Reemplazar el bloque de auth en `web/app.py`**

Reemplazar la línea de import `from web import auth, buscador, catalogo, leads` (tope del
archivo) — `auth` deja de usarse en este task (se reemplaza por `cuentas`), `leads` se
mantiene porque `chat()` todavía lo usa hasta el Task 8:

```python
from web import buscador, catalogo, cuentas, leads
from web.supabase_client import get_client
```

Reemplazar el bloque completo `web/app.py:254-311` (de `class RegistroIn` a `def logout`) por:

```python
class RegistroIn(BaseModel):
    nombre: str
    apellido: str
    celular: str
    email: EmailStr
    password: str = Field(min_length=8)


class LoginIn(BaseModel):
    email: str
    password: str


def _sesion_activa(request: Request):
    return bool(request.session.get("cliente_id"))


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
    except Exception:
        logger.exception("No se pudo conectar a Supabase")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    try:
        cliente = cuentas.registrar_cliente(
            client, entrada.nombre, entrada.apellido, entrada.celular,
            entrada.email, entrada.password,
        )
    except (cuentas.CelularDuplicadoError, cuentas.EmailDuplicadoError, ValueError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    request.session["cliente_id"] = cliente["id"]
    request.session["cliente_nombre"] = cliente["nombre"]
    return {"ok": True}


@app.post("/login")
def login(entrada: LoginIn, request: Request):
    try:
        client = get_client()
    except Exception:
        logger.exception("No se pudo conectar a Supabase")
        return JSONResponse({"error": "No pudimos conectar, probá de nuevo en un momento"}, status_code=503)
    cliente = cuentas.login_cliente(client, entrada.email, entrada.password)
    if cliente is None:
        return JSONResponse({"error": "Usuario o contraseña incorrectos"}, status_code=401)
    request.session["cliente_id"] = cliente["id"]
    request.session["cliente_nombre"] = cliente["nombre"]
    return {"ok": True}


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}
```

(Los usos de `_sesion_activa` en `/catalogo` y donde corresponda quedan igual — la función sigue llamándose igual, solo cambió qué campo de sesión mira.)

- [ ] **Step 4: Correr los tests y confirmar que pasan**

Run: `pytest tests/test_app_auth.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add web/app.py tests/test_app_auth.py
git commit -m "feat: registro y login contra Supabase en vez de SQLite"
```

---

### Task 4: Landing gateada por sesión + formulario de registro completo

**Files:**
- Modify: `web/app.py` (agregar ruta `GET /`)
- Modify: `web/static/login.html:30-36` (formulario de registro)
- Modify: `web/static/login.js` (payload de registro + redirect)
- Modify: `web/static/index.html:13-24` (eliminar el gate)
- Modify: `web/static/landing.js:1-40` (eliminar la IIFE del gate)
- Test: `tests/test_app_landing.py` (nuevo)

**Interfaces:**
- Consumes: `_sesion_activa` (Task 3).

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_app_landing.py
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_landing_sin_sesion_muestra_login(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app)
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Ingresar" in r.text


def test_landing_con_sesion_muestra_index(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_app_landing.py -v`
Expected: FAIL — hoy `GET /` lo sirve el `StaticFiles` mount y siempre devuelve `index.html`, sesión o no.

- [ ] **Step 3: Agregar la ruta gateada**

Agregar en `web/app.py`, antes de la línea `app.mount("/", StaticFiles(...))` (al final del archivo):

```python
@app.get("/")
def pagina_inicio(request: Request):
    if not _sesion_activa(request):
        return FileResponse(str(BASE / "static" / "login.html"))
    return FileResponse(str(BASE / "static" / "index.html"))
```

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `pytest tests/test_app_landing.py -v`
Expected: PASS

- [ ] **Step 5: Completar el formulario de registro en `login.html`**

Reemplazar `web/static/login.html:30-36`:

```html
    <form id="form-registro" class="form oculto">
      <input type="text" id="registro-nombre" placeholder="Nombre" autocomplete="given-name" required>
      <input type="text" id="registro-apellido" placeholder="Apellido" autocomplete="family-name" required>
      <input type="tel" id="registro-celular" placeholder="Celular" autocomplete="tel" required>
      <input type="email" id="registro-email" placeholder="Email" autocomplete="email" required>
      <input type="password" id="registro-password" placeholder="Contraseña" autocomplete="new-password" required>
      <button type="submit">Crear cuenta</button>
      <p class="error" id="registro-error"></p>
    </form>
```

- [ ] **Step 6: Actualizar `login.js`**

En `web/static/login.js`, cambiar el redirect de `enviar()` de `/catalogo` a `/`, y el payload del registro para incluir `apellido` y `celular`:

```javascript
    window.location.href = "/";
```

```javascript
formRegistro.addEventListener("submit", (e) => {
  e.preventDefault();
  enviar(
    "/registro",
    {
      nombre: document.getElementById("registro-nombre").value,
      apellido: document.getElementById("registro-apellido").value,
      celular: document.getElementById("registro-celular").value,
      email: document.getElementById("registro-email").value,
      password: document.getElementById("registro-password").value,
    },
    document.getElementById("registro-error"),
  );
});
```

- [ ] **Step 7: Eliminar el gate de `index.html` y `landing.js`**

En `web/static/index.html`, borrar el bloque `web/static/index.html:13-24` (todo el `<div id="rc-gate">...</div>`).

En `web/static/landing.js`, borrar la IIFE completa `web/static/landing.js:1-40` (desde el comentario `// --- Gate inicial...` hasta el `})();` que la cierra).

- [ ] **Step 8: Verificación manual en local**

Levantar el server y confirmar visualmente con Playwright (siguiendo el patrón ya usado en esta sesión) que: sin cookie de sesión, `http://127.0.0.1:8000/` muestra el formulario de login/registro; tras registrarse, redirige a `/` y muestra la landing normal (Fallout/Classic) sin el gate viejo.

- [ ] **Step 9: Commit**

```bash
git add web/app.py web/static/login.html web/static/login.js web/static/index.html web/static/landing.js tests/test_app_landing.py
git commit -m "feat: landing gateada por login unificado, se elimina el gate liviano"
```

---

### Task 5: Historial de pedidos — `POST /api/pedidos`

**Files:**
- Create: `web/pedidos.py`
- Modify: `web/app.py` (nuevo endpoint)
- Modify: `web/static/landing.js:2690-2716` (`registrarPedidoEnClientes`)
- Test: `tests/test_pedidos.py`, `tests/test_app_pedidos.py`

**Interfaces:**
- Consumes: nada de tasks anteriores directamente en `web/pedidos.py` (recibe el cliente de Supabase igual que `cuentas.py`).
- Produces: `guardar_pedido(client, cliente_id, productos, origen="whatsapp") -> dict`

- [ ] **Step 1: Escribir el test que falla (módulo)**

```python
# tests/test_pedidos.py
from tests.fakes_supabase import FakeSupabaseClient
from web import pedidos


def test_guardar_pedido_inserta_asociado_al_cliente():
    client = FakeSupabaseClient()
    resultado = pedidos.guardar_pedido(client, "cliente-1", ["iPhone 13", "AirPods"])
    assert resultado["cliente_id"] == "cliente-1"
    assert resultado["productos"] == ["iPhone 13", "AirPods"]
    assert resultado["origen"] == "whatsapp"
    filas = client.table("pedidos").select("*").eq("cliente_id", "cliente-1").execute().data
    assert len(filas) == 1
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_pedidos.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.pedidos'`

- [ ] **Step 3: Implementar `web/pedidos.py`**

```python
import uuid
from datetime import datetime, timezone


def guardar_pedido(client, cliente_id, productos, origen="whatsapp"):
    fila = {
        "id": str(uuid.uuid4()),
        "cliente_id": cliente_id,
        "productos": productos,
        "origen": origen,
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    client.table("pedidos").insert(fila).execute()
    return fila
```

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `pytest tests/test_pedidos.py -v`
Expected: PASS

- [ ] **Step 5: Escribir el test del endpoint (que falla)**

```python
# tests/test_app_pedidos.py
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_pedido_sin_sesion_devuelve_401(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app)
    r = c.post("/api/pedidos", json={"productos": ["iPhone 13"]})
    assert r.status_code == 401


def test_pedido_con_sesion_se_guarda(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/api/pedidos", json={"productos": ["iPhone 13", "AirPods"]})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
```

- [ ] **Step 6: Correr el test y confirmar que falla**

Run: `pytest tests/test_app_pedidos.py -v`
Expected: FAIL — `404 Not Found` en `/api/pedidos`.

- [ ] **Step 7: Agregar el endpoint en `web/app.py`**

Agregar `pedidos` a la línea de import existente — queda
`from web import buscador, catalogo, cuentas, leads, pedidos` — y agregar el endpoint
(junto a los otros endpoints de `/api/*`):

```python
class PedidoIn(BaseModel):
    productos: list[str]


@app.post("/api/pedidos")
def api_pedidos(entrada: PedidoIn, request: Request):
    cliente_id = request.session.get("cliente_id")
    if not cliente_id:
        raise HTTPException(status_code=401, detail="Sesión requerida")
    pedidos.guardar_pedido(get_client(), cliente_id, entrada.productos)
    return {"ok": True}
```

- [ ] **Step 8: Correr el test y confirmar que pasa**

Run: `pytest tests/test_app_pedidos.py -v`
Expected: PASS

- [ ] **Step 9: Actualizar `landing.js`**

Reemplazar `registrarPedidoEnClientes` (`web/static/landing.js:2690-2706`) — ya no depende de `localStorage.ttra_cliente`, la sesión va por cookie:

```javascript
function registrarPedidoEnClientes(carrito) {
  const productos = [...new Set(carrito.map((it) =>
    it.color && it.color !== "Color único" ? `${it.nombre} (${it.color})` : it.nombre
  ))];
  fetch("/api/pedidos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ productos }),
  }).catch(() => {});
}
```

- [ ] **Step 10: Commit**

```bash
git add web/pedidos.py web/app.py web/static/landing.js tests/test_pedidos.py tests/test_app_pedidos.py
git commit -m "feat: historial de pedidos asociado a la cuenta del cliente"
```

---

### Task 6: Panel `/admin/clientes` sobre Supabase

**Files:**
- Modify: `web/app.py:194-251` (`admin_clientes`)
- Test: `tests/test_app_admin_clientes.py` (nuevo)

**Interfaces:**
- Consumes: `get_client` (Task 1); tabla `clientes` y `pedidos` (Task 1/5).

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_app_admin_clientes.py
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_logueado(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    c = TestClient(appmod.app)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    c.post("/api/pedidos", json={"productos": ["iPhone 13"]})
    c.post("/logout")
    c.post("/admin/clientes/login", json={"password": "clave-admin"})
    return c


def test_admin_clientes_lista_nombre_y_pedidos(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    r = c.get("/admin/clientes")
    assert r.status_code == 200
    assert "Juan" in r.text
    assert "iPhone 13" in r.text
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_app_admin_clientes.py -v`
Expected: FAIL — el panel sigue leyendo `leads.listar_clientes()` (vacío, porque ya no se escribe ahí).

- [ ] **Step 3: Reemplazar la lectura de datos en `admin_clientes`**

En `web/app.py`, reemplazar la línea `clientes = leads.listar_clientes()` (dentro de `admin_clientes`, `web/app.py:222`) por:

```python
    client = get_client()
    filas_clientes = client.table("clientes").select("*").execute().data
    filas_pedidos = client.table("pedidos").select("*").execute().data
    pedidos_por_cliente = {}
    for p in filas_pedidos:
        pedidos_por_cliente.setdefault(p["cliente_id"], []).extend(p.get("productos", []))
    clientes = [
        {
            "nombre": f"{c.get('nombre', '')} {c.get('apellido', '')}".strip(),
            "celular": c.get("celular", ""),
            "productos": pedidos_por_cliente.get(c.get("id"), []),
            "fecha": c.get("creado_en", ""),
        }
        for c in filas_clientes
    ]
    clientes.sort(key=lambda r: r.get("fecha", ""), reverse=True)
```

(El resto de la función — armado del HTML — queda igual, ya consume `clientes` con las mismas claves `nombre`/`celular`/`productos`/`fecha`.)

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `pytest tests/test_app_admin_clientes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/app.py tests/test_app_admin_clientes.py
git commit -m "feat: panel de clientes lee de Supabase en vez de clientes.json"
```

---

### Task 7: Script de migración de datos existentes

**Files:**
- Create: `scripts/migrar_a_supabase.py`
- Test: `tests/test_migrar_a_supabase.py`

**Interfaces:**
- Consumes: `cuentas.normalizar_celular` (Task 2); lee `usuarios.db` (formato de `web/auth.py`) y `clientes.json` (formato de `web/leads.py`) tal como existen hoy.
- Produces: `migrar(client, usuarios_db_path, clientes_json_path) -> dict` con conteos `{"mayoristas": int, "leads": int}`, para poder verificar en el test y al correrlo contra los datos reales.

- [ ] **Step 1: Escribir el test que falla**

```python
# tests/test_migrar_a_supabase.py
import json
import sqlite3

from tests.fakes_supabase import FakeSupabaseClient
from scripts.migrar_a_supabase import migrar


def _usuarios_db(tmp_path):
    db_path = tmp_path / "usuarios.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE usuarios (id INTEGER PRIMARY KEY, nombre TEXT, email TEXT UNIQUE, "
        "password_hash TEXT, creado TEXT)"
    )
    conn.execute(
        "INSERT INTO usuarios (nombre, email, password_hash, creado) VALUES (?, ?, ?, ?)",
        ("Mayorista Uno", "mayorista@x.com", "hash-no-migrable", "2026-01-01 10:00"),
    )
    conn.commit()
    conn.close()
    return db_path


def _clientes_json(tmp_path):
    json_path = tmp_path / "clientes.json"
    json_path.write_text(json.dumps({
        "s1": {"nombre": "Ana", "celular": "351 123-4567", "productos": ["iPhone 13"], "fecha": "2026-01-02 11:00"},
    }), encoding="utf-8")
    return json_path


def test_migrar_crea_mayoristas_invitados_y_leads(tmp_path):
    client = FakeSupabaseClient()
    db_path = _usuarios_db(tmp_path)
    json_path = _clientes_json(tmp_path)

    conteos = migrar(client, db_path, json_path)

    assert conteos == {"mayoristas": 1, "leads": 1}
    filas = client.table("clientes").select("*").execute().data
    assert len(filas) == 2
    mayorista = next(f for f in filas if f["email"] == "mayorista@x.com")
    assert mayorista["tipo_cliente"] == "mayorista"
    lead = next(f for f in filas if f["celular"] == "3511234567")
    assert lead["auth_id"] is None  # invitado: sin cuenta todavía
    assert lead["nombre"] == "Ana"


def test_migrar_no_duplica_si_se_corre_dos_veces(tmp_path):
    client = FakeSupabaseClient()
    db_path = _usuarios_db(tmp_path)
    json_path = _clientes_json(tmp_path)

    migrar(client, db_path, json_path)
    migrar(client, db_path, json_path)

    filas = client.table("clientes").select("*").execute().data
    celulares = [f["celular"] for f in filas if f.get("celular")]
    emails = [f["email"] for f in filas if f.get("email")]
    assert len(celulares) == len(set(celulares))
    assert len(emails) == len(set(emails))
```

- [ ] **Step 2: Correr el test y confirmar que falla**

Run: `pytest tests/test_migrar_a_supabase.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'scripts.migrar_a_supabase'`

- [ ] **Step 3: Implementar `scripts/migrar_a_supabase.py`**

```python
"""Migración única de usuarios.db (mayoristas) y clientes.json (leads) a
Supabase. Correr una sola vez, antes de deployar el nuevo flujo de auth:

    python -m scripts.migrar_a_supabase

Requiere SUPABASE_URL / SUPABASE_SERVICE_KEY en el entorno (ver web/supabase_client.py).
"""
import json
import sqlite3
import uuid
from pathlib import Path

from web.cuentas import normalizar_celular
from web.supabase_client import get_client

BASE = Path(__file__).parent.parent / "web"
USUARIOS_DB_PATH = BASE / "usuarios.db"
CLIENTES_JSON_PATH = BASE / "clientes.json"


def _email_existe(client, email):
    filas = client.table("clientes").select("*").eq("email", email).execute().data
    return bool(filas)


def _migrar_mayoristas(client, db_path):
    if not Path(db_path).exists():
        return 0
    conn = sqlite3.connect(str(db_path))
    filas = conn.execute("SELECT nombre, email, creado FROM usuarios").fetchall()
    conn.close()
    migrados = 0
    for nombre, email, creado in filas:
        email = email.strip().lower()
        if _email_existe(client, email):
            continue
        client.table("clientes").insert({
            "id": str(uuid.uuid4()),
            "auth_id": None,  # se linkea cuando el mayorista resetea password y entra por /registro o /login
            "nombre": nombre,
            "apellido": "",
            "celular": f"pendiente-{uuid.uuid4()}",  # placeholder: no había celular en usuarios.db
            "email": email,
            "tipo_cliente": "mayorista",
            "creado_en": creado,
        }).execute()
        migrados += 1
    return migrados


def _migrar_leads(client, json_path):
    if not Path(json_path).exists():
        return 0
    db = json.loads(Path(json_path).read_text(encoding="utf-8"))
    migrados = 0
    for reg in db.values():
        celular = normalizar_celular(reg.get("celular", ""))
        if not celular:
            continue
        existentes = client.table("clientes").select("*").eq("celular", celular).execute().data
        if existentes:
            continue
        client.table("clientes").insert({
            "id": str(uuid.uuid4()),
            "auth_id": None,
            "nombre": reg.get("nombre", ""),
            "apellido": "",
            "celular": celular,
            "email": f"pendiente-{uuid.uuid4()}@sin-email.local",  # placeholder: no había email en clientes.json
            "tipo_cliente": "minorista",
            "creado_en": reg.get("fecha", ""),
        }).execute()
        migrados += 1
    return migrados


def migrar(client, usuarios_db_path=USUARIOS_DB_PATH, clientes_json_path=CLIENTES_JSON_PATH):
    return {
        "mayoristas": _migrar_mayoristas(client, usuarios_db_path),
        "leads": _migrar_leads(client, clientes_json_path),
    }


if __name__ == "__main__":
    resultado = migrar(get_client())
    print(f"Migrados: {resultado['mayoristas']} mayoristas, {resultado['leads']} leads")
```

- [ ] **Step 4: Correr el test y confirmar que pasa**

Run: `pytest tests/test_migrar_a_supabase.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add scripts/migrar_a_supabase.py tests/test_migrar_a_supabase.py
git commit -m "feat: script de migración de usuarios.db y clientes.json a Supabase"
```

---

### Task 8: Eliminar el código viejo (`web/auth.py`, `web/leads.py`) y limpiar dependencias

**Files:**
- Delete: `web/auth.py`, `web/leads.py`, `tests/test_auth.py`, `tests/test_leads.py`
- Modify: `web/app.py` (quitar el import de `auth`/`leads`, quitar `ClienteIn`/`POST /api/registro-cliente`, quitar `leads.guardar_lead` de `chat()`)
- Modify: `web/chat.py` si referencia `leads` — revisar antes de tocar
- Modify: `requirements.txt` (quitar `passlib[bcrypt]` y `bcrypt<5.0` si nada más los usa)
- Test: correr la suite completa

**Interfaces:**
- No produce interfaces nuevas — es limpieza. El chequeo real es que la suite completa siga en verde sin las referencias eliminadas.

- [ ] **Step 1: Confirmar qué queda referenciando `auth`/`leads`**

Run: `grep -rn "from web import auth\|import auth\|web\.auth\|from web import leads\|import leads\|web\.leads" web/ tests/ --include=*.py`

Expected: solo apariciones en `web/app.py` (import + `/api/registro-cliente` + la llamada dentro de `chat()`) y en los tests que se van a borrar en este mismo task.

- [ ] **Step 2: Quitar el endpoint de leads y las llamadas a `leads.guardar_lead` en `web/app.py`**

- Borrar `leads` de la línea `from web import buscador, catalogo, cuentas, leads, pedidos` → queda `from web import buscador, catalogo, cuentas, pedidos`.
- Borrar la clase `ClienteIn` y el endpoint `POST /api/registro-cliente` (`web/app.py:127-141`).
- En `chat()` (`web/app.py:82-124`), borrar los dos bloques `try/except` que llaman a `leads.guardar_lead(...)` (uno en la rama `USAR_IA=False`, otro en la rama con IA) — el chat sigue funcionando igual, simplemente deja de escribir a `clientes.json`.

- [ ] **Step 3: Borrar los archivos viejos**

```bash
rm web/auth.py web/leads.py tests/test_auth.py tests/test_leads.py
```

- [ ] **Step 4: Limpiar `requirements.txt`**

Quitar las líneas `passlib[bcrypt]==1.7.4` y `bcrypt<5.0` (ya no queda ningún import de `passlib` ni `bcrypt` en el proyecto tras borrar `web/auth.py` — confirmarlo con `grep -rn "passlib\|bcrypt" web/ --include=*.py` antes de borrar la línea).

- [ ] **Step 5: Correr la suite completa**

Run: `pytest -v`
Expected: PASS en todo — sin errores de import ni de módulos faltantes.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "chore: elimina web/auth.py y web/leads.py, reemplazados por Supabase"
```

---

## Después de este plan (no forma parte de las tareas de arriba)

- Crear el proyecto en Supabase y correr `supabase/schema.sql` en su SQL Editor.
- Configurar `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` en `.env` local y en las variables de entorno de Railway.
- Correr `python -m scripts.migrar_a_supabase` **una sola vez**, contra los datos reales, antes de deployar — con confirmación explícita antes de tocar producción (regla vigente de la sesión).
- Enviar a cada mayorista migrado un mail de "restablecé tu contraseña" (flujo nativo de Supabase Auth) antes de anunciarles el nuevo login.
- Deploy a prod solo con permiso explícito, como siempre.
