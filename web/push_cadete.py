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

import html
import logging
import os
import re
from urllib.parse import urlparse

from web import cadetes
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


# Los navegadores siempre suscriben contra su servicio de push. Cualquier otro
# endpoint haría que el server le pegue a una URL arbitraria (incluidas
# direcciones internas de Railway) en cada envío.
_HOSTS_PUSH = (
    "fcm.googleapis.com",
    "updates.push.services.mozilla.com",
    ".push.apple.com",
    ".notify.windows.com",
)


def endpoint_push_permitido(endpoint):
    url = urlparse(str(endpoint))
    host = (url.hostname or "").lower()
    if url.scheme != "https" or not host:
        return False
    return any(host == h.lstrip(".") or (h.startswith(".") and host.endswith(h)) for h in _HOSTS_PUSH)


def guardar_suscripcion(client, suscripcion, tabla=TABLA_CADETE, cadete=None):
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
    if not endpoint_push_permitido(endpoint):
        raise ValueError("Endpoint de push no permitido")
    fila = {"endpoint": endpoint, "p256dh": p256dh, "auth": auth}
    if cadete:
        fila["cadete"] = cadete
    existente = client.table(tabla).select("id").eq("endpoint", endpoint).execute().data
    if existente:
        client.table(tabla).update(fila).eq("endpoint", endpoint).execute()
    else:
        client.table(tabla).insert(fila).execute()
    return fila


def eliminar_suscripcion(client, endpoint, tabla=TABLA_CADETE):
    client.table(tabla).delete().eq("endpoint", endpoint).execute()


def _enviar_mail_cadete(client, titulo, html_cuerpo, slug=None):
    """Manda el mail al email de la cuenta del cadete (o, mientras no la haya
    creado, a MAIL_NOTIFICACION_ALEJO). Nunca tira excepción hacia arriba: un
    fallo de mail no puede voltear la asignación ni el pago que lo dispara."""
    try:
        destinatarios = []
        try:
            if slug is None:
                destinatarios = [c["email"] for c in cadetes.activos(client) if c.get("email")]
            else:
                destinatarios = [e for e in [cadetes.email_activo(client, slug)] if e]
        except Exception:
            logger.exception("No se pudo leer el email de la cuenta del cadete")
        # Sin cuenta creada todavía, el aviso sigue yendo al mail de siempre de Alejo.
        for destinatario in destinatarios or ([MAIL_NOTIFICACION_ALEJO] if slug in (None, cadetes.SLUG_PRIMER_CADETE) else []):
            enviar_email(destinatario, titulo, html_cuerpo)
    except EnvioEmailError:
        logger.warning("Fallo enviando mail al cadete")
    except Exception:
        logger.exception("Error inesperado enviando mail al cadete")


URL_PANEL_CADETE = "https://thetechroomarg.com/admin/cadete"


def _html_mail_panel(etiqueta, texto, boton="Abrir panel", url=URL_PANEL_CADETE):
    """Mail con el mismo lenguaje visual del panel (oscuro, tarjeta, acento rojo).
    Solo lo esencial: de qué se trata, el dato y un botón. Estilos inline y
    tablas porque los clientes de mail no respetan CSS externo."""
    etiqueta = html.escape(re.sub(r"^[^\w]+", "", str(etiqueta)).strip())
    texto = html.escape(str(texto))
    return (
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#111318" '
        'style="background:#111318;padding:24px 12px;font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Arial,sans-serif;">'
        '<tr><td align="center">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" bgcolor="#1b1e24" '
        'style="max-width:420px;background:#1b1e24;border:1px solid #2a2e37;border-radius:16px;">'
        '<tr><td style="padding:24px 24px 8px;">'
        '<span style="font-size:12px;font-weight:800;letter-spacing:.14em;color:#6f7683;">THE TECH ROOM ARG<span style="color:#c8102e;">.</span></span>'
        '</td></tr>'
        f'<tr><td style="padding:12px 24px 0;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:#aab0bd;">{etiqueta}</td></tr>'
        f'<tr><td style="padding:6px 24px 0;font-size:22px;line-height:1.3;font-weight:700;color:#f2f4f8;">{texto}</td></tr>'
        '<tr><td style="padding:24px;">'
        f'<a href="{html.escape(url)}" style="display:inline-block;background:#c8102e;color:#ffffff;text-decoration:none;'
        f'font-size:14px;font-weight:700;padding:12px 20px;border-radius:12px;">{html.escape(boton)}</a>'
        '</td></tr></table></td></tr></table>'
    )


def _notificar_mail_cadete(client, titulo, cuerpo, slug=None):
    _enviar_mail_cadete(client, titulo, _html_mail_panel(titulo, cuerpo), slug)


def enviar_mail_pago_cadete(client, monto, movimientos, saldo_a_favor=0, slug=None, saldo_restante=0):
    """Mail al cadete cada vez que Vlad le registra un pago."""
    pesos = lambda n: "$ " + f"{int(n):,}".replace(",", ".")
    detalle = f"Te pagamos {pesos(monto)} por {movimientos} movimiento{'s' if movimientos != 1 else ''}."
    if saldo_a_favor:
        detalle += f" Quedaron {pesos(saldo_a_favor)} a tu favor."
    if saldo_restante:
        detalle += f" Te quedan {pesos(saldo_restante)} pendientes."
    _enviar_mail_cadete(
        client, "💸 Te hicieron un pago",
        _html_mail_panel("Pago", detalle),
        slug,
    )


def enviar_push_cadete(client, titulo, cuerpo, url="/admin/cadete", slug=None):
    """Manda una notificación a todos los dispositivos suscriptos del
    cadete, y un mail de aviso a alejobiasutto@gmail.com. Nunca tira
    excepción hacia arriba: un fallo de push/mail no puede voltear la
    asignación del pedido/nota que lo dispara.

    email_util.enviar_email() se niega a mandar nada real si corre dentro
    de un test (PYTEST_CURRENT_TEST), así que esto es seguro de dejar sin
    mockear en los tests existentes que ya ejercitan este camino."""
    _notificar_mail_cadete(client, titulo, cuerpo, slug)
    _enviar_push(client, TABLA_CADETE, titulo, cuerpo, url, slug)


def enviar_push_admin(client, titulo, cuerpo, url="/admin/clientes"):
    """Avisa en los dispositivos de Vladimir (panel de admin). Mismo criterio:
    nunca tira excepción hacia arriba, así un fallo no voltea el pedido."""
    try:
        _enviar_push(client, TABLA_ADMIN, titulo, cuerpo, url)
    except Exception:
        logger.exception("Error inesperado enviando push al admin")


def _enviar_push(client, tabla, titulo, cuerpo, url, slug=None):
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
    if slug is not None:
        # Las suscripciones viejas (sin cadete) son de Alejo.
        suscripciones = [x for x in suscripciones or [] if (x.get("cadete") or cadetes.SLUG_PRIMER_CADETE) == slug]
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
