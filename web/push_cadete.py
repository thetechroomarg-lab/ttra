"""Web Push al panel del cadete: le avisa al celu cuando Vladimir le asigna
un pedido o una nota, sin que tenga que estar mirando la app.

Las suscripciones viven en la tabla `cadete_push_suscripciones` (ver
supabase/schema.sql) — puede haber más de una fila (el cadete reinstaló la
PWA, tiene dos celus, etc.), así que un envío le pega a todas.

Configuración (variables de entorno, ver README de deploy):
- VAPID_PUBLIC_KEY: clave pública, la misma que consume el frontend al
  suscribirse (pushManager.subscribe applicationServerKey).
- VAPID_PRIVATE_KEY: PEM de la clave privada, con los saltos de línea
  escapados como "\\n" (así entra en una sola variable de entorno).
- VAPID_CLAIMS_EMAIL: mailto: de contacto que exige el estándar VAPID.

Si no están configuradas, el envío queda deshabilitado (no rompe nada del
resto de la app) — se loguea un warning una sola vez.
"""

import logging
import os

logger = logging.getLogger(__name__)

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
_VAPID_PRIVATE_KEY_RAW = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_PRIVATE_KEY_PEM = _VAPID_PRIVATE_KEY_RAW.replace("\\n", "\n") if _VAPID_PRIVATE_KEY_RAW else None
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:contacto@thetechroomarg.com")

PUSH_CONFIGURADO = bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY_PEM)

_avisado_sin_configurar = False


def guardar_suscripcion(client, suscripcion):
    """Guarda (o actualiza) una suscripción push del cadete.

    `suscripcion` es el objeto PushSubscription tal cual lo entrega el
    navegador: {"endpoint": ..., "keys": {"p256dh": ..., "auth": ...}}.
    """
    endpoint = suscripcion.get("endpoint")
    keys = suscripcion.get("keys") or {}
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")
    if not (endpoint and p256dh and auth):
        raise ValueError("Suscripción push incompleta")
    fila = {"endpoint": endpoint, "p256dh": p256dh, "auth": auth}
    existente = client.table("cadete_push_suscripciones").select("id").eq("endpoint", endpoint).execute().data
    if existente:
        client.table("cadete_push_suscripciones").update(fila).eq("endpoint", endpoint).execute()
    else:
        client.table("cadete_push_suscripciones").insert(fila).execute()
    return fila


def eliminar_suscripcion(client, endpoint):
    client.table("cadete_push_suscripciones").delete().eq("endpoint", endpoint).execute()


def enviar_push_cadete(client, titulo, cuerpo, url="/admin/cadete"):
    """Manda una notificación a todos los dispositivos suscriptos del
    cadete. Nunca tira excepción hacia arriba: un fallo de push no puede
    voltear la asignación del pedido/nota que lo dispara."""
    global _avisado_sin_configurar
    if not PUSH_CONFIGURADO:
        if not _avisado_sin_configurar:
            logger.warning(
                "Push al cadete deshabilitado: falta VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY en el entorno"
            )
            _avisado_sin_configurar = True
        return

    from pywebpush import WebPushException, webpush
    import json as _json

    suscripciones = client.table("cadete_push_suscripciones").select("*").execute().data
    if not suscripciones:
        return

    payload = _json.dumps({"titulo": titulo, "cuerpo": cuerpo, "url": url}, ensure_ascii=False)

    for sub in suscripciones:
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY_PEM,
                vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
                ttl=3600,
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                # El navegador invalidó esa suscripción (desinstaló la PWA,
                # revocó el permiso, etc.) — se descarta en vez de reintentar
                # para siempre.
                eliminar_suscripcion(client, sub["endpoint"])
            else:
                logger.warning("Fallo enviando push al cadete: %s", exc)
        except Exception:
            logger.exception("Error inesperado enviando push al cadete")
