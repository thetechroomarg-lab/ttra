from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient
from web import mail_cuenta
from web.email_util import EnvioEmailError

DATOS = {"nombre": "maría josé", "apellido": "gómez", "celular": "+54 9 351 555-1234",
         "email": "Maria@X.com", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba", "piso": "3"}


def _admin(monkeypatch, mails=None):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    if mails is not None:
        monkeypatch.setattr(appmod, "enviar_email", lambda d, a, h: mails.append((d, a, h)))
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/admin/clientes/login", json={"password": "clave-admin"})
    return c, fake


def test_alta_requiere_sesion_admin():
    c = TestClient(appmod.app, base_url="https://testserver")
    assert c.post("/admin/clientes/nuevo", json=DATOS).status_code == 401


def test_alta_crea_cuenta_domicilio_y_manda_mail_con_password(monkeypatch):
    mails = []
    c, fake = _admin(monkeypatch, mails)

    r = c.post("/admin/clientes/nuevo", json=DATOS)

    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["mail_enviado"] is True and "password_temporal" not in cuerpo
    cliente = fake.table("clientes").select("*").eq("id", cuerpo["id"]).execute().data[0]
    assert (cliente["nombre"], cliente["apellido"]) == ("María José", "Gómez")
    assert cliente["celular"] == "3515551234" and cliente["email"] == "maria@x.com"
    assert cliente["debe_cambiar_password"] is True and cliente["auth_id"]
    domicilio = fake.table("domicilios_cliente").select("*").eq("cliente_id", cuerpo["id"]).execute().data[0]
    assert domicilio["predeterminado"] and domicilio["piso"] == "3"
    password = fake.auth._passwords["maria@x.com"]
    assert len(mails) == 1
    destinatario, asunto, html = mails[0]
    assert destinatario == "maria@x.com" and asunto == mail_cuenta.ASUNTO
    assert password in html and "María" in html and "/login.html" in html


def test_alta_con_celular_o_email_repetido_da_409(monkeypatch):
    c, _ = _admin(monkeypatch, [])
    assert c.post("/admin/clientes/nuevo", json=DATOS).status_code == 200
    r = c.post("/admin/clientes/nuevo", json={**DATOS, "email": "otro@x.com"})
    assert r.status_code == 409 and "celular" in r.json()["error"]
    r = c.post("/admin/clientes/nuevo", json={**DATOS, "celular": "3519998888"})
    assert r.status_code == 409 and "email" in r.json()["error"]


def test_alta_sin_mail_devuelve_password_para_pasarla_a_mano(monkeypatch):
    c, fake = _admin(monkeypatch)

    def falla(*_):
        raise EnvioEmailError("caído")
    monkeypatch.setattr(appmod, "enviar_email", falla)

    r = c.post("/admin/clientes/nuevo", json=DATOS)

    assert r.status_code == 200
    assert r.json()["mail_enviado"] is False
    assert r.json()["password_temporal"] == fake.auth._passwords["maria@x.com"]


def test_alta_sin_domicilio_no_crea_domicilio(monkeypatch):
    c, fake = _admin(monkeypatch, [])
    datos = {k: v for k, v in DATOS.items() if k not in ("direccion", "piso")}
    r = c.post("/admin/clientes/nuevo", json=datos)
    assert r.status_code == 200
    assert fake.table("domicilios_cliente").select("*").eq("cliente_id", r.json()["id"]).execute().data == []


def test_lista_tiene_boton_y_panel_de_alta(monkeypatch):
    c, _ = _admin(monkeypatch)
    texto = c.get("/admin/clientes/lista").text
    assert 'id="btn-nuevo-cliente"' in texto
    assert '<dialog class="alta-cliente" id="alta-cliente"' in texto
    assert 'fetch("/admin/clientes/nuevo"' in texto
    assert "backdrop-filter" in texto


def test_mail_de_cuenta_escapa_datos():
    html = mail_cuenta.html_cuenta_creada("<b>Ana</b>", "ana@x.com", "Abc<123>")
    assert "<b>Ana</b>" not in html and "&lt;b&gt;Ana" in html
    assert "Abc&lt;123&gt;" in html
