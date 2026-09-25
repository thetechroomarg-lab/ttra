import html
import os
from datetime import datetime, timedelta, timezone

from web import email_util, entregas

DIAS_HASTA_SEGUIMIENTO = 7
# Pasado este plazo ya no se manda: evita mailear pedidos viejos (ej. la
# primera corrida) y acota los reintentos si Resend falla varios días.
DIAS_MAXIMOS_SEGUIMIENTO = 14
REPLY_TO_SEGUIMIENTO = os.environ.get("MAIL_SEGUIMIENTO_REPLY_TO", "contacto@thetechroomarg.com")


def _fecha_entrega_argentina(recibo_enviado_en):
    return datetime.fromisoformat(recibo_enviado_en).astimezone(entregas.ZONA_HORARIA).date()


def pedidos_para_notificar(client, hoy=None):
    hoy = hoy or entregas.ahora_argentina().date()
    resultado = []
    for pedido in client.table("pedidos").select("*").execute().data:
        if not pedido.get("cliente_id") or pedido.get("seguimiento_enviado_en"):
            continue
        if not pedido.get("recibo_enviado_en"):
            continue
        dias = (hoy - _fecha_entrega_argentina(pedido["recibo_enviado_en"])).days
        if DIAS_HASTA_SEGUIMIENTO <= dias <= DIAS_MAXIMOS_SEGUIMIENTO:
            resultado.append(pedido)
    return resultado


def _descripcion_pedido(pedido):
    detalle = pedido.get("detalle") or []
    if detalle:
        return ", ".join(item.get("nombre", "") for item in detalle if item.get("nombre"))
    return ", ".join(pedido.get("productos") or [])


def _html_seguimiento(nombre, producto):
    return (
        f"<p>Hola {html.escape(nombre)},</p>"
        f"<p>Hace una semana te entregué {html.escape(producto)}. "
        "¿Qué te pareció todo? Respondé este mail y contame, me sirve mucho tu opinión.</p>"
        "<p>Saludos,<br>The Tech Room Arg</p>"
    )


def enviar_seguimientos(client, hoy=None, enviar_email_fn=None):
    enviar_email_fn = enviar_email_fn or email_util.enviar_email
    # Si la columna todavía no existe en la base, esto falla antes de mandar
    # nada: sin poder marcar los pedidos, cada corrida volvería a mailearlos.
    client.table("pedidos").select("id, seguimiento_enviado_en").execute()
    enviados = 0
    fallidos = 0
    for pedido in pedidos_para_notificar(client, hoy=hoy):
        filas = client.table("clientes").select("*").eq("id", pedido["cliente_id"]).execute().data
        email = (filas[0].get("email") or "").strip() if filas else ""
        if not email:
            continue
        try:
            enviar_email_fn(
                email,
                "¿Qué te pareció tu compra? — The Tech Room Arg",
                _html_seguimiento(filas[0].get("nombre") or "", _descripcion_pedido(pedido) or "tu compra"),
                reply_to=REPLY_TO_SEGUIMIENTO,
            )
        except email_util.EnvioEmailError:
            fallidos += 1
            continue
        client.table("pedidos").update({
            "seguimiento_enviado_en": datetime.now(timezone.utc).isoformat(),
        }).eq("id", pedido["id"]).execute()
        enviados += 1
    return {"enviados": enviados, "fallidos": fallidos}
