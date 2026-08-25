from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _admin_con_clientes(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    for nombre, celular, email, provincia in (
        ("Ana", "3511000001", "ana@x.com", "Córdoba"),
        ("Bruno", "3511000002", "bruno@x.com", "Santa Fe"),
    ):
        respuesta = cliente.post("/registro", json={
            "nombre": nombre, "apellido": "Cliente", "celular": celular,
            "email": email, "password": "clave1234", "provincia": provincia,
        })
        assert respuesta.status_code == 200
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})
    filas = fake.table("clientes").select("*").execute().data
    return cliente, fake, [fila["id"] for fila in filas]


def test_admin_lista_checkboxes_provincia_y_columnas_ordenables(monkeypatch):
    cliente, _fake, _ids = _admin_con_clientes(monkeypatch)

    respuesta = cliente.get("/admin/clientes/lista")

    assert respuesta.status_code == 200
    assert 'id="seleccionar-todos"' in respuesta.text
    assert 'class="cliente-check"' in respuesta.text
    assert "Provincia" in respuesta.text
    assert "Córdoba" in respuesta.text
    assert 'data-sort="nombre"' in respuesta.text
    assert 'data-sort="provincia"' in respuesta.text
    assert 'data-sort="fecha"' not in respuesta.text
    assert ">Fecha<" not in respuesta.text
    assert 'id="filtro-clientes"' in respuesta.text
    assert 'id="filtro-provincia"' in respuesta.text
    assert 'id="ordenar-clientes"' in respuesta.text
    assert "Santa Fe" in respuesta.text
    assert 'id="mail-mensaje" class="mail-editor" contenteditable="true"' in respuesta.text
    assert 'id="mail-insertar-nombre"' not in respuesta.text
    assert 'mailMensaje.innerHTML.trim()' in respuesta.text


def test_admin_envia_mail_a_clientes_seleccionados(monkeypatch):
    cliente, _fake, ids = _admin_con_clientes(monkeypatch)
    enviados = []
    monkeypatch.setattr(
        appmod,
        "enviar_email",
        lambda destinatario, asunto, cuerpo: enviados.append((destinatario, asunto, cuerpo)),
    )

    respuesta = cliente.post(
        "/admin/clientes/acciones/enviar-mail",
        json={"cliente_ids": ids, "mensaje": "Tenemos novedades para vos."},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "enviados": 2, "fallidos": 0}
    assert [mail[0] for mail in enviados] == ["ana@x.com", "bruno@x.com"]
    assert all(mail[1] == "Novedades de The Tech Room Arg" for mail in enviados)
    assert all("Tenemos novedades para vos." in mail[2] for mail in enviados)


def test_admin_envia_mail_rich_text_personalizado_y_seguro(monkeypatch):
    cliente, _fake, ids = _admin_con_clientes(monkeypatch)
    enviados = []
    monkeypatch.setattr(
        appmod,
        "enviar_email",
        lambda destinatario, asunto, cuerpo: enviados.append((destinatario, asunto, cuerpo)),
    )

    respuesta = cliente.post(
        "/admin/clientes/acciones/enviar-mail",
        json={
            "cliente_ids": ids,
            "mensaje": (
                "<p><strong>Oferta especial</strong></p>"
                "<div>Texto en otro párrafo</div><ul><li>Un beneficio</li></ul>"
                "<script>alert('no')</script>"
            ),
        },
    )

    assert respuesta.status_code == 200
    cuerpo_ana = next(cuerpo for email, _asunto, cuerpo in enviados if email == "ana@x.com")
    cuerpo_bruno = next(cuerpo for email, _asunto, cuerpo in enviados if email == "bruno@x.com")
    assert cuerpo_ana.startswith("<p>Hola Ana,</p>")
    assert cuerpo_bruno.startswith("<p>Hola Bruno,</p>")
    assert "<strong>Oferta especial</strong>" in cuerpo_ana
    assert "<p>Texto en otro párrafo</p>" in cuerpo_ana
    assert "<ul><li>Un beneficio</li></ul>" in cuerpo_ana
    assert "<script" not in cuerpo_ana
    assert "alert('no')" not in cuerpo_ana
    assert cuerpo_ana.endswith("<p>Saludos,<br>Vlad.</p>")


def test_admin_elimina_varias_cuentas_seleccionadas(monkeypatch):
    cliente, fake, ids = _admin_con_clientes(monkeypatch)

    respuesta = cliente.post(
        "/admin/clientes/acciones/eliminar",
        json={"cliente_ids": ids},
    )

    assert respuesta.status_code == 200
    assert respuesta.json() == {"ok": True, "eliminados": 2}
    assert fake.table("clientes").select("*").execute().data == []
    assert fake.auth._usuarios_por_email == {}


def test_acciones_masivas_requieren_sesion_admin(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    cliente = TestClient(appmod.app, base_url="https://testserver")

    respuesta = cliente.post(
        "/admin/clientes/acciones/eliminar",
        json={"cliente_ids": ["cliente-id"]},
    )

    assert respuesta.status_code == 401
