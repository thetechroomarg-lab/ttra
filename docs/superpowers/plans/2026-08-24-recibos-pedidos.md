# Recibos de Pedidos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emitir recibos internos por email en USD para pedidos actuales, conservar su instantánea de checkout y consultar el historial por fecha.

**Architecture:** El checkout enviará una instantánea de cada ítem y del total USD al endpoint de pedidos. El backend persistirá esa información en `pedidos`, generará el HTML del recibo desde el registro persistido y solo marcará una emisión después de que Resend responda correctamente. El panel mostrará pendientes del día y un historial filtrado por fecha.

**Tech Stack:** FastAPI, Pydantic, Supabase, Resend, HTML/CSS/JavaScript embebido en el panel admin, pytest.

**Spec:** `docs/superpowers/specs/2026-08-24-recibos-pedidos-design.md`

## Global Constraints

- El recibo es interno, no fiscal, y se expresa siempre en USD.
- No registrar ni validar medios o importes de pago.
- Usar únicamente el detalle persistido en el checkout; nunca recalcular desde el catálogo.
- Los endpoints de recibo requieren sesión de administrador.
- Mantener compatibilidad con pedidos existentes que carecen de detalle y total.
- Escribir primero la prueba que falla antes de cada cambio de comportamiento.

---

### Task 1: Instantánea de checkout y migración de pedidos

**Files:**
- Modify: `supabase/schema.sql:25-34`
- Modify: `web/pedidos.py:1-15`
- Modify: `web/app.py:1459-1518`
- Modify: `web/static/landing.js:3390-3524`
- Test: `tests/test_app_pedidos.py`

**Interfaces:**
- Consumes: `PedidoIn` y `pedidos.guardar_pedido` existentes.
- Produces: `PedidoIn.detalle: list[DetallePedidoIn]`, `PedidoIn.total_usd: int`, y `guardar_pedido(client, cliente_id, productos, fecha_entrega, detalle, total_usd, origen="whatsapp")`.

- [ ] **Step 1: Write the failing test**

```python
def test_crear_pedido_guarda_detalle_y_total_usd(monkeypatch):
    cliente = _cliente_autenticado(monkeypatch)
    respuesta = cliente.post("/api/pedidos", json={
        "productos": ["iPhone 15"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{"nombre": "iPhone 15", "color": "Negro", "cantidad": 2,
                     "usd_unitario": 500, "usd_subtotal": 1000}],
        "total_usd": 1000,
    })
    assert respuesta.status_code == 200
    fila = fake.table("pedidos").select("*").execute().data[0]
    assert fila["detalle"][0]["cantidad"] == 2
    assert fila["total_usd"] == 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_app_pedidos.py::test_crear_pedido_guarda_detalle_y_total_usd -q`

Expected: FAIL because `detalle` and `total_usd` are not accepted or persisted.

- [ ] **Step 3: Write minimal implementation**

```python
class DetallePedidoIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=300)
    color: str | None = Field(default=None, max_length=100)
    cantidad: int = Field(ge=1, le=100)
    usd_unitario: int = Field(ge=0)
    usd_subtotal: int = Field(ge=0)

class PedidoIn(BaseModel):
    productos: list[str]
    fecha_entrega: date
    detalle: list[DetallePedidoIn] = Field(min_length=1)
    total_usd: int = Field(ge=0)
```

Persistir `detalle` y `total_usd` en `pedidos.guardar_pedido`; añadir columnas nullable `detalle jsonb` y `total_usd numeric` en el SQL. En el navegador, construir el detalle y el total USD final desde el carrito antes de vaciarlo. Hacer que `registrarPedidoEnClientes` devuelva la promesa y esperarla antes de abrir WhatsApp; si la API falla, informar el error y no completar el checkout sin una instantánea recuperable.

- [ ] **Step 4: Run focused tests**

Run: `./.venv/bin/pytest tests/test_app_pedidos.py tests/test_entregas.py -q`

Expected: PASS.

### Task 2: Servicio de recibo y garantías reutilizables

**Files:**
- Create: `web/recibos.py`
- Modify: `web/app.py:245-630`
- Test: `tests/test_recibos.py`
- Test: `tests/test_app_admin_clientes.py`

**Interfaces:**
- Consumes: fila `pedidos` con `detalle`, `total_usd`, cliente con email y `enviar_email`.
- Produces: `recibos.garantias_para_detalle(detalle) -> list[str]`, `recibos.html_recibo(cliente, pedido) -> str`, y `POST /admin/pedidos/{pedido_id}/recibo`.

- [ ] **Step 1: Write the failing tests**

```python
def test_html_recibo_usa_snapshot_y_garantias():
    contenido = recibos.html_recibo(
        {"nombre": "Ana", "apellido": "Pérez"},
        {"recibo_id": "TTRA-000001", "detalle": [
            {"nombre": "iPhone 15", "cantidad": 1, "usd_unitario": 900, "usd_subtotal": 900},
            {"nombre": "Notebook Lenovo", "cantidad": 1, "usd_unitario": 700, "usd_subtotal": 700},
        ], "total_usd": 1600},
    )
    assert "U$D 1.600" in contenido
    assert "12 meses" in contenido
    assert "6 meses" in contenido

def test_emitir_recibo_envia_mail_y_marca_pedido(monkeypatch):
    monkeypatch.setattr(appmod, "enviar_email", lambda *args: None)
    respuesta = admin.post(f"/admin/pedidos/{pedido_id}/recibo")
    assert respuesta.status_code == 200
    pedido = fake.table("pedidos").select("*").eq("id", pedido_id).execute().data[0]
    assert pedido["recibo_id"].startswith("TTRA-")
    assert pedido["recibo_enviado_en"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_recibos.py tests/test_app_admin_clientes.py::test_admin_emite_recibo -q`

Expected: FAIL because the receipt module and endpoint do not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def emitir_recibo(client, pedido_id):
    pedido = _pedido_por_id(client, pedido_id)
    cliente = _cliente_por_id(client, pedido["cliente_id"])
    if not pedido.get("detalle") or pedido.get("total_usd") is None:
        raise ValueError("Este pedido histórico no tiene el detalle necesario para emitir un recibo")
    recibo_id = pedido.get("recibo_id") or _nuevo_recibo_id()
    enviar_email(cliente["email"], f"Recibo {recibo_id} — The Tech Room Arg", recibos.html_recibo(cliente, pedido | {"recibo_id": recibo_id}))
    client.table("pedidos").update({"recibo_id": recibo_id, "recibo_enviado_en": _ahora_utc()}).eq("id", pedido_id).execute()
```

Centralizar las reglas existentes de `web/buscador.py` en `web/recibos.py`, escapando toda información de cliente y productos. Si el email falla, no hacer `update`. El reenvío conserva `recibo_id` y actualiza la fecha solo tras éxito.

- [ ] **Step 4: Run focused tests**

Run: `./.venv/bin/pytest tests/test_recibos.py tests/test_app_admin_clientes.py -q`

Expected: PASS.

### Task 3: Panel de pendientes e historial por fecha

**Files:**
- Modify: `web/app.py:717-1024`
- Test: `tests/test_app_admin_clientes.py`

**Interfaces:**
- Consumes: `pedidos` con `fecha_entrega`, `detalle`, `total_usd`, `recibo_id`, `recibo_enviado_en` y endpoint de emisión.
- Produces: filas `.pedido-hoy` pendientes, botón `.btn-enviar-recibo`, selector `#fecha-historial-pedidos` y sección `#historial-pedidos`.

- [ ] **Step 1: Write the failing tests**

```python
def test_admin_muestra_solo_pedidos_hoy_sin_recibo(monkeypatch):
    pagina = admin_autenticado(monkeypatch).get("/admin/clientes")
    assert "Pedido pendiente" in pagina.text
    assert "Enviar recibo" in pagina.text
    assert "TTRA-000001" not in pagina.text

def test_admin_historial_filtra_pedidos_por_fecha(monkeypatch):
    pagina = admin_autenticado(monkeypatch).get("/admin/clientes?fecha_pedidos=2026-08-20")
    assert "Historial de pedidos" in pagina.text
    assert "Recibo enviado" in pagina.text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_app_admin_clientes.py::test_admin_muestra_solo_pedidos_hoy_sin_recibo tests/test_app_admin_clientes.py::test_admin_historial_filtra_pedidos_por_fecha -q`

Expected: FAIL because the current panel renders every current-day order in a text block and has no history selector.

- [ ] **Step 3: Write minimal implementation**

```html
<section class="pedidos-hoy">
  <h2>Pedidos pendientes para hoy (N)</h2>
  <div class="pedido-hoy">… <button class="btn-enviar-recibo" data-id="…">Enviar recibo</button></div>
</section>
<section class="historial-pedidos">
  <label for="fecha-historial-pedidos">Historial por fecha</label>
  <input id="fecha-historial-pedidos" type="date" value="YYYY-MM-DD">
  <div id="historial-pedidos">…</div>
</section>
```

Usar `fecha_pedidos` como query string con una fecha ISO validada, volver a cargarla al cambiar el selector y renderizar la fecha elegida. El botón confirma la acción, invoca el endpoint y recarga la página solo después de éxito. Mostrar estado explícito para pedido pendiente, recibo enviado o detalle histórico incompleto.

- [ ] **Step 4: Run focused tests**

Run: `./.venv/bin/pytest tests/test_app_admin_clientes.py -q`

Expected: PASS.

### Task 4: Verificación integrada y ejecución local

**Files:**
- Modify: `supabase/schema.sql` only if the migration needs an idempotent adjustment identified by tests.
- Test: `tests/test_app_pedidos.py`, `tests/test_recibos.py`, `tests/test_app_admin_clientes.py`, `tests/test_app_landing.py`, `tests/test_entregas.py`

**Interfaces:**
- Consumes: todas las interfaces de Tasks 1-3.
- Produces: migración lista para Supabase y servidor local accesible.

- [ ] **Step 1: Run the complete test suite**

Run: `./.venv/bin/pytest -q`

Expected: PASS with no failures.

- [ ] **Step 2: Validate source formatting**

Run: `git diff --check`

Expected: exit code 0.

- [ ] **Step 3: Start local server**

Run: `./.venv/bin/uvicorn web.app:app --host 127.0.0.1 --port 8000`

Expected: `Uvicorn running on http://127.0.0.1:8000`.

- [ ] **Step 4: Verify admin route responds locally**

Run: `curl -I http://127.0.0.1:8000/admin/clientes`

Expected: HTTP 200 or authenticated panel login response.
