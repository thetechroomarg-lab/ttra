---
name: mailing
description: Arma y envía la campaña semanal de mailing de novedades a los clientes de The Tech Room Arg — detecta productos nuevos del catálogo, suma una nota/promo manual opcional, y solo envía cuando Vladimir lo confirma explícitamente. Usar cuando Vladimir dice "dejá esta nota para la próxima campaña", "mandá la campaña de novedades", o cuando corre la rutina semanal programada.
---

# Campaña de mailing de novedades

Escribe DIRECTO en la base de producción (Supabase) al enviar — no hay
ambiente de prueba separado (ver `web/supabase_client.py`).

## Dejar una nota/promo para la próxima campaña

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/nota.py "Todo el stock de iPhone 13 con $30 de descuento esta semana"
```

Reemplaza cualquier nota pendiente sin usar (el script avisa si pisa una).

## Rutina semanal (automática, vía skill `schedule`)

Cada lunes 9:00 AM (hora Argentina) corré:

```bash
cd "/Users/toraba/TTRA Project"
./.venv/bin/python .claude/skills/mailing/scripts/armar_borrador.py
```

El script:
- Compara `web/productos.json` contra el último snapshot y detecta productos nuevos.
- Lee la nota pendiente (si hay) y la consume — queda limpia después de esta corrida, se haya aprobado el borrador o no.
- Si no hay productos nuevos ni nota, imprime `SIN_NOVEDADES` — no hace falta seguir, no le muestres nada a Vladimir esta semana.
- Si imprime `PRIMERA_CORRIDA`, tampoco hay nada para mostrar (recién se inicializó el snapshot).
- Si arma un borrador, imprime `BORRADOR_LISTO` seguido de un resumen (cantidad de productos, si incluye nota, cantidad de destinatarios), y guarda el HTML completo en `web/mailing/data/borrador_actual.json` (campo `html_preview`).

Si imprimió `BORRADOR_LISTO`:

1. Leé `web/mailing/data/borrador_actual.json`, tomá el campo `html_preview`.
2. Escribilo a un archivo `.html` y publicalo con tu herramienta Artifact (favicon 📧, título "Campaña de novedades").
3. Mandale una notificación push a Vladimir con la herramienta PushNotification: cantidad de productos nuevos, si incluye nota, cantidad de destinatarios, y que revise el link del artifact.
4. No envíes nada vos solo — el envío real requiere que Vladimir lo pida explícitamente después de revisar el artifact.

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
- Si `armar_borrador.py` imprime `SIN_NOVEDADES` o `PRIMERA_CORRIDA`, no generes notificación ni artifact esa semana.
- La columna `clientes.no_mailing` tiene que existir en Supabase antes de correr cualquiera de estos scripts contra producción (`supabase/schema.sql`, corrida a mano en el SQL Editor).
