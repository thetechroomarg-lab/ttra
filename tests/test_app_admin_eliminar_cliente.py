from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _admin_y_cliente(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    "provincia": "Córdoba",
    })
    cliente.post("/api/pedidos", json={"productos": ["iPhone 13"]})
    cliente.post("/logout")
    cliente.post("/admin/clientes/login", json={"password": "clave-admin"})
    return cliente, fake


def test_admin_elimina_cuenta_y_libera_datos_unicos(monkeypatch):
    admin, fake = _admin_y_cliente(monkeypatch)
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    fake.table("interacciones_cliente").insert({
        "id": "inter-1", "cliente_id": cliente_id, "tipo_evento": "view_product",
    }).execute()

    eliminado = admin.post(f"/admin/clientes/{cliente_id}/eliminar")

    assert eliminado.status_code == 200
    assert fake.table("clientes").select("*").eq("id", cliente_id).execute().data == []
    assert fake.table("pedidos").select("*").eq("cliente_id", cliente_id).execute().data == []
    assert fake.table("interacciones_cliente").select("*").eq("cliente_id", cliente_id).execute().data == []

    nuevo = TestClient(appmod.app, base_url="https://testserver")
    registrado = nuevo.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "otra-clave",
    "provincia": "Córdoba",
    })
    assert registrado.status_code == 200


def test_eliminar_cliente_requiere_sesion_admin(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    cliente = TestClient(appmod.app, base_url="https://testserver")

    respuesta = cliente.post("/admin/clientes/cliente-id/eliminar")

    assert respuesta.status_code == 401
