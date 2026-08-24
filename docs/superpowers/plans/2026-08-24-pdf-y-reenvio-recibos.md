# PDF y Reenvío de Recibos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir ver el PDF y reenviar recibos emitidos conservando su fecha original.

**Architecture:** Un módulo `web/recibos.py` generará el PDF desde la instantánea inmutable de `pedidos`. Los endpoints de administración validarán sesión y estado emitido; el email conservará `recibo_emitido_en` y actualizará solo el último envío. El historial mostrará acciones únicamente para recibos emitidos.

**Tech Stack:** FastAPI, Supabase, reportlab, Resend, pytest, Poppler.

**Spec:** `docs/superpowers/specs/2026-08-24-pdf-y-reenvio-recibos-design.md`

## Global Constraints

- El PDF no se almacena ni se expone por URL pública.
- Solo el administrador puede abrir o reenviar un recibo.
- Se usan únicamente los valores persistidos en el pedido.
- La fecha original `recibo_emitido_en` no cambia al reenviar.
- Escribir primero la prueba que falla antes de cada comportamiento nuevo.

---

### Task 1: Fecha original de emisión y reenvío seguro

**Files:**
- Modify: `supabase/schema.sql:25-46`
- Modify: `web/app.py:519-551`
- Test: `tests/test_app_admin_clientes.py`

**Interfaces:**
- Produces: columna nullable `pedidos.recibo_emitido_en` y `POST /admin/pedidos/{pedido_id}/recibo` que devuelve `reenviado`.

- [ ] **Step 1: Write the failing test**

```python
def test_reenviar_recibo_conserva_fecha_original(monkeypatch):
    pedido = pedido_emitido()
    original = pedido["recibo_emitido_en"]
    monkeypatch.setattr(appmod, "enviar_email", lambda *args: None)
    respuesta = admin.post(f"/admin/pedidos/{pedido['id']}/recibo")
    fila = pedido_por_id(pedido["id"])
    assert respuesta.json()["reenviado"] is True
    assert fila["recibo_emitido_en"] == original
    assert fila["recibo_enviado_en"] != original
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_app_admin_clientes.py::test_reenviar_recibo_conserva_fecha_original -q`

Expected: FAIL because the original issuance date is not persisted.

- [ ] **Step 3: Implement minimal persistence**

```python
emitido_en = pedido.get("recibo_emitido_en") or pedido.get("recibo_enviado_en") or ahora_iso
enviar_email(...)
client.table("pedidos").update({
    "recibo_id": recibo_id,
    "recibo_emitido_en": emitido_en,
    "recibo_enviado_en": ahora_iso,
}).eq("id", pedido_id).execute()
```

Add `alter table pedidos add column if not exists recibo_emitido_en timestamptz;` to the migration.

- [ ] **Step 4: Run focused test**

Run: `./.venv/bin/pytest tests/test_app_admin_clientes.py -q`

Expected: PASS.

### Task 2: Generador y endpoint PDF protegido

**Files:**
- Modify: `web/recibos.py`
- Modify: `web/app.py:519-551`
- Test: `tests/test_recibos.py`
- Test: `tests/test_app_admin_clientes.py`

**Interfaces:**
- Produces: `recibos.pdf_recibo(cliente, pedido) -> bytes` and `GET /admin/pedidos/{pedido_id}/recibo.pdf`.

- [ ] **Step 1: Write the failing tests**

```python
def test_pdf_recibo_contiene_datos_inmutables():
    pdf = recibos.pdf_recibo(cliente, pedido_emitido)
    assert pdf.startswith(b"%PDF")
    assert "TTRA-000001" in PdfReader(BytesIO(pdf)).pages[0].extract_text()

def test_pdf_recibo_requiere_admin_y_recibo_emitido(monkeypatch):
    assert anon.get(f"/admin/pedidos/{pedido_id}/recibo.pdf").status_code == 401
    assert admin.get(f"/admin/pedidos/{pedido_pendiente}/recibo.pdf").status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `./.venv/bin/pytest tests/test_recibos.py tests/test_app_admin_clientes.py::test_pdf_recibo_requiere_admin_y_recibo_emitido -q`

Expected: FAIL because no PDF generator or endpoint exists.

- [ ] **Step 3: Implement minimal PDF generation**

```python
def pdf_recibo(cliente, pedido):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    # Wordmark, ID, original date, rows, discounts, total and grouped warranties.
    pdf.save()
    return buffer.getvalue()
```

Use `reportlab.platypus` tables with a page header/footer; return `Response(pdf, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=recibo-<id>.pdf"})`. Reject missing detail or `recibo_enviado_en`.

- [ ] **Step 4: Render and inspect**

Run: `pdftoppm -png tmp/pdfs/recibo-prueba.pdf tmp/pdfs/recibo-prueba`

Expected: one legible page with no clipping or overlap.

### Task 3: Historial actions and verification

**Files:**
- Modify: `web/app.py:895-1060`
- Test: `tests/test_app_admin_clientes.py`

**Interfaces:**
- Consumes: emitted receipt fields and PDF endpoint.
- Produces: `.btn-ver-recibo-pdf` and `.btn-reenviar-recibo` only for emitted rows.

- [ ] **Step 1: Write the failing test**

```python
def test_historial_muestra_ojo_y_reenvio_solo_para_recibos_emitidos(monkeypatch):
    pagina = admin.get("/admin/clientes")
    assert 'class="btn-ver-recibo-pdf"' in pagina.text
    assert 'class="btn-reenviar-recibo"' in pagina.text
    assert 'data-id="pedido-pendiente"' not in acciones_de_historial(pagina.text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `./.venv/bin/pytest tests/test_app_admin_clientes.py::test_historial_muestra_ojo_y_reenvio_solo_para_recibos_emitidos -q`

Expected: FAIL because the history has no receipt action icons.

- [ ] **Step 3: Implement actions**

```html
<a class="btn-ver-recibo-pdf" target="_blank" href="/admin/pedidos/<id>/recibo.pdf">...</a>
<button class="btn-reenviar-recibo" data-id="<id>" title="Reenviar recibo">...</button>
```

The resend action confirms intent, invokes the existing receipt endpoint, and reloads only after success. Render `recibo_emitido_en` as the original issue date in the historical row.

- [ ] **Step 4: Run full verification and local check**

Run: `./.venv/bin/pytest -q && git diff --check`

Expected: all tests pass and no whitespace errors.
