# Recibos PDF con Evidencias Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generar recibos PDF sin solapamientos, con fotos de entrega y garantías completas resumidas.

**Architecture:** El generador convierte texto de tabla en párrafos ajustables y recibe bytes de evidencias. El endpoint reúne las fotos antes de emitir, y el visor histórico las descarga del bucket privado.

**Tech Stack:** FastAPI, Supabase Storage, ReportLab, pytest.

**Spec:** `docs/superpowers/specs/2026-08-24-recibos-pdf-design.md`

## Global Constraints

- Conservar imágenes de serie privadas y comprimidas en JPEG de hasta 2,5 MB.
- No permitir que texto largo invada otra columna.
- No alterar el número, fecha original ni adjunto PDF del recibo.

---

### Task 1: Tabla y garantías del PDF

**Files:**
- Modify: `web/recibos.py`
- Test: `tests/test_recibos.py`

- [ ] Escribir una prueba fallida que use un nombre sin espacios y compruebe que el PDF se genera con la garantía extensa correcta.
- [ ] Ejecutar `pytest tests/test_recibos.py -v` y confirmar el fallo.
- [ ] Convertir cada celda en `Paragraph`, usar columnas que entren en A4 y reemplazar garantías cortas por textos resumidos por familia.
- [ ] Ejecutar `pytest tests/test_recibos.py -v` y confirmar el pase.

### Task 2: Evidencias en emisión y visor histórico

**Files:**
- Modify: `web/app.py`
- Test: `tests/test_app_admin_clientes.py`

- [ ] Escribir una prueba fallida de emisión multipart con una foto JPEG y verificar que se pasa al generador PDF.
- [ ] Ejecutar `pytest tests/test_app_admin_clientes.py -k fotos -v` y confirmar el fallo.
- [ ] Leer y validar archivos antes de crear el PDF; guardarlos en el bucket, pasarlos al generador y descargarlos por ruta para el visor histórico.
- [ ] Ejecutar `pytest tests/test_app_admin_clientes.py -k 'recibo or pdf' -v` y confirmar el pase.

### Task 3: Verificación

**Files:**
- Test: `tests/test_recibos.py`, `tests/test_app_admin_clientes.py`

- [ ] Ejecutar `.venv/bin/pytest -q && git diff --check`.
- [ ] Commit: `feat: include delivery photos in receipt PDFs`.
