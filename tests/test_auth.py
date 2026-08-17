import pytest

from web import auth


@pytest.fixture
def conn(tmp_path):
    c = auth.get_conn(tmp_path / "test_usuarios.db")
    yield c
    c.close()


def test_crear_y_verificar_usuario(conn):
    auth.crear_usuario(conn, "Juan Perez", "Juan@Ejemplo.com", "clave123", "2026-08-17 10:00")
    usuario = auth.verificar_usuario(conn, "juan@ejemplo.com", "clave123")
    assert usuario is not None
    assert usuario["nombre"] == "Juan Perez"
    assert usuario["email"] == "juan@ejemplo.com"


def test_verificar_con_password_incorrecta_devuelve_none(conn):
    auth.crear_usuario(conn, "Juan Perez", "juan@ejemplo.com", "clave123", "2026-08-17 10:00")
    assert auth.verificar_usuario(conn, "juan@ejemplo.com", "clave-mala") is None


def test_verificar_email_inexistente_devuelve_none(conn):
    assert auth.verificar_usuario(conn, "nadie@ejemplo.com", "clave123") is None


def test_crear_usuario_email_duplicado_lanza_error(conn):
    auth.crear_usuario(conn, "Juan Perez", "juan@ejemplo.com", "clave123", "2026-08-17 10:00")
    with pytest.raises(auth.EmailDuplicadoError):
        auth.crear_usuario(conn, "Otro Nombre", "JUAN@ejemplo.com", "otra-clave", "2026-08-17 11:00")
