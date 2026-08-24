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
