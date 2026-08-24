# Recibos de Pedidos - Diseño

## Objetivo

Permitir al administrador emitir por email un recibo interno en USD para cada pedido pendiente de entrega del día. El recibo debe reflejar el precio y las cantidades vistos por el cliente al confirmar su checkout, incluir el detalle de garantías aplicable y conservar un historial consultable por fecha.

## Alcance

- Los nuevos pedidos guardan una instantánea inmutable de sus ítems: nombre, color, cantidad, precio unitario USD y subtotal USD, más el total USD final.
- La lista operativa de `/admin/clientes` muestra solo los pedidos cuya entrega es hoy y que todavía no tienen recibo emitido.
- Cada pedido pendiente se renderiza como una fila con cliente, detalle resumido, total USD y el botón `Enviar recibo`.
- Al enviar, el backend construye y envía un email HTML mediante Resend al email del cliente. Incluye logo de The Tech Room Arg, identificador de recibo, fecha, detalle, total USD y garantías por producto.
- Una emisión exitosa guarda `recibo_enviado_en` y un identificador de recibo. Entonces el pedido deja de figurar en la lista operativa.
- El panel incorpora un selector de fecha para consultar el historial de pedidos de la fecha elegida. El historial muestra pedidos con o sin recibo, incluyendo estado y fecha de emisión cuando exista.
- Un recibo ya emitido solo se reenvía tras confirmación explícita; conserva su mismo identificador y no se genera una venta nueva.

## Fuera de Alcance

- No es una factura ni comprobante fiscal.
- No se registran medios, importes ni conciliación de pago.
- No se recalculan precios desde el catálogo al emitir: la fuente del recibo es la instantánea del checkout.
- Los pedidos históricos sin instantánea de precio/cantidad no permiten emitir un recibo, porque no sería fiel a la compra. Continúan visibles en el historial con ese estado.

## Modelo de Datos

La tabla `pedidos` incorpora:

- `detalle jsonb`: arreglo de ítems con `nombre`, `color`, `cantidad`, `usd_unitario` y `usd_subtotal`.
- `total_usd numeric`: total final del checkout en USD, luego de descuentos aplicables.
- `recibo_id text unique`: identificador estable generado al emitir el primer recibo.
- `recibo_enviado_en timestamptz`: fecha de envío exitoso.

Los campos admiten `NULL` para mantener compatibles los pedidos existentes.

## Flujo

1. El cliente confirma el carrito por WhatsApp. Antes de abrir WhatsApp, el navegador registra en `/api/pedidos` el detalle y total USD calculados localmente.
2. El backend valida tipos y cantidades, asocia el pedido al cliente autenticado y persiste la instantánea junto con la fecha de entrega.
3. El admin abre el panel. La sección `Pedidos para hoy` carga solamente pedidos de hoy sin `recibo_enviado_en`.
4. Al pulsar `Enviar recibo`, el frontend pide confirmación y llama a un endpoint autenticado de administración.
5. El endpoint carga pedido y cliente, rechaza pedidos sin instantánea, crea un ID si es la primera emisión, genera el HTML y envía el email. Solo tras un envío exitoso persiste `recibo_enviado_en`.
6. El pedido desaparece de la lista operativa. El selector de historial permite elegir una fecha y ver todos sus pedidos, con el estado `Pendiente`, `Recibo enviado` o `Sin detalle histórico`.

## Garantías

Las garantías se centralizan en una función reutilizable, basada en el nombre del producto:

- Apple nuevo: 12 meses y gestión en One Click o MacStation.
- Notebooks: 6 meses.
- Samsung, Motorola y Xiaomi: 3 meses.
- Otras categorías: la condición general vigente del negocio.

Para Samsung, Motorola, Xiaomi, notebooks y condiciones generales, se incluyen las exclusiones actuales: solo fallas de fábrica; no caídas, rayones, humedad, mal uso ni software no confiable; se requiere caja y accesorios cuando corresponda. El recibo agrupa condiciones repetidas para no duplicarlas por cada ítem.

## Seguridad y Errores

- Todos los endpoints de recibos requieren la sesión actual de administrador.
- Los valores enviados por el cliente no se usan para emitir: el backend lee el pedido persistido y escapa el HTML.
- Si Resend falla, el pedido permanece pendiente y no se marca como emitido.
- El usuario recibe un error legible si falta email, falta detalle histórico o el pedido no existe.

## Pruebas

- Persistencia del detalle y total USD al crear un pedido.
- Filtrado de pedidos pendientes del día y exclusión tras emitir el recibo.
- Endpoint de recibo: autorización, contenido HTML, garantías correctas, marca de envío solo después de éxito y reenvío con el mismo ID.
- Render del panel: fila por pedido, botón y selector de historial por fecha.
- Compatibilidad: pedido anterior sin detalle se ve en historial pero no emite recibo.
