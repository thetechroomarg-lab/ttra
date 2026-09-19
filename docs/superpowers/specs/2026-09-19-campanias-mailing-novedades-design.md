# Campañas de mailing de novedades a clientes

## Objetivo

Automatizar el envío semanal de un mail de "novedades" a la base de clientes de THE TECH ROOM ARG: productos nuevos detectados en el catálogo, más una nota/promo opcional que Vladimir deja de antemano. El armado del mail es automático; el envío real a la base nunca es automático — siempre requiere una confirmación explícita de Vladimir sobre el borrador.

## Alcance

- Audiencia: todos los clientes de la tabla `clientes` con `email` cargado (cuentas creadas, no solo los que compraron).
- Frecuencia: semanal, disparado los lunes.
- Contenido: productos nuevos del catálogo desde el último envío + nota manual opcional.
- Fuera de alcance: segmentación de audiencia, opt-in explícito al momento de alta de cuenta, A/B testing de asuntos, métricas de apertura/click.

## Arquitectura

Un agente cron de Claude (configurado con la skill `schedule`) corre todos los lunes y ejecuta el paso de **armado de borrador**. El paso de **envío real** nunca ocurre dentro del cron: queda a cargo de un comando manual (`/mailing enviar`) que Vladimir corre después de revisar el borrador. Esto separa la detección/composición (automática) del acto de mandar mail a toda la base (siempre manual), que es la acción de mayor riesgo del sistema.

```
Lunes (cron)                          Cuando Vladimir aprueba
─────────────                          ───────────────────────
1. Diff productos.json vs snapshot     4. Lee borrador_actual.json
2. Arma HTML del mail                  5. Envía por Resend a clientes
3. Publica Artifact + notifica            (excluye no_mailing=true)
   → guarda borrador_actual.json       6. Actualiza snapshot + log
```

Si Vladimir no aprueba nada durante la semana, el lunes siguiente se genera un borrador nuevo (sin acumular envíos pendientes; el borrador viejo queda descartado, no se manda retroactivamente).

## Componentes

### Estado persistente

Archivos JSON en el repo (no requiere tabla nueva en Supabase, salvo la columna de baja):

- `web/mailing/snapshot_catalogo.json` — copia de `productos.json` en el momento del último borrador armado. Se usa para diffear y detectar altas.
- `web/mailing/nota_pendiente.json` — `{texto, creada_en}` con la nota/promo manual que Vladimir dejó antes del lunes. Se limpia (se pone `null`) después de usarse en un borrador, la haya aprobado o no.
- `web/mailing/borrador_actual.json` — último borrador armado: lista de productos incluidos, HTML completo, URL del artifact publicado, fecha de armado, cantidad de destinatarios calculada. Lo lee `/mailing enviar`.
- `web/mailing/enviados.log` — una línea por campaña efectivamente enviada (fecha, cantidad de productos, destinatarios ok/fallidos), para no reenviar el mismo borrador dos veces y tener trazabilidad.

### Detección de productos nuevos

En cada corrida del cron:
1. Cargar `snapshot_catalogo.json` (si no existe, es la primera corrida: no hay "nuevos", solo se guarda el snapshot inicial y no se arma borrador).
2. Comparar contra `web/productos.json` actual por nombre normalizado (mismo criterio de normalización que ya usa el resto del proyecto para consolidar productos).
3. Los productos presentes ahora y ausentes en el snapshot anterior son "nuevos" de la semana.
4. Si no hay productos nuevos y no hay nota pendiente, el cron no arma borrador ni notifica (semana sin novedades, no se manda mail vacío).

### Agente cron semanal (skill `schedule`)

Rutina programada (lunes 9:00 AM, hora Argentina) que:
1. Ejecuta la detección de productos nuevos.
2. Lee `nota_pendiente.json` si existe.
3. Arma el HTML del mail (ver sección Template).
4. Publica el HTML como Artifact privado (para previsualización fiel, con imágenes y estilos reales).
5. Guarda `borrador_actual.json`.
6. Envía una notificación push a Vladimir con: cantidad de productos nuevos, si incluye nota, cantidad de destinatarios, y el link del artifact.

### Skill nueva `/mailing`

Dos subcomandos:

- **`/mailing nota <texto>`** — guarda `nota_pendiente.json` con el texto dado, para que el próximo borrador semanal lo incluya. Si ya había una nota pendiente sin usar, la reemplaza (avisa cuál pisa).
- **`/mailing enviar`** — lee `borrador_actual.json`, muestra un resumen final (cantidad de destinatarios, productos, nota), pide confirmación explícita, y si Vladimir confirma:
  1. Consulta `clientes` filtrando `email IS NOT NULL AND no_mailing != true`.
  2. Envía el HTML vía `web/email_util.enviar_email()` (mismo mecanismo que ya usa `/pedido` para credenciales), uno por destinatario.
  3. Si un envío individual falla, lo loguea y continúa con el resto (no aborta la campaña).
  4. Al terminar, reporta "enviado a X/Y, Z fallidos" y escribe una línea en `enviados.log`.
  5. Marca `borrador_actual.json` como usado (no se puede reenviar el mismo borrador dos veces sin pasar por un cron nuevo).

Si se corre `/mailing enviar` sin borrador pendiente o con uno ya usado, informa que no hay nada para enviar.

## Template del mail

Estilo: terminal oscuro (fondo negro/verde, consistente con el tema actual de la web — `theme.css`), implementado con estilos inline y atributos `bgcolor`/`color` además de CSS en `<style>`, para degradar razonablemente en clientes de mail que ignoran CSS embebido (Gmail, Outlook).

Estructura:
1. **Header** — nombre "THE TECH ROOM ARG" (texto, no hay logo propio en el repo todavía) y fecha.
2. **Banner de nota** (solo si hay nota manual pendiente) — destacado arriba de los productos, con más protagonismo visual que el resto del cuerpo.
3. **Grilla de productos nuevos** — por cada producto: imagen (`link_imagen`), nombre, precio, y link a su página pública `/p/<slug>` (reutiliza la página existente de producto individual).
4. **Footer** — datos de contacto y link de baja ("no quiero recibir más novedades").

## Cumplimiento: baja de mailing

Se agrega la columna `no_mailing` (booleano, default `false`) a la tabla `clientes`. Cada mail incluye un link de baja único por cliente (`/mailing/baja/<id_o_token>`) que marca `no_mailing=true` sin requerir login. Los clientes con `no_mailing=true` quedan excluidos de la query de destinatarios en `/mailing enviar`. Esto es la única pieza de infraestructura que toca la web (`web/app.py`), fuera de la skill y el cron.

## Manejo de errores

- **Primera corrida sin snapshot previo:** no arma borrador, solo inicializa el snapshot.
- **`productos.json` no accesible o vacío:** el cron aborta esa corrida sin notificar (evita falso positivo de "0 productos nuevos" cuando en realidad falló la lectura), y loguea el error para revisión manual.
- **Fallo de Resend en un destinatario puntual:** se loguea y se continúa; no aborta la campaña completa.
- **`/mailing enviar` corrido dos veces sobre el mismo borrador:** la segunda vez informa que ya fue enviado, no reenvía.
- **Nota pendiente vieja nunca usada:** si pasan varias semanas sin que se apruebe ningún borrador, la nota sigue esperando hasta el próximo borrador que sí se arme (no expira sola).

## Testing

- Probar la detección de productos nuevos con un `productos.json` de prueba (agregar/quitar entradas) contra un snapshot fijo.
- Probar `/mailing nota` y `/mailing enviar` contra una base de clientes de prueba (no la real) antes de habilitar el cron en producción.
- Primer envío real: correr `/mailing enviar` manualmente una vez, revisado a mano, antes de dejar el cron semanal andando solo para el armado de borradores.
- Verificar que el link de baja funciona sin login y que el cliente dado de baja no aparece en el siguiente borrador de destinatarios.
