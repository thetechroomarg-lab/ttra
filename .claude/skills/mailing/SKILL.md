---
name: mailing
description: Arma y envía la campaña semanal de mailing de novedades a los clientes de The Tech Room Arg — siempre exactamente 10 productos (5 por columna: los nuevos del catálogo primero, completando al azar si faltan), suma una nota/promo manual opcional, y solo envía cuando Vladimir lo confirma explícitamente. Usar cuando Vladimir dice "dejá esta nota para la próxima campaña", "mandá la campaña de novedades", o cuando corre la rutina semanal programada.
---

# Campaña de mailing de novedades

Escribe DIRECTO en la base de producción (Supabase) al enviar — no hay
ambiente de prueba separado (ver `web/supabase_client.py`).

## Dejar una nota/promo para la próxima campaña

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/nota.py "texto exacto que Vladimir dictó, nunca un descuento inventado por vos"
```

Reemplaza cualquier nota pendiente sin usar (el script avisa si pisa una). El texto de la nota SIEMPRE sale textual de lo que Vladimir escribió — nunca inventar ni completar un número de descuento, aunque sea a modo de ejemplo.

## Rutina semanal (automática, vía skill `schedule`)

Cada sábado 20:00 (hora Argentina) corré:

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/armar_borrador.py
```

El script:
- Compara `web/productos.json` contra el último snapshot y detecta productos nuevos.
- Arma la selección final de la campaña: **siempre exactamente 10 productos, sin excepción, 5 por columna** — prioriza los nuevos de la semana y completa al azar con el resto del catálogo si hay menos de 10 nuevos (`web/mailing/catalogo_diff.seleccionar_para_campania`).
- Lee la nota pendiente (si hay) y la consume — queda limpia después de esta corrida, se haya aprobado el borrador o no.
- Si imprime `PRIMERA_CORRIDA`, no hay nada para mostrar todavía (recién se inicializó el snapshot) — no generes notificación ni artifact esa semana.
- Si arma un borrador, imprime `BORRADOR_LISTO` seguido de un resumen (cuántos de los 10 son realmente nuevos vs. relleno, si incluye nota, cantidad de destinatarios), y guarda el HTML completo en `web/mailing/data/borrador_actual.json` (campo `html_preview`).

Si imprimió `BORRADOR_LISTO`:

1. Leé `web/mailing/data/borrador_actual.json`, tomá el campo `html_preview`.
2. Escribilo a un archivo `.html` y publicalo con tu herramienta Artifact (favicon 📧, título "Campaña de novedades").
3. Mandale una notificación push a Vladimir con la herramienta PushNotification: cantidad de productos nuevos, si incluye nota, cantidad de destinatarios, y que revise el link del artifact.
4. No envíes nada vos solo — el envío real requiere que Vladimir lo pida explícitamente después de revisar el artifact.

La cantidad de destinatarios y los datos de producto quedan congelados al momento de armar el borrador. Si Vladimir aprueba la campaña más de uno o dos días después, avisale que convendría un chequeo rápido de precios antes de mandarla, por si quedaron desactualizados.

## Enviar la campaña aprobada

Cuando Vladimir confirma (dice "dale, mandala" o similar) después de haber visto el artifact:

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/enviar_campania.py
```

- Envía el HTML del borrador (personalizado por cliente solo en el link de baja) a todos los clientes con email y sin `no_mailing=true`.
- Si falla un envío individual, sigue con el resto — al final reporta `ENVIADA: X/Y destinatarios, Z fallidos`.
- Marca el borrador como usado — no se puede reenviar el mismo borrador dos veces, hace falta uno nuevo de la próxima corrida semanal.

Contale a Vladimir el resultado final en el chat.

## Gotchas

- El envío real (`enviar_campania.py`) NUNCA se corre automáticamente ni sin que Vladimir lo haya pedido explícitamente para ese borrador puntual.
- Si `armar_borrador.py` imprime `PRIMERA_CORRIDA`, no generes notificación ni artifact esa semana.
- Nunca inventar un descuento, promo o condición comercial — ni real ni de ejemplo. La nota siempre sale textual de `/mailing nota`.
- La columna `clientes.no_mailing` tiene que existir en Supabase antes de correr cualquiera de estos scripts contra producción (`supabase/schema.sql`, corrida a mano en el SQL Editor).
