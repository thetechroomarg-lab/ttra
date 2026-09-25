# Seguimiento post-entrega y programa de fidelización — Design

## Resumen

Dos features independientes que se enganchan al mismo evento: una entrega marcada como completada.

1. **Mail de seguimiento**: a los 7 días de la entrega, mail automático 1 a 1 preguntando qué le pareció, con reply-to a Vladimir.
2. **Fidelización**: cada entrega completada de un pedido con cuenta de cliente suma un sello. Al 5to sello se emite un código promo automático de US$20. El ciclo reinicia recién cuando el cliente usa ese código.

## Motivación

- El seguimiento post-venta hoy no existe: no hay contacto con el cliente después de la entrega.
- La fidelización busca replicar el modelo de tarjeta de sellos (tipo lavadero) sin integrar Apple/Google Wallet real (requiere cuentas de desarrollador que Vladimir no quiere gestionar). Se resuelve en cambio como una tarjeta visual dentro del perfil web ya existente.

## Arquitectura

Ambas features se enganchan al mismo punto de entrada: donde hoy se marca una entrega como completada (`web/entregas.py`, usado desde `/admin/tareas-entrega/{tarea_id}/completar` en `paginas_cadete.py`). Ese punto ya dispara la lógica existente de entregas; se le agregan dos efectos adicionales, cada uno en su propio módulo:

- `web/mailing/seguimiento.py`: no se dispara en el momento de la entrega, sino por un cron diario aparte (mismo patrón que el borrador semanal de novedades vía la skill `schedule`), que barre pedidos entregados hace 7 días.
- Lógica de fidelización: función pura que vive junto a `pedidos.py`/`cuentas.py` (el módulo exacto se decide en el plan de implementación), invocada directamente en el momento de completar la entrega.

## Modelo de datos (Supabase)

En `pedidos`:
- `seguimiento_enviado_en timestamptz` (nullable). Null hasta que el mail se envía con éxito.

En `clientes`:
- `sellos_fidelidad int not null default 0`. Sube de a 1 por cada entrega completada de un pedido con `cliente_id`. Rango 0-4 durante el ciclo activo.
- `fidelidad_ultimo_codigo text` (nullable). Referencia al código promo emitido al llegar a 5 sellos, mientras no se haya usado.

Ambas columnas siguen el patrón de altas manuales documentado para columnas previas (`condiciones_mayorista_aceptadas_en`, `no_mailing`): se agregan a `supabase/schema.sql` y hay que correrlas a mano en el SQL Editor de Supabase antes de que el código nuevo corra contra producción.

## Flujo: mail de seguimiento

1. Cron diario ejecuta `web/mailing/seguimiento.py`.
2. Consulta pedidos con entrega completada hace exactamente 7 días (ventana de un día, para no depender de que el cron corra a una hora exacta) y `seguimiento_enviado_en` nulo.
3. Para cada uno, arma un mail corto y personalizado con el nombre del cliente y el producto entregado, pidiendo feedback, con `reply-to` apuntando a la casilla de Vladimir.
4. Envía con `web/email_util.enviar_email` (ya existente).
5. Si el envío tiene éxito, marca `seguimiento_enviado_en = now()`. Si falla, lo deja nulo para que el cron lo reintente el día siguiente — nunca deja de reintentar silenciosamente ni duplica el envío el mismo día en que sí tuvo éxito.

Es un mail transaccional 1 a 1, de bajo riesgo: se envía automático, sin preview ni aprobación previa de Vladimir (a diferencia del mailing masivo de novedades).

## Flujo: fidelización

1. Al completar una entrega, si el pedido tiene `cliente_id` (no es invitado): incrementar `clientes.sellos_fidelidad` en 1.
2. Si `sellos_fidelidad` llega a 5:
   - Generar un código promo nuevo de US$20 usando la infraestructura existente de códigos promo (`/api/codigos-promo`).
   - Guardar su identificador en `fidelidad_ultimo_codigo`.
   - **No** resetear `sellos_fidelidad` todavía — se mantiene en 5 mientras el código no se use, como señal de "premio disponible".
3. Cuando el cliente consume ese código promo (flujo ya existente de validar/consumir), se detecta que coincide con `fidelidad_ultimo_codigo` de su cuenta y ahí sí: `sellos_fidelidad = 0`, `fidelidad_ultimo_codigo = null`. Empieza un ciclo nuevo.

### Visual en `/perfil`

- Si `fidelidad_ultimo_codigo` es null: tarjeta de 5 círculos, rellenos según `sellos_fidelidad` (0 a 4 llenos), estilo tarjeta de sellos de cafetería.
- Si `fidelidad_ultimo_codigo` tiene valor: la tarjeta muestra "premio disponible: código {codigo} — US$20 de descuento en tu próxima compra" en vez de los círculos.

## Testing

Con `tests/fakes_supabase.py`, patrón ya establecido en el repo:

- Entrega completada sin `cliente_id` → no suma sello.
- Entrega completada con `cliente_id` → suma un sello.
- Llega a 5 → se emite código promo, `sellos_fidelidad` se mantiene en 5, no resetea todavía.
- Consumir el código de fidelidad → resetea `sellos_fidelidad` a 0 y limpia `fidelidad_ultimo_codigo`.
- Cron de seguimiento no duplica envío si corre dos veces el mismo día sobre el mismo pedido.
- Cron de seguimiento reintenta al día siguiente si `enviar_email` falló.

## Fuera de alcance

- Integración real con Apple Wallet / Google Wallet (requiere cuentas de desarrollador que Vladimir explícitamente no quiere gestionar).
- Aplicación automática del descuento a un pedido en curso — el código se genera y queda disponible, pero el cliente lo usa en su próxima compra a través del flujo de códigos promo ya existente.
- Cambiar el criterio de qué "cuenta" como sello (ya se definió: cualquier pedido entregado, sin monto mínimo).
