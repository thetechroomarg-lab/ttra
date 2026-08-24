# Adjuntos y Numeración de Recibos - Diseño

## Objetivo

Adjuntar el PDF al email de emisión y reenvío, y asignar a cada nuevo recibo un número interno correlativo empezando en `0001-1993`.

## Flujo

- La secuencia PostgreSQL `recibos_numero_seq` inicia en `1993`.
- La función SQL `siguiente_numero_recibo()` devuelve `0001-` concatenado con el siguiente valor de la secuencia.
- Al emitir por primera vez, el backend obtiene ese número vía RPC, genera el PDF y envía el email con el PDF adjunto.
- Solo si Resend responde correctamente, persiste `recibo_id`, `recibo_emitido_en` y `recibo_enviado_en`.
- Al reenviar, reutiliza el `recibo_id` y la fecha original, genera el mismo PDF desde la instantánea y lo adjunta otra vez.

## Datos y Seguridad

- Los IDs existentes no se modifican.
- La secuencia en la base de datos evita números duplicados ante envíos concurrentes.
- El PDF adjunto usa exclusivamente el pedido persistido y conserva los controles de sesión admin.
- Un error de Resend no marca el pedido como emitido.

## Pruebas

- Nuevo recibo recibe `0001-1993` desde el RPC simulado.
- Email inicial y reenvío incluyen adjunto PDF con nombre estable.
- Reenvío conserva número y fecha de emisión.
- Error de email no persiste número ni fechas.
