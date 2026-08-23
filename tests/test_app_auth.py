from fastapi.testclient import TestClient
from types import SimpleNamespace

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    return TestClient(appmod.app, base_url="https://testserver")


def test_registro_exitoso_crea_sesion(monkeypatch):
    c = _cliente(monkeypatch)
    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    assert r.status_code == 200
    assert r.json() == {"ok": True, "requiere_confirmacion_email": False}


def test_registro_pasa_redirect_publico_a_supabase(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://thetechroomarg.com")

    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })

    assert r.status_code == 200
    assert fake.auth.last_sign_up_payload["options"]["email_redirect_to"] == (
        "https://thetechroomarg.com/login.html"
    )


def test_registro_usa_forwarded_host_si_base_url_interna(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="http://127.0.0.1:8000")

    r = c.post(
        "/registro",
        json={
            "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
            "email": "juan@x.com", "password": "clave1234",
        },
        headers={
            "X-Forwarded-Host": "thetechroomarg.com",
            "X-Forwarded-Proto": "https",
        },
    )

    assert r.status_code == 200
    assert fake.auth.last_sign_up_payload["options"]["email_redirect_to"] == (
        "https://thetechroomarg.com/login.html"
    )


def test_registro_pendiente_de_confirmacion_no_crea_sesion(monkeypatch):
    fake = FakeSupabaseClient()
    fake.auth.next_sign_up_session = None
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://thetechroomarg.com", follow_redirects=False)

    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })

    assert r.status_code == 200
    assert r.json() == {
        "ok": True,
        "requiere_confirmacion_email": True,
        "email_redirect_to": "https://thetechroomarg.com/login.html",
    }
    assert c.get("/api/me").status_code == 401


def test_completar_signup_con_access_token_crea_sesion_y_redirige_a_landing(monkeypatch):
    fake = FakeSupabaseClient()
    fake.auth.next_sign_up_session = None
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://thetechroomarg.com", follow_redirects=False)

    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    auth_id = fake.auth._usuarios_por_email["juan@x.com"].id
    fake.auth.get_user = lambda jwt=None: SimpleNamespace(user=SimpleNamespace(id=auth_id))

    r = c.post("/auth/completar-signup", json={"access_token": "token-valido"})

    assert r.status_code == 200
    assert r.json() == {"ok": True, "debe_cambiar_password": False}
    me = c.get("/api/me")
    assert me.status_code == 200
    assert me.json()["email"] == "juan@x.com"


def test_registro_celular_duplicado_devuelve_400(monkeypatch):
    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/registro", json={
        "nombre": "Otro", "apellido": "Nombre", "celular": "3511234567",
        "email": "otro@x.com", "password": "clave1234",
    })
    assert r.status_code == 400
    assert "error" in r.json()


def test_login_correcto(monkeypatch):
    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/login", json={"email": "juan@x.com", "password": "clave1234"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "debe_cambiar_password": False}


def test_login_incorrecto_devuelve_mensaje_generico(monkeypatch):
    c = _cliente(monkeypatch)
    r = c.post("/login", json={"email": "nadie@x.com", "password": "loquesea"})
    assert r.status_code == 401
    assert r.json()["error"] == "Usuario o contraseña incorrectos"


def test_password_temporal_fuerza_cambio_antes_de_usar_el_resto_de_la_app(monkeypatch):
    from web import cuentas as cuentas_mod

    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    fake = appmod.get_client()
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    c.post("/logout")

    temporal = cuentas_mod.resetear_password_cliente(fake, cliente_id)["password"]

    r = c.post("/login", json={"email": "juan@x.com", "password": temporal})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "debe_cambiar_password": True}

    # Con la flag activa, el resto de la app queda bloqueado.
    assert c.post("/chat", json={"mensaje": "hola", "sesion": "s1"}).status_code == 403
    assert c.post("/api/pedidos", json={"productos": ["x"]}).status_code == 403
    r_home = c.get("/", follow_redirects=False)
    assert "login" in r_home.headers.get("location", "") or "login" in r_home.text.lower()

    r = c.post("/cambiar-password-obligatorio", json={"password": "claveElegidaPorMi1"})
    assert r.status_code == 200

    # Ya cambiada, el resto de la app queda accesible de nuevo.
    assert c.post("/chat", json={"mensaje": "hola", "sesion": "s1"}).status_code == 200


def test_logout_limpia_sesion(monkeypatch):
    c = _cliente(monkeypatch)
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/logout")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    assert c.get("/api/catalogo").status_code == 200  # pública, no requiere sesión


def test_registro_con_supabase_caido_da_mensaje_claro(monkeypatch):
    def _client_roto():
        raise Exception("connection refused")

    monkeypatch.setattr(appmod, "get_client", _client_roto)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    assert r.status_code == 503
    assert "error" in r.json()


def test_login_con_supabase_caido_da_503_no_500(monkeypatch):
    """get_client() no puede fallar por una caída real de Supabase (no hace
    llamadas de red), así que la falla real ocurre dentro de
    cuentas.login_cliente. Ese error debe convertirse en un 503 claro, no en
    un 500 crudo ni en el 401 genérico de credenciales incorrectas."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)

    def _login_roto(_client, _email, _password):
        raise Exception("connection timed out")

    monkeypatch.setattr(appmod.cuentas, "login_cliente", _login_roto)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/login", json={"email": "juan@x.com", "password": "clave1234"})
    assert r.status_code == 503
    assert "error" in r.json()


def test_login_email_no_confirmado_devuelve_403_con_mensaje_claro(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)

    def _login_no_confirmado(_client, _client_datos, _email, _password):
        raise appmod.cuentas.EmailNoConfirmadoError(
            "Confirmá tu email antes de ingresar — revisá tu bandeja de entrada"
        )

    monkeypatch.setattr(appmod.cuentas, "login_cliente", _login_no_confirmado)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/login", json={"email": "juan@x.com", "password": "clave1234"})
    assert r.status_code == 403
    assert "confirmá tu email" in r.json()["error"].lower()
