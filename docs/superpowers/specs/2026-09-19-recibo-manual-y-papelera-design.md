# Recibo Manual desde Nota y Papelera de Borrados - Diseño

## Objetivo

Resolver dos problemas del panel de cadete detectados en uso real:

1. El cadete puede quedarse sin forma de emitir un recibo si borra por error el pedido asociado (caso real ocurrido). Se necesita una vía de recibo que no dependa de que exista una fila viva en `pedidos`.
2. Hoy el borrado de pedidos y tareas/notas es definitivo e irreversible. Se necesita una papelera temporal (48hs) donde admin y cadete puedan ver y, si hace falta, deshacer un borrado.

## Alcance

### Recibo manual desde nota

- Las notas del cadete (tabla `tareas_entrega`, sin cambios en su naturaleza) ganan un botón `Recibo` en su tarjeta, visible siempre (nota nueva o vieja).
- Al tocarlo se abre un panel de generación de recibo, standalone y no ligado a la tabla `clientes` ni a `pedidos`:
  - Nombre del cliente (texto libre).
  - Email del cliente (texto libre, requerido para el envío).
  - Buscador de ítems con autocompletado en vivo contra el catálogo real de productos. Al elegir un ítem se agrega una línea con su nombre y precio en USD precargado; el precio es editable.
  - Puede agregar múltiples ítems (múltiples líneas).
  - Carga de hasta 10 fotos (mismo límite de 2,5MB por foto que ya usa el recibo de pedidos).
  - Botón `Enviar`: genera el PDF, lo manda por email a la dirección cargada, y persiste el registro.
- Si la nota ya tiene un recibo manual enviado, el botón pasa a decir `Reenviar recibo` (mismo patrón que ya usa el recibo de pedidos).
- Reutiliza `recibos.pdf_recibo()` / `recibos.html_recibo()` armando un objeto "pedido-like" en memoria a partir de los ítems cargados, para que el PDF salga con el mismo formato que el recibo de un pedido normal.
- Permisos: mismo esquema que ya rige sobre las notas — el cadete solo puede operar sobre las suyas (`asignado_a` = su slug), el admin sobre todas.

### Papelera de borrados

- El borrado de pedidos y de tareas/notas deja de ser definitivo: pasa a ser un soft-delete con marca de quién y cuándo.
- Toda fila borrada es visible en una papelera durante 48hs desde el borrado, con opción de restaurar (vuelve a aparecer en las listas normales, igual que estaba).
- Pasadas las 48hs, la fila se purga (hard-delete real) y deja de ser recuperable.
- El admin ve en su papelera todo lo borrado (pedidos + tareas/notas, de cualquier cadete). El cadete ve solo lo que tenía asignado o que él mismo borró.
- Cada elemento de la papelera muestra: qué es (pedido o nota), a quién pertenece/título, quién lo borró, cuándo, y cuánto tiempo falta para que se purgue.
- CTA nuevo `Borrados` en el menú de admin (junto a "Clientes" y "Pedidos y recibos") y en el menú de cadete (junto a "Cerrar sesión"), cada uno apuntando a su propia vista de papelera.

## Fuera de Alcance

- El recibo manual no crea ni modifica filas en `pedidos` ni en `clientes` — es un registro aparte (`recibos_manuales`), no un "pedido encubierto".
- No hay recálculo de cantidades por ítem: cada línea es un ítem con un precio editable; para representar más de una unidad, se ajusta el precio de esa línea.
- La purga de la papelera no usa un cron/job en background — no hay infraestructura de tareas programadas en el proyecto. Se purga de forma perezosa: cada vez que se consulta una papelera (admin o cadete), el backend borra primero (hard-delete) lo que ya superó las 48hs, y devuelve el resto. En el peor caso (nadie abre la papelera por días), las filas vencidas quedan invisibles para todos los listados igual, porque todos los queries activos ya filtran `borrado_en IS NULL`; solo se demora la purga física, sin efecto visible.
- No se agrega un histórico permanente de borrados más allá de las 48hs — pasado ese plazo, el dato se pierde, tal como se especificó.
- No se toca el recibo de pedidos existente (`POST /admin/pedidos/{id}/recibo`): sigue funcionando exactamente igual.

## Modelo de Datos

### `pedidos` y `tareas_entrega` (columnas nuevas en ambas)

- `borrado_en timestamptz` (nullable, `NULL` = activo).
- `borrado_por text` (nullable, quién ejecutó el borrado: "Vlad" o el slug/nombre del cadete).

Todos los `SELECT` que listan pedidos o tareas activos en el panel (admin y cadete) agregan el filtro `borrado_en IS NULL`.

### Tabla nueva `recibos_manuales`

- `id uuid` (PK)
- `tarea_id` (FK a `tareas_entrega`)
- `nombre_cliente text`
- `email_cliente text`
- `items jsonb` — arreglo de `{nombre, precio_usd}`
- `total_usd numeric` — suma de los ítems
- `fotos_series text[]` — mismo patrón de storage que usa `pedidos.fotos_series`
- `recibo_id text unique`
- `creado_por text`
- `creado_en timestamptz`
- `enviado_en timestamptz` (nullable hasta el primer envío exitoso)

## Flujo

### Recibo manual

1. El cadete abre una nota y toca `Recibo`.
2. El panel carga el catálogo (mismo dataset que ya usa `/api/catalogo`) para el autocompletado de ítems.
3. El cadete completa nombre, email, agrega ítems (cada uno autocompleta precio USD, editable) y opcionalmente fotos.
4. Al tocar `Enviar`, el frontend llama a `POST /admin/tareas-entrega/{tarea_id}/recibo-manual`.
5. El backend valida sesión (cadete dueño de la nota, o admin), arma un objeto "pedido-like" con los ítems y el total, genera el PDF con `recibos.pdf_recibo()`, lo envía por email con `enviar_email()`, y si el envío tiene éxito persiste el registro en `recibos_manuales` con `enviado_en`.
6. Si el email falla, no se persiste como enviado y se devuelve el error igual que hace hoy el recibo de pedidos (`EnvioEmailError`).

### Papelera

1. Borrar un pedido o una tarea deja de ser `DELETE`: los endpoints `DELETE /admin/pedidos/{id}` y `DELETE /admin/tareas-entrega/{id}` pasan a hacer `UPDATE` seteando `borrado_en = now()` y `borrado_por = <quién está logueado>`.
2. `GET /admin/papelera` (solo admin): purga lo vencido (>48hs), luego devuelve pedidos + tareas con `borrado_en` no nulo, de cualquiera.
3. `GET /admin/cadete/papelera` (solo cadete): mismo mecanismo de purga, filtrado a lo que el cadete tenía asignado o él mismo borró.
4. `POST /admin/papelera/{tipo}/{id}/restaurar` (`tipo` = `pedido` | `tarea`): limpia `borrado_en` y `borrado_por` de esa fila. Mismas reglas de permiso que el borrado (cadete solo sobre lo suyo, admin sobre todo).
5. Las vistas HTML de papelera (una para admin, una para cadete) reusan el mismo componente de tarjeta: qué es, a quién pertenece, quién y cuándo lo borró, cuánto falta para expirar, botón restaurar. Papelera vacía muestra un estado vacío simple, nunca un error.

## Seguridad y Errores

- Todos los endpoints nuevos requieren sesión de admin o cadete activa (mismo chequeo `_clientes_admin_activo` / `_cadete_activo` que ya usa el resto del panel).
- El cadete nunca puede restaurar ni ver en su papelera un pedido/nota que no era suyo, ni tocar `recibo-manual` de una nota ajena.
- El recibo manual no reutiliza datos de `clientes`: el nombre/email se cargan a mano en el panel, así que no hay riesgo de filtrar datos de otro cliente por error de vínculo.
- Si Resend falla al enviar el recibo manual, el registro no queda marcado como enviado y el cadete puede reintentar sin duplicar el `recibo_id`.
- La purga perezosa de la papelera no puede purgar antes de tiempo: solo actúa sobre filas con `borrado_en` de más de 48hs.
