# Landing pública con carrito y cierre por WhatsApp — Diseño

**Fecha:** 2026-08-17
**Branch:** web-ttra

## Objetivo

Reemplazar el chat como página principal (`/`) por una landing pública (sin login) con
botones por sección, una grilla de productos por sección, y un carrito de compras que
vive en el navegador. Al cerrar el pedido, se genera un mensaje de WhatsApp precargado
con el detalle y los 3 precios (U$D / pesos / transferencia), sin pasar por ninguna
cuenta ni checkout propio.

Este diseño reemplaza el rol de `/` (antes el chat) construido en una iteración previa;
mantiene intacto (sin enlazar) todo lo ya construido de login/registro/catálogo con tabs,
por si se retoma más adelante.

## Alcance (v1)

- Landing pública en `/`: header, carrousel de marcas (RobCo/CRT, ya existente), 5
  botones grandes de sección (Celulares, Accesorios Celulares, Tablets, Notebooks y
  Macbooks, Gaming), grilla de productos de la sección elegida.
- Cada producto tiene un botón "Agregar al carrito 🛒"; cada click suma una unidad.
- Carrito visible como panel deslizable (ícono con contador en el header), con
  cantidad +/- y quitar por ítem, subtotal, y botón "Cerrar pedido por WhatsApp".
- Carrito persiste solo en `localStorage` del navegador (clave `ttra_carrito`),
  identificado por el nombre del producto. No hay backend de carrito.
- El botón de WhatsApp arma el mensaje con cada ítem (nombre, cantidad, precio U$D
  unitario) y el total en las 3 formas (U$D / pesos contado / transferencia), y abre
  `https://wa.me/543512145217?text=...` con ese texto precargado (mismo número que ya
  usa `web/reglas.py`).
- `GET /api/catalogo` deja de exigir sesión — pasa a ser pública (ya no hay cuenta en
  el flujo principal).
- El chat viejo (`web/static/styles.css`, `web/static/chat.js`) y el login/registro/
  `/catalogo` con tabs quedan en el repo sin enlazar desde la landing — no se borra
  nada de eso.

Fuera de alcance: checkout propio (pagos, envío), persistencia de carrito en backend,
login para navegar o comprar, edición del pedido después de enviado por WhatsApp.

## Arquitectura

### a) Frontend — `web/static/index.html` (reemplaza el contenido actual)

Se convierte en la landing: header con carrousel de marcas (reutiliza el patrón ya
construido en `catalogo.html`/`catalogo.css`), fila de 5 botones de sección, grilla de
productos, panel de carrito deslizable. Usa `theme.css` y `boot.js` ya existentes (boot
sequence una vez por sesión, tema RobCo/CRT).

Archivos nuevos: `web/static/landing.css`, `web/static/landing.js`.
El `styles.css`/`chat.js` viejos quedan sin `<link>`/`<script>` en `index.html`.

### b) Carrito — dentro de `landing.js`

- Estado: array `[{nombre, usd, pesos, transferencia, cantidad}]` en
  `localStorage["ttra_carrito"]`.
- Funciones: `agregarAlCarrito(producto)`, `cambiarCantidad(nombre, delta)`,
  `quitarDelCarrito(nombre)`, `totales()` (suma usd/pesos/transferencia según
  cantidad de cada ítem), `renderCarrito()`.
- El contador del ícono de carrito se actualiza en cada cambio.

### c) Checkout por WhatsApp

Función `armarMensajeWhatsapp(carrito)` que arma un texto tipo:

```
Hola! Quiero encargar:
- iPhone 15 128GB x1 — U$D 650
- Cargador Apple 20W x2 — U$D 60

Total: U$D 710 · $ 1.104.500 contado · $ 1.137.850 transferencia
```

y abre `https://wa.me/543512145217?text=` + `encodeURIComponent(mensaje)` en una
pestaña nueva. No se limpia el carrito automáticamente al abrir WhatsApp (el cliente
puede haberse arrepentido de cerrar); se limpia con un botón aparte "Vaciar carrito".

### d) Backend — `web/app.py`

- `GET /api/catalogo`: se elimina el chequeo `_sesion_activa` — responde igual
  (secciones + fallback de "actualizando precios") sin requerir sesión.
- Nada más cambia: `/login`, `/registro`, `/logout`, `/catalogo` (con tabs) siguen
  existiendo y funcionando igual, solo que no hay ningún link hacia ellos desde la
  landing nueva.

## Testing

- Backend: actualizar los tests que hoy asumen 401 sin sesión en `/api/catalogo`
  (`tests/test_app_catalogo.py`) para reflejar que ahora es pública; el resto de los
  tests de auth (login/registro/logout, `/catalogo` con tabs) no cambian.
- Frontend: sin tests automáticos (es UI + localStorage). Verificación manual:
  levantar el server, elegir una sección, agregar productos al carrito, subir/bajar
  cantidad, quitar un ítem, y confirmar que "Cerrar pedido por WhatsApp" abre
  `wa.me` con el texto correcto (nombre, cantidades, y los 3 totales).
