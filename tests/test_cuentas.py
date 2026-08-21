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


def test_registrar_cliente_insert_falla_por_email_duplicado():
    """Caso concreto: lead invitado con email X, se intenta registrar distinto celular con email X.
    Auth sign_up tiene éxito, pero insert falla por violación del unique de email.
    Debe levantarse EmailDuplicadoError, no CelularDuplicadoError."""
    client = FakeSupabaseClient()
    # Simula un lead invitado con celular Y, email X, sin auth_id
    client.table("clientes").insert({
        "id": "id-lead-1", "auth_id": None, "nombre": "Ana", "apellido": "",
        "celular": "3511111111", "email": "x@example.com",
    }).execute()

    # Monkeypatchea insert para simular falla de unique constraint en email
    original_table = client.table

    def patched_table(nombre):
        tabla = original_table(nombre)
        if nombre == "clientes":
            original_insert = tabla.insert
            def failing_insert(payload):
                if "3519999999" in str(payload):  # Solo falla para el nuevo celular
                    raise Exception('duplicate key value violates unique constraint "clientes_email_key"')
                return original_insert(payload)
            tabla.insert = failing_insert
        return tabla

    client.table = patched_table

    # Intenta registrar con celular distinto (3519999999) pero email X (igual al lead)
    with pytest.raises(cuentas.EmailDuplicadoError):
        cuentas.registrar_cliente(
            client, "Otra", "Persona", "3519999999", "x@example.com", "clave1234"
        )
    # El usuario de auth debe haber hecho rollback
    assert "x@example.com" not in client.auth._usuarios_por_email
