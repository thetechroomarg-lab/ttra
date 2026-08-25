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


def test_tarea_completada_desaparece_de_pendientes_de_hoy(monkeypatch):
    cliente, fake = _admin_con_fecha_fija(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "tarea-1", "fecha_entrega": "2026-08-24",
        "titulo": "Retirar packaging", "nota": None, "direccion": None, "orden": 1,
    }).execute()
    cliente.post("/admin/tareas-entrega/tarea-1/completar")

    r = cliente.get("/admin/clientes")

    assert "Retirar packaging" not in r.text
    assert "No hay pedidos pendientes para hoy." in r.text
