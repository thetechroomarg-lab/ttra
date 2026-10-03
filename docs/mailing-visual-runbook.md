# Runbook: mailing visual

## Configuración esperada en Railway

Servicio: `ttra`, entorno `production`, rama `web-ttra`.

| Configuración | Valor |
| --- | --- |
| Volumen persistente montado | `/data` |
| `PRODUCTOS_PATH` | `/data/productos.json` |
| `MAILING_ASSETS_PATH` | `/data/mailing-assets` |
| `PUBLIC_APP_URL` | `https://thetechroomarg.com` |

La aplicación solo habilita carga, aprobación y envío cuando el token administrativo está configurado. No copiar secretos en archivos, comandos guardados, arte, manifests ni logs. Confirmar el mount y las variables en Railway antes de desplegar. Si falta el volumen, la carga y el envío fallan de forma cerrada; no usar almacenamiento efímero.

## Migración Supabase

El esquema fuente está en `supabase/schema.sql`. Revisar y ejecutar en Supabase SQL Editor únicamente el bloque idempotente de `mailing_campanias`, `mailing_envios_detalle` y `transicionar_mailing_campania` de ese archivo. La función valida transiciones permitidas y tiene `EXECUTE` solo para `service_role`.

Verificar con una fila de prueba identificada por UUID explícito que se pueda leer y avanzar por `previsualizado -> aprobado -> enviando -> enviado`, sin destinatarios ni llamadas a Resend. Eliminar únicamente esa fila de prueba por su UUID conocido, y confirmar que no queden filas asociadas. No borrar campañas reales ni resetear tablas.

## Despliegue

1. Confirmar rama y commit exacto `web-ttra`; ejecutar toda la suite antes del push.
2. Confirmar mount `/data`, variables anteriores y migración aplicada.
3. Desplegar y esperar estado `Online` en Railway.
4. No enviar correo durante el deploy ni el smoke test.

## Smoke test sin envío

1. Generar un arte de prueba y crear una versión `previsualizado` usando la skill local.
2. Consultar la URL del asset; debe responder `200`, el tipo MIME correcto y bytes cuyo SHA-256 coincide con el manifest.
3. Abrir `preview.html`; comprobar hero, contenido comercial HTML y baja. Revisar con imágenes habilitadas y bloqueadas, en 390×844 y 1440×900.
4. Consultar `resumen.py`; verificar catálogo, asset y destinatarios actuales.
5. Si la prueba funcional requiere aprobar, usar solo una campaña de prueba vacía/sin envío. Nunca ejecutar `enviar.py` en este smoke test.

## Rollback

Ante un fallo, no intentar envíos ni repetir una operación potencialmente parcial. El rollback operativo más seguro es volver al deployment previo en Railway. Para cortar operaciones administrativas sin borrar datos, retirar o rotar `ADMIN_TOKEN` en el servicio y volver a desplegar/configurar el valor seguro; las rutas administrativas fallarán cerradas. No eliminar el volumen ni sus archivos. Si la migración ya se aplicó, dejar tablas y función intactas hasta una revisión separada; no ejecutar `DROP` como rollback automático.

## Invariante de envío

Preparación, preview y aprobación no envían correo. Cada versión debe estar aprobada, mantener catálogo y asset vigentes, y recibir una instrucción explícita separada con `ENVIAR <version-id>`. Una campaña real —incluso a una sola dirección— requiere autorización explícita de Vladimir para esa campaña.
