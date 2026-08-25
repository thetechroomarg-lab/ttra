from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_admin_puede_crear_tarea_manual_de_entrega(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})

    respuesta = cliente.post("/admin/tareas-entrega", json={
        "fecha_entrega": "2026-08-24",
        "titulo": "Retirar packaging",
        "nota": "Antes de salir",
        "direccion": "Av. Colón 123, Córdoba",
    })

    assert respuesta.status_code == 200
    tarea = fake.table("tareas_entrega").select("*").execute().data[0]
    assert tarea["titulo"] == "Retirar packaging"
    assert tarea["direccion"] == "Av. Colón 123, Córdoba"


def test_admin_guarda_el_cliente_elegido_en_una_tarea_manual(monkeypatch):
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Vladimir", "apellido": "Ostapoff",
        "celular": "3510000000", "email": "vladimir@example.com",
    }).execute()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})

    respuesta = cliente.post("/admin/tareas-entrega", json={
        "fecha_entrega": "2026-08-24",
        "titulo": "Visitar cliente",
        "cliente_id": "cliente-1",
    })

    assert respuesta.status_code == 200
    tarea = fake.table("tareas_entrega").select("*").execute().data[0]
    assert tarea["cliente_id"] == "cliente-1"


def test_panel_admin_muestra_selector_y_nombre_del_cliente_de_la_tarea(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Vladimir", "apellido": "Ostapoff",
        "celular": "3510000000", "email": "vladimir@example.com",
    }).execute()
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24", "titulo": "Visitar cliente",
        "cliente_id": "cliente-1", "orden": 1,
    }).execute()

    respuesta = cliente.get("/admin/clientes")

    assert 'id="tarea-cliente"' in respuesta.text
    assert '<option value="cliente-1" data-direccion="">Vladimir Ostapoff</option>' in respuesta.text
    assert "Cliente: Vladimir Ostapoff" in respuesta.text


def test_selector_de_cliente_de_tarea_incluye_la_direccion_guardada(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("clientes").insert({
        "id": "cliente-2", "nombre": "Impo", "apellido": "Cba",
        "celular": "3510000001", "email": None, "direccion": "Pardos y Morenos 1784, Cordoba",
    }).execute()

    respuesta = cliente.get("/admin/clientes")

    assert 'data-direccion="Pardos y Morenos 1784, Cordoba"' in respuesta.text


def test_panel_admin_usa_selector_de_clientes_grande_y_scrolleable_en_mobile(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Vladimir", "apellido": "Ostapoff",
        "celular": "3510000000", "email": "vladimir@example.com",
    }).execute()

    respuesta = cliente.get("/admin/clientes")

    assert 'id="tarea-cliente-movil"' in respuesta.text
    assert 'id="tarea-clientes-movil"' in respuesta.text
    assert "max-height:260px" in respuesta.text
    assert "overflow-y:auto" in respuesta.text
    assert 'document.getElementById("tarea-cliente").value = boton.dataset.value' in respuesta.text


def test_panel_admin_estiliza_el_formulario_de_tareas(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})

    respuesta = cliente.get("/admin/clientes")

    assert 'id="form-tarea-entrega"' in respuesta.text
    assert ".form-tarea-entrega input" in respuesta.text
    assert ".form-tarea-entrega button" in respuesta.text


def test_panel_admin_autocompleta_la_direccion_de_una_tarea_manual(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})

    respuesta = cliente.get("/admin/clientes")

    assert 'id="tarea-direccion-sugerencias"' in respuesta.text
    assert 'fetch("/api/configuracion-publica")' in respuesta.text
    assert "AutocompleteSuggestion.fetchAutocompleteSuggestions" in respuesta.text
    assert 'includedRegionCodes: ["ar"]' in respuesta.text


def _admin_con_fecha_fija(monkeypatch, fecha_iso="2026-08-24"):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    monkeypatch.setattr(
        appmod.entregas, "ahora_argentina",
        lambda: __import__("datetime").datetime.fromisoformat(fecha_iso + "T10:00:00").replace(tzinfo=appmod.entregas.ZONA_HORARIA),
    )
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})
    return cliente, fake


def test_tarea_manual_aparece_en_el_listado_unico_de_pendientes_de_hoy(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Retirar packaging", "nota": None, "direccion": None, "orden": 1,
    }).execute()

    r = cliente.get("/admin/clientes")

    assert "Tareas para hoy" not in r.text
    assert "Pedidos pendientes para hoy (1)" in r.text
    assert "Retirar packaging" in r.text
    assert '<button class="btn-completar-tarea" type="button" data-id="tarea-1">Completado</button>' in r.text


def test_tarea_manual_muestra_las_cuatro_acciones_de_entrega(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Visitar cliente", "direccion": "Av. Colón 123, Córdoba", "orden": 1,
    }).execute()

    respuesta = cliente.get("/admin/clientes")

    assert 'class="btn-completar-tarea"' in respuesta.text
    assert 'class="btn-direcciones"' in respuesta.text
    assert 'class="btn-editar-tarea"' in respuesta.text
    assert 'class="btn-eliminar-tarea"' in respuesta.text


def test_panel_admin_abre_calendario_para_editar_fechas_de_pedidos_y_tareas(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("pedidos").insert({
        "id": "pedido-1", "fecha_entrega": "2026-08-24", "recibo_enviado_en": None,
    }).execute()
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Visitar cliente", "orden": 1,
    }).execute()

    respuesta = cliente.get("/admin/clientes")

    assert 'id="modal-fecha-entrega"' in respuesta.text
    assert 'id="fecha-entrega-admin" type="date"' in respuesta.text
    assert 'id="fecha-entrega-guardar"' in respuesta.text
    assert 'prompt("Nueva fecha de entrega' not in respuesta.text
    assert 'data-tipo="pedido"' in respuesta.text
    assert 'data-tipo="tarea"' in respuesta.text


def test_tarea_manual_sin_direccion_permite_agregarla(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Visitar cliente", "orden": 1,
    }).execute()

    respuesta = cliente.put("/admin/tareas-entrega/tarea-1/direccion", json={
        "direccion_entrega": "Av. Colón 123, Córdoba",
    })

    assert respuesta.status_code == 200
    tarea = fake.table("tareas_entrega").select("*").eq("id", "tarea-1").execute().data[0]
    assert tarea["direccion"] == "Av. Colón 123, Córdoba"


def test_admin_puede_editar_la_fecha_de_una_tarea_manual(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    monkeypatch.setattr(appmod.entregas, "fecha_entrega_valida", lambda _: True)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Visitar cliente", "orden": 1,
    }).execute()

    respuesta = cliente.put("/admin/tareas-entrega/tarea-1/fecha-entrega", json={
        "fecha_entrega": "2026-08-25",
    })

    assert respuesta.status_code == 200
    tarea = fake.table("tareas_entrega").select("*").eq("id", "tarea-1").execute().data[0]
    assert tarea["fecha_entrega"] == "2026-08-25"


def test_admin_puede_eliminar_una_tarea_manual(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Visitar cliente", "orden": 1,
    }).execute()

    respuesta = cliente.delete("/admin/tareas-entrega/tarea-1")

    assert respuesta.status_code == 200
    assert fake.table("tareas_entrega").select("*").eq("id", "tarea-1").execute().data == []


def test_admin_puede_completar_una_tarea_manual(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Retirar packaging", "nota": None, "direccion": None, "orden": 1,
    }).execute()

    respuesta = cliente.post("/admin/tareas-entrega/tarea-1/completar")

    assert respuesta.status_code == 200
    tarea = fake.table("tareas_entrega").select("*").eq("id", "tarea-1").execute().data[0]
    assert tarea["completada_en"]


def test_admin_puede_reordenar_juntas_tareas_y_pedidos_del_dia(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("pedidos").insert({
        "id": "pedido-1", "fecha_entrega": "2026-08-24", "recibo_enviado_en": None,
    }).execute()
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24", "orden": 1,
    }).execute()

    respuesta = cliente.put("/admin/entregas/orden", json={"items": [
        {"tipo": "tarea", "id": "tarea-1"},
        {"tipo": "pedido", "id": "pedido-1"},
    ]})

    assert respuesta.status_code == 200
    pedido = fake.table("pedidos").select("*").eq("id", "pedido-1").execute().data[0]
    tarea = fake.table("tareas_entrega").select("*").eq("id", "tarea-1").execute().data[0]
    assert tarea["orden"] == 1
    assert pedido["orden_entrega"] == 2


def test_panel_admin_muestra_tiradores_para_arrastrar_entregas(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("pedidos").insert({
        "id": "pedido-1", "fecha_entrega": "2026-08-24", "recibo_enviado_en": None,
    }).execute()
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24", "orden": 1,
    }).execute()

    respuesta = cliente.get("/admin/clientes")

    assert 'data-tipo-entrega="pedido"' in respuesta.text
    assert 'data-tipo-entrega="tarea"' in respuesta.text
    assert 'class="arrastrar-entrega"' in respuesta.text
    assert 'fetch("/admin/entregas/orden"' in respuesta.text


def test_panel_admin_tiene_fallback_nativo_de_drag_para_desktop(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("pedidos").insert({
        "id": "pedido-1", "fecha_entrega": "2026-08-24", "recibo_enviado_en": None,
    }).execute()

    respuesta = cliente.get("/admin/clientes")

    assert 'class="arrastrar-entrega" draggable="true"' in respuesta.text
    assert 'addEventListener("dragstart"' in respuesta.text
    assert 'addEventListener("dragover"' in respuesta.text
    assert 'addEventListener("drop"' in respuesta.text


def test_panel_admin_respeta_el_orden_mixto_guardado(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("clientes").insert({
        "id": "cliente-1", "nombre": "Cliente", "apellido": "Pedido",
        "celular": "3510000000", "email": "cliente@example.com",
    }).execute()
    fake.table("pedidos").insert({
        "id": "pedido-1", "cliente_id": "cliente-1", "fecha_entrega": "2026-08-24",
        "recibo_enviado_en": None, "orden_entrega": 2,
    }).execute()
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24", "titulo": "Primero tarea",
        "orden": 1,
    }).execute()

    respuesta = cliente.get("/admin/clientes")

    assert respuesta.text.index('data-tipo-entrega="tarea" data-entrega-id="tarea-1"') < respuesta.text.index(
        'data-tipo-entrega="pedido" data-entrega-id="pedido-1"'
    )


def test_tarea_completada_desaparece_de_pendientes_de_hoy(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Retirar packaging", "nota": None, "direccion": None, "orden": 1,
    }).execute()
    cliente.post("/admin/tareas-entrega/tarea-1/completar")

    r = cliente.get("/admin/clientes")

    assert "Tarea completada: Retirar packaging" in r.text
    assert "No hay pedidos pendientes para hoy." in r.text


def test_tarea_manual_completada_aparece_en_el_historial_de_su_dia(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Visitar cliente", "nota": "Llevar catálogo", "orden": 1,
        "completada_en": "2026-08-24T16:00:00+00:00",
    }).execute()

    respuesta = cliente.get("/admin/clientes?fecha_pedidos=2026-08-24")

    assert "Tarea completada: Visitar cliente" in respuesta.text
    assert "Llevar catálogo" in respuesta.text
