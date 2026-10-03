from tests.fakes_supabase import FakeSupabaseClient
from web.mailing import destinatarios


def test_incluye_clientes_con_email_y_sin_baja():
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({"id": "1", "email": "a@x.com"}).execute()
    fake.table("clientes").insert({"id": "2", "email": "b@x.com", "no_mailing": False}).execute()

    elegibles = destinatarios.clientes_elegibles(fake)

    assert {e["id"] for e in elegibles} == {"1", "2"}


def test_excluye_dados_de_baja_y_sin_email():
    fake = FakeSupabaseClient()
    fake.table("clientes").insert({"id": "1", "email": "a@x.com", "no_mailing": True}).execute()
    fake.table("clientes").insert({"id": "2", "email": None}).execute()
    fake.table("clientes").insert({"id": "3", "email": "c@x.com"}).execute()

    elegibles = destinatarios.clientes_elegibles(fake)

    assert [e["id"] for e in elegibles] == ["3"]
