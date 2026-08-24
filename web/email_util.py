import os
import base64

import httpx

REMITENTE = "The Tech Room Arg <noreply@thetechroomarg.com>"


class EnvioEmailError(Exception):
    pass


def enviar_email(destinatario, asunto, html, adjuntos=None):
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
