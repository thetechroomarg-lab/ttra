# Recibo Manual desde Nota y Papelera de Borrados — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the cadete emit a standalone receipt from a nota (independent of any `pedidos` row), and turn the current permanent delete of pedidos/tareas into a 48h-recoverable soft-delete with a "Borrados" screen for admin and cadete.

**Architecture:** Two additive features on top of the existing FastAPI monolith (`web/app.py`), no new services. (1) Soft-delete: `pedidos` and `tareas_entrega` gain `borrado_en`/`borrado_por` columns; every existing "active" read gets a `not borrado_en` filter; delete becomes an `UPDATE`; a new `/admin/papelera` (admin) and `/admin/cadete/papelera` (cadete) pair of endpoints list what's soft-deleted in the last 48h (purging anything older on each read) and a restore endpoint clears the two columns. (2) Recibo manual: a new `recibos_manuales` table + `web/recibos_manuales.py` module hold a standalone item list (name/price typed by the cadete, matched against the real catalog for price precarga) that reuses the existing `recibos.pdf_recibo()`/`html_recibo()` PDF/email machinery by building a "pedido-like" dict in memory — no `pedidos` row is created or touched.

**Tech Stack:** FastAPI + Pydantic, Supabase (postgres) via `supabase-py`, vanilla JS (no bundler — inline `<script>`/`<style>` in `web/app.py` f-strings), pytest with `tests/fakes_supabase.py` as the DB fake, Playwright for manual UI verification (no JS unit test runner in this repo).

**Spec:** [docs/superpowers/specs/2026-09-19-recibo-manual-y-papelera-design.md](../specs/2026-09-19-recibo-manual-y-papelera-design.md)

## Global Constraints

- Cadete identity is a single fixed slug: `CADETE_SLUG = "alejo"` (`web/app.py:76`). There is no per-cadete-user table — "who deleted it" is always either `"Vlad"` (admin session) or `CADETE_SLUG` (cadete session).
- The cadete can only ever see/operate on pedidos/tareas where `asignado_a == CADETE_SLUG` (existing rule, `_puede_operar_entrega`, `web/app.py:420-423`) — the papelera and recibo-manual features must not weaken this.
- No background jobs/cron exist in this project. The 48h purge is lazy: it happens inside the papelera GET endpoints, never on a schedule.
- Every soft-deleted row must still pass through the *same* validation the live table enforces today (e.g. `recibo_id` uniqueness) — soft-delete only adds two nullable columns, it changes no other constraint.
- Frontend has no build step and no JS test runner — all new UI is inline HTML/CSS/JS inside `web/app.py` f-strings, following the exact patterns already in the file (see Task 6 and Task 9 for the concrete conventions to copy).
- Money is always USD (`usd` field in `web/productos.json`, `usd_unitario`/`usd_subtotal`/`total_usd` in receipts) — never introduce a pesos field into the manual-receipt flow.

---

## Task 1: Schema — soft-delete columns and `recibos_manuales` table

**Files:**
- Modify: `supabase/schema.sql`

**Interfaces:**
- Produces: columns `pedidos.borrado_en`, `pedidos.borrado_por`, `tareas_entrega.borrado_en`, `tareas_entrega.borrado_por`; table `recibos_manuales` with columns `id, tarea_id, nombre_cliente, email_cliente, items, total_usd, fotos_series, recibo_id, creado_por, creado_en, enviado_en`.

This is a pure SQL migration file. `tests/fakes_supabase.py` is an in-memory fake that does **not** read this file, so no pytest exercises it directly — verification is a manual read-back (Step 2 below). The columns must exist in the real Supabase database before Task 2 is deployed; that's a manual `psql`/Supabase SQL editor step outside this repo, tracked separately — this task only updates the schema file that documents/drives it.

- [ ] **Step 1: Add the columns and the new table**

Append at the end of the `pedidos` block (right after `web/app.py`-adjacent line `supabase/schema.sql:100`, i.e. after the existing `lat`/`lng` columns and before the `pedidos_recibo_id_unico` index):

```sql
-- Borrado temporal (papelera): una fila con borrado_en no nulo queda oculta
-- de todas las listas activas pero sigue existiendo 48hs por si hay que
-- restaurarla. Se purga (delete real) al superar ese plazo, de forma
-- perezosa, la próxima vez que alguien abre la papelera.
alter table pedidos add column if not exists borrado_en timestamptz;
alter table pedidos add column if not exists borrado_por text;
```

Append at the end of the `tareas_entrega` block (after the existing `observaciones_cadete` column, `supabase/schema.sql:128`):

```sql
alter table tareas_entrega add column if not exists borrado_en timestamptz;
alter table tareas_entrega add column if not exists borrado_por text;
```

Add a new table after the `tareas_entrega` block:

```sql
-- Recibos generados a mano desde una nota del cadete, sin depender de que
-- exista un pedido en la base (ver panel "Recibo" en /admin/cadete). Los
-- items son una instantánea: nombre + precio USD tal cual los cargó el
-- cadete, no una referencia viva al catálogo.
create table if not exists recibos_manuales (
  id uuid primary key default gen_random_uuid(),
  tarea_id uuid references tareas_entrega(id) on delete set null,
  nombre_cliente text not null,
  email_cliente text not null,
  items jsonb not null,
  total_usd numeric not null,
  fotos_series jsonb not null default '[]'::jsonb,
  recibo_id text unique,
  creado_por text not null,
  creado_en timestamptz not null default now(),
  enviado_en timestamptz
);
create index if not exists recibos_manuales_tarea_idx on recibos_manuales (tarea_id);
alter table recibos_manuales enable row level security;
```

- [ ] **Step 2: Verify the file parses as valid SQL structure (manual read-back, no DB needed)**

Run: `grep -n "borrado_en\|borrado_por\|recibos_manuales" supabase/schema.sql`
Expected: 7 matches — 2 in `pedidos`, 2 in `tareas_entrega`, and 3+ inside the new `recibos_manuales` block (table name appears in `create table`, the index, and the RLS line).

- [ ] **Step 3: Commit**

```bash
git add supabase/schema.sql
git commit -m "feat: columnas de borrado temporal y tabla de recibos manuales"
```

---

## Task 2: Soft-delete for `pedidos`

**Files:**
- Modify: `web/pedidos.py:195-199` (`eliminar_pedido`)
- Modify: `web/app.py` (helpers, `DELETE /admin/pedidos/{pedido_id}`, and every existing "active pedidos" read)
- Test: `tests/test_pedidos.py` (pure `pedidos.py` functions)
- Test: `tests/test_app_pedidos.py` (HTTP-level: delete no longer removes the row, active listings hide it)

**Interfaces:**
- Produces: `pedidos.eliminar_pedido(client, pedido_id, borrado_por)` (now soft-deletes; same name, new required 3rd arg), `pedidos.restaurar_pedido(client, pedido_id)` (new), `web.app._activo(fila) -> bool` (new module-level helper), `web.app._quien_opera(request) -> str | None` (new module-level helper).
- Consumes: nothing from other tasks.

- [ ] **Step 1: Write the failing test for the pure `pedidos.py` functions**

Add to `tests/test_pedidos.py` (check the existing file's imports first — it already imports `web.pedidos as pedidos` and `FakeSupabaseClient`; match that pattern):

```python
def test_eliminar_pedido_marca_borrado_en_vez_de_borrar():
    fake = FakeSupabaseClient()
    fake.table("pedidos").insert({
        "id": "p1", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
    }).execute()

    pedidos.eliminar_pedido(fake, "p1", "Vlad")

    filas = fake.table("pedidos").select("*").eq("id", "p1").execute().data
    assert len(filas) == 1
    assert filas[0]["borrado_por"] == "Vlad"
    assert filas[0]["borrado_en"] is not None


def test_restaurar_pedido_limpia_borrado():
    fake = FakeSupabaseClient()
    fake.table("pedidos").insert({
        "id": "p1", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "borrado_en": "2026-09-19T10:00:00+00:00", "borrado_por": "Vlad",
    }).execute()

    pedidos.restaurar_pedido(fake, "p1")

    fila = fake.table("pedidos").select("*").eq("id", "p1").execute().data[0]
    assert fila["borrado_en"] is None
    assert fila["borrado_por"] is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_pedidos.py -k "borrado" -v`
Expected: FAIL — `restaurar_pedido` doesn't exist, and `eliminar_pedido` still takes 2 args and does a hard delete (so the first assertion `len(filas) == 1` fails too).

- [ ] **Step 3: Implement in `web/pedidos.py`**

Replace lines 195-199:

```python
def eliminar_pedido(client, pedido_id, borrado_por):
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise ValueError("Pedido no encontrado")
    client.table("pedidos").update({
        "borrado_en": datetime.now(timezone.utc).isoformat(),
        "borrado_por": borrado_por,
    }).eq("id", pedido_id).execute()


def restaurar_pedido(client, pedido_id):
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas:
        raise ValueError("Pedido no encontrado")
    client.table("pedidos").update({"borrado_en": None, "borrado_por": None}).eq("id", pedido_id).execute()
```

Check the top of `web/pedidos.py` for an existing `from datetime import datetime, timezone` (or similar) import — add it if missing.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_pedidos.py -k "borrado" -v`
Expected: PASS

- [ ] **Step 5: Add the `_activo`/`_quien_opera` helpers in `web/app.py`**

Insert right after `_puede_operar_entrega` (`web/app.py:423`):

```python
def _activo(fila):
    return not fila.get("borrado_en")


def _quien_opera(request: Request):
    if _clientes_admin_activo(request):
        return "Vlad"
    if _cadete_activo(request):
        return CADETE_SLUG
    return None
```

- [ ] **Step 6: Wire the DELETE endpoint and every "not found" check for pedidos to respect soft-delete**

Modify `web/app.py:3932-3941` (`DELETE /admin/pedidos/{pedido_id}`):

```python
@app.delete("/admin/pedidos/{pedido_id}")
def admin_pedido_eliminar(pedido_id: str, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    filas = client.table("pedidos").select("*").eq("id", pedido_id).execute().data
    if not filas or not _activo(filas[0]):
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    pedidos.eliminar_pedido(client, pedido_id, _quien_opera(request))
    return {"ok": True}
```

Then, in `web/app.py`, change the `if not filas:` guard to `if not filas or not _activo(filas[0]):` at each of these single-row lookups (same file, each already reads `client.table("pedidos").select("*").eq("id", pedido_id).execute().data` right before the check — locate by the surrounding route decorator, since exact line numbers may have shifted after Step 5's insertion):
- `admin_pedido_enviar_recibo` (`POST /admin/pedidos/{pedido_id}/recibo`, originally `web/app.py:832-834`)
- `admin_pedido_pdf_recibo` (`GET /admin/pedidos/{pedido_id}/recibo.pdf`, originally `web/app.py:902-904`)
- `admin_pedido_editar_fecha` (`PUT /admin/pedidos/{pedido_id}/fecha-entrega`, originally `web/app.py:3921-3923`)
- `admin_pedido_agregar_direccion` (`PUT /admin/pedidos/{pedido_id}/direccion`, originally `web/app.py:3952-3954`)
- `admin_pedido_derivar` (`PUT /admin/pedidos/{pedido_id}/derivar`, originally `web/app.py:3966-3968`)

For each, the change is mechanical: `if not filas:` → `if not filas or not _activo(filas[0]):`.

Finally, filter the "list all active pedidos" reads so a soft-deleted pedido stops appearing anywhere except the papelera:
- `web/app.py:1593` (admin "Pedidos y recibos" panel): `pedidos = [] if mostrar_clientes else client.table("pedidos").select("*").execute().data` → append `pedidos = [p for p in pedidos if _activo(p)]` on the next line.
- `web/app.py:2656` (cadete panel): `pedidos = client.table("pedidos").select("*").eq("asignado_a", CADETE_SLUG).execute().data` → append `pedidos = [p for p in pedidos if _activo(p)]` on the next line.
- `web/app.py:2999` (cliente historial in admin): `filas_pedidos = client.table("pedidos").select("*").eq("cliente_id", cliente_id).execute().data` → append `filas_pedidos = [p for p in filas_pedidos if _activo(p)]` on the next line.
- `web/app.py:3984` (`admin_reordenar_entregas`, inside the list comprehension): change the comprehension's condition from `if pedido.get("fecha_entrega") == fecha_hoy and not pedido.get("recibo_enviado_en")` to `if _activo(pedido) and pedido.get("fecha_entrega") == fecha_hoy and not pedido.get("recibo_enviado_en")`.

- [ ] **Step 7: Write the failing HTTP-level test**

Add to `tests/test_app_pedidos.py` (match its existing login/monkeypatch pattern — check the top of the file for how it logs in as admin):

```python
def test_eliminar_pedido_es_recuperable_y_desaparece_de_listas(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})
    fake.table("clientes").insert({"id": "c1", "nombre": "Ana", "apellido": "Lopez"}).execute()
    fake.table("pedidos").insert({
        "id": "p1", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
    }).execute()

    respuesta = cliente.delete("/admin/pedidos/p1")
    assert respuesta.status_code == 200

    fila = fake.table("pedidos").select("*").eq("id", "p1").execute().data[0]
    assert fila["borrado_en"] is not None
    assert fila["borrado_por"] == "Vlad"

    respuesta_doble_borrado = cliente.delete("/admin/pedidos/p1")
    assert respuesta_doble_borrado.status_code == 404
```

- [ ] **Step 8: Run to verify it fails, then implement (already done in Steps 5-6), then verify it passes**

Run: `.venv/bin/python -m pytest tests/test_app_pedidos.py -k "recuperable" -v`
Expected: PASS (implementation already in place from Steps 5-6 — this step is confirming the wiring, not writing new production code)

- [ ] **Step 9: Run the full existing pedidos test suite to catch regressions**

Run: `.venv/bin/python -m pytest tests/test_pedidos.py tests/test_app_pedidos.py tests/test_app_admin_clientes.py tests/test_app_admin_cadete.py -v`
Expected: all PASS — pay special attention to any existing test that asserted a hard delete (`fake.table("pedidos").select(...).execute().data == []` after a `DELETE` call) and fix its assertion to match the new soft-delete behavior if one exists.

- [ ] **Step 10: Commit**

```bash
git add web/pedidos.py web/app.py tests/test_pedidos.py tests/test_app_pedidos.py
git commit -m "feat: borrado de pedidos pasa a ser recuperable (papelera)"
```

---

## Task 3: Soft-delete for `tareas_entrega`

**Files:**
- Modify: `web/app.py` (`DELETE /admin/tareas-entrega/{tarea_id}` and every existing "active tareas" read)
- Test: `tests/test_app_admin_tareas.py`

**Interfaces:**
- Consumes: `_activo(fila)`, `_quien_opera(request)` from Task 2.
- Produces: nothing new consumed by later tasks beyond the same soft-delete convention.

There's no `web/tareas.py` module — all tareas_entrega logic is inline in `web/app.py` (confirmed: no such file exists). Soft-delete goes directly in the route handler, matching that existing convention.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_app_admin_tareas.py` (it already has a helper for admin login — reuse it; check the file's existing tests for the exact login call):

```python
def test_eliminar_tarea_es_recuperable(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-20", "titulo": "Llamar a Ana", "orden": 1,
    }).execute()

    respuesta = cliente.delete("/admin/tareas-entrega/t1")
    assert respuesta.status_code == 200

    fila = fake.table("tareas_entrega").select("*").eq("id", "t1").execute().data[0]
    assert fila["borrado_en"] is not None
    assert fila["borrado_por"] == "Vlad"

    respuesta_doble_borrado = cliente.delete("/admin/tareas-entrega/t1")
    assert respuesta_doble_borrado.status_code == 404
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app_admin_tareas.py -k "recuperable" -v`
Expected: FAIL — `DELETE` still hard-deletes, so the first `select` after delete returns an empty list and `fila = ...[0]` raises `IndexError`.

- [ ] **Step 3: Implement**

Replace `web/app.py:4117-4126` (`DELETE /admin/tareas-entrega/{tarea_id}`):

```python
@app.delete("/admin/tareas-entrega/{tarea_id}")
def admin_tarea_eliminar(tarea_id: str, request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    filas = client.table("tareas_entrega").select("*").eq("id", tarea_id).execute().data
    if not filas or not _activo(filas[0]):
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    client.table("tareas_entrega").update({
        "borrado_en": datetime.now(timezone.utc).isoformat(),
        "borrado_por": _quien_opera(request),
    }).eq("id", tarea_id).execute()
    return {"ok": True, "tarea_id": tarea_id}
```

Confirm `from datetime import datetime, timezone` is already imported at the top of `web/app.py` (it is — used elsewhere for `recibo_emitido_en`).

Then change `if not filas:` → `if not filas or not _activo(filas[0]):` at these other tareas_entrega single-row lookups (locate by route decorator, since line numbers shift):
- `admin_tarea_completar` (originally around `web/app.py:4040`)
- `admin_tarea_derivar` (originally `web/app.py:4079-4081`)
- `admin_tarea_editar_fecha` (originally around `web/app.py:4065` — same pattern as pedidos' fecha-entrega edit)
- any other `PUT /admin/tareas-entrega/{tarea_id}/...` handler reading `filas = client.table("tareas_entrega").select("*").eq("id", tarea_id)...` (grep `web/app.py` for `"tareas_entrega").select("*").eq("id", tarea_id)` to find every occurrence and update each)

And filter the "list active tareas" reads:
- `web/app.py:2657` (cadete panel): `tareas = client.table("tareas_entrega").select("*").eq("asignado_a", CADETE_SLUG).execute().data` → append `tareas = [t for t in tareas if _activo(t)]`.
- `web/app.py:1594` (admin panel): `tareas = [] if mostrar_clientes else client.table("tareas_entrega").select("*").execute().data` → append `tareas = [t for t in tareas if _activo(t)]`.
- `web/app.py:3988` (`admin_reordenar_entregas`): change the comprehension condition from `if not tarea.get("completada_en")` to `if _activo(tarea) and not tarea.get("completada_en")`.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_app_admin_tareas.py -k "recuperable" -v`
Expected: PASS

- [ ] **Step 5: Run the full existing tareas/cadete test suites to catch regressions**

Run: `.venv/bin/python -m pytest tests/test_app_admin_tareas.py tests/test_app_admin_cadete.py -v`
Expected: all PASS. As in Task 2 Step 9, fix any pre-existing test that asserted hard-delete semantics.

- [ ] **Step 6: Commit**

```bash
git add web/app.py tests/test_app_admin_tareas.py
git commit -m "feat: borrado de tareas/notas del cadete pasa a ser recuperable"
```

---

## Task 4: Papelera list endpoints with lazy 48h purge

**Files:**
- Modify: `web/app.py` (new helper + two new GET endpoints)
- Test: `tests/test_app_papelera.py` (new file)

**Interfaces:**
- Consumes: `_activo(fila)` (Task 2/3, used inversely here).
- Produces: `_purgar_y_listar_papelera(client, asignado_a=None) -> tuple[list[dict], list[dict]]` returning `(pedidos_borrados, tareas_borradas)`, both sorted by `borrado_en` descending. Later tasks (5, 6) call this same helper and consume this exact return shape.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_app_papelera.py`:

```python
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _iso_hace(horas):
    return (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()


def test_admin_papelera_lista_borrados_recientes_y_purga_vencidos(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})

    fake.table("pedidos").insert({
        "id": "reciente", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "borrado_en": _iso_hace(2), "borrado_por": "Vlad",
    }).execute()
    fake.table("pedidos").insert({
        "id": "vencido", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-18",
        "borrado_en": _iso_hace(50), "borrado_por": "Vlad",
    }).execute()
    fake.table("tareas_entrega").insert({
        "id": "tarea-reciente", "fecha_entrega": "2026-09-20", "titulo": "Llamar a Ana", "orden": 1,
        "borrado_en": _iso_hace(1), "borrado_por": "alejo",
    }).execute()

    respuesta = cliente.get("/admin/papelera")
    assert respuesta.status_code == 200
    assert "reciente" in respuesta.text
    assert "vencido" not in respuesta.text
    assert "tarea-reciente" in respuesta.text

    assert fake.table("pedidos").select("*").eq("id", "vencido").execute().data == []
    assert fake.table("pedidos").select("*").eq("id", "reciente").execute().data != []


def test_cadete_papelera_solo_ve_lo_propio(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/cadete/login", json={"password": "clave-cadete"})

    fake.table("pedidos").insert({
        "id": "propio", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "asignado_a": "alejo", "borrado_en": _iso_hace(1), "borrado_por": "alejo",
    }).execute()
    fake.table("pedidos").insert({
        "id": "ajeno", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "asignado_a": None, "borrado_en": _iso_hace(1), "borrado_por": "Vlad",
    }).execute()

    respuesta = cliente.get("/admin/cadete/papelera")
    assert respuesta.status_code == 200
    assert "propio" in respuesta.text
    assert "ajeno" not in respuesta.text


def test_papelera_requiere_sesion(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    cliente = TestClient(appmod.app, base_url="https://testserver")
    assert cliente.get("/admin/papelera").status_code in (401, 303, 307)
    assert cliente.get("/admin/cadete/papelera").status_code in (401, 303, 307)
```

Check `tests/test_app_admin_cadete.py` for the exact `CADETE_PASSWORD` monkeypatch target and login body shape before finalizing — copy that convention verbatim instead of guessing.

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app_papelera.py -v`
Expected: FAIL with 404 (routes don't exist yet).

- [ ] **Step 3: Implement the purge+list helper and the two routes**

Add near `_activo`/`_quien_opera` in `web/app.py`:

```python
def _purgar_y_listar_papelera(client, asignado_a=None):
    limite = datetime.now(timezone.utc) - timedelta(hours=48)

    def _procesar(tabla):
        filas = client.table(tabla).select("*").execute().data
        vivas, vencidas = [], []
        for fila in filas:
            borrado_en = fila.get("borrado_en")
            if not borrado_en:
                continue
            momento = datetime.fromisoformat(borrado_en)
            (vencidas if momento < limite else vivas).append(fila)
        for fila in vencidas:
            client.table(tabla).delete().eq("id", fila["id"]).execute()
        if asignado_a is not None:
            vivas = [f for f in vivas if f.get("asignado_a") == asignado_a or f.get("borrado_por") == asignado_a]
        vivas.sort(key=lambda f: f.get("borrado_en", ""), reverse=True)
        return vivas

    return _procesar("pedidos"), _procesar("tareas_entrega")
```

`timedelta` must be imported — check the top of `web/app.py`'s `from datetime import ...` line and add `timedelta` if missing.

Add the two routes (near the other `/admin/papelera`-adjacent admin routes, e.g. right before `DELETE /admin/pedidos/{pedido_id}`):

```python
def _tarjeta_papelera(tipo, fila, clientes_por_id):
    item_id = html.escape(fila.get("id", ""))
    if tipo == "pedido":
        cliente = clientes_por_id.get(fila.get("cliente_id"), {})
        titulo = f"Pedido de {html.escape(cliente.get('nombre', '') or 'cliente')}"
    else:
        titulo = f"Nota: {html.escape(fila.get('titulo') or '')}"
    borrado_por = html.escape(fila.get("borrado_por") or "—")
    borrado_en = html.escape(fila.get("borrado_en") or "")
    return (
        f'<div class="papelera-item"><div class="papelera-item-detalle">'
        f'<strong>{titulo}</strong><br><span>Borrado por {borrado_por} · {borrado_en}</span></div>'
        f'<div class="papelera-item-acciones">'
        f'<button class="btn-restaurar-papelera" type="button" data-tipo="{tipo}" data-id="{item_id}">Restaurar</button>'
        f'</div></div>'
    )


def _pagina_papelera(request: Request, titulo_pagina: str, pedidos_borrados, tareas_borradas, clientes_por_id, url_salir):
    items_html = "".join(
        [_tarjeta_papelera("pedido", p, clientes_por_id) for p in pedidos_borrados]
        + [_tarjeta_papelera("tarea", t, clientes_por_id) for t in tareas_borradas]
    ) or '<p class="papelera-vacia">No hay elementos borrados.</p>'
    return f"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>{titulo_pagina}</title>{_ADMIN_CLIENTES_PWA_HEAD}{_ADMIN_CLIENTES_ESTILO}
<style>
  .papelera-item {{ display:flex; justify-content:space-between; align-items:center; gap:12px; padding:12px; border:1px solid var(--op-border-strong); border-radius:var(--op-r-sm); margin-bottom:8px; background:var(--op-surface); }}
  .papelera-item-detalle span {{ color:var(--op-text-dim); font-size:var(--op-fs-small); }}
  .papelera-vacia {{ color:var(--op-text-dim); padding:20px 0; }}
</style>
</head><body>
<div class="panel">
  <div class="panel-header"><h1>{titulo_pagina}</h1>
    <div class="panel-header-acciones"><a class="btn-clientes" href="{url_salir}">Volver</a></div>
  </div>
  <section>{items_html}</section>
</div>
<script>
document.querySelectorAll(".btn-restaurar-papelera").forEach((btn) => {{
  btn.addEventListener("click", async () => {{
    btn.disabled = true;
    const r = await fetch(`/admin/papelera/${{btn.dataset.tipo}}/${{btn.dataset.id}}/restaurar`, {{ method: "POST" }});
    if (!r.ok) {{ alert("No se pudo restaurar."); btn.disabled = false; return; }}
    location.reload();
  }});
}});
</script>
</body></html>"""


@app.get("/admin/papelera", response_class=HTMLResponse)
def admin_papelera(request: Request):
    if not _clientes_admin_activo(request):
        raise HTTPException(status_code=401, detail="Sesión de admin requerida")
    client = get_client()
    pedidos_borrados, tareas_borradas = _purgar_y_listar_papelera(client)
    clientes_por_id = {c.get("id"): c for c in client.table("clientes").select("*").execute().data}
    return _pagina_papelera(request, "Borrados", pedidos_borrados, tareas_borradas, clientes_por_id, "/admin/clientes")


@app.get("/admin/cadete/papelera", response_class=HTMLResponse)
def admin_cadete_papelera(request: Request):
    if not _cadete_activo(request):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    client = get_client()
    pedidos_borrados, tareas_borradas = _purgar_y_listar_papelera(client, asignado_a=CADETE_SLUG)
    clientes_por_id = {c.get("id"): c for c in client.table("clientes").select("*").execute().data}
    return _pagina_papelera(request, "Borrados", pedidos_borrados, tareas_borradas, clientes_por_id, "/admin/cadete")
```

- [ ] **Step 4: Run to verify tests pass**

Run: `.venv/bin/python -m pytest tests/test_app_papelera.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/app.py tests/test_app_papelera.py
git commit -m "feat: vistas de papelera para admin y cadete con purga a las 48hs"
```

---

## Task 5: Restore endpoint

**Files:**
- Modify: `web/app.py` (one new POST route)
- Modify: `web/pedidos.py` (already has `restaurar_pedido` from Task 2 — reused here)
- Test: `tests/test_app_papelera.py`

**Interfaces:**
- Consumes: `pedidos.restaurar_pedido(client, pedido_id)` (Task 2), `_puede_operar_entrega(request, fila)` (existing).

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_app_papelera.py`:

```python
def test_admin_restaura_pedido_borrado(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})
    fake.table("pedidos").insert({
        "id": "p1", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "borrado_en": _iso_hace(1), "borrado_por": "Vlad",
    }).execute()

    respuesta = cliente.post("/admin/papelera/pedido/p1/restaurar")
    assert respuesta.status_code == 200

    fila = fake.table("pedidos").select("*").eq("id", "p1").execute().data[0]
    assert fila["borrado_en"] is None


def test_cadete_no_puede_restaurar_pedido_ajeno(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/cadete/login", json={"password": "clave-cadete"})
    fake.table("pedidos").insert({
        "id": "ajeno", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "asignado_a": None, "borrado_en": _iso_hace(1), "borrado_por": "Vlad",
    }).execute()

    respuesta = cliente.post("/admin/papelera/pedido/ajeno/restaurar")
    assert respuesta.status_code == 403


def test_restaura_tarea_borrada(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-20", "titulo": "Llamar a Ana", "orden": 1,
        "borrado_en": _iso_hace(1), "borrado_por": "Vlad",
    }).execute()

    respuesta = cliente.post("/admin/papelera/tarea/t1/restaurar")
    assert respuesta.status_code == 200
    fila = fake.table("tareas_entrega").select("*").eq("id", "t1").execute().data[0]
    assert fila["borrado_en"] is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app_papelera.py -k restaura -v`
Expected: FAIL (404, route doesn't exist).

- [ ] **Step 3: Implement**

Add to `web/app.py`, right after the two papelera GET routes from Task 4:

```python
@app.post("/admin/papelera/{tipo}/{item_id}/restaurar")
def admin_papelera_restaurar(tipo: Literal["pedido", "tarea"], item_id: str, request: Request):
    if not (_clientes_admin_activo(request) or _cadete_activo(request)):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    client = get_client()
    tabla = "pedidos" if tipo == "pedido" else "tareas_entrega"
    filas = client.table(tabla).select("*").eq("id", item_id).execute().data
    if not filas:
        raise HTTPException(status_code=404, detail="No encontrado")
    fila = filas[0]
    if not fila.get("borrado_en"):
        raise HTTPException(status_code=404, detail="No está borrado")
    if not _clientes_admin_activo(request):
        propio = fila.get("asignado_a") == CADETE_SLUG or fila.get("borrado_por") == CADETE_SLUG
        if not propio:
            raise HTTPException(status_code=403, detail="No podés restaurar este elemento")
    if tipo == "pedido":
        pedidos.restaurar_pedido(client, item_id)
    else:
        client.table("tareas_entrega").update({"borrado_en": None, "borrado_por": None}).eq("id", item_id).execute()
    return {"ok": True, "tipo": tipo, "id": item_id}
```

`Literal` must already be imported (it's used by `OrdenEntregaItemIn.tipo` at `web/app.py:3609`) — confirm, no new import needed.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_app_papelera.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add web/app.py tests/test_app_papelera.py
git commit -m "feat: restaurar pedidos y notas desde la papelera"
```

---

## Task 6: "Borrados" CTA in the admin and cadete menus

**Files:**
- Modify: `web/app.py:1819` (admin "Pedidos y recibos" panel header)
- Modify: `web/app.py:2305` (admin "Clientes" list panel header)
- Modify: `web/app.py:2787` (cadete panel header)
- Test: `tests/test_app_admin_clientes.py`, `tests/test_app_admin_cadete.py`

**Interfaces:**
- Consumes: routes `/admin/papelera` and `/admin/cadete/papelera` from Task 4.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_app_admin_clientes.py` (reuse its existing admin-login helper):

```python
def test_panel_pedidos_tiene_link_a_papelera(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})

    assert 'href="/admin/papelera"' in cliente.get("/admin/clientes").text
    assert 'href="/admin/papelera"' in cliente.get("/admin/clientes/lista").text
```

Add to `tests/test_app_admin_cadete.py`:

```python
def test_panel_cadete_tiene_link_a_papelera(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/cadete/login", json={"password": "clave-cadete"})

    assert 'href="/admin/cadete/papelera"' in cliente.get("/admin/cadete").text
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app_admin_clientes.py -k papelera tests/test_app_admin_cadete.py -k papelera -v`
Expected: FAIL — link not present yet.

- [ ] **Step 3: Implement**

`web/app.py:1819`:
```python
-    <div class="panel-header-acciones"><a class="btn-clientes" href="/admin/clientes/lista">Clientes</a><button id="salir">Cerrar sesión</button></div>
+    <div class="panel-header-acciones"><a class="btn-clientes" href="/admin/clientes/lista">Clientes</a><a class="btn-clientes" href="/admin/papelera">Borrados</a><button id="salir">Cerrar sesión</button></div>
```

`web/app.py:2305`:
```python
-    <div class="panel-header-acciones"><a class="btn-clientes" href="/admin/clientes">Pedidos y recibos</a><button id="salir">Cerrar sesión</button></div>
+    <div class="panel-header-acciones"><a class="btn-clientes" href="/admin/clientes">Pedidos y recibos</a><a class="btn-clientes" href="/admin/papelera">Borrados</a><button id="salir">Cerrar sesión</button></div>
```

`web/app.py:2787`:
```python
-    <div class="panel-header-acciones"><button id="salir">Cerrar sesión</button></div>
+    <div class="panel-header-acciones"><a class="btn-clientes" href="/admin/cadete/papelera">Borrados</a><button id="salir">Cerrar sesión</button></div>
```

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_app_admin_clientes.py tests/test_app_admin_cadete.py -v`
Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add web/app.py tests/test_app_admin_clientes.py tests/test_app_admin_cadete.py
git commit -m "feat: CTA Borrados en el menu de admin y de cadete"
```

---

## Task 7: `web/recibos_manuales.py` — pure logic for the standalone receipt

**Files:**
- Create: `web/recibos_manuales.py`
- Test: `tests/test_recibos_manuales.py` (new file)

**Interfaces:**
- Produces: `construir_items(items_crudos: list[dict]) -> list[dict]` (validates/normalizes `[{"nombre": str, "precio_usd": float}]`, raises `ValueError` on bad input), `calcular_total(items: list[dict]) -> float`, `armar_pedido_like(nombre_cliente, items, total_usd, recibo_id, emitido_en, creado_por) -> dict` (shape consumed by `recibos.pdf_recibo`/`html_recibo` in Task 8).
- Consumes: nothing (pure functions, no DB/network).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_recibos_manuales.py`:

```python
import pytest

from web import recibos_manuales


def test_construir_items_normaliza_precio_a_float():
    items = recibos_manuales.construir_items([
        {"nombre": "iPhone 11 128GB", "precio_usd": "425"},
        {"nombre": "Funda", "precio_usd": 10},
    ])
    assert items == [
        {"nombre": "iPhone 11 128GB", "precio_usd": 425.0},
        {"nombre": "Funda", "precio_usd": 10.0},
    ]


def test_construir_items_rechaza_lista_vacia():
    with pytest.raises(ValueError):
        recibos_manuales.construir_items([])


def test_construir_items_rechaza_nombre_vacio_o_precio_invalido():
    with pytest.raises(ValueError):
        recibos_manuales.construir_items([{"nombre": "  ", "precio_usd": 10}])
    with pytest.raises(ValueError):
        recibos_manuales.construir_items([{"nombre": "Funda", "precio_usd": -5}])
    with pytest.raises(ValueError):
        recibos_manuales.construir_items([{"nombre": "Funda", "precio_usd": "no-es-numero"}])


def test_calcular_total_suma_precios():
    items = [{"nombre": "A", "precio_usd": 10.5}, {"nombre": "B", "precio_usd": 4.5}]
    assert recibos_manuales.calcular_total(items) == 15.0


def test_armar_pedido_like_tiene_la_forma_que_espera_recibos_py():
    items = [{"nombre": "iPhone 11 128GB", "precio_usd": 425.0}]
    pedido = recibos_manuales.armar_pedido_like(
        nombre_cliente="Ana Lopez",
        items=items,
        total_usd=425.0,
        recibo_id="0001-1993",
        emitido_en="2026-09-19T12:00:00+00:00",
        creado_por="alejo",
    )
    assert pedido["detalle"] == [{
        "nombre": "iPhone 11 128GB", "color": None, "cantidad": 1,
        "usd_unitario": 425.0, "usd_subtotal": 425.0,
    }]
    assert pedido["total_usd"] == 425.0
    assert pedido["descuento_usd"] == 0
    assert pedido["recibo_id"] == "0001-1993"
    assert pedido["recibo_emitido_en"] == "2026-09-19T12:00:00+00:00"
    assert pedido["entregado_por_cadete"] is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_recibos_manuales.py -v`
Expected: FAIL — `web/recibos_manuales.py` doesn't exist (`ModuleNotFoundError`).

- [ ] **Step 3: Implement**

Create `web/recibos_manuales.py`:

```python
"""Lógica pura del recibo manual: un recibo standalone armado desde una nota
del cadete, sin depender de una fila en ``pedidos``. Ver
docs/superpowers/specs/2026-09-19-recibo-manual-y-papelera-design.md.
"""


def construir_items(items_crudos):
    if not items_crudos:
        raise ValueError("El recibo necesita al menos un ítem")
    items = []
    for item in items_crudos:
        nombre = str(item.get("nombre") or "").strip()
        if not nombre:
            raise ValueError("Cada ítem necesita un nombre")
        try:
            precio = float(item.get("precio_usd"))
        except (TypeError, ValueError):
            raise ValueError(f"Precio inválido para '{nombre}'")
        if precio <= 0:
            raise ValueError(f"El precio de '{nombre}' tiene que ser mayor a 0")
        items.append({"nombre": nombre, "precio_usd": precio})
    return items


def calcular_total(items):
    return sum(item["precio_usd"] for item in items)


def armar_pedido_like(nombre_cliente, items, total_usd, recibo_id, emitido_en, creado_por):
    return {
        "detalle": [
            {
                "nombre": item["nombre"],
                "color": None,
                "cantidad": 1,
                "usd_unitario": item["precio_usd"],
                "usd_subtotal": item["precio_usd"],
            }
            for item in items
        ],
        "total_usd": total_usd,
        "descuento_usd": 0,
        "recibo_id": recibo_id,
        "recibo_emitido_en": emitido_en,
        "entregado_por_cadete": True,
        "_nombre_cliente_manual": nombre_cliente,
    }
```

Note: `recibos.html_recibo`/`pdf_recibo` take a separate `cliente` dict (with `nombre`/`apellido`) as their first argument — Task 8's route handler builds that from the manual `nombre_cliente` string directly (split into `nombre`/`apellido` or passed whole as `nombre` with `apellido` empty), it does not come from `armar_pedido_like`. The `_nombre_cliente_manual` key here is unused by `recibos.py` and only kept for debugging/logging; it's harmless extra data in the dict.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_recibos_manuales.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web/recibos_manuales.py tests/test_recibos_manuales.py
git commit -m "feat: logica pura del recibo manual standalone"
```

---

## Task 8: `POST /admin/tareas-entrega/{tarea_id}/recibo-manual` endpoint

**Files:**
- Modify: `web/app.py` (new endpoint + `_tarjeta_tarea_cadete` gets a "Recibo" button)
- Test: `tests/test_app_recibo_manual.py` (new file)

**Interfaces:**
- Consumes: `recibos_manuales.construir_items`, `calcular_total`, `armar_pedido_like` (Task 7); `recibos.pdf_recibo`, `recibos.html_recibo` (existing, unchanged); `_nuevo_recibo_id(client)`, `_puede_operar_entrega(request, fila)` (existing).
- Produces: the endpoint; later Task 9 only adds the frontend panel that calls it — no new backend interface for Task 9 to consume beyond this endpoint's URL and its multipart body shape (`nombre`, `email`, `items` as a JSON string, `fotos` as files — same shape the existing `/admin/pedidos/{id}/recibo` endpoint already uses for `fotos`).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_app_recibo_manual.py`:

```python
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _login_cadete(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/cadete/login", json={"password": "clave-cadete"})
    return fake, cliente


def test_recibo_manual_envia_mail_y_persiste(monkeypatch):
    fake, cliente = _login_cadete(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-20", "titulo": "Entrega en Nva Cordoba",
        "orden": 1, "asignado_a": "alejo",
    }).execute()

    correos_enviados = []
    monkeypatch.setattr(
        appmod, "enviar_email",
        lambda destinatario, asunto, html, adjuntos=None: correos_enviados.append((destinatario, asunto)),
    )

    respuesta = cliente.post(
        "/admin/tareas-entrega/t1/recibo-manual",
        data={
            "nombre": "Ana Lopez",
            "email": "ana@example.com",
            "items": '[{"nombre": "iPhone 11 128GB", "precio_usd": 425}]',
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["ok"] is True
    assert cuerpo["recibo_id"]

    assert correos_enviados == [("ana@example.com", f"Recibo {cuerpo['recibo_id']} — The Tech Room Arg")]
    registro = fake.table("recibos_manuales").select("*").eq("tarea_id", "t1").execute().data[0]
    assert registro["nombre_cliente"] == "Ana Lopez"
    assert registro["total_usd"] == 425.0
    assert registro["enviado_en"] is not None


def test_recibo_manual_rechaza_items_vacios(monkeypatch):
    fake, cliente = _login_cadete(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-20", "titulo": "Entrega", "orden": 1, "asignado_a": "alejo",
    }).execute()

    respuesta = cliente.post(
        "/admin/tareas-entrega/t1/recibo-manual",
        data={"nombre": "Ana", "email": "ana@example.com", "items": "[]"},
    )
    assert respuesta.status_code == 400


def test_recibo_manual_bloquea_nota_ajena(monkeypatch):
    fake, cliente = _login_cadete(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-20", "titulo": "Entrega", "orden": 1, "asignado_a": None,
    }).execute()

    respuesta = cliente.post(
        "/admin/tareas-entrega/t1/recibo-manual",
        data={"nombre": "Ana", "email": "ana@example.com", "items": '[{"nombre":"X","precio_usd":10}]'},
    )
    assert respuesta.status_code == 403
```

Check the real `enviar_email` signature in `web/email_util.py` before finalizing the monkeypatch lambda's parameter list — match it exactly (the existing `/admin/pedidos/{id}/recibo` endpoint call at `web/app.py:873-878` shows the call site's argument order: `destinatario, asunto, html, adjuntos`).

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_app_recibo_manual.py -v`
Expected: FAIL — 404, route doesn't exist.

- [ ] **Step 3: Implement the endpoint**

Add to `web/app.py`, near the other tareas_entrega routes (after `admin_tarea_eliminar`):

```python
@app.post("/admin/tareas-entrega/{tarea_id}/recibo-manual")
async def admin_tarea_recibo_manual(tarea_id: str, request: Request):
    if not (_clientes_admin_activo(request) or _cadete_activo(request)):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    client = get_client()
    filas = client.table("tareas_entrega").select("*").eq("id", tarea_id).execute().data
    if not filas or not _activo(filas[0]):
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    tarea = filas[0]
    if not _puede_operar_entrega(request, tarea):
        raise HTTPException(status_code=403, detail="Esta nota no está asignada a tu usuario")

    formulario = await request.form()
    nombre_cliente = (formulario.get("nombre") or "").strip()
    email_cliente = (formulario.get("email") or "").strip()
    if not nombre_cliente or not email_cliente:
        return JSONResponse({"error": "Nombre y email son obligatorios"}, status_code=400)
    try:
        items_crudos = json.loads(formulario.get("items") or "[]")
        items = recibos_manuales.construir_items(items_crudos)
    except (ValueError, TypeError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)

    total_usd = recibos_manuales.calcular_total(items)
    recibo_id = _nuevo_recibo_id(client)
    emitido_en = datetime.now(timezone.utc).isoformat()
    pedido_para_mail = recibos_manuales.armar_pedido_like(
        nombre_cliente, items, total_usd, recibo_id, emitido_en, _quien_opera(request),
    )
    partes_nombre = nombre_cliente.split(" ", 1)
    cliente_para_mail = {
        "nombre": partes_nombre[0],
        "apellido": partes_nombre[1] if len(partes_nombre) > 1 else "",
        "email": email_cliente,
    }

    fotos_pdf, adjuntos_fotos, fotos_guardadas = [], [], []
    for foto in formulario.getlist("fotos")[:10]:
        if not getattr(foto, "filename", None):
            continue
        contenido = await foto.read()
        if not contenido or len(contenido) > 2_500_000:
            return JSONResponse({"error": "Cada foto comprimida debe pesar menos de 2,5 MB"}, status_code=400)
        nombre_archivo = f"serie-{uuid.uuid4().hex}.jpg"
        ruta = f"recibos-manuales/{tarea_id}/{nombre_archivo}"
        client.storage.from_("recibos-series").upload(ruta, contenido, {"content-type": "image/jpeg"})
        fotos_guardadas.append(ruta)
        fotos_pdf.append(contenido)
        adjuntos_fotos.append({"filename": nombre_archivo, "content": contenido})

    try:
        pdf_adjunto = recibos.pdf_recibo(cliente_para_mail, pedido_para_mail, fotos=fotos_pdf)
        enviar_email(
            email_cliente,
            f"Recibo {recibo_id} — The Tech Room Arg",
            recibos.html_recibo(cliente_para_mail, pedido_para_mail),
            [{"filename": f"recibo-{recibo_id}.pdf", "content": pdf_adjunto}, *adjuntos_fotos],
        )
    except EnvioEmailError as e:
        return JSONResponse({"error": str(e)}, status_code=502)

    registro = {
        "id": str(uuid.uuid4()),
        "tarea_id": tarea_id,
        "nombre_cliente": nombre_cliente,
        "email_cliente": email_cliente,
        "items": items,
        "total_usd": total_usd,
        "fotos_series": fotos_guardadas,
        "recibo_id": recibo_id,
        "creado_por": _quien_opera(request),
        "creado_en": emitido_en,
        "enviado_en": datetime.now(timezone.utc).isoformat(),
    }
    client.table("recibos_manuales").insert(registro).execute()
    return {"ok": True, "recibo_id": recibo_id}
```

Add `from web import recibos_manuales` near the existing `from web import buscador, catalogo, cuentas, ...` import line (`web/app.py:30`).

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_app_recibo_manual.py -v`
Expected: PASS

- [ ] **Step 5: Add the "Recibo" button to the nota card**

Modify `_tarjeta_tarea_cadete` (`web/app.py:2717-2742`) — add a button reusing the existing `.btn-enviar-recibo` CSS class (already styled at `web/app.py:1232-1234`/`1484-1486` for the pedido recibo flow) so no new CSS is needed for the button itself:

```python
        boton_recibo_manual = (
            f'<button class="btn-enviar-recibo btn-recibo-nota" type="button" data-id="{tarea_id}">Recibo</button>'
        )
        return (
            f'<div class="pedido-hoy"><div class="pedido-hoy-detalle">'
            f'<strong>Tarea: {html.escape(tarea.get("titulo") or "")}</strong>'
            f'{detalle_cliente}<br><span>{html.escape(tarea.get("nota") or "")}</span>{detalle_obs}</div>'
            f'<div class="pedido-acciones">{_boton_vamos(direccion)}{_boton_whatsapp_cliente(cliente_tarea.get("celular"))}'
            f'<button class="btn-completar-tarea" type="button" data-id="{tarea_id}">Completado</button>{boton_fecha}{boton_derivar_vlad}{boton_recibo_manual}</div></div>'
        )
```

(The wiring for this button's click handler — opening the panel from Task 9 — belongs to Task 9, since it doesn't exist until then. This step only adds the button markup and its `data-id`.)

- [ ] **Step 6: Run the full test suite to catch regressions**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS

- [ ] **Step 7: Commit**

```bash
git add web/app.py tests/test_app_recibo_manual.py
git commit -m "feat: endpoint de recibo manual desde nota + boton en la tarjeta"
```

---

## Task 9: Frontend — recibo-manual panel with catalog autocomplete

**Files:**
- Modify: `web/app.py` (new modal markup + CSS + JS inside the `admin_cadete` route, ~`web/app.py:2793-2919` region)
- Manual verification: Playwright via `.claude/skills/run-ttra-web/driver.py` conventions (no JS unit tests exist in this repo)

**Interfaces:**
- Consumes: `GET /api/catalogo` (existing, unchanged — returns `{"secciones": {seccion: [producto, ...]}}` where each `producto` has `nombre` and `usd`), `POST /admin/tareas-entrega/{tarea_id}/recibo-manual` (Task 8).

- [ ] **Step 1: Add the modal markup**

In `web/app.py`, right after the existing `<div class="modal-series" ...>` block (`web/app.py:2808`), add:

```python
<div class="modal-recibo-manual" id="modal-recibo-manual" hidden><div class="modal-recibo-manual-contenido" role="dialog" aria-modal="true" aria-labelledby="recibo-manual-titulo">
  <h2 id="recibo-manual-titulo">Generar recibo</h2>
  <label for="recibo-manual-nombre">Nombre</label>
  <input id="recibo-manual-nombre" placeholder="Nombre del cliente">
  <label for="recibo-manual-email">Email</label>
  <input id="recibo-manual-email" type="email" placeholder="email@ejemplo.com">
  <label for="recibo-manual-item-buscar">Agregar ítem</label>
  <div class="recibo-manual-buscador">
    <input id="recibo-manual-item-buscar" autocomplete="off" placeholder="Escribí para buscar en el catálogo">
    <ul id="recibo-manual-sugerencias" class="recibo-manual-sugerencias" role="listbox" hidden></ul>
  </div>
  <ul id="recibo-manual-items" class="recibo-manual-items"></ul>
  <div class="recibo-manual-total">Total: US$ <span id="recibo-manual-total">0</span></div>
  <div class="series-acciones">
    <button id="recibo-manual-agregar-foto" type="button">Agregar foto</button>
    <button id="recibo-manual-cancelar" type="button">Cancelar</button>
    <button id="recibo-manual-enviar" type="button">Enviar</button>
  </div>
</div></div>
```

- [ ] **Step 2: Add the CSS**

Right after the `.modal-fecha-entrega` CSS block near `web/app.py:1286-1289`, add:

```python
  .modal-recibo-manual { position:fixed; inset:0; z-index:30; background:rgba(0,0,0,.7); display:flex; align-items:center; justify-content:center; padding:20px; }
  .modal-recibo-manual[hidden] { display:none; }
  .modal-recibo-manual-contenido { width:min(520px,100%); max-height:90vh; overflow-y:auto; background:var(--op-surface); border:1px solid var(--op-border-strong); border-radius:var(--op-r-md); padding:20px; box-sizing:border-box; box-shadow:0 1px 2px rgba(0,0,0,.4), 0 12px 28px -8px rgba(0,0,0,.55); }
  .modal-recibo-manual h2 { color:var(--op-text); font-size:var(--op-fs-title); margin:0 0 12px; }
  .modal-recibo-manual label { display:block; color:var(--op-text-dim); font-size:var(--op-fs-small); margin:10px 0 4px; }
  .modal-recibo-manual input { box-sizing:border-box; width:100%; min-height:42px; border:1px solid var(--op-border-strong); border-radius:var(--op-r-sm); padding:0 10px; background:var(--op-input-bg); color:var(--op-text); font:inherit; }
  .recibo-manual-buscador { position:relative; }
  .recibo-manual-sugerencias { position:absolute; z-index:1; top:100%; left:0; right:0; margin:2px 0 0; padding:4px; list-style:none; background:var(--op-surface); border:1px solid var(--op-border-strong); border-radius:var(--op-r-sm); max-height:200px; overflow-y:auto; }
  .recibo-manual-sugerencias[hidden] { display:none; }
  .recibo-manual-sugerencias li { padding:8px; border-radius:var(--op-r-sm); cursor:pointer; color:var(--op-text); font-size:var(--op-fs-small); }
  .recibo-manual-sugerencias li:hover { background:var(--op-surface-2); }
  .recibo-manual-items { list-style:none; margin:10px 0; padding:0; }
  .recibo-manual-items li { display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid var(--op-border-strong); }
  .recibo-manual-items li span { flex:1; color:var(--op-text); font-size:var(--op-fs-small); }
  .recibo-manual-items li input { width:100px; min-height:36px; }
  .recibo-manual-items li button { border:0; background:transparent; color:var(--op-text-dim); font-size:18px; cursor:pointer; }
  .recibo-manual-total { color:var(--op-text); font-weight:600; margin:10px 0; }
```

- [ ] **Step 3: Add the JS**

Right after the existing series-modal script block (after the `.btn-enviar-recibo` handler, i.e. after `web/app.py:2919` from the earlier investigation excerpt — the exact insertion point is right after the last `</script>`-adjacent handler that references `modalSeries`), add:

```python
let catalogoRecibo = null;
async function cargarCatalogoRecibo() {{
  if (catalogoRecibo) return catalogoRecibo;
  const r = await fetch("/api/catalogo");
  const datos = await r.json().catch(() => ({{}}));
  catalogoRecibo = Object.values(datos.secciones || {{}}).flat();
  return catalogoRecibo;
}}
let itemsReciboManual = [];
let fotosReciboManual = [];
let tareaReciboManualActiva = null;
const modalReciboManual = document.getElementById("modal-recibo-manual");
function renderItemsReciboManual() {{
  const lista = document.getElementById("recibo-manual-items");
  lista.innerHTML = itemsReciboManual.map((item, indice) => `
    <li><span>${{item.nombre}}</span>
    <input type="number" min="0" step="0.01" value="${{item.precio_usd}}" data-indice="${{indice}}" class="recibo-manual-precio">
    <button type="button" data-indice="${{indice}}" aria-label="Quitar ítem">×</button></li>
  `).join("");
  lista.querySelectorAll(".recibo-manual-precio").forEach((input) => {{
    input.addEventListener("input", () => {{
      itemsReciboManual[Number(input.dataset.indice)].precio_usd = Number(input.value) || 0;
      actualizarTotalReciboManual();
    }});
  }});
  lista.querySelectorAll("button").forEach((boton) => {{
    boton.addEventListener("click", () => {{
      itemsReciboManual.splice(Number(boton.dataset.indice), 1);
      renderItemsReciboManual();
      actualizarTotalReciboManual();
    }});
  }});
}}
function actualizarTotalReciboManual() {{
  const total = itemsReciboManual.reduce((suma, item) => suma + (Number(item.precio_usd) || 0), 0);
  document.getElementById("recibo-manual-total").textContent = total.toFixed(2);
}}
const buscadorReciboManual = document.getElementById("recibo-manual-item-buscar");
const sugerenciasReciboManual = document.getElementById("recibo-manual-sugerencias");
buscadorReciboManual.addEventListener("input", async () => {{
  const texto = buscadorReciboManual.value.trim().toLowerCase();
  if (!texto) {{ sugerenciasReciboManual.hidden = true; return; }}
  const catalogo = await cargarCatalogoRecibo();
  const coincidencias = catalogo.filter((p) => (p.nombre || "").toLowerCase().includes(texto)).slice(0, 8);
  sugerenciasReciboManual.innerHTML = coincidencias.map((p, indice) =>
    `<li data-indice="${{indice}}" data-nombre="${{p.nombre}}" data-usd="${{p.usd ?? 0}}">${{p.nombre}} — US$ ${{p.usd ?? 0}}</li>`
  ).join("");
  sugerenciasReciboManual.hidden = coincidencias.length === 0;
  sugerenciasReciboManual.querySelectorAll("li").forEach((li) => {{
    li.addEventListener("click", () => {{
      itemsReciboManual.push({{ nombre: li.dataset.nombre, precio_usd: Number(li.dataset.usd) || 0 }});
      renderItemsReciboManual();
      actualizarTotalReciboManual();
      buscadorReciboManual.value = "";
      sugerenciasReciboManual.hidden = true;
    }});
  }});
}});
document.getElementById("recibo-manual-agregar-foto").addEventListener("click", () => {{
  const selector = Object.assign(document.createElement("input"), {{ type:"file", accept:"image/*", capture:"environment" }});
  selector.addEventListener("change", async () => {{
    if (selector.files?.[0]) fotosReciboManual.push(await comprimirFotoSerie(selector.files[0]));
  }});
  selector.click();
}});
document.querySelectorAll(".btn-recibo-nota").forEach((btn) => {{
  btn.addEventListener("click", () => {{
    tareaReciboManualActiva = btn.dataset.id;
    itemsReciboManual = []; fotosReciboManual = [];
    document.getElementById("recibo-manual-nombre").value = "";
    document.getElementById("recibo-manual-email").value = "";
    renderItemsReciboManual(); actualizarTotalReciboManual();
    modalReciboManual.hidden = false;
  }});
}});
document.getElementById("recibo-manual-cancelar").addEventListener("click", () => {{ modalReciboManual.hidden = true; }});
document.getElementById("recibo-manual-enviar").addEventListener("click", async () => {{
  if (!tareaReciboManualActiva) return;
  const boton = document.getElementById("recibo-manual-enviar");
  const nombre = document.getElementById("recibo-manual-nombre").value.trim();
  const email = document.getElementById("recibo-manual-email").value.trim();
  if (!nombre || !email) {{ alert("Completá nombre y email."); return; }}
  if (itemsReciboManual.length === 0) {{ alert("Agregá al menos un ítem."); return; }}
  boton.disabled = true; boton.textContent = "Enviando...";
  const cuerpo = new FormData();
  cuerpo.append("nombre", nombre);
  cuerpo.append("email", email);
  cuerpo.append("items", JSON.stringify(itemsReciboManual));
  fotosReciboManual.forEach((foto) => cuerpo.append("fotos", foto));
  const r = await fetch(`/admin/tareas-entrega/${{tareaReciboManualActiva}}/recibo-manual`, {{ method:"POST", body:cuerpo }});
  const respuesta = await r.json().catch(() => ({{}}));
  boton.disabled = false; boton.textContent = "Enviar";
  if (!r.ok) {{ alert(respuesta.error || "No se pudo enviar el recibo."); return; }}
  modalReciboManual.hidden = true;
  alert(`Recibo ${{respuesta.recibo_id}} enviado.`);
}});
```

This JS block reuses `comprimirFotoSerie` (already defined earlier in the same `<script>` for the pedido-recibo photo flow, `web/app.py:2882-2890`) — no duplicate compression logic.

- [ ] **Step 4: Manual verification with the running app**

Start the server and drive it (per `.claude/skills/run-ttra-web/SKILL.md`):

```bash
lsof -ti:8000 -sTCP:LISTEN | xargs -r kill
nohup .venv/bin/uvicorn web.app:app --host 127.0.0.1 --port 8000 > /tmp/ttra-uvicorn.log 2>&1 &
for i in $(seq 1 20); do curl -sf http://127.0.0.1:8000 >/dev/null 2>&1 && break; sleep 1; done
```

Then with a short Playwright script (or an extension of `driver.py`): log into `/admin/cadete` with the real `CADETE_PASSWORD`, create a nota, click "Recibo", verify the modal opens, type into the item search box, verify suggestions appear from the real catalog, pick one, verify the price field is populated and editable, verify the running total updates, and verify the "Enviar" button either succeeds or shows a clear error (since `enviar_email` needs real Resend credentials in `.env` — a local run without them is expected to surface the email error message, not crash or leave the UI in a broken state).

Take a screenshot of the opened modal to confirm no layout break (`page.screenshot(path="/tmp/ttra-shots/recibo-manual-modal.png")`).

Stop the server after: `lsof -ti:8000 -sTCP:LISTEN | xargs -r kill`

- [ ] **Step 5: Run the full test suite one last time**

Run: `.venv/bin/python -m pytest tests/ -q`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add web/app.py
git commit -m "feat: panel de recibo manual con autocompletado de catalogo en el panel de cadete"
```
