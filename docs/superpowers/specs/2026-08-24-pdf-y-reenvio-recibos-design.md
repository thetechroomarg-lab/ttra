# PDF y Reenvío de Recibos - Diseño

## Objetivo

Permitir al administrador abrir el PDF de un recibo emitido y reenviar el mismo comprobante al cliente, conservando siempre la fecha original de emisión.

## Alcance

- El historial de pedidos mostrará un ícono de ojo solo si el pedido tiene `recibo_enviado_en`.
- El ojo abre `GET /admin/pedidos/{pedido_id}/recibo.pdf` en una pestaña nueva.
- El endpoint genera el PDF en memoria con `reportlab`; no persiste archivos ni crea URLs públicas.
- El PDF usa la instantánea persistida del pedido: cliente, identificador, ítems, cantidades, precios USD, descuentos, total y garantías.
- Los pedidos con recibo emitido mostrarán además un ícono de reenvío.
- El reenvío llama al endpoint existente de recibos y vuelve a enviar el email al cliente.
- Se agrega `recibo_emitido_en timestamptz`, que se define en el primer envío exitoso y no se modifica al reenviar.
- `recibo_enviado_en` conserva la fecha del último envío. Para registros emitidos antes de esta columna, el primer PDF o reenvío inicializa `recibo_emitido_en` con el valor existente de `recibo_enviado_en`.

## Modelo de Datos

La tabla `pedidos` incorpora `recibo_emitido_en timestamptz`. La migración es idempotente.

## Seguridad y Errores

- PDF y reenvío requieren sesión activa del administrador.
- Un pedido sin recibo emitido devuelve 400 y no expone su PDF.
- Un pedido sin instantánea suficiente devuelve 400.
- El PDF y email escapan los textos de cliente y producto; se generan desde datos persistidos, no desde parámetros de URL.
- Si el reenvío falla, no altera la fecha original ni marca un envío nuevo.

## Presentación

- El PDF contiene el wordmark de The Tech Room Arg, ID del recibo, fecha original de emisión, detalle de compra, descuentos, total USD y garantías agrupadas.
- Se renderiza una página de prueba a PNG durante desarrollo para validar que no tenga recortes ni superposiciones.

## Pruebas

- El endpoint PDF rechaza usuarios no admin y pedidos sin recibo.
- El PDF contiene ID, fecha original, total y producto esperado.
- El panel muestra ojo y reenvío solo para recibos emitidos.
- El reenvío conserva `recibo_emitido_en` y actualiza `recibo_enviado_en` únicamente después de que Resend responde correctamente.
