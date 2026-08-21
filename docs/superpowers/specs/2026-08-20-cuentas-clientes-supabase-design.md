# Cuentas de cliente unificadas + Supabase — Diseño

**Fecha:** 2026-08-20
**Branch:** web-ttra

## Objetivo

Hoy los datos de contacto de clientes viven en dos sistemas separados y sin relación:

1. **Leads** (`clientes.json` + `clientes.csv`, `web/leads.py`): nombre + celular
   capturados por el "gate" de la landing y por los pedidos de WhatsApp. Se guardan en
   el filesystem del contenedor, que Railway borra en cada deploy — hoy se puede estar
   perdiendo esta data sin que se note.
2. **Cuentas de mayoristas** (`usuarios.db`, SQLite, `web/auth.py`): email + password
   con bcrypt, usadas para dar acceso a `/catalogo`. No tiene ninguna relación con los
   leads de arriba — un mayorista puede existir dos veces (una como lead, otra como
   cuenta) sin que el sistema lo note.

El objetivo es unificar ambos en un solo registro de cliente por persona, sólido
(no se pierde en cada deploy), sin duplicados (garantizado por la base de datos, no por
revisión manual), usando Supabase (Postgres + Supabase Auth) como backend.

## Alcance (v1)

- Una sola cuenta de cliente por persona: nombre, apellido, celular, email, password —
  los 4 primeros son obligatorios para crear la cuenta.
- El registro/login reemplaza al "gate" actual: nadie navega el catálogo ni chatea sin
  antes crear cuenta o loguearse.
- Deduplicación real: `celular` y `email` son `UNIQUE` a nivel de base de datos. Intentar
  registrar un celular o email ya existente da error, no crea una fila nueva.
- Login/registro se maneja con Supabase Auth (no bcrypt casero) — deja la puerta abierta
  a agregar "Ingresar con Google" más adelante sin cambiar el modelo de datos.
- Historial de pedidos (WhatsApp) queda asociado al `cliente_id`, no a un array suelto
  dentro del registro.
- Migración de los dos sistemas actuales a la tabla nueva (ver sección Migración).
- El panel `/admin/clientes` pasa a leer de Supabase en vez de `clientes.json`.

Fuera de alcance por ahora: login con Google real (solo se deja la puerta abierta),
diferenciación de precios por `tipo_cliente`, recuperación de contraseña vía flujo
propio (usa el de Supabase Auth tal cual viene), panel de administración de cuentas más
allá de lo que ya existe en `/admin/clientes`.

## Arquitectura

### a) Modelo de datos (Supabase Postgres)

- `auth.users` (tabla nativa de Supabase Auth): maneja `email` y `password` de forma
  nativa, garantiza `email` único.
- `clientes` (tabla propia, `id` = `auth.users.id`, FK):
  - `nombre` (text, not null)
  - `apellido` (text, not null)
  - `celular` (text, not null, `UNIQUE`, normalizado a solo dígitos antes de guardar)
  - `tipo_cliente` (text, default `'minorista'`) — queda el campo para uso futuro, sin
    lógica de precios distinta en v1.
  - `creado_en`, `actualizado_en` (timestamps)
- `pedidos` (tabla nueva):
  - `id`, `cliente_id` (FK a `clientes.id`), `productos` (jsonb), `fecha`, `origen`
    (`whatsapp` | `chat`)
  - Reemplaza el array `productos[]` que hoy vive suelto dentro de cada registro de
    `clientes.json`.

### b) Autenticación — nuevo módulo `web/supabase_auth.py`

- Usa `supabase-py` (cliente oficial) contra el proyecto de Supabase.
- Registro: `supabase.auth.sign_up(email, password)` + insert en `clientes` con
  nombre/apellido/celular en la misma operación (si el insert en `clientes` falla por
  celular duplicado, se informa el error específico — Supabase Auth ya habrá creado el
  usuario de auth, así que hay que decidir si se hace rollback o se deja la cuenta de
  auth "húmeda" para reintentar; **se hace rollback** llamando a
  `supabase.auth.admin.delete_user` para no dejar cuentas de auth sin perfil).
- Login: `supabase.auth.sign_in_with_password(email, password)`.
- Sesión: se mantiene la misma `SessionMiddleware` de Starlette que ya existe — al
  loguear con éxito se guarda `request.session["cliente_id"]` (uuid de Supabase), no se
  expone el JWT de Supabase al frontend.
- `web/auth.py` (SQLite) se elimina una vez migrado.

### c) Endpoints (`web/app.py`)

- `POST /registro`: ahora requiere nombre, apellido, celular, email, password — pasa por
  `supabase_auth.registrar(...)`. Reemplaza al `POST /api/registro-cliente` del gate
  actual.
- `POST /login`, `POST /logout`: se adaptan a `supabase_auth`, mismo contrato de sesión
  que hoy.
- `GET /catalogo`, `GET /api/catalogo`: el chequeo de sesión pasa de
  `request.session["usuario_email"]` a `request.session["cliente_id"]`.
- La landing (`index.html`) pasa a requerir sesión igual que `/catalogo` — se cae la
  distinción actual entre "landing con gate liviano" y "catálogo con login fuerte".
- `POST /chat`: sigue funcionando igual pero el `cliente_id` de sesión reemplaza al
  `celular` como identificador de a quién pertenece la conversación.
- Pedido por WhatsApp (`registrarPedidoEnClientes` en `landing.js`): en vez de POST a
  `/api/registro-cliente` con celular, hace POST a un endpoint nuevo
  `POST /api/pedidos` que inserta en la tabla `pedidos` usando el `cliente_id` de la
  sesión activa (ya no depende de `localStorage.ttra_cliente`).
- `GET /admin/clientes`: pasa a hacer un `select` sobre `clientes` + `pedidos` en
  Supabase en vez de leer `clientes.json`.
- `web/leads.py` se elimina una vez migrado (`clientes.json`/`.csv` dejan de generarse).

### d) Frontend

- El gate actual (`#rc-gate`, `landing.js` líneas ~1-36) se reemplaza por un formulario
  de registro/login (mismo lugar en el flujo: aparece antes de poder ver productos),
  pidiendo nombre, apellido, celular, email, password — con toggle a "ya tengo cuenta"
  para loguearse en vez de registrarse.
- `web/static/login.html`/`catalogo.html` existentes (del sistema de mayoristas) se
  funden en este mismo formulario — deja de haber dos pantallas de login distintas.

### e) Migración de datos existentes

1. **`usuarios.db` (mayoristas)**: por cada fila, `supabase.auth.admin.create_user` con
   el email existente y una password aleatoria temporal + insert en `clientes` con
   `tipo_cliente='mayorista'`, `nombre`/`apellido` (si no hay apellido registrado, se
   deja vacío y se le pide completarlo en su primer login). Como el hash de bcrypt no es
   compatible con Supabase Auth, cada mayorista recibe un mail de "restablecé tu
   contraseña" (flujo nativo de Supabase) antes de poder loguearse por primera vez.
2. **`clientes.json`/`.csv` (leads)**: se importan como filas de `clientes` **sin**
   fila en `auth.users` todavía (quedan como "invitados", sin poder loguearse). Si en el
   futuro alguien se registra con el mismo **celular** (nunca por email — ver "Nota de
   seguridad" más abajo), el registro debe detectar la fila invitada existente y
   completarla (agregarle el `auth.users.id`) en vez de fallar por el `UNIQUE` de
   celular — esto es la única excepción al "UNIQUE bloquea todo" de arriba, y hay que
   implementarla explícitamente en el flujo de registro. Los pedidos ya asociados a ese
   lead se migran a la tabla `pedidos` con ese `cliente_id`.
3. La migración corre una sola vez, como script (`scripts/migrar_a_supabase.py`, fuera
   del código de producción), antes de deployar el nuevo flujo de auth.

## Manejo de errores

- Registro con celular/email duplicado (de una cuenta ya activa, no invitada): mensaje
  claro ("ese celular/email ya tiene una cuenta, iniciá sesión") — nunca crea fila
  duplicada.
- Falla de conexión a Supabase: la landing/catálogo debe degradar a un mensaje de
  "no pudimos conectar, probá de nuevo en un momento" en vez de un error 500 crudo —
  mismo criterio que ya usa `web/app.py` para `productos.json` faltante.
- Rollback de `auth.users` si el insert en `clientes` falla (ver sección Autenticación).

## Testing

- `TestClient` de FastAPI (mockeando el cliente de Supabase, no contra la instancia
  real): registro exitoso, registro con celular duplicado, registro con email
  duplicado, login correcto, login incorrecto, logout, acceso a landing/catálogo sin
  sesión (bloquea) y con sesión (permite).
- Caso especial: registro que "completa" un lead invitado existente (mismo celular)
  debe vincular en vez de fallar.
- Test del endpoint `POST /api/pedidos`: inserta correctamente asociado al `cliente_id`
  de sesión, rechaza si no hay sesión activa.
- Script de migración: correr contra una copia de `clientes.json`/`usuarios.db` de
  prueba y verificar conteo de filas migradas y que no haya duplicados por celular/email
  antes de correrlo contra los datos reales.

## Después de este plan

- **Dejar activada** la confirmación de email en Authentication → Settings del proyecto
  de Supabase (Email Auth → "Confirm email" — es el default de un proyecto nuevo, no
  hay que tocarlo). Es la única prueba real de que quien se registra es dueño del email
  que puso: si se desactiva, cualquiera podría registrarse con el email de un cliente
  existente. `web/cuentas.py` distingue este caso ("Confirmá tu email antes de
  ingresar") de una contraseña incorrecta, así que la UX no queda rota por dejarla
  activada — solo hay que avisarle al usuario que revise su bandeja de entrada.
- Configurar `SESSION_SECRET` (clave de firma de las cookies de sesión) como variable de
  entorno en Railway — sin esto, cualquiera que lea el código puede forjar una sesión de
  cualquier cliente.
- Configurar `ADMIN_CLIENTES_PASSWORD` como variable de entorno en Railway — sin esto, el
  panel `/admin/clientes` (que expone nombre/celular/pedidos de todos los clientes) usa
  una contraseña de desarrollo conocida.

## Nota de seguridad: por qué la vinculación de cuenta es solo por celular

La vinculación de una fila "invitada" (lead o mayorista migrado sin cuenta todavía) con
la cuenta real que se crea en `/registro` es **solo por celular, nunca por email**. El
email no prueba que quien se registra sea el dueño real de esa fila — cualquiera puede
escribir el email de otra persona en el formulario — así que usarlo como llave de
vinculación abriría una forma de apropiarse de la fila (nombre, celular, historial de
pedidos) de un cliente existente sin ninguna verificación real.

Por esto los mayoristas migrados (que no tenían un celular real en `usuarios.db`) **no**
se migran como filas "invitadas" esperando que se registren para vincularse: el script
de migración les crea una cuenta real de Supabase Auth desde el primer momento
(`auth.admin.create_user` + `auth.reset_password_for_email`, ver sección de Migración
arriba), así que nunca quedan en un estado que otra persona pueda reclamar.
