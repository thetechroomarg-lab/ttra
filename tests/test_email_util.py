import httpx
import pytest

from web import email_util


class _RespuestaOk:
    status_code = 200
    text = ""


def _capturar_envio(monkeypatch):
    capturado = {}

    def post_falso(url, headers, json, timeout):
        capturado["json"] = json
        return _RespuestaOk()

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("RESEND_API_KEY", "clave-falsa")
    monkeypatch.setattr(httpx, "post", post_falso)
    return capturado


def test_enviar_email_sigue_bloqueado_dentro_de_un_test():
    with pytest.raises(email_util.EnvioEmailError):
        email_util.enviar_email("cliente@x.com", "Asunto", "<p>hola</p>")


def test_enviar_email_con_reply_to_lo_manda_a_resend(monkeypatch):
    capturado = _capturar_envio(monkeypatch)

    email_util.enviar_email("cliente@x.com", "Asunto", "<p>hola</p>", reply_to="contacto@thetechroomarg.com")

    assert capturado["json"]["reply_to"] == ["contacto@thetechroomarg.com"]


def test_enviar_email_sin_reply_to_no_manda_la_clave(monkeypatch):
    capturado = _capturar_envio(monkeypatch)

    email_util.enviar_email("cliente@x.com", "Asunto", "<p>hola</p>")

    assert "reply_to" not in capturado["json"]
