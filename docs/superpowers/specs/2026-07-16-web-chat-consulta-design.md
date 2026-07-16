# Web de consulta (chat) — Diseño

**Fecha:** 2026-07-16
**Branch:** idea-web

## Objetivo

Una web **local** (por ahora) con **solo un chat**, donde un cliente escribe o habla su
consulta, la IA (Claude API) la entiende por lenguaje natural, busca en el listado de
precios de THE TECH ROOM ARG y responde en **formato WhatsApp** con los 3 precios
(🇺🇸 U$D · 🇦🇷 pesos · 🏦 transferencia), **sin mostrar nunca el proveedor**.

## Alcance (v1)

- Chat de texto **y audio** (voz del cliente transcrita en el navegador).
- Corre **local** en la compu de Vladimir; se publica más adelante.
- El bot habla **solo de productos/precios**; si le preguntan otra cosa, redirige amable
  al catálogo.
- Si el producto no está: **una sola** recomendación de lo más parecido, sin insistir.
- Cierre de venta: deriva al **WhatsApp** de Vladimir (`wa.me/543512145217`).

Fuera de alcance por ahora: publicación online, integración directa con WhatsApp,
historial de conversaciones persistente, panel de administración.

## Arquitectura

Tres piezas:

### a) Datos — `productos.json`

Generado por el pipeline actual del listado (mismo origen que los CSV). Un array de
productos, cada uno con:

- `nombre` (limpio, sin marca duplicada, con colores si el proveedor los da)
- `categoria` / `subcategoria` (ej. Samsung/Celulares, Apple/iPhone)
- `usd`, `pesos`, `transferencia` (precios de venta ya con margen)
- `colores` (si están)
- `link_imagen`

**No incluye `proveedor`** — así es imposible que se filtre al cliente. Se regenera cada
vez que se actualiza el listado (5 proveedores + cotización).

### b) Backend (Python / FastAPI)

Servidor local que:

- Guarda la **API key de Claude** en variable de entorno (nunca en el navegador).
- Sirve la página del frontend.
- Expone un endpoint `POST /chat` que recibe `{mensaje, historial}`, arma el prompt para
  Claude con el `productos.json` + las **reglas del negocio** (formato WhatsApp, 3 precios,
  sin proveedor, una sola recomendación, derivar a WhatsApp, no inventar precios) y
  devuelve la respuesta.
- Reusa el venv y el código existente del proyecto.

### c) Frontend — página de chat

Una sola página HTML/JS:

- Burbujas de chat (cliente / bot).
- Campo de texto + botón enviar.
- Botón 🎤 que usa la **Web Speech API** del navegador (gratis) para transcribir la voz
  del cliente a texto y mandarla.

### Flujo

Cliente escribe/habla → frontend `POST /chat` → backend consulta a Claude con los
productos y las reglas → respuesta en formato WhatsApp vuelve al chat.

## Manejo de errores y casos borde

- **No encontrado:** una sola sugerencia del más parecido; si no hay nada cercano, mensaje
  amable sin insistir.
- **Fuera de tema:** redirige amable al catálogo.
- **API caída / sin internet:** el chat muestra "problema técnico, escribime al WhatsApp"
  con el link, para no perder la venta.
- **`productos.json` vacío/desactualizado:** el backend lo loguea (para Vladimir) y el chat
  responde que los precios se están actualizando.
- **Precios:** el bot **nunca inventa** un precio; solo usa los del JSON.

## Reglas de negocio (heredadas)

- Formato WhatsApp, cordial, con emojis, cerrando con una pregunta.
- Siempre los 3 precios por producto.
- **Nunca** mostrar el proveedor.
- Ceñirse a lo que pide el cliente; una sola recomendación si no está.

## Testing

- **Datos:** el `productos.json` se genera con los campos correctos y **sin** `proveedor`.
- **Backend:** preguntas típicas ("iphone 13", "algo barato samsung", "tenés el poco f7?")
  → responde con precios correctos, formato WhatsApp, sin proveedor, una sola recomendación
  cuando no encuentra.
- **Manual:** abrir la página local, escribir y probar el micrófono.

## Stack

- Python 3 + venv del proyecto, FastAPI (backend), Anthropic SDK (Claude API).
- HTML/CSS/JS plano (frontend), Web Speech API para voz.
- pytest para tests.
