# Web de consulta (chat) — THE TECH ROOM ARG

Chat local que responde consultas de clientes usando el listado de precios.

## Configuración (una vez)

1. Instalar dependencias:
   ```bash
   ./.venv/bin/pip install -r requirements.txt
   ```
2. Copiar `web/.env.example` a `web/.env` y pegar la API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

## Cada vez que actualizás precios

Generar el `productos.json` desde el `entrada.json` del pipeline + la cotización del día:
```bash
./.venv/bin/python web/generar_datos.py entrada.json 1540 web/productos.json
```

## Cotización desde el panel

En **Pedidos y recibos** o **Clientes**, entrar a **Cotización del dólar**.
El formulario integrado `/admin/clientes#cotizacion` (la ruta antigua redirige) requiere la sesión de administrador, ofrece
teclado numérico móvil y acepta pesos enteros positivos, sin separadores.
Al guardar, las siguientes consultas del catálogo y del carrito usan el nuevo
valor para pesos y transferencia. Las páginas ya abiertas deben recargarse.
También se usa en los nuevos correos de pedido y en el cálculo de cobros.

La cotización manual se guarda atómicamente en `cotizacion-admin.json`, junto a
`PRODUCTOS_PATH`; puede configurarse otra ubicación con `COTIZACION_PATH`.
En Railway esa ubicación **debe estar dentro del volumen persistente** y staging
debe usar un volumen separado del de producción. No compartir este archivo entre
ambientes ni usar discos independientes para réplicas del mismo servicio.
La cotización manual tiene prioridad sobre posteriores publicaciones del
catálogo; los archivos originales y sus hashes no se modifican. Si todavía no
se guardó una cotización manual, se mantiene el comportamiento anterior.

Verificación local:
```bash
./.venv/bin/python -m pytest tests -q
./.venv/bin/python tests/browser/admin_cotizacion.py
```

## Corrección del precio y fotos del recibo

Desde **Enviar recibo**, el administrador puede corregir el precio unitario
en USD de cada producto. Se guarda automáticamente al terminar de escribir
o salir del campo; **Guardar precios** permite guardarlo o reintentarlo manualmente. Se conservan cantidades,
descuentos y precios del catálogo; se actualizan el pedido y las cinco
alternativas de pago. Se conserva el método seleccionado y su importe total
se recalcula. En pagos combinados se conservan los importes manuales y se
recalcula el saldo automático, si lo había; se debe revisar que cubran el nuevo total.
Una edición pendiente impide enviar el recibo. Los cambios desde otra pestaña
se detectan y requieren volver a abrir el formulario.

La edición se bloquea cuando comienza la emisión o ya hay un cobro registrado,
incluidos los reintentos tras un fallo de correo, para conservar el importe
del recibo reservado.

**Agregar foto**, debajo de los pagos, ofrece **Sacar foto** y **Elegir de la
galería**. La cámara requiere HTTPS y permiso del navegador; captura en memoria,
sin descargar ni guardar una copia en la galería. Las fotos se pueden quitar
antes de enviar y se adjuntan al PDF/correo mediante el almacenamiento existente.
El límite sigue siendo diez imágenes. La cámara se apaga al capturar, cerrarla
o salir del formulario. Si el permiso falla, la galería sigue disponible.

Prueba del flujo con cámara simulada y correo interceptado:
```bash
./.venv/bin/python -m pytest tests/browser/recibo_precios_fotos.py tests/browser/entregas_pagos.py -q
```

## Levantar el chat

```bash
./.venv/bin/uvicorn web.app:app --reload --port 8000
```
Abrir en el navegador: http://localhost:8000
(El micrófono funciona en Chrome/Edge.)


## Ganancia privada en USD

El panel `/admin/clientes#ganancia` comparte navegación y sesión con Pedidos y
Cotización. Ofrece filtros inclusivos de fecha argentina, ingresos/gastos
manuales, correcciones con control de versión y anulaciones auditadas. Los
importes mostrados son USD. Confirmados y estimados se suman por separado;
pendientes incompletos se excluyen y permiten completar datos con motivo.

Antes de desplegar esta versión aplicar `supabase/migrations/20261020_ganancia.sql`
en la base de destino verificada. La migración no se ejecuta automáticamente.
Las tres tablas y sus RPC están restringidas a service_role; costos y evidencia
no se agregan al detalle público de pedidos ni a los recibos.

Los costos se capturan al cargar pedidos. Cambios de costo al anexar productos
se conservan como conflictos pendientes, nunca se sustituyen silenciosamente.
Pedidos con costos conocidos no se fusionan automáticamente al reprogramarlos.
El recibo aceptado por el proveedor de correo genera una venta idempotente;
esto no acredita entrega del correo. Cada pago efectivo a Alejo captura su
cotización y se descuenta una vez, incluido el anticipo. Los movimientos que
cubre ese pago no vuelven a deducirse. Los gastos se imputan en su fecha de pago.

Reconstrucción: `python -m scripts.reconstruir_ganancias --dry-run --salida /ruta/privada/informe.json`
consulta todas las páginas sin escribir ni reenviar correos. `--fuentes` admite
JSON `{ "costos": [{"fecha":"YYYY-MM-DD","fuente":"referencia", "costos":{}}], "cambios":{}}`.
Los cambios se identifican por ID del pago a Alejo. `aproximacion_actual: true`
permite usar una lista actual como referencia para ventas antiguas sin otra
lista; siempre queda estimado, con evidencia explícita. Sin detalle/costo o
cotización verificable, el histórico permanece pendiente. La identidad de un
legacy sólo se concilia con un pedido mediante vínculo explícito, nunca por
coincidencia de nombre o monto. Los legacy sin vínculo se excluyen de totales.

`--apply` importa idempotentemente después de verificar el esquema. Repetir no
pisa correcciones ni rellena silenciosamente pendientes; completar desde el
panel conserva la evidencia anterior en ganancia_revisiones. El informe se
guarda privado (0600), y no debe versionarse ni exponerse como archivo público.
Si falla la captura financiera después de enviar un recibo o pagar, se registra
el error: recuperar con `ganancia_servicio.conciliar_venta` o
`conciliar_pago_cadete`, sin repetir el envío o el pago original.

Validación: tests/test_ganancia*.py, tests/browser/admin_secciones.py y
`tests/sql/ganancia.sql` (sólo base PostgreSQL temporal vacía). La demo local usa
FakeSupabaseClient, datos ficticios y correo desactivado; no es la base real.
