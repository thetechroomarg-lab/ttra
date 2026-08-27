from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _admin_logueado(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/admin/clientes/login", json={"password": "clave-admin"})
    return c, fake


def _cadete_logueado():
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    return c


def test_cadete_no_puede_entrar_con_contrasena_incorrecta():
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/admin/cadete/login", json={"password": "mala"})
    assert r.status_code == 401
    assert "Panel de entregas" in c.get("/admin/cadete").text


def test_cadete_ve_solo_las_entregas_que_se_le_derivaron(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fecha_hoy = appmod.entregas.ahora_argentina().date().isoformat()
    fake.table("pedidos").insert({
        "id": "pedido-1", "fecha_entrega": fecha_hoy, "productos": ["iPhone 13"],
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1}], "total_usd": 500,
        "direccion_entrega": "Av. Colón 123",
    }).execute()
    fake.table("pedidos").insert({
        "id": "pedido-2", "fecha_entrega": fecha_hoy, "productos": ["Galaxy A56"],
        "detalle": [{"nombre": "Galaxy A56", "cantidad": 1}], "total_usd": 300,
    }).execute()
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": fecha_hoy, "titulo": "Retirar equipo", "orden": 1,
    }).execute()

    admin.put("/admin/pedidos/pedido-1/derivar", json={"derivado": True})
    admin.put("/admin/tareas-entrega/tarea-1/derivar", json={"derivado": True})

    cadete = _cadete_logueado()
    r = cadete.get("/admin/cadete")

    assert 'data-id="pedido-1"' in r.text
    assert "Retirar equipo" in r.text
    assert 'data-id="pedido-2"' not in r.text
    assert "Vamos" in r.text
    assert "Nueva tarea" not in r.text
    assert 'class="btn-editar-entrega"' not in r.text
    assert 'class="btn-eliminar-entrega"' not in r.text


def test_cadete_ve_boton_de_whatsapp_del_cliente(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fecha_hoy = appmod.entregas.ahora_argentina().date().isoformat()
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
    }).execute()
    fake.table("pedidos").insert({
        "id": "pedido-1", "cliente_id": "cliente-1", "fecha_entrega": fecha_hoy,
        "productos": ["iPhone 13"], "detalle": [{"nombre": "iPhone 13", "cantidad": 1}],
        "total_usd": 500,
    }).execute()
    admin.put("/admin/pedidos/pedido-1/derivar", json={"derivado": True})

    r = _cadete_logueado().get("/admin/cadete")

    assert 'class="btn-whatsapp-cliente" href="https://wa.me/5493511234567"' in r.text


def test_admin_ve_boton_derivar_y_al_derivar_pasa_a_quitar(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fecha_hoy = appmod.entregas.ahora_argentina().date().isoformat()
    fake.table("pedidos").insert({
        "id": "pedido-1", "fecha_entrega": fecha_hoy, "productos": ["iPhone 13"],
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1}], "total_usd": 500,
    }).execute()

    r = admin.get("/admin/clientes")
    assert 'class="btn-derivar-entrega" type="button" data-id="pedido-1" data-tipo="pedido"' in r.text

    derivar = admin.put("/admin/pedidos/pedido-1/derivar", json={"derivado": True})
    assert derivar.status_code == 200
    assert fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]["asignado_a"] == "alejo"

    r = admin.get("/admin/clientes")
    assert "Derivado a Alejo" in r.text
    assert 'class="btn-quitar-derivacion" type="button" data-id="pedido-1" data-tipo="pedido"' in r.text

    quitar = admin.put("/admin/pedidos/pedido-1/derivar", json={"derivado": False})
    assert quitar.status_code == 200
    assert fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]["asignado_a"] is None


def test_cadete_ve_las_observaciones_y_el_total_a_cobrar(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fecha_hoy = appmod.entregas.ahora_argentina().date().isoformat()
    fake.table("pedidos").insert({
        "id": "pedido-1", "fecha_entrega": fecha_hoy, "productos": ["iPhone 13"],
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1}], "total_usd": 500,
    }).execute()

    admin.put("/admin/pedidos/pedido-1/derivar", json={
        "derivado": True, "observaciones": "Dejar en portería",
    })
    fila = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    assert fila["observaciones_cadete"] == "Dejar en portería"

    r = _cadete_logueado().get("/admin/cadete")
    assert "Observaciones: Dejar en portería" in r.text
    assert "Total a cobrar: U$D 500" in r.text

    admin.put("/admin/pedidos/pedido-1/derivar", json={"derivado": False})
    fila = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    assert fila["observaciones_cadete"] is None


def test_recibo_enviado_por_cadete_marca_entregado_por_alejo(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    cliente_id = "cliente-1"
    fake.table("clientes").insert({
        "id": cliente_id, "nombre": "Juan", "apellido": "Pérez", "email": "juan@x.com",
    }).execute()
    fake.table("pedidos").insert({
        "id": "pedido-1", "cliente_id": cliente_id, "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
    }).execute()
    admin.put("/admin/pedidos/pedido-1/derivar", json={"derivado": True})

    enviados = []
    monkeypatch.setattr(appmod, "enviar_email", lambda *args: enviados.append(args))

    cadete = _cadete_logueado()
    r = cadete.post("/admin/pedidos/pedido-1/recibo")

    assert r.status_code == 200
    assert "Entregado por Alejo" in enviados[0][2]
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    assert pedido["observaciones_cadete"] == "Entregado por Alejo"


def test_recibo_enviado_por_cadete_conserva_las_instrucciones_previas(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Juan", "apellido": "Pérez", "email": "juan@x.com",
    }).execute()
    fake.table("pedidos").insert({
        "id": "pedido-1", "cliente_id": "cliente-1", "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
    }).execute()
    admin.put("/admin/pedidos/pedido-1/derivar", json={
        "derivado": True, "observaciones": "Dejar en portería",
    })
    monkeypatch.setattr(appmod, "enviar_email", lambda *args: None)

    cadete = _cadete_logueado()
    r = cadete.post("/admin/pedidos/pedido-1/recibo")

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    assert pedido["observaciones_cadete"] == "Dejar en portería · Entregado por Alejo"


def test_recibo_enviado_por_admin_no_marca_entregado_por_alejo(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Juan", "apellido": "Pérez", "email": "juan@x.com",
    }).execute()
    fake.table("pedidos").insert({
        "id": "pedido-1", "cliente_id": "cliente-1", "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
    }).execute()

    enviados = []
    monkeypatch.setattr(appmod, "enviar_email", lambda *args: enviados.append(args))

    r = admin.post("/admin/pedidos/pedido-1/recibo")

    assert r.status_code == 200
    assert "Entregado por Alejo" not in enviados[0][2]
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    assert pedido.get("observaciones_cadete") is None


def test_tarea_completada_por_cadete_marca_entregado_por_alejo(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24", "titulo": "Retirar equipo", "orden": 1,
    }).execute()
    admin.put("/admin/tareas-entrega/tarea-1/derivar", json={"derivado": True})

    cadete = _cadete_logueado()
    r = cadete.post("/admin/tareas-entrega/tarea-1/completar")

    assert r.status_code == 200
    tarea = fake.table("tareas_entrega").select("*").eq("id", "tarea-1").execute().data[0]
    assert tarea["observaciones_cadete"] == "Entregado por Alejo"


def test_cadete_no_puede_operar_una_entrega_que_no_le_derivaron(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fecha_hoy = appmod.entregas.ahora_argentina().date().isoformat()
    fake.table("pedidos").insert({
        "id": "pedido-1", "fecha_entrega": fecha_hoy, "productos": ["iPhone 13"],
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1}], "total_usd": 500,
    }).execute()
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": fecha_hoy, "titulo": "Retirar equipo", "orden": 1,
    }).execute()

    cadete = _cadete_logueado()

    r = cadete.post("/admin/pedidos/pedido-1/recibo")
    assert r.status_code == 403

    r = cadete.post("/admin/tareas-entrega/tarea-1/completar")
    assert r.status_code == 403


def test_cadete_puede_completar_una_tarea_derivada(monkeypatch):
    admin, fake = _admin_logueado(monkeypatch)
    fecha_hoy = appmod.entregas.ahora_argentina().date().isoformat()
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": fecha_hoy, "titulo": "Retirar equipo", "orden": 1,
    }).execute()
    admin.put("/admin/tareas-entrega/tarea-1/derivar", json={"derivado": True})

    cadete = _cadete_logueado()
    r = cadete.post("/admin/tareas-entrega/tarea-1/completar")

    assert r.status_code == 200
    assert fake.table("tareas_entrega").select("*").eq("id", "tarea-1").execute().data[0]["completada_en"]


def test_cadete_no_puede_crear_tareas_ni_derivar(monkeypatch):
    _admin_logueado(monkeypatch)
    cadete = _cadete_logueado()

    r = cadete.post("/admin/tareas-entrega", json={
        "fecha_entrega": appmod.entregas.ahora_argentina().date().isoformat(),
        "titulo": "Intento de tarea", "cliente_nombre": "Cliente",
    })
    assert r.status_code == 401

    r = cadete.put("/admin/pedidos/pedido-1/derivar", json={"derivado": True})
    assert r.status_code == 401
