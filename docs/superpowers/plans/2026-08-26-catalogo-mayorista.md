# Catálogo Mayorista por Cliente Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Habilitar desde Admin un catálogo mayorista por cuenta, con descuentos de hasta USD 50 y un piso garantizado de USD 20 limpios después de USD 7 de gastos.

**Architecture:** La generación del catálogo conservará costos en un archivo privado separado. Un módulo puro calculará elegibilidad y precios mayoristas; las rutas de catálogo y pedidos resolverán el tipo de cliente en servidor y compartirán ese cálculo. El frontend seguirá usando la interfaz actual, pero desactivará descuentos minoristas cuando la respuesta indique modo mayorista.

**Tech Stack:** Python 3.12, FastAPI, Supabase/PostgREST, JavaScript sin framework, pytest.

**Spec:** `docs/superpowers/specs/2026-08-26-catalogo-mayorista-design.md`

## Global Constraints

- El catálogo, precios y promociones minoristas actuales no deben cambiar.
- Piso mayorista absoluto: `costo proveedor + USD 27` por unidad.
- Descuento máximo: USD 50 por unidad, en bandas objetivo de USD 5.
- Productos con margen bruto menor a USD 35 o costo inválido se excluyen del catálogo mayorista.
- El modo mayorista no acumula descuento por cantidad ni códigos de mailing.
- Costos, márgenes y proveedores nunca se envían al navegador.
- El backend vuelve a calcular precios y totales antes de guardar un pedido.
- Preservar `web/proveedores.json` y cualquier cambio no relacionado del worktree.

---

### Task 1: Índice privado de costos

**Files:**
- Modify: `web/productos.py:141-214`
- Modify: `web/app.py:40-50`
- Test: `tests/test_productos.py`

**Interfaces:**
- Produces: `generar_costos(items: list[dict]) -> dict[str, float]`
- Produces: `escribir_productos_json(...)` escribe `costos.json` junto a las salidas actuales.
- Produces: `COSTOS_PATH: pathlib.Path` en `web.app`.

- [ ] **Step 1: Write the failing cost-index tests**

```python
from web.productos import generar_costos


def test_genera_indice_privado_del_costo_consolidado():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 630, "proveedor": "fr"},
        {"nombre": "iphone 13 128gb", "costo": 610, "proveedor": "az"},
    ]
    assert generar_costos(items) == {"iphone 13 128gb": 610}


def test_escribir_productos_json_escribe_costos_sin_exponerlos(tmp_path):
    ruta = tmp_path / "productos.json"
    escribir_productos_json(
        [{"nombre": "Moto G15 128GB", "costo": 150, "proveedor": "va"}],
        1540,
        ruta,
    )
    publico = json.loads(ruta.read_text(encoding="utf-8"))
    costos = json.loads((tmp_path / "costos.json").read_text(encoding="utf-8"))
    assert "costo" not in publico[0]
    assert costos == {"Moto G15 128GB": 150}
```

- [ ] **Step 2: Run tests and verify RED**

Run: `$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_productos.py -q`

Expected: FAIL because `generar_costos` does not exist and `costos.json` is absent.

- [ ] **Step 3: Implement private cost generation**

Add to `web/productos.py`:

```python
def generar_costos(items):
    return {
        _nombre_estandar_note(_sin_cargador(fila["nombre"])): fila["costo"]
        for fila in consolidar(items)["lista"]
        if not _excluido(fila["nombre"])
    }
```

Extend `escribir_productos_json` to write `costos.json` with UTF-8 and add to `web/app.py`:

```python
COSTOS_PATH = Path(os.environ.get(
    "COSTOS_PATH", str(PRODUCTOS_PATH.with_name("costos.json"))
))
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_productos.py tests/test_app_admin_productos.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add web/productos.py web/app.py tests/test_productos.py
git commit -m "feat: conservar costos privados del catalogo"
```

---

### Task 2: Motor puro de precios mayoristas

**Files:**
- Create: `web/mayoristas.py`
- Create: `tests/test_mayoristas.py`

**Interfaces:**
- Consumes: productos públicos con `nombre`, `usd`, `pesos`, `transferencia` y costos por nombre.
- Produces: `descuento_por_margen(precio_publico: float, costo: float) -> float | None`
- Produces: `catalogo_mayorista(productos: list[dict], costos: dict[str, float]) -> list[dict]`

- [ ] **Step 1: Write failing band and safety tests**

```python
import pytest
from web.mayoristas import catalogo_mayorista, descuento_por_margen


@pytest.mark.parametrize(("margen", "esperado"), [
    (34, None), (35, 5), (40, 10), (45, 15), (50, 20),
    (55, 25), (60, 30), (65, 35), (70, 40), (75, 45), (80, 50), (200, 50),
])
def test_descuento_por_banda_de_margen(margen, esperado):
    assert descuento_por_margen(500 + margen, 500) == esperado


def test_catalogo_mayorista_filtra_sin_costo_y_recalcula_monedas():
    productos = [
        {"nombre": "Elegible", "usd": 180, "pesos": 280800, "transferencia": 289485},
        {"nombre": "Sin costo", "usd": 180, "pesos": 280800, "transferencia": 289485},
    ]
    resultado = catalogo_mayorista(productos, {"Elegible": 100})
    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Elegible"
    assert resultado[0]["usd"] == 130
    assert resultado[0]["pesos"] == round(130 * (280800 / 180))
    assert resultado[0]["transferencia"] == round(130 * (289485 / 180))
    assert resultado[0]["usd"] >= 100 + 27
```

- [ ] **Step 2: Run tests and verify RED**

Run: `$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_mayoristas.py -q`

Expected: FAIL because `web.mayoristas` does not exist.

- [ ] **Step 3: Implement the pricing module**

Create `web/mayoristas.py` with constants `GASTO_USD = 7`, `GANANCIA_LIMPIA_MINIMA_USD = 20`, `MARGEN_MINIMO_ELEGIBLE_USD = 35`, and `DESCUENTO_MAXIMO_USD = 50`. Compute the target band with `min(50, floor(margen / 5) * 5 - 30)`, reject margins below 35, and clamp with `precio_publico - costo - 27`. Copy product dictionaries and recalculate currency fields proportionally from the original USD; never add cost or margin fields to output.

```python
def descuento_por_margen(precio_publico, costo):
    margen = precio_publico - costo
    if margen < 35:
        return None
    objetivo = min(50, (int(margen) // 5) * 5 - 30)
    return max(0, min(objetivo, precio_publico - costo - 27))
```

- [ ] **Step 4: Run tests and verify GREEN**

Run: `$env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_mayoristas.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add web/mayoristas.py tests/test_mayoristas.py
git commit -m "feat: calcular precios mayoristas seguros"
```

---

### Task 3: Habilitación mayorista desde Admin Clientes

**Files:**
- Modify: `web/app.py:280-325,1131-1885`
- Modify: `tests/test_app_admin_clientes.py`

**Interfaces:**
- Produces: `POST /admin/clientes/{cliente_id}/mayorista` body `{"habilitado": bool}`.
- Persists: `clientes.tipo_cliente` as `mayorista` or `minorista`.

- [ ] **Step 1: Write failing authorization and UI tests**

```python
def test_admin_habilita_y_revoca_acceso_mayorista(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").execute().data[0]

    habilitar = c.post(f'/admin/clientes/{cliente["id"]}/mayorista', json={"habilitado": True})
    assert habilitar.status_code == 200
    assert fake.table("clientes").select("*").eq("id", cliente["id"]).execute().data[0]["tipo_cliente"] == "mayorista"
    assert "Quitar mayorista" in c.get("/admin/clientes/lista").text

    revocar = c.post(f'/admin/clientes/{cliente["id"]}/mayorista', json={"habilitado": False})
    assert revocar.status_code == 200
    assert fake.table("clientes").select("*").eq("id", cliente["id"]).execute().data[0]["tipo_cliente"] == "minorista"


def test_admin_no_habilita_contacto_sin_cuenta(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    fake.table("clientes").insert({"id": "lead", "nombre": "Lead", "auth_id": None}).execute()
    r = c.post("/admin/clientes/lead/mayorista", json={"habilitado": True})
    assert r.status_code == 400
```

- [ ] **Step 2: Run tests and verify RED**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_app_admin_clientes.py -q`

Expected: FAIL with 404 for the missing route and missing UI controls.

- [ ] **Step 3: Implement endpoint and controls**

Add a Pydantic input with `habilitado: bool`, authenticate with `_clientes_admin_activo`, fetch the client, reject missing `auth_id` when enabling, and update `tipo_cliente`. Normalize `tipo_cliente` into each client view row. Render a badge and action button; attach JavaScript that confirms, posts JSON, handles an error body, and reloads on success.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_app_admin_clientes.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add web/app.py tests/test_app_admin_clientes.py
git commit -m "feat: gestionar acceso mayorista desde admin"
```

---

### Task 4: Catálogo mayorista resuelto por sesión

**Files:**
- Modify: `web/app.py:225-250,2363-2380,2846-2860`
- Modify: `tests/test_app_catalogo.py`
- Modify: `tests/test_app_auth.py`

**Interfaces:**
- Consumes: `mayoristas.catalogo_mayorista(productos, costos)` from Task 2.
- Produces: `_tipo_cliente_sesion(request: Request) -> str`.
- Produces: `_catalogo_autorizado(request: Request) -> tuple[list[dict], str]`.
- Changes: `GET /api/catalogo` accepts `request` and includes `modo_precio`.

- [ ] **Step 1: Write failing session-aware catalog tests**

```python
def test_catalogo_publico_permanece_minorista(tmp_path, monkeypatch):
    # Arrange PRODUCTOS_PATH with one public product.
    r = TestClient(appmod.app).get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["modo_precio"] == "minorista"
    assert r.json()["secciones"]["Celulares"][0]["usd"] == 180


def test_catalogo_mayorista_filtra_y_descuenta_por_sesion(tmp_path, monkeypatch):
    c, fake = _cliente_autenticado(monkeypatch)
    cliente = fake.table("clientes").select("*").execute().data[0]
    fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq("id", cliente["id"]).execute()
    monkeypatch.setattr(appmod, "COSTOS_PATH", tmp_path / "costos.json")
    (tmp_path / "costos.json").write_text('{"Elegible": 100}', encoding="utf-8")
    r = c.get("/api/catalogo")
    assert r.json()["modo_precio"] == "mayorista"
    assert r.json()["secciones"]["Celulares"][0]["usd"] == 130
    assert "costo" not in r.text
```

- [ ] **Step 2: Run tests and verify RED**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_app_catalogo.py tests/test_app_auth.py -q`

Expected: FAIL because catalog responses lack `modo_precio` and ignore the session.

- [ ] **Step 3: Implement server-side catalog selection**

Add private JSON loading with safe failure. Resolve the session client from Supabase on every catalog request. Return existing sections for minorista and transformed sections for mayorista. Keep `/api/catalogo` public and never include internal calculation fields. Add `tipo_cliente`/`modo_precio` to `/api/me` for authenticated UI state.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_app_catalogo.py tests/test_app_auth.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add web/app.py tests/test_app_catalogo.py tests/test_app_auth.py
git commit -m "feat: servir catalogo mayorista por sesion"
```

---

### Task 5: Interfaz mayorista sin descuentos acumulados

**Files:**
- Modify: `web/static/index.html`
- Modify: `web/static/landing.js:100-130,3186-3618,3870-3910`
- Modify: `web/static/landing.css`
- Modify: `web/static/classic.css`
- Modify: `tests/test_app_landing.py`

**Interfaces:**
- Consumes: `modo_precio` from `GET /api/catalogo`.
- Produces frontend state: `modoPrecioActual` equal to `minorista` or `mayorista`.

- [ ] **Step 1: Write failing frontend contract tests**

```python
def test_modo_mayorista_muestra_insignia_y_anula_descuentos_minoristas():
    html = (appmod.BASE / "static" / "index.html").read_text(encoding="utf-8")
    js = (appmod.BASE / "static" / "landing.js").read_text(encoding="utf-8")
    assert 'id="indicador-mayorista"' in html
    assert 'modoPrecioActual === "mayorista"' in js
    assert 'borrarDescuentoMailing()' in js
    assert 'return modoPrecioActual === "mayorista" ? null' in js
```

Also add a behavioral JavaScript test if the repository's available runner supports it; otherwise keep assertions focused on the observable HTML/JS contract and cover price behavior through API and order tests.

- [ ] **Step 2: Run test and verify RED**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_app_landing.py -q`

Expected: FAIL because the indicator and mode branches are absent.

- [ ] **Step 3: Implement the mode-aware UI**

When loading `/api/catalogo`, store `modo_precio`; show `Cuenta mayorista · precios preferenciales` only in mayorista. Make `calcularDescuento` return `null` in mayorista. Clear saved mailing discounts and hide/disable their controls. Ensure cart reconciliation replaces stale saved prices with the current authorized catalog and removes unavailable products. Keep cards, search, categories, checkout, WhatsApp, and visual layout otherwise unchanged.

- [ ] **Step 4: Run frontend tests and verify GREEN**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_app_landing.py tests/test_app_catalogo.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add web/static/index.html web/static/landing.js web/static/landing.css web/static/classic.css tests/test_app_landing.py
git commit -m "feat: adaptar carrito al modo mayorista"
```

---

### Task 6: Validación autoritativa y auditoría de pedidos

**Files:**
- Modify: `supabase/schema.sql:54-75`
- Modify: `web/app.py:2505-2620`
- Modify: `web/pedidos.py:27-110`
- Modify: `tests/fakes_supabase.py`
- Modify: `tests/test_app_pedidos.py`
- Modify: `tests/test_pedidos.py`

**Interfaces:**
- Consumes: `_catalogo_autorizado(request)` from Task 4.
- Persists: `pedidos.modo_precio text not null default 'minorista'`.
- Persists: `pedidos.descuento_mayorista_usd numeric not null default 0`.
- Changes: `guardar_pedido(..., modo_precio="minorista", descuento_mayorista_usd=0)`.

- [ ] **Step 1: Write failing tamper and audit tests**

```python
def test_pedido_mayorista_recalcula_y_guarda_auditoria(monkeypatch):
    c, fake = _cliente_mayorista_con_catalogo(monkeypatch, precio_publico=180, costo=100)
    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{"nombre": "Elegible", "cantidad": 2, "usd_unitario": 130, "usd_subtotal": 260}],
        "total_usd": 260, "descuento_usd": 0,
    })
    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["modo_precio"] == "mayorista"
    assert pedido["descuento_mayorista_usd"] == 100
    assert pedido["total_usd"] == 260


def test_pedido_rechaza_precio_manipulado(monkeypatch):
    c, _fake = _cliente_mayorista_con_catalogo(monkeypatch, precio_publico=180, costo=100)
    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{"nombre": "Elegible", "cantidad": 1, "usd_unitario": 1, "usd_subtotal": 1}],
        "total_usd": 1,
    })
    assert r.status_code == 409
    assert "precios" in r.json()["error"].lower()
```

Add the equivalent minorista test to prove current authorized prices still save normally.

- [ ] **Step 2: Run tests and verify RED**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_app_pedidos.py tests/test_pedidos.py -q`

Expected: FAIL because the backend currently trusts submitted totals and audit columns do not exist.

- [ ] **Step 3: Implement authoritative validation and schema migration**

Index the authorized catalog by exact product name. For every submitted detail row, require a catalog match and exact `usd_unitario`; calculate `usd_subtotal = usd_unitario * cantidad` and total on the server. Reject differences with HTTP 409 and a refresh message. For mayorista, calculate audit discount against the current public catalog. Pass only server-calculated values to `guardar_pedido`. Add idempotent `alter table ... add column if not exists` statements and update consolidation in `web/pedidos.py` so only orders with the same `modo_precio` consolidate.

- [ ] **Step 4: Run order tests and verify GREEN**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_app_pedidos.py tests/test_pedidos.py tests/test_recibos.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add supabase/schema.sql web/app.py web/pedidos.py tests/fakes_supabase.py tests/test_app_pedidos.py tests/test_pedidos.py tests/test_recibos.py
git commit -m "feat: validar y auditar pedidos mayoristas"
```

---

### Task 7: Integración completa y preparación operativa

**Files:**
- Modify: `tests/test_app_catalogo.py`
- Test: full `tests/` suite.

**Interfaces:**
- Verifies all interfaces produced by Tasks 1–6 together.

- [ ] **Step 1: Add one end-to-end regression test**

In `tests/test_app_catalogo.py`, create a client, enable it through the real admin endpoint, fetch the catalog, assert the wholesale price and filtered product, revoke through the endpoint, then assert the public price returns. Use `FakeSupabaseClient`, temporary product/cost files, and real FastAPI routes; do not call helpers directly.

- [ ] **Step 2: Run the integration test and verify it passes**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest tests/test_app_catalogo.py -q`

Expected: PASS.

- [ ] **Step 3: Run the full suite and diff checks**

Run: `$env:ADMIN_CLIENTES_PASSWORD='test-only'; $env:SESSION_SECRET='test-session'; $env:PYTHONUTF8='1'; .\.venv\Scripts\python.exe -m pytest -q`

Expected: all tests PASS.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 4: Verify generated artifacts and security boundary**

Generate a catalog in a temporary directory and inspect all three JSON outputs. Confirm `productos.json` contains no `costo`, `proveedor`, `margen`, or discount-capacity field; `costos.json` is not mounted by a FastAPI static route; and anonymous `/api/catalogo` returns current public values.

- [ ] **Step 5: Commit any integration-only test changes**

```powershell
git add tests/test_app_catalogo.py
git commit -m "test: cubrir flujo completo de acceso mayorista"
```

- [ ] **Step 6: Production handoff checklist**

Before deployment, apply `supabase/schema.sql` to production, configure `COSTOS_PATH` only if `PRODUCTOS_PATH` uses a non-default location, regenerate the product catalog so `costos.json` exists, then deploy `web-ttra`. Verify anonymous and minorista catalogs first, enable one controlled account, verify wholesale eligibility/prices and a test checkout, and only then enable real wholesale customers.
