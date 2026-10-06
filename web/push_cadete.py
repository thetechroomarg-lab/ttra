"""Web Push a los paneles: al del cadete le avisa al celu cuando Vladimir le
asigna un pedido o una nota, y al de admin cuando entra un pedido de la web,
sin que tengan que estar mirando la app.

Las suscripciones del admin viven aparte, en `admin_push_suscripciones`.

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

from web.email_util import EnvioEmailError, enviar_email

logger = logging.getLogger(__name__)

MAIL_NOTIFICACION_ALEJO = "alejobiasutto@gmail.com"

VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY")
_VAPID_PRIVATE_KEY_RAW = os.environ.get("VAPID_PRIVATE_KEY")
VAPID_PRIVATE_KEY_PEM = _VAPID_PRIVATE_KEY_RAW.replace("\\n", "\n") if _VAPID_PRIVATE_KEY_RAW else None
VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "mailto:contacto@thetechroomarg.com")

PUSH_CONFIGURADO = bool(VAPID_PUBLIC_KEY and VAPID_PRIVATE_KEY_PEM)

_avisado_sin_configurar = False

TABLA_CADETE = "cadete_push_suscripciones"
TABLA_ADMIN = "admin_push_suscripciones"


def guardar_suscripcion(client, suscripcion, tabla=TABLA_CADETE):
    """Guarda (o actualiza) una suscripción push del cadete (o del admin).

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
    existente = client.table(tabla).select("id").eq("endpoint", endpoint).execute().data
    if existente:
        client.table(tabla).update(fila).eq("endpoint", endpoint).execute()
    else:
        client.table(tabla).insert(fila).execute()
    return fila


def eliminar_suscripcion(client, endpoint, tabla=TABLA_CADETE):
    client.table(tabla).delete().eq("endpoint", endpoint).execute()


def _notificar_mail_alejo(titulo, cuerpo):
    """Le manda un mail a alejobiasutto@gmail.com cada vez que se le asigna
    un pedido o una tarea. Nunca tira excepción hacia arriba, mismo criterio
    que el push: un fallo de mail no puede voltear la asignación."""
    try:
        html = f"<p>{cuerpo}</p><p><a href='https://thetechroomarg.com/admin/cadete'>Ver en el panel</a></p>"
        enviar_email(MAIL_NOTIFICACION_ALEJO, titulo, html)
    except EnvioEmailError:
        logger.warning("Fallo enviando mail de notificación a Alejo")
    except Exception:
        logger.exception("Error inesperado enviando mail de notificación a Alejo")


def enviar_push_cadete(client, titulo, cuerpo, url="/admin/cadete"):
    """Manda una notificación a todos los dispositivos suscriptos del
    cadete, y un mail de aviso a alejobiasutto@gmail.com. Nunca tira
    excepción hacia arriba: un fallo de push/mail no puede voltear la
    asignación del pedido/nota que lo dispara.

    email_util.enviar_email() se niega a mandar nada real si corre dentro
    de un test (PYTEST_CURRENT_TEST), así que esto es seguro de dejar sin
    mockear en los tests existentes que ya ejercitan este camino."""
    _notificar_mail_alejo(titulo, cuerpo)
    _enviar_push(client, TABLA_CADETE, titulo, cuerpo, url)


def enviar_push_admin(client, titulo, cuerpo, url="/admin/clientes"):
    """Avisa en los dispositivos de Vladimir (panel de admin). Mismo criterio:
    nunca tira excepción hacia arriba, así un fallo no voltea el pedido."""
    try:
        _enviar_push(client, TABLA_ADMIN, titulo, cuerpo, url)
    except Exception:
        logger.exception("Error inesperado enviando push al admin")


def _enviar_push(client, tabla, titulo, cuerpo, url):
    global _avisado_sin_configurar
    if not PUSH_CONFIGURADO:
        if not _avisado_sin_configurar:
            logger.warning(
                "Push deshabilitado: falta VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY en el entorno"
            )
            _avisado_sin_configurar = True
        return

    from py_vapid import Vapid
    from pywebpush import WebPushException, webpush
    import json as _json

    suscripciones = client.table(tabla).select("*").execute().data
    if not suscripciones:
        return

    payload = _json.dumps({"titulo": titulo, "cuerpo": cuerpo, "url": url}, ensure_ascii=False)
    # La clave viene en PEM; pywebpush solo acepta un string en base64 DER,
    # así que se le pasa la clave ya cargada.
    clave_vapid = Vapid.from_pem(VAPID_PRIVATE_KEY_PEM.encode())

    for sub in suscripciones:
        subscription_info = {
            "endpoint": sub["endpoint"],
            "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=clave_vapid,
                vapid_claims={"sub": VAPID_CLAIMS_EMAIL},
                ttl=3600,
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None)
            if status in (404, 410):
                # El navegador invalidó esa suscripción (desinstaló la PWA,
                # revocó el permiso, etc.) — se descarta en vez de reintentar
                # para siempre.
                eliminar_suscripcion(client, sub["endpoint"], tabla)
            else:
                logger.warning("Fallo enviando push (%s): %s", tabla, exc)
        except Exception:
            logger.exception("Error inesperado enviando push (%s)", tabla)
