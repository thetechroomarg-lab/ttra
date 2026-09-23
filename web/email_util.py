import os
import base64

import httpx

REMITENTE = "The Tech Room Arg <noreply@thetechroomarg.com>"


class EnvioEmailError(Exception):
    pass


def enviar_email(destinatario, asunto, html, adjuntos=None):
    if os.environ.get("PYTEST_CURRENT_TEST"):
        # Nunca un mail real desde un test. Si de verdad querés probar el envío,
        # mockeá esta función (o `enviar_email` en el módulo que la importa) —
        # no la dejes pasar de largo hasta acá.
        raise EnvioEmailError(
            "enviar_email() bloqueado: se está corriendo dentro de un test "
            "(PYTEST_CURRENT_TEST) y no se mockeó. Un envío real desde un test "
            "le mandaría mails de prueba a un destinatario real."
        )
    api_key = os.environ.get("RESEND_API_KEY")
    if not api_key:
        raise EnvioEmailError("RESEND_API_KEY no configurado")
    r = httpx.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "from": REMITENTE, "to": [destinatario], "subject": asunto, "html": html,
            "attachments": [
                {"filename": adjunto["filename"], "content": base64.b64encode(adjunto["content"]).decode("ascii")}
                for adjunto in (adjuntos or [])
            ],
        },
        timeout=10,
    )
    if r.status_code >= 400:
        raise EnvioEmailError(f"Resend devolvió {r.status_code}: {r.text}")
