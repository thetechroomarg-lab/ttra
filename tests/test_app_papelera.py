from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _iso_hace(horas):
    return (datetime.now(timezone.utc) - timedelta(hours=horas)).isoformat()


def test_admin_papelera_lista_borrados_recientes_y_purga_vencidos(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})

    fake.table("pedidos").insert({
        "id": "reciente", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "borrado_en": _iso_hace(2), "borrado_por": "Vlad",
    }).execute()
    fake.table("pedidos").insert({
        "id": "vencido", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-18",
        "borrado_en": _iso_hace(50), "borrado_por": "Vlad",
    }).execute()
    fake.table("tareas_entrega").insert({
        "id": "tarea-reciente", "fecha_entrega": "2026-09-20", "titulo": "Llamar a Ana", "orden": 1,
        "borrado_en": _iso_hace(1), "borrado_por": "alejo",
    }).execute()

    respuesta = cliente.get("/admin/papelera")
    assert respuesta.status_code == 200
    assert "reciente" in respuesta.text
    assert "vencido" not in respuesta.text
    assert "tarea-reciente" in respuesta.text

    assert fake.table("pedidos").select("*").eq("id", "vencido").execute().data == []
    assert fake.table("pedidos").select("*").eq("id", "reciente").execute().data != []


def test_cadete_papelera_solo_ve_lo_propio(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/cadete/login", json={"password": "clave-cadete"})

    fake.table("pedidos").insert({
        "id": "propio", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "asignado_a": "alejo", "borrado_en": _iso_hace(1), "borrado_por": "alejo",
    }).execute()
    fake.table("pedidos").insert({
        "id": "ajeno", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "asignado_a": None, "borrado_en": _iso_hace(1), "borrado_por": "Vlad",
    }).execute()

    respuesta = cliente.get("/admin/cadete/papelera")
    assert respuesta.status_code == 200
    assert "propio" in respuesta.text
    assert "ajeno" not in respuesta.text


def test_cadete_papelera_usa_manifest_y_estilo_propios(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/cadete/login", json={"password": "clave-cadete"})

    respuesta = cliente.get("/admin/cadete/papelera")
    assert respuesta.status_code == 200
    assert "admin-cadete.webmanifest" in respuesta.text
    assert "admin-clientes.webmanifest" not in respuesta.text


def test_admin_papelera_usa_manifest_y_estilo_admin(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})

    respuesta = cliente.get("/admin/papelera")
    assert respuesta.status_code == 200
    assert "admin-cadete.webmanifest" not in respuesta.text


def test_papelera_requiere_sesion(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    cliente = TestClient(appmod.app, base_url="https://testserver")
    assert cliente.get("/admin/papelera").status_code in (401, 303, 307)
    assert cliente.get("/admin/cadete/papelera").status_code in (401, 303, 307)


def test_admin_restaura_pedido_borrado(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})
    fake.table("pedidos").insert({
        "id": "p1", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "borrado_en": _iso_hace(1), "borrado_por": "Vlad",
    }).execute()

    respuesta = cliente.post("/admin/papelera/pedido/p1/restaurar")
    assert respuesta.status_code == 200

    fila = fake.table("pedidos").select("*").eq("id", "p1").execute().data[0]
    assert fila["borrado_en"] is None


def test_cadete_no_puede_restaurar_pedido_ajeno(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/cadete/login", json={"password": "clave-cadete"})
    fake.table("pedidos").insert({
        "id": "ajeno", "cliente_id": "c1", "productos": [], "fecha_entrega": "2026-09-20",
        "asignado_a": None, "borrado_en": _iso_hace(1), "borrado_por": "Vlad",
    }).execute()

    respuesta = cliente.post("/admin/papelera/pedido/ajeno/restaurar")
    assert respuesta.status_code == 403


def test_restaura_tarea_borrada(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-20", "titulo": "Llamar a Ana", "orden": 1,
        "borrado_en": _iso_hace(1), "borrado_por": "Vlad",
    }).execute()

    respuesta = cliente.post("/admin/papelera/tarea/t1/restaurar")
    assert respuesta.status_code == 200
    fila = fake.table("tareas_entrega").select("*").eq("id", "t1").execute().data[0]
    assert fila["borrado_en"] is None
