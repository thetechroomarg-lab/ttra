# Campañas de Mailing de Novedades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatizar el armado semanal de un mail de novedades (productos nuevos + nota manual opcional) para toda la base de clientes, con el envío real siempre disparado a mano por Vladimir tras revisar un preview.

**Architecture:** Un módulo Python puro (`web/mailing/`) hace la detección de productos nuevos, la selección de destinatarios y el armado del HTML — todo testeable con pytest y sin tocar red. Dos scripts finos de skill (`armar_borrador.py`, `enviar_campania.py`) orquestan ese módulo contra Supabase/Resend, siguiendo el mismo patrón que `.claude/skills/pedido/scripts/cargar_pedido.py`. El disparo semanal vive fuera del repo, como una rutina cron de la skill `schedule` que corre `armar_borrador.py` y usa las herramientas Artifact + PushNotification del agente para mostrarle el preview a Vladimir — nunca envía sola. `web/app.py` gana un endpoint público `/mailing/baja/{cliente_id}` para las bajas.

**Tech Stack:** FastAPI (`web/app.py`), Supabase (postgres) vía `supabase-py`, Resend API vía `web/email_util.enviar_email`, pytest con `tests/fakes_supabase.py` como doble de Supabase, estado en archivos JSON planos (sin tabla nueva salvo una columna).

**Spec:** [docs/superpowers/specs/2026-09-19-campanias-mailing-novedades-design.md](../specs/2026-09-19-campanias-mailing-novedades-design.md)

## Global Constraints

- El envío real a toda la base NUNCA es automático: solo lo dispara `enviar_campania.py`, que solo se corre cuando Vladimir lo pide explícitamente después de ver el preview.
- Audiencia elegible: filas de `clientes` con `email` cargado y `no_mailing` distinto de `true`.
- La rutina semanal (skill `schedule`) solo corre el paso de armado de borrador — nunca `enviar_campania.py`.
- No hay ambiente de prueba separado para Supabase — los scripts escriben/leen directo en producción, igual que `.claude/skills/pedido/scripts/cargar_pedido.py`.
- Sin tabla nueva en Supabase salvo la columna `no_mailing` en `clientes`; el resto del estado (snapshot, nota, borrador, log) vive en archivos JSON en `web/mailing/data/` (gitignored, igual que `web/clientes.json`).
- Los campos de producto (`usd`, `pesos`, `transferencia`, `colores`) se toman tal cual están en `web/productos.json`, sin recalcular nada.
- Detección de "producto nuevo" es por coincidencia exacta de `nombre` contra el snapshot anterior — no existe un normalizador de nombres compartido en el proyecto, no inventar uno acá.

---

## Task 1: Schema — columna `no_mailing` en `clientes`

**Files:**
- Modify: `supabase/schema.sql:33` (justo después del bloque de `condiciones_mayorista_aceptadas_en`)
- Modify: `.gitignore`

**Interfaces:**
- Produces: columna `clientes.no_mailing boolean not null default false`.

Esta columna la necesita `web/mailing/destinatarios.py` (Task 4) para filtrar la audiencia. `tests/fakes_supabase.py` no lee `schema.sql`, así que ningún test de este repo la ejercita directamente — hay que correr este archivo a mano en el SQL Editor de Supabase antes de que `enviar_campania.py` corra contra producción (igual que ya se documenta para las columnas de `2026-08-20-cuentas-clientes-supabase.md:98`).

- [ ] **Step 1: Agregar la columna al schema**

En `supabase/schema.sql`, después de la línea 33 (`alter table clientes add column if not exists condiciones_mayorista_aceptadas_en timestamptz;`), agregar:

```sql
-- Un cliente que se dio de baja del mailing de novedades (link en el
-- footer del mail) queda excluido de la audiencia de próximas campañas.
alter table clientes add column if not exists no_mailing boolean not null default false;
```

- [ ] **Step 2: Ignorar el estado local de mailing en git**

En `.gitignore`, agregar una línea nueva después de `web/clientes.csv`:

```
web/mailing/data/
```

- [ ] **Step 3: Verificar**

Run: `grep -n "no_mailing" supabase/schema.sql && grep -n "web/mailing/data" .gitignore`
Expected: una línea con `alter table clientes ... no_mailing` y una línea `web/mailing/data/`.

- [ ] **Step 4: Commit**

```bash
git add supabase/schema.sql .gitignore
git commit -m "feat: columna no_mailing para bajas de la campaña de novedades"
```

---

## Task 2: `web/mailing/estado.py` — persistencia del snapshot, nota, borrador y log

**Files:**
- Create: `web/mailing/__init__.py`
- Create: `web/mailing/estado.py`
- Test: `tests/test_mailing_estado.py`

**Interfaces:**
- Produces: `leer_snapshot(data_dir) -> list|None`, `guardar_snapshot(data_dir, productos)`, `leer_nota_pendiente(data_dir) -> str|None`, `guardar_nota_pendiente(data_dir, texto)`, `limpiar_nota_pendiente(data_dir)`, `leer_borrador(data_dir) -> dict|None`, `guardar_borrador(data_dir, borrador)`, `marcar_borrador_usado(data_dir)`, `registrar_envio(data_dir, linea)`. Todas toman `data_dir: pathlib.Path` explícito (sin estado global) para que los tests usen `tmp_path`.

- [ ] **Step 1: Crear el paquete**

```bash
mkdir -p web/mailing
touch web/mailing/__init__.py
```

- [ ] **Step 2: Escribir el test que falla**

`tests/test_mailing_estado.py`:

```python
from web.mailing import estado


def test_snapshot_no_existe_devuelve_none(tmp_path):
    assert estado.leer_snapshot(tmp_path) is None


def test_guardar_y_leer_snapshot(tmp_path):
    productos = [{"nombre": "IPHONE 11 128GB"}]
    estado.guardar_snapshot(tmp_path, productos)
    assert estado.leer_snapshot(tmp_path) == productos


def test_nota_pendiente_ciclo_completo(tmp_path):
    assert estado.leer_nota_pendiente(tmp_path) is None

    estado.guardar_nota_pendiente(tmp_path, "20% off en fundas")
    assert estado.leer_nota_pendiente(tmp_path) == "20% off en fundas"

    estado.limpiar_nota_pendiente(tmp_path)
    assert estado.leer_nota_pendiente(tmp_path) is None


def test_borrador_ciclo_completo(tmp_path):
    assert estado.leer_borrador(tmp_path) is None

    estado.guardar_borrador(tmp_path, {"productos": [], "usado": False})
    assert estado.leer_borrador(tmp_path)["usado"] is False

    estado.marcar_borrador_usado(tmp_path)
    assert estado.leer_borrador(tmp_path)["usado"] is True


def test_registrar_envio_agrega_lineas(tmp_path):
    estado.registrar_envio(tmp_path, "linea 1")
    estado.registrar_envio(tmp_path, "linea 2")
    contenido = (tmp_path / "enviados.log").read_text(encoding="utf-8")
    assert contenido == "linea 1\nlinea 2\n"
```

- [ ] **Step 3: Correr los tests para verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_mailing_estado.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.mailing.estado'`

- [ ] **Step 4: Implementar**

`web/mailing/estado.py`:

```python
"""Persistencia en disco del estado de las campañas de mailing (snapshot del
catálogo, nota pendiente, borrador actual, log de envíos). Vive fuera de
Supabase: son archivos JSON simples, sin necesidad de una tabla nueva."""
import json
from datetime import datetime, timezone


def _leer(path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _escribir(path, datos):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def leer_snapshot(data_dir):
    return _leer(data_dir / "snapshot_catalogo.json")


def guardar_snapshot(data_dir, productos):
    _escribir(data_dir / "snapshot_catalogo.json", productos)


def leer_nota_pendiente(data_dir):
    datos = _leer(data_dir / "nota_pendiente.json")
    return (datos or {}).get("texto")


def guardar_nota_pendiente(data_dir, texto):
    _escribir(data_dir / "nota_pendiente.json", {
        "texto": texto,
        "creada_en": datetime.now(timezone.utc).isoformat(),
    })


def limpiar_nota_pendiente(data_dir):
    _escribir(data_dir / "nota_pendiente.json", {"texto": None, "creada_en": None})


def leer_borrador(data_dir):
    return _leer(data_dir / "borrador_actual.json")


def guardar_borrador(data_dir, borrador):
    _escribir(data_dir / "borrador_actual.json", borrador)


def marcar_borrador_usado(data_dir):
    borrador = leer_borrador(data_dir)
    if borrador is not None:
        borrador["usado"] = True
        guardar_borrador(data_dir, borrador)


def registrar_envio(data_dir, linea):
    path = data_dir / "enviados.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(linea.rstrip("\n") + "\n")
```

- [ ] **Step 5: Correr los tests para verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_mailing_estado.py -v`
Expected: PASS (5 tests)

- [ ] **Step 6: Commit**

```bash
git add web/mailing/__init__.py web/mailing/estado.py tests/test_mailing_estado.py
git commit -m "feat: persistencia de estado de campañas de mailing"
```

---

## Task 3: `web/mailing/catalogo_diff.py` — detección de productos nuevos

**Files:**
- Create: `web/mailing/catalogo_diff.py`
- Test: `tests/test_mailing_catalogo_diff.py`

**Interfaces:**
- Consumes: nada de tasks anteriores.
- Produces: `detectar_nuevos(productos_actuales: list[dict], snapshot_anterior: list[dict]) -> list[dict]`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_mailing_catalogo_diff.py`:

```python
from web.mailing import catalogo_diff


def test_detecta_producto_que_no_estaba_en_el_snapshot():
    actuales = [{"nombre": "A"}, {"nombre": "B"}]
    snapshot = [{"nombre": "A"}]

    nuevos = catalogo_diff.detectar_nuevos(actuales, snapshot)

    assert nuevos == [{"nombre": "B"}]


def test_no_detecta_nada_si_el_catalogo_no_cambio():
    actuales = [{"nombre": "A"}, {"nombre": "B"}]
    snapshot = [{"nombre": "A"}, {"nombre": "B"}]

    assert catalogo_diff.detectar_nuevos(actuales, snapshot) == []


def test_snapshot_vacio_todo_es_nuevo():
    actuales = [{"nombre": "A"}]

    assert catalogo_diff.detectar_nuevos(actuales, []) == [{"nombre": "A"}]
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_mailing_catalogo_diff.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.mailing.catalogo_diff'`

- [ ] **Step 3: Implementar**

`web/mailing/catalogo_diff.py`:

```python
"""Detecta productos nuevos comparando el catálogo actual contra el último
snapshot usado en una corrida anterior del cron de mailing."""


def detectar_nuevos(productos_actuales, snapshot_anterior):
    nombres_anteriores = {p.get("nombre") for p in snapshot_anterior}
    return [p for p in productos_actuales if p.get("nombre") not in nombres_anteriores]
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_mailing_catalogo_diff.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add web/mailing/catalogo_diff.py tests/test_mailing_catalogo_diff.py
git commit -m "feat: deteccion de productos nuevos para la campana de mailing"
```

---

## Task 4: `web/mailing/destinatarios.py` — selección de destinatarios elegibles

**Files:**
- Create: `web/mailing/destinatarios.py`
- Test: `tests/test_mailing_destinatarios.py`

**Interfaces:**
- Consumes: cliente de Supabase (`client.table("clientes").select("*").execute().data`), columna `no_mailing` de Task 1.
- Produces: `clientes_elegibles(client) -> list[{"id": str, "email": str}]`.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_mailing_destinatarios.py`:

```python
from tests.fakes_supabase import FakeSupabaseClient
from web.mailing import destinatarios


def test_incluye_clientes_con_email_y_sin_baja():
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({"id": "1", "email": "a@x.com"}).execute()
    fake.table("clientes").insert({"id": "2", "email": "b@x.com", "no_mailing": False}).execute()

    elegibles = destinatarios.clientes_elegibles(fake)

    assert {e["id"] for e in elegibles} == {"1", "2"}


def test_excluye_dados_de_baja_y_sin_email():
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({"id": "1", "email": "a@x.com", "no_mailing": True}).execute()
    fake.table("clientes").insert({"id": "2", "email": None}).execute()
    fake.table("clientes").insert({"id": "3", "email": "c@x.com"}).execute()

    elegibles = destinatarios.clientes_elegibles(fake)

    assert [e["id"] for e in elegibles] == ["3"]
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_mailing_destinatarios.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.mailing.destinatarios'`

- [ ] **Step 3: Implementar**

`web/mailing/destinatarios.py`:

```python
"""Selección de clientes elegibles para recibir una campaña de mailing de
novedades (tienen email y no se dieron de baja)."""


def clientes_elegibles(client):
    filas = client.table("clientes").select("*").execute().data
    return [
        {"id": fila["id"], "email": fila["email"]}
        for fila in filas
        if fila.get("email") and not fila.get("no_mailing")
    ]
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_mailing_destinatarios.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add web/mailing/destinatarios.py tests/test_mailing_destinatarios.py
git commit -m "feat: seleccion de destinatarios elegibles para mailing"
```

---

## Task 5: `web/mailing/template.py` — armado del HTML del mail

**Files:**
- Create: `web/mailing/template.py`
- Test: `tests/test_mailing_template.py`

**Interfaces:**
- Consumes: `web.slugs.url_producto(nombre, base)` (ya existe en `web/slugs.py:14`).
- Produces: `armar_html(productos_nuevos: list[dict], nota: str|None = None, cliente_id: str|None = None, base_url: str = BASE_URL) -> str`.

Estilo: terminal oscuro consistente con `web/static/theme.css` (fondo `#030a03`, panel `#0b1f0b`, verde `#33ff66`, verde brillante `#7bffa0`, verde tenue `#1f8c3f`, fuente `'Share Tech Mono', 'Courier New', monospace`), con estilos inline para máxima compatibilidad en clientes de mail.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_mailing_template.py`:

```python
from web.mailing import template


def _producto(nombre="IPHONE 11 128GB", usd=425, colores=None):
    return {
        "nombre": nombre, "usd": usd, "pesos": 667250, "transferencia": 687887,
        "colores": colores or ["Black"],
    }


def test_incluye_nombre_precio_y_link_del_producto():
    html = template.armar_html([_producto()], nota=None, cliente_id=None)

    assert "IPHONE 11 128GB" in html
    assert "U$D 425" in html
    assert "/p/iphone-11-128gb" in html


def test_incluye_nota_cuando_se_pasa():
    html = template.armar_html([_producto()], nota="20% off en fundas", cliente_id=None)

    assert "20% off en fundas" in html


def test_no_incluye_banner_de_nota_si_no_hay_nota():
    html = template.armar_html([_producto()], nota=None, cliente_id=None)

    assert "20% off" not in html


def test_link_de_baja_usa_el_cliente_id():
    html = template.armar_html([_producto()], nota=None, cliente_id="cliente-123")

    assert "/mailing/baja/cliente-123" in html


def test_sin_cliente_id_el_link_de_baja_es_un_placeholder():
    html = template.armar_html([_producto()], nota=None, cliente_id=None)

    assert 'href="#"' in html
```

- [ ] **Step 2: Correr los tests para verificar que fallan**

Run: `.venv/bin/python -m pytest tests/test_mailing_template.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'web.mailing.template'`

- [ ] **Step 3: Implementar**

`web/mailing/template.py`:

```python
"""Arma el HTML del mail semanal de novedades, con estilo terminal oscuro
consistente con la web (ver web/static/theme.css). Usa estilos inline para
degradar razonablemente en clientes de mail que ignoran CSS embebido."""
import html

from web.slugs import url_producto

BASE_URL = "https://thetechroomarg.com"

_BG = "#030a03"
_PANEL = "#0b1f0b"
_VERDE = "#33ff66"
_VERDE_BRILLANTE = "#7bffa0"
_VERDE_TENUE = "#1f8c3f"
_FUENTE = "'Share Tech Mono', 'Courier New', monospace"


def _tarjeta_producto(producto, base_url):
    nombre = html.escape(producto.get("nombre", ""))
    colores = producto.get("colores") or []
    colores_html = (
        f"<p style='margin:4px 0 0; font-size:13px; color:{_VERDE_TENUE};'>"
        f"{html.escape(', '.join(colores))}</p>"
        if colores else ""
    )
    link = url_producto(producto.get("nombre", ""), base=base_url)
    return f"""
<td style="padding:12px; vertical-align:top; width:50%;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:{_PANEL}; border:1px solid {_VERDE_TENUE}; border-radius:6px;">
    <tr><td style="padding:16px;">
      <p style="margin:0; font-family:{_FUENTE}; font-size:15px; font-weight:bold; color:{_VERDE_BRILLANTE};">{nombre}</p>
      {colores_html}
      <p style="margin:10px 0 0; font-family:{_FUENTE}; font-size:14px; color:{_VERDE};">U$D {producto.get("usd")}</p>
      <p style="margin:2px 0 0; font-family:{_FUENTE}; font-size:12px; color:{_VERDE_TENUE};">$ {producto.get("pesos")} contado &middot; $ {producto.get("transferencia")} transferencia</p>
      <a href="{link}" style="display:inline-block; margin-top:12px; padding:8px 14px; background:{_VERDE}; color:{_BG}; text-decoration:none; font-family:{_FUENTE}; font-weight:bold; font-size:13px; border-radius:4px;">Ver producto</a>
    </td></tr>
  </table>
</td>"""


def armar_html(productos_nuevos, nota=None, cliente_id=None, base_url=BASE_URL):
    baja_url = f"{base_url}/mailing/baja/{cliente_id}" if cliente_id else "#"

    banner_nota = ""
    if nota:
        banner_nota = f"""
<tr><td style="padding:0 20px 20px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background:{_VERDE_TENUE}; border-radius:6px;">
    <tr><td style="padding:16px; font-family:{_FUENTE}; font-size:14px; color:{_BG}; font-weight:bold;">
      {html.escape(nota)}
    </td></tr>
  </table>
</td></tr>"""

    filas_productos = ""
    for i in range(0, len(productos_nuevos), 2):
        par = productos_nuevos[i:i + 2]
        celdas = "".join(_tarjeta_producto(p, base_url) for p in par)
        if len(par) == 1:
            celdas += "<td style='width:50%;'></td>"
        filas_productos += f"<tr>{celdas}</tr>"

    return f"""<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0; padding:0; background:{_BG};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{_BG};">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px; background:{_BG};">
<tr><td style="padding:0 20px 20px; text-align:center;">
  <p style="margin:0; font-family:'Archivo Black', sans-serif; font-size:20px; color:{_VERDE_BRILLANTE}; letter-spacing:1px;">THE TECH ROOM ARG</p>
  <p style="margin:4px 0 0; font-family:{_FUENTE}; font-size:12px; color:{_VERDE_TENUE};">Novedades de la semana</p>
</td></tr>
{banner_nota}
<tr><td style="padding:0 12px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">{filas_productos}</table>
</td></tr>
<tr><td style="padding:24px 20px 8px; text-align:center;">
  <p style="margin:0; font-family:{_FUENTE}; font-size:11px; color:{_VERDE_TENUE};">
    <a href="{baja_url}" style="color:{_VERDE_TENUE};">No quiero recibir más novedades por mail</a>
  </p>
</td></tr>
</table>
</td></tr>
</table>
</body>
</html>"""
```

- [ ] **Step 4: Correr los tests para verificar que pasan**

Run: `.venv/bin/python -m pytest tests/test_mailing_template.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add web/mailing/template.py tests/test_mailing_template.py
git commit -m "feat: template HTML del mail de novedades"
```

---

## Task 6: Endpoint público `/mailing/baja/{cliente_id}`

**Files:**
- Modify: `web/app.py` (agregar la ruta justo después de `pagina_producto_publico`, antes de `@app.get("/api/recomendados")`, alrededor de la línea 4258)
- Test: `tests/test_app_mailing_baja.py`

**Interfaces:**
- Consumes: `_PRODUCTO_PUBLICO_ESTILO` (ya definido en `web/app.py:4205`), `WHATSAPP` (ya importado en `web/app.py:36`), `get_client()` (`web/app.py`).
- Produces: `GET /mailing/baja/{cliente_id}` — 404 si el cliente no existe, 200 y marca `no_mailing=True` si existe.

- [ ] **Step 1: Escribir el test que falla**

`tests/test_app_mailing_baja.py`:

```python
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_baja_marca_no_mailing_en_true(monkeypatch):
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({"id": "cliente-1", "email": "a@x.com", "no_mailing": False}).execute()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    cliente = TestClient(appmod.app, base_url="https://testserver")

    respuesta = cliente.get("/mailing/baja/cliente-1")

    assert respuesta.status_code == 200
    fila = fake.table("clientes").select("*").eq("id", "cliente-1").execute().data[0]
    assert fila["no_mailing"] is True


def test_baja_con_cliente_inexistente_devuelve_404(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    cliente = TestClient(appmod.app, base_url="https://testserver")

    respuesta = cliente.get("/mailing/baja/no-existe")

    assert respuesta.status_code == 404
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `.venv/bin/python -m pytest tests/test_app_mailing_baja.py -v`
Expected: FAIL con 404 en el primer test (la ruta no existe todavía, FastAPI devuelve 404 para cualquier ruta no registrada — para distinguirlo del 404 "a propósito" del segundo test, confirmar que el primer test también falla en el assert de `no_mailing`)

- [ ] **Step 3: Implementar**

En `web/app.py`, agregar inmediatamente después del cierre de `pagina_producto_publico` (antes de `@app.get("/api/recomendados")`):

```python
@app.get("/mailing/baja/{cliente_id}", response_class=HTMLResponse)
def mailing_baja(cliente_id: str):
    client = get_client()
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        return HTMLResponse(
            f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
            f"<title>No encontramos esa cuenta</title>{_PRODUCTO_PUBLICO_ESTILO}</head>"
            f"<body><div class='tarjeta'><h1>No encontramos esa cuenta</h1>"
            f"<p class='colores'>El link puede estar vencido. Escribime por WhatsApp si seguís recibiendo mails.</p>"
            f"<a class='btn-wa' href='{WHATSAPP}'>Escribir por WhatsApp</a></div></body></html>",
            status_code=404,
        )
    client.table("clientes").update({"no_mailing": True}).eq("id", cliente_id).execute()
    return HTMLResponse(
        f"<!doctype html><html lang='es'><head><meta charset='utf-8'>"
        f"<title>Listo — The Tech Room Arg</title>{_PRODUCTO_PUBLICO_ESTILO}</head>"
        f"<body><div class='tarjeta'><h1>Listo</h1>"
        f"<p class='colores'>No vas a recibir más mails de novedades. Si te arrepentís, escribime por WhatsApp.</p>"
        f"<a class='btn-wa' href='{WHATSAPP}'>Escribir por WhatsApp</a></div></body></html>"
    )
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `.venv/bin/python -m pytest tests/test_app_mailing_baja.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add web/app.py tests/test_app_mailing_baja.py
git commit -m "feat: endpoint publico de baja de mailing de novedades"
```

---

## Task 7: Script `armar_borrador.py` (paso del cron)

**Files:**
- Create: `.claude/skills/mailing/scripts/armar_borrador.py`

**Interfaces:**
- Consumes: `web.mailing.catalogo_diff.detectar_nuevos`, `web.mailing.destinatarios.clientes_elegibles`, `web.mailing.estado.*`, `web.mailing.template.armar_html`, `web.supabase_client.get_client`.
- Produces: `web/mailing/data/borrador_actual.json` con `html_preview` (para que el agente lo publique como Artifact); imprime `PRIMERA_CORRIDA`, `SIN_NOVEDADES` o `BORRADOR_LISTO` según el caso.

Es un script de orquestación (como `cargar_pedido.py`), no tiene test de pytest — su lógica de negocio ya está testeada en `web/mailing/*`. Se verifica corriéndolo a mano (Step 2).

- [ ] **Step 1: Escribir el script**

`.claude/skills/mailing/scripts/armar_borrador.py`:

```python
#!/usr/bin/env python3
"""Arma el borrador semanal de la campaña de mailing de novedades: detecta
productos nuevos del catálogo, suma la nota pendiente (si hay), arma el HTML
y lo deja guardado para que el agente lo publique como Artifact.

Uso:
    ./.venv/bin/python .claude/skills/mailing/scripts/armar_borrador.py

No envía nada — solo arma el borrador. El envío real lo dispara
enviar_campania.py, siempre a mano (ver .claude/skills/mailing/SKILL.md).
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

from web.mailing import catalogo_diff, destinatarios, estado, template
from web.supabase_client import get_client

DATA_DIR = PROJECT_DIR / "web" / "mailing" / "data"


def main():
    productos_actuales = json.loads(
        (PROJECT_DIR / "web" / "productos.json").read_text(encoding="utf-8")
    )

    snapshot_anterior = estado.leer_snapshot(DATA_DIR)
    if snapshot_anterior is None:
        estado.guardar_snapshot(DATA_DIR, productos_actuales)
        print("PRIMERA_CORRIDA: snapshot inicializado, no hay borrador para armar todavía.")
        return

    nuevos = catalogo_diff.detectar_nuevos(productos_actuales, snapshot_anterior)
    nota = estado.leer_nota_pendiente(DATA_DIR)

    # Se actualiza en cada corrida, se arme borrador o no, para que la
    # próxima comparación sea siempre contra el catálogo más reciente.
    estado.guardar_snapshot(DATA_DIR, productos_actuales)

    if not nuevos and not nota:
        print("SIN_NOVEDADES: no hay productos nuevos ni nota pendiente, no se arma borrador.")
        return

    client = get_client()
    elegibles = destinatarios.clientes_elegibles(client)
    html = template.armar_html(nuevos, nota)

    borrador = {
        "productos": nuevos,
        "nota": nota,
        "html_preview": html,
        "destinatarios": len(elegibles),
        "armado_en": datetime.now(timezone.utc).isoformat(),
        "usado": False,
    }
    estado.guardar_borrador(DATA_DIR, borrador)
    estado.limpiar_nota_pendiente(DATA_DIR)

    print("BORRADOR_LISTO")
    print("productos_nuevos:", len(nuevos))
    for producto in nuevos:
        print("  -", producto["nombre"])
    print("incluye_nota:", bool(nota))
    print("destinatarios:", len(elegibles))
    print("archivo:", DATA_DIR / "borrador_actual.json")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificar a mano**

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/armar_borrador.py
```

Expected (primera corrida en la máquina, sin snapshot previo): `PRIMERA_CORRIDA: snapshot inicializado, no hay borrador para armar todavía.`

Correrlo una segunda vez sin tocar `productos.json` ni dejar nota:
Expected: `SIN_NOVEDADES: no hay productos nuevos ni nota pendiente, no se arma borrador.`

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/mailing/scripts/armar_borrador.py
git commit -m "feat: script de armado de borrador de campana de mailing"
```

---

## Task 8: Script `nota.py`

**Files:**
- Create: `.claude/skills/mailing/scripts/nota.py`

**Interfaces:**
- Consumes: `web.mailing.estado.leer_nota_pendiente`, `web.mailing.estado.guardar_nota_pendiente`.

- [ ] **Step 1: Escribir el script**

`.claude/skills/mailing/scripts/nota.py`:

```python
#!/usr/bin/env python3
"""Deja una nota/promo pendiente para que la incluya el próximo borrador
semanal de la campaña de mailing de novedades.

Uso:
    ./.venv/bin/python .claude/skills/mailing/scripts/nota.py "texto de la nota"
"""
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from web.mailing import estado

DATA_DIR = PROJECT_DIR / "web" / "mailing" / "data"


def main():
    if len(sys.argv) != 2:
        print("ERROR: pasá la nota como único argumento (entre comillas).", file=sys.stderr)
        sys.exit(1)
    texto = sys.argv[1].strip()
    if not texto:
        print("ERROR: la nota no puede estar vacía.", file=sys.stderr)
        sys.exit(1)

    anterior = estado.leer_nota_pendiente(DATA_DIR)
    if anterior:
        print(f"AVISO: pisaste una nota pendiente que no se había usado: {anterior!r}")

    estado.guardar_nota_pendiente(DATA_DIR, texto)
    print("OK: nota guardada para el próximo borrador.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificar a mano**

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/nota.py "Nota de prueba"
./.venv/bin/python .claude/skills/mailing/scripts/nota.py "Otra nota"
```

Expected: la primera corrida imprime `OK: nota guardada...`; la segunda imprime primero `AVISO: pisaste una nota pendiente que no se había usado: 'Nota de prueba'` y después `OK: nota guardada...`.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/mailing/scripts/nota.py
git commit -m "feat: script para dejar nota pendiente de campana de mailing"
```

---

## Task 9: Script `enviar_campania.py`

**Files:**
- Create: `.claude/skills/mailing/scripts/enviar_campania.py`

**Interfaces:**
- Consumes: `web.mailing.destinatarios.clientes_elegibles`, `web.mailing.estado.leer_borrador`, `web.mailing.estado.marcar_borrador_usado`, `web.mailing.estado.registrar_envio`, `web.mailing.template.armar_html`, `web.email_util.enviar_email`, `web.email_util.EnvioEmailError`, `web.supabase_client.get_client`.

- [ ] **Step 1: Escribir el script**

`.claude/skills/mailing/scripts/enviar_campania.py`:

```python
#!/usr/bin/env python3
"""Envía la campaña de mailing de novedades ya aprobada por Vladimir a todos
los clientes elegibles. NUNCA se corre automáticamente — solo cuando
Vladimir confirmó el borrador que armó armar_borrador.py.

Uso:
    ./.venv/bin/python .claude/skills/mailing/scripts/enviar_campania.py
"""
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv
load_dotenv(PROJECT_DIR / "web" / ".env")

from web.mailing import destinatarios, estado, template
from web.email_util import EnvioEmailError, enviar_email
from web.supabase_client import get_client

DATA_DIR = PROJECT_DIR / "web" / "mailing" / "data"
ASUNTO = "Novedades de la semana en The Tech Room Arg"


def main():
    borrador = estado.leer_borrador(DATA_DIR)
    if borrador is None:
        print("ERROR: no hay ningún borrador armado. Corré armar_borrador.py primero.", file=sys.stderr)
        sys.exit(1)
    if borrador.get("usado"):
        print("ERROR: el último borrador ya fue enviado. Esperá al próximo borrador semanal.", file=sys.stderr)
        sys.exit(1)

    client = get_client()
    elegibles = destinatarios.clientes_elegibles(client)
    productos = borrador["productos"]
    nota = borrador.get("nota")

    ok, fallidos = 0, 0
    for cliente in elegibles:
        html = template.armar_html(productos, nota, cliente_id=cliente["id"])
        try:
            enviar_email(cliente["email"], ASUNTO, html)
            ok += 1
        except EnvioEmailError as e:
            fallidos += 1
            print(f"FALLÓ envío a {cliente['email']}: {e}", file=sys.stderr)
        time.sleep(0.4)

    estado.marcar_borrador_usado(DATA_DIR)
    estado.registrar_envio(
        DATA_DIR,
        f"{datetime.now(timezone.utc).isoformat()} | productos={len(productos)} | ok={ok} | fallidos={fallidos}",
    )

    print(f"ENVIADA: {ok}/{ok + fallidos} destinatarios, {fallidos} fallidos.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verificar a mano (contra la base real — revisar bien antes de correr)**

No correr en esta etapa sin un borrador real armado por Task 7 y revisado por Vladimir. Verificación mínima de que el script no rompe con "sin borrador":

```bash
cd "/Users/toraba/TTRA Project"
rm -f web/mailing/data/borrador_actual.json
./.venv/bin/python .claude/skills/mailing/scripts/enviar_campania.py
```

Expected: `ERROR: no hay ningún borrador armado. Corré armar_borrador.py primero.` con exit code 1.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/mailing/scripts/enviar_campania.py
git commit -m "feat: script de envio de campana de mailing aprobada"
```

---

## Task 10: `SKILL.md` de `/mailing`

**Files:**
- Create: `.claude/skills/mailing/SKILL.md`

**Interfaces:**
- Consumes: los tres scripts de Tasks 7-9, las herramientas Artifact y PushNotification del agente.

- [ ] **Step 1: Escribir el SKILL.md**

`.claude/skills/mailing/SKILL.md`:

```markdown
---
name: mailing
description: Arma y envía la campaña semanal de mailing de novedades a los clientes de The Tech Room Arg — detecta productos nuevos del catálogo, suma una nota/promo manual opcional, y solo envía cuando Vladimir lo confirma explícitamente. Usar cuando Vladimir dice "dejá esta nota para la próxima campaña", "mandá la campaña de novedades", o cuando corre la rutina semanal programada.
---

# Campaña de mailing de novedades

Escribe DIRECTO en la base de producción (Supabase) al enviar — no hay
ambiente de prueba separado (ver `web/supabase_client.py`).

## Dejar una nota/promo para la próxima campaña

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/nota.py "Todo el stock de iPhone 13 con $30 de descuento esta semana"
```

Reemplaza cualquier nota pendiente sin usar (el script avisa si pisa una).

## Rutina semanal (automática, vía skill `schedule`)

Cada lunes 9:00 AM (hora Argentina) corré:

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/armar_borrador.py
```

El script:
- Compara `web/productos.json` contra el último snapshot y detecta productos nuevos.
- Lee la nota pendiente (si hay) y la consume — queda limpia después de esta corrida, se haya aprobado el borrador o no.
- Si no hay productos nuevos ni nota, imprime `SIN_NOVEDADES` — no hace falta seguir, no le muestres nada a Vladimir esta semana.
- Si imprime `PRIMERA_CORRIDA`, tampoco hay nada para mostrar (recién se inicializó el snapshot).
- Si arma un borrador, imprime `BORRADOR_LISTO` seguido de un resumen (cantidad de productos, si incluye nota, cantidad de destinatarios), y guarda el HTML completo en `web/mailing/data/borrador_actual.json` (campo `html_preview`).

Si imprimió `BORRADOR_LISTO`:

1. Leé `web/mailing/data/borrador_actual.json`, tomá el campo `html_preview`.
2. Escribilo a un archivo `.html` y publicalo con tu herramienta Artifact (favicon 📧, título "Campaña de novedades").
3. Mandale una notificación push a Vladimir con la herramienta PushNotification: cantidad de productos nuevos, si incluye nota, cantidad de destinatarios, y que revise el link del artifact.
4. No envíes nada vos solo — el envío real requiere que Vladimir lo pida explícitamente después de revisar el artifact.

## Enviar la campaña aprobada

Cuando Vladimir confirma (dice "dale, mandala" o similar) después de haber visto el artifact:

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/enviar_campania.py
```

- Envía el HTML del borrador (personalizado por cliente solo en el link de baja) a todos los clientes con email y sin `no_mailing=true`.
- Si falla un envío individual, sigue con el resto — al final reporta `ENVIADA: X/Y destinatarios, Z fallidos`.
- Marca el borrador como usado — no se puede reenviar el mismo borrador dos veces, hace falta uno nuevo de la próxima corrida semanal.

Contale a Vladimir el resultado final en el chat.

## Gotchas

- El envío real (`enviar_campania.py`) NUNCA se corre automáticamente ni sin que Vladimir lo haya pedido explícitamente para ese borrador puntual.
- Si `armar_borrador.py` imprime `SIN_NOVEDADES` o `PRIMERA_CORRIDA`, no generes notificación ni artifact esa semana.
- La columna `clientes.no_mailing` tiene que existir en Supabase antes de correr cualquiera de estos scripts contra producción (`supabase/schema.sql`, corrida a mano en el SQL Editor).
```

- [ ] **Step 2: Verificar**

Run: `cat .claude/skills/mailing/SKILL.md | head -5`
Expected: el frontmatter con `name: mailing` y la `description`.

- [ ] **Step 3: Commit**

```bash
git add .claude/skills/mailing/SKILL.md
git commit -m "docs: skill /mailing para campanas de novedades"
```

---

## Task 11: Correr el schema en Supabase y configurar la rutina semanal (pasos manuales, fuera del repo)

No hay código para este task — son dos acciones de configuración que hace la persona que despliega, después de que todo lo anterior esté commiteado.

- [ ] **Step 1: Aplicar el schema en Supabase**

Abrir el SQL Editor del proyecto de Supabase en producción y correr el contenido agregado en Task 1 (`alter table clientes add column if not exists no_mailing boolean not null default false;`). Confirmar con:

```sql
select column_name from information_schema.columns where table_name = 'clientes' and column_name = 'no_mailing';
```

Expected: una fila.

- [ ] **Step 2: Correr `armar_borrador.py` una vez a mano para inicializar el snapshot en el servidor**

Si el servidor de producción no comparte disco con la máquina donde se corrió Task 7 (Railway sí lo pierde en cada deploy — el `web/mailing/data/` no es persistente entre deploys salvo que se monte un volumen), correr manualmente una vez después del primer deploy:

```bash
./.venv/bin/python .claude/skills/mailing/scripts/armar_borrador.py
```

Expected: `PRIMERA_CORRIDA: snapshot inicializado, no hay borrador para armar todavía.` — es esperable y correcto la primera vez en cada entorno nuevo.

- [ ] **Step 3: Configurar la rutina cron semanal con la skill `schedule`**

Usar la skill `schedule` para crear una rutina nueva:
- Cron: `0 9 * * 1` (lunes 9:00 AM, hora Argentina — ajustar el timezone según lo que pida la skill `schedule`).
- Prompt de la rutina: `Corré .venv/bin/python .claude/skills/mailing/scripts/armar_borrador.py en "/Users/toraba/TTRA Project" y seguí las instrucciones de .claude/skills/mailing/SKILL.md para publicar el Artifact y notificar a Vladimir si armó un borrador.`

- [ ] **Step 4: Probar el flujo completo una vez con datos reales antes de dejar la rutina sola**

Agregar (o esperar) un producto nuevo real en `productos.json`, correr `armar_borrador.py` a mano, revisar el artifact, y correr `enviar_campania.py` una vez confirmado a mano por Vladimir — antes de confiar en que la rutina semanal lo haga sin supervisión directa las primeras veces.
