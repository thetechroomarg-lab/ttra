from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_logueado(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    c.post("/api/pedidos", json={"productos": ["iPhone 13"]})
    c.post("/logout")
    c.post("/admin/clientes/login", json={"password": "clave-admin"})
    return c


def test_admin_clientes_lista_nombre_y_link_a_historial(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    r = c.get("/admin/clientes")
    assert r.status_code == 200
    assert "Juan" in r.text
    assert "/historial" in r.text
    assert "Productos consultados" not in r.text


def test_admin_clientes_es_instalable_y_responsive_en_mobile(monkeypatch):
    c = _cliente_logueado(monkeypatch)

    panel = c.get("/admin/clientes")
    manifest = c.get("/admin-clientes.webmanifest")

    assert panel.status_code == 200
    assert '<meta name="viewport" content="width=device-width, initial-scale=1">' in panel.text
    assert '<link rel="manifest" href="/admin-clientes.webmanifest">' in panel.text
    assert 'navigator.serviceWorker.register("/sw.js")' in panel.text
    assert 'class="tabla-scroll"' in panel.text
    assert "@media (max-width: 640px)" in panel.text
    assert manifest.status_code == 200
    assert manifest.json()["start_url"] == "/admin/clientes"
    assert manifest.json()["scope"] == "/admin/clientes"
    assert manifest.json()["display"] == "standalone"


def test_admin_clientes_historial_muestra_pedidos_del_cliente(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    fake.table("interacciones_cliente").insert({
        "id": "inter-1",
        "cliente_id": cliente_id,
        "anon_id": "anon-juan",
        "session_id": "anon-juan",
        "tipo_evento": "view_item",
        "producto_nombre": "iPhone 13",
        "metadata": {},
        "fecha": "2026-08-22T18:35:00+00:00",
    }).execute()

    r = c.get(f"/admin/clientes/{cliente_id}/historial")
    assert r.status_code == 200
    assert "Juan" in r.text
    assert "iPhone 13" in r.text
    assert "view item" in r.text


def test_admin_clientes_historial_muestra_ranking_de_productos_consultados(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    fake.table("interacciones_cliente").insert({
        "id": "inter-1",
        "cliente_id": cliente_id,
        "anon_id": "anon-juan",
        "session_id": "anon-juan",
        "tipo_evento": "view_item",
        "producto_nombre": "iPhone 13",
        "metadata": {},
        "fecha": "2026-08-22T18:35:00+00:00",
    }).execute()
    fake.table("interacciones_cliente").insert({
        "id": "inter-2",
        "cliente_id": cliente_id,
        "anon_id": "anon-juan",
        "session_id": "anon-juan",
        "tipo_evento": "view_item",
        "producto_nombre": "iPhone 13",
        "metadata": {},
        "fecha": "2026-08-22T18:36:00+00:00",
    }).execute()
    fake.table("interacciones_cliente").insert({
        "id": "inter-3",
        "cliente_id": cliente_id,
        "anon_id": "anon-juan",
        "session_id": "anon-juan",
        "tipo_evento": "view_item",
        "producto_nombre": "Galaxy A56",
        "metadata": {},
        "fecha": "2026-08-22T18:37:00+00:00",
    }).execute()

    r = c.get(f"/admin/clientes/{cliente_id}/historial")

    assert r.status_code == 200
    assert "Productos más consultados" in r.text
    assert "Ranking por cantidad de vistas" in r.text
    assert "iPhone 13</td><td>2</td>" in r.text
    assert "Galaxy A56</td><td>1</td>" in r.text
    assert r.text.index("iPhone 13</td><td>2</td>") < r.text.index("Galaxy A56</td><td>1</td>")


def test_admin_envia_mailing_solo_con_productos_disponibles(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [
            {"nombre": "iPhone 13", "categoria": "Apple - iPhone", "usd": 560, "pesos": 873600, "transferencia": 900619},
            {"nombre": "Galaxy A56", "categoria": "Samsung", "usd": 300, "pesos": 468000, "transferencia": 482474},
        ],
    )
    mails_enviados = []
    monkeypatch.setattr(
        appmod, "enviar_email",
        lambda destinatario, asunto, html: mails_enviados.append((destinatario, asunto, html)),
    )

    r = c.post(
        f"/admin/clientes/{cliente_id}/mailing-oferta",
        json={"productos": ["iPhone 13", "Galaxy A56", "No existe"]},
    )

    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["enviados"] == 2
    assert r.json()["omitidos"] == ["No existe"]
    assert r.json()["codigo"].startswith("TTRA-")
    assert len(mails_enviados) == 1
    assert mails_enviados[0][0] == "juan@x.com"
    assert "iPhone 13" in mails_enviados[0][2]
    assert "Galaxy A56" in mails_enviados[0][2]
    assert "No existe" not in mails_enviados[0][2]
    assert "U$D 5 de descuento" in mails_enviados[0][2]
    assert "USD billete: U$D 555" in mails_enviados[0][2]
    assert "Dólar banco USA: U$D 570" in mails_enviados[0][2]
    assert "USDT: U$D 561" in mails_enviados[0][2]
    assert "Pesos contado: $ 865.800" in mails_enviados[0][2]
    assert "Transferencia en pesos: $ 892.578" in mails_enviados[0][2]
    assert "te ofrezco" in mails_enviados[0][2]
    assert "te armo la propuesta" in mails_enviados[0][2]
    assert r.json()["codigo"] in mails_enviados[0][2]
    assert f"codigo={r.json()['codigo']}" in mails_enviados[0][2]
    assert "agregar=1" in mails_enviados[0][2]
    assert "producto=iPhone+13" in mails_enviados[0][2]
    filas_codigo = fake.table("codigos_descuento").select("*").eq("code", r.json()["codigo"]).execute().data
    assert len(filas_codigo) == 1
    assert filas_codigo[0]["cliente_id"] == cliente_id
    assert filas_codigo[0]["activo"] is True
    assert filas_codigo[0]["productos"] == ["iPhone 13", "Galaxy A56"]


def test_admin_mailing_falla_si_nada_sigue_disponible(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [{"nombre": "Galaxy A56", "categoria": "Samsung"}])

    r = c.post(
        f"/admin/clientes/{cliente_id}/mailing-oferta",
        json={"productos": ["iPhone 13"]},
    )

    assert r.status_code == 400
    assert "sigue disponible" in r.json()["error"].lower()


def test_admin_mailing_informa_si_falta_tabla_codigos_descuento(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [{"nombre": "iPhone 13", "categoria": "Apple - iPhone", "usd": 560, "pesos": 873600, "transferencia": 900619}],
    )

    class ClientSinCodigos:
        def table(self, nombre):
            if nombre == "codigos_descuento":
                raise Exception('relation "codigos_descuento" does not exist')
            return fake.table(nombre)

    monkeypatch.setattr(appmod, "get_client", lambda: ClientSinCodigos())

    r = c.post(
        f"/admin/clientes/{cliente_id}/mailing-oferta",
        json={"productos": ["iPhone 13"]},
    )

    assert r.status_code == 503
    assert "codigos_descuento" in r.json()["error"]


def test_admin_clientes_historial_requiere_sesion_admin():
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/admin/clientes/algun-id/historial", follow_redirects=False)
    assert r.status_code in (302, 307)


def test_admin_clientes_historial_cliente_inexistente(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    r = c.get("/admin/clientes/id-que-no-existe/historial")
    assert r.status_code == 404


def test_admin_resetea_password_y_manda_mail(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]

    mails_enviados = []
    monkeypatch.setattr(
        appmod, "enviar_email",
        lambda destinatario, asunto, html: mails_enviados.append((destinatario, asunto, html)),
    )

    r = c.post(f"/admin/clientes/{cliente_id}/resetear-password")

    assert r.status_code == 200
    assert len(mails_enviados) == 1
    assert mails_enviados[0][0] == "juan@x.com"


def test_admin_resetea_password_requiere_sesion_admin():
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/admin/clientes/algun-id/resetear-password")
    assert r.status_code == 401


def test_admin_resetea_password_cliente_inexistente(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    r = c.post("/admin/clientes/id-que-no-existe/resetear-password")
    assert r.status_code == 400
