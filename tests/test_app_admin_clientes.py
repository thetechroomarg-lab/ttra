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
    "provincia": "Córdoba",
    })
    c.post("/api/pedidos", json={"productos": ["iPhone 13"]})
    c.post("/logout")
    c.post("/admin/clientes/login", json={"password": "clave-admin"})
    return c


def test_admin_clientes_lista_nombre_y_link_a_historial(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    r = c.get("/admin/clientes/lista")
    assert r.status_code == 200
    assert "Juan" in r.text
    assert "/historial" in r.text
    assert "Productos consultados" not in r.text


def test_landing_admin_separa_clientes_en_una_vista_accesible(monkeypatch):
    c = _cliente_logueado(monkeypatch)

    r = c.get("/admin/clientes")

    assert 'href="/admin/clientes/lista"' in r.text
    assert "Clientes" in r.text
    assert "Buscar por nombre, email, celular o provincia" not in r.text


def test_admin_historial_muestra_el_icono_de_calendario_claro(monkeypatch):
    c = _cliente_logueado(monkeypatch)

    r = c.get("/admin/clientes")

    assert 'color-scheme:dark' in r.text
    assert '#fecha-historial-pedidos::-webkit-calendar-picker-indicator' in r.text
    assert 'filter:none' in r.text


def test_admin_apila_controles_y_muestra_clientes_como_tarjetas_en_mobile(monkeypatch):
    c = _cliente_logueado(monkeypatch)

    r = c.get("/admin/clientes/lista")

    assert ".filtros-clientes { flex-direction:column; }" in r.text
    assert ".pedido-hoy { align-items:stretch; flex-direction:column; }" in r.text
    assert "overflow-wrap:anywhere" in r.text
    assert ".tabla-scroll { overflow:visible; }" in r.text
    assert "#tabla-clientes thead { display:none; }" in r.text
    assert '#tabla-clientes td:nth-child(2)::before { content:"Nombre"; }' in r.text
    assert "#tabla-clientes, #tabla-clientes tbody, #tabla-clientes tr, #tabla-clientes td" in r.text
    assert "#filtro-clientes { flex:0 1 auto; min-height:38px; }" in r.text
    assert "#tabla-clientes .col-check { justify-content:flex-start; text-align:left; }" in r.text
    assert ".pedido-acciones > * { box-sizing:border-box; flex:1 1 140px; min-height:42px; }" in r.text
    assert ".pedido-acciones .btn-direcciones, .pedido-acciones .btn-agregar-direccion { align-items:center; display:flex; justify-content:center; }" in r.text
    assert ".pedido-acciones .btn-enviar-recibo { grid-area:recibo; }" in r.text
    assert ".pedido-acciones .btn-direcciones { grid-area:direcciones; }" in r.text
    assert ".pedido-acciones .btn-editar-entrega { grid-area:editar; }" in r.text
    assert ".pedido-acciones .btn-eliminar-entrega { grid-area:eliminar; }" in r.text
    assert 'grid-template-areas:"recibo direcciones" "editar eliminar"' in r.text


def test_admin_muestra_pedidos_programados_para_hoy(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "pedido-hoy", "cliente_id": cliente["id"], "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24",
    }).execute()
    monkeypatch.setattr(appmod.entregas, "ahora_argentina", lambda: __import__("datetime").datetime(2026, 8, 24, 10, 0, tzinfo=appmod.entregas.ZONA_HORARIA))

    r = c.get("/admin/clientes")

    assert "Pedidos pendientes para hoy" in r.text
    assert "iPhone 13" in r.text


def test_admin_muestra_el_proveedor_solo_en_el_detalle_interno(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "pedido-proveedor", "cliente_id": cliente["id"], "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1, "proveedor": "az"}],
    }).execute()
    monkeypatch.setattr(appmod.entregas, "ahora_argentina", lambda: __import__("datetime").datetime(2026, 8, 24, 10, 0, tzinfo=appmod.entregas.ZONA_HORARIA))

    r = c.get("/admin/clientes")

    assert r.status_code == 200
    assert "Proveedor: az" in r.text


def test_admin_envia_recibo_y_marca_el_pedido(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "pedido-recibo", "cliente_id": cliente["id"], "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{
            "nombre": "iPhone 13", "color": "Negro", "cantidad": 1,
            "usd_unitario": 500, "usd_subtotal": 500,
        }],
        "total_usd": 500,
        "descuento_usd": 0,
    }).execute()
    enviados = []
    monkeypatch.setattr(appmod, "enviar_email", lambda *args: enviados.append(args))

    r = c.post("/admin/pedidos/pedido-recibo/recibo")

    assert r.status_code == 200
    assert enviados[0][0] == "juan@x.com"
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-recibo").execute().data[0]
    assert pedido["recibo_id"] == "0001-1993"
    assert pedido["recibo_enviado_en"]
    assert enviados[0][3][0]["filename"] == "recibo-0001-1993.pdf"


def test_admin_reenvia_recibo_y_conserva_la_fecha_original(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    original = "2026-08-20T15:00:00+00:00"
    fake.table("pedidos").insert({
        "id": "pedido-reenvio", "cliente_id": cliente["id"], "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24", "recibo_id": "TTRA-ORIGINAL",
        "recibo_enviado_en": original,
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
    }).execute()
    monkeypatch.setattr(appmod, "enviar_email", lambda *args: None)

    r = c.post("/admin/pedidos/pedido-reenvio/recibo")

    assert r.status_code == 200
    assert r.json()["reenviado"] is True
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-reenvio").execute().data[0]
    assert pedido["recibo_emitido_en"] == original
    assert pedido["recibo_enviado_en"] != original


def test_pdf_recibo_requiere_admin_y_recibo_emitido(monkeypatch):
    anon = TestClient(appmod.app, base_url="https://testserver")
    assert anon.get("/admin/pedidos/cualquiera/recibo.pdf").status_code == 401

    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "pendiente-pdf", "cliente_id": cliente["id"], "productos": ["iPhone 13"],
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
    }).execute()

    assert c.get("/admin/pedidos/pendiente-pdf/recibo.pdf").status_code == 400


def test_admin_muestra_solo_pedidos_hoy_pendientes_de_recibo(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    for pedido in (
        {"id": "pendiente", "recibo_enviado_en": None, "productos": ["Galaxy A56"]},
        {"id": "emitido", "recibo_enviado_en": "2026-08-24T12:00:00+00:00", "productos": ["iPhone 15"]},
    ):
        fake.table("pedidos").insert({
            **pedido, "cliente_id": cliente["id"], "fecha_entrega": "2026-08-24",
            "detalle": [{"nombre": pedido["productos"][0], "cantidad": 1, "usd_unitario": 300, "usd_subtotal": 300}],
            "total_usd": 300,
        }).execute()
    monkeypatch.setattr(appmod.entregas, "ahora_argentina", lambda: __import__("datetime").datetime(2026, 8, 24, 10, 0, tzinfo=appmod.entregas.ZONA_HORARIA))

    r = c.get("/admin/clientes")

    assert "Pedidos pendientes para hoy (1)" in r.text
    assert "Galaxy A56" in r.text
    assert 'data-pedido-id="pendiente"' in r.text
    assert 'data-pedido-id="emitido"' not in r.text


def test_admin_muestra_historial_de_pedidos_para_la_fecha_elegida(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "historico", "cliente_id": cliente["id"], "productos": ["Notebook Lenovo"],
        "fecha_entrega": "2026-08-20", "recibo_id": "TTRA-ABCD1234",
        "recibo_enviado_en": "2026-08-20T15:00:00+00:00",
        "detalle": [{"nombre": "Notebook Lenovo", "cantidad": 1, "usd_unitario": 700, "usd_subtotal": 700}],
        "total_usd": 700,
    }).execute()

    r = c.get("/admin/clientes?fecha_pedidos=2026-08-20")

    assert "Historial de pedidos" in r.text
    assert 'value="2026-08-20"' in r.text
    assert "Notebook Lenovo" in r.text
    assert "Recibo enviado" in r.text
    assert 'class="btn-ver-recibo-pdf"' in r.text
    assert 'class="btn-reenviar-recibo"' in r.text


def test_admin_historial_oculta_pendientes_y_pedidos_de_otras_fechas(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "pendiente-hoy", "cliente_id": cliente["id"], "productos": ["Galaxy A56"],
        "fecha_entrega": "2026-08-24", "detalle": [{"nombre": "Galaxy A56", "cantidad": 1}], "total_usd": 300,
    }).execute()
    fake.table("pedidos").insert({
        "id": "emitido-ayer", "cliente_id": cliente["id"], "productos": ["iPhone 15"],
        "fecha_entrega": "2026-08-23", "recibo_enviado_en": "2026-08-23T18:00:00+00:00",
        "detalle": [{"nombre": "iPhone 15", "cantidad": 1}], "total_usd": 500,
    }).execute()
    monkeypatch.setattr(appmod.entregas, "ahora_argentina", lambda: __import__("datetime").datetime(2026, 8, 24, 10, 0, tzinfo=appmod.entregas.ZONA_HORARIA))

    r = c.get("/admin/clientes?fecha_pedidos=2026-08-23")

    assert "iPhone 15" in r.text
    assert "Galaxy A56" not in r.text
    assert "Pedidos pendientes para hoy" not in r.text


def test_admin_puede_editar_y_eliminar_una_entrega_pendiente(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "editable", "cliente_id": cliente["id"], "productos": ["Galaxy A56"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{"nombre": "Galaxy A56", "cantidad": 1, "usd_unitario": 300, "usd_subtotal": 300}],
        "total_usd": 300,
    }).execute()
    monkeypatch.setattr(appmod.entregas, "ahora_argentina", lambda: __import__("datetime").datetime(2026, 8, 24, 10, 0, tzinfo=appmod.entregas.ZONA_HORARIA))

    editar = c.put("/admin/pedidos/editable/fecha-entrega", json={"fecha_entrega": "2026-08-25"})

    assert editar.status_code == 200
    assert fake.table("pedidos").select("*").eq("id", "editable").execute().data[0]["fecha_entrega"] == "2026-08-25"
    eliminar = c.delete("/admin/pedidos/editable")
    assert eliminar.status_code == 200
    assert fake.table("pedidos").select("*").eq("id", "editable").execute().data == []


def test_admin_puede_agregar_direccion_a_una_entrega_pendiente(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "sin-direccion", "cliente_id": cliente["id"], "productos": ["Galaxy A56"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{"nombre": "Galaxy A56", "cantidad": 1, "usd_unitario": 300, "usd_subtotal": 300}],
        "total_usd": 300,
    }).execute()
    monkeypatch.setattr(appmod.entregas, "ahora_argentina", lambda: __import__("datetime").datetime(2026, 8, 24, 10, 0, tzinfo=appmod.entregas.ZONA_HORARIA))

    panel = c.get("/admin/clientes")
    guardar = c.put("/admin/pedidos/sin-direccion/direccion", json={"direccion_entrega": "Av. Colón 123, Córdoba"})

    assert 'class="btn-agregar-direccion"' in panel.text
    assert "Agregar dirección" in panel.text
    assert 'id="modal-direccion"' in panel.text
    assert 'id="direccion-entrega-admin"' in panel.text
    assert 'id="modal-series"' in panel.text
    assert guardar.status_code == 200
    pedido = fake.table("pedidos").select("*").eq("id", "sin-direccion").execute().data[0]
    assert pedido["direccion_entrega"] == "Av. Colón 123, Córdoba"


def test_admin_centra_los_paneles_flotantes_en_todas_las_resoluciones(monkeypatch):
    c = _cliente_logueado(monkeypatch)

    panel = c.get("/admin/clientes")

    assert ".modal-series, .modal-direccion { display:flex;" in panel.text


def test_admin_ubica_historial_arriba_y_muestra_controles_de_entrega(monkeypatch):
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "con-controles", "cliente_id": cliente["id"], "productos": ["Galaxy A56"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{"nombre": "Galaxy A56", "cantidad": 1, "usd_unitario": 300, "usd_subtotal": 300}],
        "total_usd": 300,
    }).execute()
    monkeypatch.setattr(appmod.entregas, "ahora_argentina", lambda: __import__("datetime").datetime(2026, 8, 24, 10, 0, tzinfo=appmod.entregas.ZONA_HORARIA))

    r = c.get("/admin/clientes")

    assert r.text.index("Historial de pedidos") < r.text.index("Pedidos pendientes para hoy")
    assert 'class="btn-editar-entrega"' in r.text
    assert 'class="btn-eliminar-entrega"' in r.text


def test_admin_clientes_es_instalable_y_responsive_en_mobile(monkeypatch):
    c = _cliente_logueado(monkeypatch)

    panel = c.get("/admin/clientes/lista")
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
    assert 'href="/admin/clientes/lista"' in r.text


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
