# Ganancia en USD y panel integrado — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native execution, or superpowers:subagent-driven-development if selected by the user. Steps use checkbox syntax.

**Goal:** Integrar Cotización del dólar y Ganancia dentro del panel, mostrar saldos por vía de pago y reconstruir ganancias netas históricas en USD.

**Architecture:** Mantener FastAPI, Supabase y el panel HTML/JS existente. Separar cálculo financiero puro, persistencia idempotente, conciliación histórica y componentes del panel. Los importes originales y su evidencia permanecen privados; la sección muestra solamente USD.

**Tech Stack:** Python, Decimal, FastAPI, PostgreSQL/Supabase, HTML/CSS/JavaScript, pytest y Playwright.

**Spec:** `docs/superpowers/specs/2026-10-20-ganancias-usd-y-saldos-pago.md`

## Global Constraints

- Acceso exclusivo del administrador, adaptado al celular.
- Todos los importes financieros de esta sección se muestran en USD; las monedas de origen se conservan internamente como evidencia.
- Un costo ausente nunca se trata como cero.
- Los pendientes no se suman como ganancia confirmada.
- No modificar recibos originales ni reenviar correos al reconstruir el historial.
- No restar además los movimientos de entrega cubiertos por ese mismo pago.
- Mantener la vista local con datos simulados.
- Cotización del dólar y Ganancia se abren dentro del panel existente, sin pestañas nuevas.
- Conservar los cambios actuales de precios/fotos y los archivos pendientes del usuario.

## Review Focus

1. Cotización histórica ausente: registro pendiente, nunca conversión silenciosa al cambio actual (tareas 3 y 5).
2. Reenvíos, doble toque y reimportación: una sola operación económica por fuente (tareas 3–5).
3. Venta importada y recibo del mismo pedido: conciliación explícita sin doble ingreso (tarea 5).
4. Pagos agrupados, anticipos y anulaciones de Alejo: gasto efectivo una sola vez (tareas 3–5).
5. Pago mixto con valores inválidos o redondeos: título y campo coinciden sin sobrescribir montos manuales (tarea 1).

## Secuencia

Los tres componentes son entregables independientes: tarea 1 (pagos), tarea 2 (navegación/cotización), tareas 3–6 (ganancia). Comprobar y guardar cada uno por separado.

### Tarea 1: saldo visible por vía de pago

**Files:** modificar `web/ui/entregas_pago.js.html`; ampliar `tests/browser/entregas_pagos.py`.
**Interfaces:** `saldoParaMetodo(opcion, seleccion, totalUsd): number|null`; consume `datos.opciones` y valores actuales; produce el mismo monto para el título de alternativa y el autocompletado.

- [ ] Escribir prueba: total 500, contado 450; alternativas USD USA=52, USDT=51, ARS=75000 y transferencia=77320 con cotización 1500. Al seleccionar transferencia, campo=77320 editable; título coincide. Probar deselección, pagos inválidos y saldo cero.
- [ ] Ejecutar `.venv/bin/python -m pytest tests/browser/entregas_pagos.py -q` y observar el fallo esperado.
- [ ] Centralizar conversión/redondeo del saldo; opciones seleccionadas muestran su importe asignado, las demás el saldo. Reutilizar esa función al seleccionar métodos; mantener validación del total y autoguardado de precio.
- [ ] Repetir pruebas de navegador con cámara simulada y pagos mixtos; comprobar ambos temas y móvil.
- [ ] Commit solamente de este componente.

### Tarea 2: navegación integrada y cotización

**Files:** crear `web/ui/admin_secciones.html`, `web/ui/admin_secciones.js.html`, `web/ui/admin_secciones.css.html`; modificar `web/app.py`, `web/ui/cotizacion.html`; ampliar `tests/test_admin_cotizacion.py`; crear `tests/browser/admin_secciones.py`.
**Interfaces:** `abrirSeccionAdmin(nombre)` con `pedidos`, `cotizacion`, `ganancia`; secciones dentro de `/admin/clientes`, hash navegable y mismo encabezado. Reutilizar POST `/admin/cotizacion` sin cambiar persistencia.

- [ ] Pruebas de navegación dentro del panel, Atrás/Adelante, recarga con hash, cotización numérica y acceso sin sesión denegado. La ruta antigua debe llevar a `/admin/clientes#cotizacion`.
- [ ] Ejecutar pruebas nuevas y confirmar fallos.
- [ ] Extraer el formulario de cotización como componente del panel; reutilizar estilos y sesión. Mostrar Ganancia con estado de carga y error explícito mientras consulta el servicio, sin totales ficticios.
- [ ] Verificar teclado móvil, guardado, navegación y ausencia de pestañas nuevas.
- [ ] Commit de la integración.

### Tarea 3: libro privado y cálculo en USD

**Files:** crear `supabase/migrations/20261020_ganancia.sql`, `web/ganancia.py`, `tests/test_ganancia.py`; actualizar `supabase/schema.sql` y `tests/fakes_supabase.py`.
**Interfaces:** `calcular_venta(pedido, costos, comisiones): dict`; `convertir_usd(monto, moneda, cotizacion): Decimal|None`; `registrar_movimiento(client, movimiento): dict`; `resumen(client, desde, hasta): dict`.

- [ ] Pruebas: venta 500, costo 400, comisión comprobada 5 -> margen 95; gasto separado Alejo 10 -> neto del período 85. Cobro ya neto no descuenta otra comisión; costo/cambio ausente produce pendiente. Repetir misma fuente no duplica.
- [ ] Ejecutar `.venv/bin/python -m pytest tests/test_ganancia.py -q` y confirmar fallos.
- [ ] Crear tabla `ganancia_movimientos`: UUID, fuente_tipo/fuente_id únicos, fecha_operacion, tipo, concepto, ingreso_usd, costo_usd, comision_usd, gasto_usd, estado_evidencia, evidencia JSONB privada, version_calculo, anulado_en, creado_en. Usar numeric, no floats para cálculo. RLS sin políticas públicas. Tabla privada de revisiones para correcciones y anulaciones; operación transaccional con control de versión.
- [ ] Implementar cálculo Decimal, resumen con confirmados/estimados separados y conteo de pendientes. Límites de fecha inclusivos en America/Argentina/Cordoba. Mantener pérdidas negativas.
- [ ] Probar restricciones reales de SQL cuando haya una base de prueba; no aplicar migración a producción durante desarrollo. Comprobar autenticación y ausencia de costos en APIs públicas.
- [ ] Commit del modelo y cálculo.

### Tarea 4: captura de operaciones nuevas

**Files:** modificar `web/app.py`, `web/pedidos.py`, `web/saldo_cadete.py`; crear `web/ganancia_servicio.py`, `tests/test_ganancia_integracion.py`; revisar la carga administrativa existente sin sobrescribir sus cambios pendientes.
**Interfaces:** `capturar_costos(client, pedido_id, costos, fuente): None`; `conciliar_venta(client, pedido_id): dict`; `conciliar_pago_cadete(client, pago_id, cotizacion): dict`.

- [ ] Pruebas: guardar costo exacto por producto/cantidad en carga web y administrativa; edición USD cambia ingreso, no costo. Emitir y reenviar conserva un registro; fallo de correo no crea ingreso confirmado. Pago Alejo con anticipo se registra una vez; movimientos cubiertos no agregan gastos duplicados.
- [ ] Confirmar fallos de las nuevas pruebas.
- [ ] Guardar evidencia de costo en almacenamiento privado asociado al pedido (no dentro de JSON público del recibo). Registrar cotización del desembolso de Alejo. Conciliar tras confirmación de emisión y tras pago; conservar operaciones pendientes de conciliación si falla el libro, sin reenviar correos.
- [ ] Verificar proveedores exactos, promociones con costo desconocido, errores parciales y reintentos.
- [ ] Commit de captura automática.

### Tarea 5: reconstrucción histórica e importación

**Files:** crear `web/ganancia_historial.py`, `scripts/reconstruir_ganancias.py`, `tests/test_ganancia_historial.py`; consultar `web/historial_importado.py` y archivos de `outputs` como evidencia de solo lectura.
**Interfaces:** `preparar_historial(recibos, importados, pagos_cadete, fuentes_costos, fuentes_cambio): dict`; `importar_historial(client, informe): dict`. CLI con `--dry-run` por defecto y `--apply` explícito; reporte local JSON.

- [ ] Pruebas de recibos faltantes, números no correlativos, importación duplicada, productos ambiguos, cambios de precio/proveedor, costo documentado versus aproximado, moneda/cotización desconocida, pagos legacy y anticipos.
- [ ] Confirmar fallos antes de implementar.
- [ ] Inventariar todas las páginas de datos y primera fecha disponible. Emparejar costos por identidad exacta y fecha documentada; no tomar fecha de modificación del archivo como prueba de vigencia. Conciliar venta importada/recibo y pagos reconstruidos/efectivos. Casos ambiguos quedan pendientes con motivo.
- [ ] Generar informe con cobertura, fuentes, duplicados, confirmados, estimados y pendientes. Importador idempotente con registros auditables; no cambia comprobantes originales.
- [ ] Verificar importación repetida sin cambios y suma del informe versus libro. Preparar la carga histórica solicitada; aplicarla únicamente con esquema y destino de producción verificados, sin tocar datos reales desde la demo.
- [ ] Commit de conciliación/importación.

### Tarea 6: sección Ganancia y carga manual

**Files:** crear `web/ganancia_routes.py`, `web/ui/ganancia.html`, `web/ui/ganancia.js.html`, `tests/test_ganancia_routes.py`, `tests/browser/ganancia.py`; modificar integración de `web/app.py` y `web/README.md`.
**Interfaces:** GET `/admin/ganancia?desde=YYYY-MM-DD&hasta=YYYY-MM-DD`; POST `/admin/ganancia/manual` (clave idempotencia, fecha, concepto, tipo ingreso/gasto, monto_usd); PATCH `/admin/ganancia/manual/{id}` (versión y corrección/anulación auditada). Todos exigen sesión admin.

- [ ] Pruebas de filtros, USD exclusivo, importes/fechas inválidos, doble toque, pérdida negativa, edición concurrente y autorización; la suma estimada nunca se presenta como confirmada.
- [ ] Confirmar fallos.
- [ ] Implementar sección dentro de la app con total neto, desglose, estados de evidencia y detalle de movimientos. Formularios móviles para ingreso/gasto y corrección; tecla decimal. Etiquetar fechas de ventas y desembolsos. Mostrar qué falta completar en cada pendiente.
- [ ] Completar demo local con datos ficticios y errores recuperables de API. Probar en móvil y escritorio, filtros y navegación integrada.
- [ ] Ejecutar `.venv/bin/python -m pytest tests -q` y pruebas de navegador afectadas. Revisar diff y acceso privado. Documentar migración, conciliación y recuperación de fallos.
- [ ] Commit final del panel; conservar la rama para revisión local. No mezclar automáticamente en staging/main por la autorización de una entrega anterior.

## Revisión del plan

Cobertura: pagos (1), integración móvil y cotización (2), USD/evidencia/descuentos/comisiones (3), eventos nuevos y Alejo (4), reconstrucción desde primer registro e idempotencia (5), filtros/manuales y validación final (6). Las cinco condiciones de revisión tienen pruebas asignadas. Las interfaces del libro separan dinero original privado de valores USD mostrados.
