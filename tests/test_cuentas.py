import pytest

from tests.fakes_supabase import FakeSupabaseClient
from web import cuentas


def test_normalizar_celular_saca_el_codigo_de_pais_argentino():
    """"+543513017015" y "3513017015" son el mismo número de celular — sin
    esto, se migran/registran como dos clientes distintos."""
    assert cuentas.normalizar_celular("+543513017015") == "3513017015"
    assert cuentas.normalizar_celular("543513017015") == "3513017015"
    assert cuentas.normalizar_celular("3513017015") == "3513017015"


def test_normalizar_celular_no_toca_numeros_que_no_empiezan_con_54():
    assert cuentas.normalizar_celular("351 123-4567") == "3511234567"


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


def test_login_cliente_propaga_error_que_no_es_de_credencial():
    """Si Supabase está caído (timeout, conexión rechazada, etc.), no hay que
    disfrazarlo de "usuario no encontrado": hay que dejarlo propagar para que
    el endpoint de arriba lo distinga y devuelva un 503 en vez de un 401."""
    client = FakeSupabaseClient()

    def _sign_in_roto(_credenciales):
        raise Exception("connection timed out")

    client.auth.sign_in_with_password = _sign_in_roto
    with pytest.raises(Exception, match="connection timed out"):
        cuentas.login_cliente(client, "ana@x.com", "clave1234")


def test_login_cliente_email_no_confirmado_levanta_error_especifico():
    """Si Supabase tiene la confirmación de email activada (el default en
    proyectos nuevos) y el usuario todavía no confirmó, sign_in_with_password
    falla con un mensaje que menciona "confirm" — hay que distinguirlo de una
    contraseña incorrecta para poder mostrar un mensaje útil."""
    client = FakeSupabaseClient()

    def _sign_in_no_confirmado(_credenciales):
        raise Exception("Email not confirmed")

    client.auth.sign_in_with_password = _sign_in_no_confirmado
    with pytest.raises(cuentas.EmailNoConfirmadoError):
        cuentas.login_cliente(client, "ana@x.com", "clave1234")


def test_registrar_cliente_insert_falla_por_email_duplicado():
    """Caso concreto: el INSERT final falla por una violación de unique de
    email que no fue detectada por los chequeos previos (p. ej. condición de
    carrera). Debe levantarse EmailDuplicadoError, no CelularDuplicadoError,
    y el usuario de auth recién creado debe hacer rollback."""
    client = FakeSupabaseClient()

    # Monkeypatchea insert para simular falla de unique constraint en email
    original_table = client.table

    def patched_table(nombre):
        tabla = original_table(nombre)
        if nombre == "clientes":
            def failing_insert(_payload):
                raise Exception('duplicate key value violates unique constraint "clientes_email_key"')
            tabla.insert = failing_insert
        return tabla

    client.table = patched_table

    with pytest.raises(cuentas.EmailDuplicadoError):
        cuentas.registrar_cliente(
            client, "Otra", "Persona", "3519999999", "x@example.com", "clave1234"
        )
    # El usuario de auth debe haber hecho rollback
    assert "x@example.com" not in client.auth._usuarios_por_email


def test_registrar_cliente_no_vincula_fila_invitada_solo_por_email():
    """Un email por sí solo NO alcanza para reclamar una fila existente: si
    alcanzara, cualquiera que supiera el email de un cliente migrado podría
    registrarse con ese email y "robar" su fila (nombre, celular, pedidos)
    sin ninguna verificación de que es su dueño real. La vinculación de una
    fila invitada es solo por celular (ver test de arriba)."""
    client = FakeSupabaseClient()
    client.table("clientes").insert({
        "id": "id-mayorista-1", "auth_id": None, "nombre": "Mayorista Uno", "apellido": "",
        "celular": "pendiente-xxx", "email": "mayorista@x.com", "tipo_cliente": "mayorista",
    }).execute()

    cliente = cuentas.registrar_cliente(
        client, "Impostor", "Impostor", "3512223344", "mayorista@x.com", "clave1234"
    )

    # Se crea una fila NUEVA, distinta de la del mayorista — no se tocó su fila.
    assert cliente["id"] != "id-mayorista-1"
    filas = client.table("clientes").select("*").eq("celular", "pendiente-xxx").execute().data
    assert len(filas) == 1
    assert filas[0]["id"] == "id-mayorista-1"
    assert filas[0]["auth_id"] is None  # la fila del mayorista sigue intacta, sin dueño

    # Nota: en la práctica esto no llega a pasar en absoluto, porque el
    # email ya está en uso por la fila del mayorista y `EmailDuplicadoError`
    # (arriba, test_registrar_cliente_email_duplicado) actúa primero SI ese
    # email ya tiene una cuenta de Supabase Auth real asociada. Este test usa
    # un doble que no simula ese chequeo cruzado; lo importante acá es
    # documentar que el criterio de vinculación en sí no acepta el email
    # como prueba de identidad.
