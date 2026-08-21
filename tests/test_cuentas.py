import pytest

from tests.fakes_supabase import FakeSupabaseClient
from web import cuentas


def test_registrar_cliente_exitoso():
    client = FakeSupabaseClient()
    cliente = cuentas.registrar_cliente(
        client, "Ana", "Gómez", "351 123-4567", "ana@x.com", "clave1234"
    )
    assert cliente["nombre"] == "Ana"
    assert cliente["apellido"] == "Gómez"
    assert cliente["celular"] == "3511234567"  # normalizado, sin espacios ni guiones
    assert cliente["email"] == "ana@x.com"
    assert cliente["id"]  # uuid propio asignado


def test_registrar_cliente_celular_duplicado_de_cuenta_ya_activa():
    client = FakeSupabaseClient()
    cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    with pytest.raises(cuentas.CelularDuplicadoError):
        cuentas.registrar_cliente(client, "Otra", "Persona", "3511234567", "otra@x.com", "clave1234")


def test_registrar_cliente_email_duplicado():
    client = FakeSupabaseClient()
    cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    with pytest.raises(cuentas.EmailDuplicadoError):
        cuentas.registrar_cliente(client, "Otra", "Persona", "3519999999", "ana@x.com", "clave1234")


def test_registrar_cliente_vincula_lead_invitado_por_celular():
    client = FakeSupabaseClient()
    # Simula un lead migrado sin cuenta: auth_id ausente.
    client.table("clientes").insert({
        "id": "id-lead-1", "auth_id": None, "nombre": "Ana", "apellido": "",
        "celular": "3511234567", "email": "",
    }).execute()

    cliente = cuentas.registrar_cliente(
        client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234"
    )
    assert cliente["id"] == "id-lead-1"  # se completó la fila existente, no se creó otra
    filas = client.table("clientes").select("*").eq("celular", "3511234567").execute().data
    assert len(filas) == 1
    assert filas[0]["auth_id"] == cliente["auth_id"]
    assert filas[0]["apellido"] == "Gómez"


def test_registrar_cliente_hace_rollback_si_falla_el_perfil():
    client = FakeSupabaseClient()

    def _insert_que_falla(_payload):
        raise Exception("boom: fila inválida")

    client.table("clientes").insert = _insert_que_falla
    with pytest.raises(cuentas.CelularDuplicadoError):
        cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    # El usuario de auth no debe quedar húmedo tras el rollback.
    assert "ana@x.com" not in client.auth._usuarios_por_email


def test_login_cliente_correcto():
    client = FakeSupabaseClient()
    cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    cliente = cuentas.login_cliente(client, "ana@x.com", "clave1234")
    assert cliente is not None
    assert cliente["nombre"] == "Ana"


def test_login_cliente_password_incorrecta():
    client = FakeSupabaseClient()
    cuentas.registrar_cliente(client, "Ana", "Gómez", "3511234567", "ana@x.com", "clave1234")
    assert cuentas.login_cliente(client, "ana@x.com", "otraclave") is None


def test_login_cliente_sin_cuenta():
    client = FakeSupabaseClient()
    assert cuentas.login_cliente(client, "nadie@x.com", "loquesea") is None
