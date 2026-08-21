from tests.fakes_supabase import FakeSupabaseClient
from web import pedidos


def test_guardar_pedido_inserta_asociado_al_cliente():
    client = FakeSupabaseClient()
    resultado = pedidos.guardar_pedido(client, "cliente-1", ["iPhone 13", "AirPods"])
    assert resultado["cliente_id"] == "cliente-1"
    assert resultado["productos"] == ["iPhone 13", "AirPods"]
    assert resultado["origen"] == "whatsapp"
    filas = client.table("pedidos").select("*").eq("cliente_id", "cliente-1").execute().data
    assert len(filas) == 1
