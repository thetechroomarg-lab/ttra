# Web de catálogo con login — Diseño

**Fecha:** 2026-08-17
**Branch:** web-ttra

## Objetivo

Una web pública para clientes de THE TECH ROOM ARG, con login (usuario/contraseña, con
Gmail a agregar más adelante) y un catálogo dividido en 5 secciones, con tema oscuro y
estilo profesional/chic, y un carrousel rotativo de marcas debajo del header.

## Alcance (v1)

- Login con usuario/contraseña (nombre, email, password). **Gmail queda fuera de v1**,
  se agrega después sin romper el flujo de user/pass.
- Registro con formulario simple (nombre, email, password).
- Catálogo con 5 secciones, generadas a partir de `web/productos.json` (mismo dato que
  ya usa el chat):
  - **Celulares** — iPhone (nuevo y usado), Samsung, Xiaomi, Motorola, Realme, y
    teléfonos de otras marcas hoy perdidos en "Otros" (Oppo, Nokia, Infinix, Honor,
    Itel, celulares genéricos).
  - **Accesorios Celulares** — AirPods, Watch, cargadores, cables, AirTags, audio JBL,
    drone, cámara, extensores wifi, y cualquier producto de "Otros" que no matchee
    ninguna otra regla (default).
  - **Tablets** — iPad.
  - **Notebooks y Macbooks** — Mac (categoría `Mac`) + notebooks PC (categoría
    `Notebook`).
  - **Gaming** — consolas (PS5, Switch, R36S), volante Logitech.
- Carrousel rotativo con los nombres de marcas en estilo chic (texto, sin logos reales
  por ahora).
- Tema oscuro en toda la web (grafito/negro de fondo, acento dorado/cobre).

Fuera de alcance por ahora: login con Gmail, logos reales de marca, checkout/compra
(el catálogo muestra precios, la venta se sigue cerrando por WhatsApp como hoy),
recuperación de contraseña por email, panel de administración de usuarios.

## Arquitectura

Todo vive en el mismo proceso FastAPI (`web/app.py`) que ya sirve el chat — no se levanta
un servidor aparte.

### a) Autenticación — `web/auth.py`

- SQLite en `web/usuarios.db`, tabla `usuarios` (id, nombre, email único, password_hash,
  creado).
- Password hasheado con `bcrypt` (via `passlib`).
- Sesión: cookie firmada de Starlette (`SessionMiddleware`), no JWT — no hace falta a
  esta escala y evita el riesgo de guardar tokens en localStorage.
- Rutas: `GET/POST /login`, `GET/POST /registro`, `POST /logout`.
- Login inválido → mensaje genérico ("usuario o contraseña incorrectos"), nunca revela
  si el email existe. Registro con email duplicado → error claro sin crear duplicado.

### b) Mapeo de catálogo — `web/catalogo.py`

- Función `secciones_catalogo(productos)` que recorre `productos.json` y devuelve un
  dict `{seccion: [productos]}` con las 5 secciones de arriba.
- Reglas por categoría existente (`iPhone`→Celulares, `Mac`→Notebooks y Macbooks, etc.)
  más reglas por palabra clave sobre el `nombre` para lo que hoy cae en `Otros`
  (marcas de teléfono no reconocidas, gaming, accesorios). Todo lo que no matchea
  ninguna palabra clave cae en Accesorios Celulares por defecto.
- No se toca `bands.py` ni `consolidate.py` — el pipeline de precios sigue igual; este
  mapeo es una capa nueva solo para la web.

### c) Rutas protegidas

- `GET /catalogo`: página HTML, redirige a `/login` si no hay sesión activa.
- `GET /api/catalogo`: devuelve el JSON de las 5 secciones (usa `secciones_catalogo` +
  `productos.json`), protegida igual que `/catalogo`.
- Si `productos.json` no existe o está vacío, el catálogo muestra "Estamos actualizando
  los precios" en vez de romper (mismo criterio que ya usa `web/app.py` para el chat).

### d) Frontend

- `web/static/login.html` — formulario de login y de registro (toggle entre ambos),
  tema oscuro.
- `web/static/catalogo.html` + `catalogo.css` + `catalogo.js` — carrousel de marcas
  arriba (CSS puro, sin librerías externas), 5 secciones abajo navegables (tabs).
- Estilo: fondo grafito/negro, acentos dorado/cobre, tipografía elegante — consistente
  en login y catálogo.

## Testing

- `TestClient` de FastAPI: registro exitoso, registro con email duplicado, login
  correcto, login incorrecto, logout, `/catalogo` y `/api/catalogo` bloquean sin
  sesión y permiten con sesión.
- Test unitario de `secciones_catalogo` cubriendo casos ambiguos de "Otros" (Oppo, PS5,
  cargador Apple, drone) para confirmar que caen en la sección esperada.
