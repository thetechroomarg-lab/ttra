from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_baja_marca_no_mailing_en_true(monkeypatch):
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({"id": "cliente-1", "email": "a@x.com", "no_mailing": False}).execute()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    cliente = TestClient(appmod.app, base_url="https://testserver")

    respuesta = cliente.get("/mailing/baja/cliente-1")

    assert respuesta.status_code == 200
    fila = fake.table("clientes").select("*").eq("id", "cliente-1").execute().data[0]
    assert fila["no_mailing"] is True


def test_baja_con_cliente_inexistente_devuelve_404(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    cliente = TestClient(appmod.app, base_url="https://testserver")

    respuesta = cliente.get("/mailing/baja/no-existe")

    assert respuesta.status_code == 404
