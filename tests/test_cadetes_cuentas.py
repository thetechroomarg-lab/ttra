import pytest
from fastapi.testclient import TestClient

import web.app as appmod
from web import cadetes
from tests.fakes_supabase import FakeSupabaseClient


@pytest.fixture
def fake(monkeypatch):
    monkeypatch.setattr(appmod, "_CADETE_EXIGIR_CUENTA", True)
    f = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: f)
    cadetes._cache.clear()
    f.table("cadetes").insert({"id": "c1", "nombre": "Alejo", "email": "alejo@example.com", "rol": "cadete",
                               "activo": True, "password_hash": cadetes.hashear_password("clave-larga-123")}).execute()
    return f


def _c():
    return TestClient(appmod.app, base_url="https://testserver")


def test_hash_no_guarda_texto_plano_y_verifica():
    h = cadetes.hashear_password("abc12345")
    assert "abc12345" not in h and cadetes.verificar_password("abc12345", h)
    assert not cadetes.verificar_password("otra", h) and not cadetes.verificar_password("x", "basura")


def test_login_con_cuenta_da_acceso_al_panel(fake):
    c = _c()
    assert c.post("/admin/cadete/login", json={"email": "ALEJO@example.com", "password": "clave-larga-123"}).status_code == 200
    assert "Ingresar" not in c.get("/admin/cadete").text


def test_login_con_cuenta_rechaza_clave_o_email_malos(fake):
    c = _c()
    assert c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "mala"}).status_code == 401
    assert c.post("/admin/cadete/login", json={"email": "nadie@example.com", "password": "clave-larga-123"}).status_code == 401
    assert "Ingresar" in c.get("/admin/cadete").text


def test_dar_de_baja_la_cuenta_corta_la_sesion(fake):
    c = _c()
    c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"})
    fake.table("cadetes").update({"activo": False}).eq("id", "c1").execute()
    cadetes._cache.clear()
    assert "Ingresar" in c.get("/admin/cadete").text
    assert c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"}).status_code == 401


def test_cambiar_la_clave_invalida_sesiones_viejas(fake):
    c = _c()
    c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"})
    fake.table("cadetes").update({"password_hash": cadetes.hashear_password("nueva-clave-456")}).eq("id", "c1").execute()
    cadetes._cache.clear()
    assert "Ingresar" in c.get("/admin/cadete").text


def test_contrasena_unica_sin_cuenta_obligatoria_es_la_llave_de_emergencia(fake, monkeypatch):
    monkeypatch.setattr(appmod, "_CADETE_EXIGIR_CUENTA", False)
    c = _c()
    assert c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD}).status_code == 200
    assert "Ingresar" not in c.get("/admin/cadete").text


def test_sesion_de_cuenta_falla_cerrado_si_la_base_cae(fake, monkeypatch):
    c = _c()
    c.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"})
    cadetes._cache.clear()
    def roto(): raise RuntimeError("db caida")
    monkeypatch.setattr(appmod, "get_client", roto)
    assert "Ingresar" in c.get("/admin/cadete").text


@pytest.fixture
def sin_cuentas(monkeypatch):
    monkeypatch.setattr(appmod, "_CADETE_EXIGIR_CUENTA", True)
    f = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: f)
    cadetes._cache.clear()
    return f


def test_primer_ingreso_con_la_clave_unica_obliga_a_crear_cuenta(sin_cuentas):
    c = _c()
    r = c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    assert r.json() == {"ok": True, "crear_cuenta": True}
    pagina = c.get("/admin/cadete").text
    assert "Creá tu cuenta" in pagina and "Panel de entregas" not in pagina
    # con solo la clave única no se puede operar el panel
    assert c.get("/admin/cadete/push/vapid-public-key").status_code == 401


def test_crear_cuenta_deja_logueado_y_guarda_hash(sin_cuentas):
    c = _c()
    c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    assert c.post("/admin/cadete/cuenta", json={"email": "Alejo@Example.com", "password": "clave-larga-123"}).status_code == 200
    fila = sin_cuentas.table("cadetes").select("*").execute().data[0]
    assert fila["email"] == "alejo@example.com" and "clave-larga-123" not in fila["password_hash"]
    assert "Creá tu cuenta" not in c.get("/admin/cadete").text
    assert c.get("/admin/cadete/push/vapid-public-key").status_code != 401


def test_no_se_puede_crear_cuenta_sin_probar_la_clave_unica(sin_cuentas):
    r = _c().post("/admin/cadete/cuenta", json={"email": "x@example.com", "password": "clave-larga-123"})
    assert r.status_code == 401 and not sin_cuentas.table("cadetes").select("*").execute().data


def test_con_cuenta_creada_la_clave_unica_ya_no_sirve(fake):
    r = _c().post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    assert r.status_code == 409


def test_cuenta_con_clave_corta_o_email_invalido_se_rechaza(sin_cuentas):
    c = _c()
    c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    assert c.post("/admin/cadete/cuenta", json={"email": "x@example.com", "password": "corta"}).status_code == 422
    assert c.post("/admin/cadete/cuenta", json={"email": "no-es-mail", "password": "clave-larga-123"}).status_code == 422


def _mails(monkeypatch):
    enviados = []
    from web import push_cadete
    monkeypatch.setattr(push_cadete, "enviar_email", lambda dest, asunto, html, **k: enviados.append((dest, asunto, html)))
    return enviados


def test_aviso_de_nota_va_al_email_de_la_cuenta_y_escapa_html(fake, monkeypatch):
    from web import push_cadete
    enviados = _mails(monkeypatch)
    push_cadete.enviar_push_cadete(fake, "📝 Nueva nota asignada", "<b>retirar</b>")
    dest, _, cuerpo = enviados[0]
    assert dest == "alejo@example.com" and "<b>" not in cuerpo and "&lt;b&gt;" in cuerpo


def test_sin_cuenta_el_aviso_sigue_yendo_al_mail_de_siempre(sin_cuentas, monkeypatch):
    from web import push_cadete
    enviados = _mails(monkeypatch)
    push_cadete.enviar_push_cadete(sin_cuentas, "t", "c")
    assert enviados[0][0] == push_cadete.MAIL_NOTIFICACION_ALEJO


def test_registrar_pago_manda_mail_al_cadete(fake, monkeypatch):
    enviados = _mails(monkeypatch)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    fake.table("movimientos_cadete").insert({"id": "m1", "tipo": "entrega", "referencia_id": "p1",
                                             "descripcion": "Entrega", "monto_ars": 6000,
                                             "creado_en": "2026-11-18T10:00:00+00:00"}).execute()
    admin = _c()
    admin.post("/admin/clientes/login", json={"password": "clave-admin"})
    r = admin.post("/admin/cadete/movimientos/pagar")
    assert r.status_code == 200, r.text
    dest, asunto, cuerpo = enviados[-1]
    assert dest == "alejo@example.com" and "pago" in asunto.lower() and "6.000" in cuerpo


def test_lo_que_el_admin_deriva_le_llega_a_la_cuenta_del_cadete(fake, monkeypatch):
    """La cuenta propia ocupa el mismo lugar que la clave única: lo derivado a
    'alejo' aparece en su panel y lo que ve es solo lo derivado."""
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    hoy = appmod.entregas.ahora_argentina().date().isoformat()
    fake.table("tareas_entrega").insert({"id": "t1", "fecha_entrega": hoy, "titulo": "Nota derivada", "orden": 1}).execute()
    fake.table("tareas_entrega").insert({"id": "t2", "fecha_entrega": hoy, "titulo": "Nota de Vlad", "orden": 2}).execute()
    admin = _c()
    admin.post("/admin/clientes/login", json={"password": "clave-admin"})
    assert admin.put("/admin/tareas-entrega/t1/derivar", json={"derivado": True}).status_code == 200
    cadete = _c()
    cadete.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"})
    pagina = cadete.get("/admin/cadete").text
    assert "Nota derivada" in pagina and "Nota de Vlad" not in pagina
    assert fake.table("tareas_entrega").select("*").eq("id", "t1").execute().data[0]["asignado_a"] == appmod.CADETE_SLUG
