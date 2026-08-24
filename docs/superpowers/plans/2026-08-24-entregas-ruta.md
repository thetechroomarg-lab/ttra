# Entregas y Ruta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Guardar direcciones de checkout y administrar una ruta diaria reordenable con tareas manuales.

**Architecture:** `pedidos` conserva la dirección y orden de pedidos web; `tareas_entrega` almacena tareas administrativas con fecha, texto, dirección y orden. El panel combina ambas fuentes por fecha y persiste cada cambio de orden. Google Maps recibe una consulta URL-encoded, sin API externa.

**Tech Stack:** FastAPI, Supabase/Postgres, HTML/CSS/JavaScript nativo.

## Tasks

### Task 1: Persistencia de dirección y tareas
- [ ] Agregar `direccion_entrega` y `orden_entrega` a `pedidos`, crear `tareas_entrega` e índices por fecha/orden en `supabase/schema.sql`.
- [ ] Añadir pruebas para guardar dirección, crear tarea y actualizar orden.
- [ ] Implementar helpers en `web/pedidos.py` y los endpoints admin autenticados.

### Task 2: Checkout
- [ ] Añadir el campo obligatorio `Especificá dirección de entrega` al carrito.
- [ ] Enviar y validar `direccion_entrega` en `PedidoIn` y `/api/pedidos`.
- [ ] Probar que un pedido sin dirección es rechazado y que la dirección se persiste.

### Task 3: Ruta diaria
- [ ] Renderizar pedidos y tareas en una sola lista diaria con botón `Direcciones` que abre Google Maps.
- [ ] Agregar formulario de tarea manual con fecha, título, nota y dirección opcional.
- [ ] Implementar drag and drop con Pointer Events para desktop y mobile; guardar el orden en backend.
- [ ] Probar creación, reordenamiento y enlace de mapas.

### Task 4: Verificación
- [ ] Ejecutar `pytest -q`, `git diff --check` y una prueba manual de mobile/desktop.
