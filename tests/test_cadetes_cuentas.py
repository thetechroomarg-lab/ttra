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
    f.table("cadetes").insert({"id": "c1", "nombre": "Alejo", "email": "alejo@example.com", "rol": "cadete", "slug": "alejo", "aprobado": True,
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
    assert c.post("/admin/cadete/cuenta", json={"nombre": "Alejo", "email": "Alejo@Example.com", "password": "clave-larga-123"}).status_code == 200
    fila = sin_cuentas.table("cadetes").select("*").execute().data[0]
    assert fila["email"] == "alejo@example.com" and "clave-larga-123" not in fila["password_hash"]
    assert "Creá tu cuenta" not in c.get("/admin/cadete").text
    assert c.get("/admin/cadete/push/vapid-public-key").status_code != 401


def test_no_se_puede_crear_cuenta_sin_probar_la_clave_unica(sin_cuentas):
    r = _c().post("/admin/cadete/cuenta", json={"nombre": "X", "email": "x@example.com", "password": "clave-larga-123"})
    assert r.status_code == 401 and not sin_cuentas.table("cadetes").select("*").execute().data


def test_con_cuentas_existentes_la_clave_unica_sigue_llevando_solo_al_alta(fake):
    c = _c()
    assert c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD}).json()["crear_cuenta"] is True
    assert c.get("/admin/cadete/push/vapid-public-key").status_code == 401


def test_cuenta_con_clave_corta_o_email_invalido_se_rechaza(sin_cuentas):
    c = _c()
    c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    assert c.post("/admin/cadete/cuenta", json={"nombre": "X", "email": "x@example.com", "password": "corta"}).status_code == 422
    assert c.post("/admin/cadete/cuenta", json={"nombre": "X", "email": "no-es-mail", "password": "clave-larga-123"}).status_code == 422


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


# ---- varios cadetes -------------------------------------------------------

def _admin(monkeypatch):
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    a = _c()
    a.post("/admin/clientes/login", json={"password": "clave-admin"})
    return a


def _alta_maria(fake):
    c = _c()
    c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    r = c.post("/admin/cadete/cuenta", json={"nombre": "María Pérez", "email": "maria@example.com", "password": "clave-maria-123"})
    return c, r


def test_segundo_cadete_queda_pendiente_y_no_puede_entrar(fake):
    c, r = _alta_maria(fake)
    assert r.json() == {"ok": True, "pendiente": True}
    fila = [x for x in fake.table("cadetes").select("*").execute().data if x["email"] == "maria@example.com"][0]
    assert fila["aprobado"] is False and fila["slug"] == "maria-perez"
    r = _c().post("/admin/cadete/login", json={"email": "maria@example.com", "password": "clave-maria-123"})
    assert r.status_code == 403


def test_primer_cadete_de_todos_queda_aprobado_con_el_slug_historico(sin_cuentas):
    c = _c()
    c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    c.post("/admin/cadete/cuenta", json={"nombre": "Alejandro", "email": "a@example.com", "password": "clave-larga-123"})
    fila = sin_cuentas.table("cadetes").select("*").execute().data[0]
    assert fila["aprobado"] is True and fila["slug"] == "alejo"


def test_email_repetido_no_crea_otra_cuenta(fake):
    c = _c()
    c.post("/admin/cadete/login", json={"password": appmod.CADETE_PASSWORD})
    r = c.post("/admin/cadete/cuenta", json={"nombre": "Otro", "email": "ALEJO@example.com", "password": "clave-larga-123"})
    assert r.status_code == 409


def test_admin_aprueba_y_el_cadete_nuevo_puede_entrar(fake, monkeypatch):
    _alta_maria(fake)
    admin = _admin(monkeypatch)
    cid = [x for x in fake.table("cadetes").select("*").execute().data if x["email"] == "maria@example.com"][0]["id"]
    assert admin.post(f"/admin/cadetes/{cid}/aprobar").status_code == 200
    assert _c().post("/admin/cadete/login", json={"email": "maria@example.com", "password": "clave-maria-123"}).status_code == 200
    assert "María Pérez" in admin.get("/admin/cadetes").text
    assert _c().post(f"/admin/cadetes/{cid}/aprobar").status_code == 401


def _con_maria_aprobada(fake, monkeypatch):
    _alta_maria(fake)
    fake.table("cadetes").update({"aprobado": True}).eq("slug", "maria-perez").execute()
    cadetes._cache.clear()
    return _admin(monkeypatch)


def test_con_dos_cadetes_el_admin_elige_a_quien_derivar(fake, monkeypatch):
    admin = _con_maria_aprobada(fake, monkeypatch)
    hoy = appmod.entregas.ahora_argentina().date().isoformat()
    fake.table("tareas_entrega").insert({"id": "t1", "fecha_entrega": hoy, "titulo": "Nota para María", "orden": 1}).execute()
    pagina = admin.get("/admin/clientes").text
    assert 'class="sel-derivar-entrega"' in pagina and 'value="maria-perez"' in pagina and 'value="alejo"' in pagina
    assert admin.put("/admin/tareas-entrega/t1/derivar", json={"derivado": True, "cadete": "maria-perez"}).status_code == 200
    assert fake.table("tareas_entrega").select("*").eq("id", "t1").execute().data[0]["asignado_a"] == "maria-perez"
    maria = _c()
    assert maria.post("/admin/cadete/login", json={"email": "maria@example.com", "password": "clave-maria-123"}).status_code == 200
    alejo = _c()
    alejo.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"})
    assert "Nota para María" in maria.get("/admin/cadete").text
    assert "Nota para María" not in alejo.get("/admin/cadete").text
    assert "Derivado a María Pérez" in admin.get("/admin/clientes").text


def test_no_se_puede_derivar_a_un_cadete_pendiente_o_inexistente(fake, monkeypatch):
    _alta_maria(fake)  # pendiente
    admin = _admin(monkeypatch)
    fake.table("tareas_entrega").insert({"id": "t1", "fecha_entrega": "2026-11-20", "titulo": "N", "orden": 1}).execute()
    assert admin.put("/admin/tareas-entrega/t1/derivar", json={"derivado": True, "cadete": "maria-perez"}).status_code == 400
    assert admin.put("/admin/tareas-entrega/t1/derivar", json={"derivado": True, "cadete": "nadie"}).status_code == 400


def test_un_cadete_no_toca_lo_de_otro(fake, monkeypatch):
    admin = _con_maria_aprobada(fake, monkeypatch)
    fake.table("tareas_entrega").insert({"id": "t1", "fecha_entrega": "2026-11-20", "titulo": "De María", "orden": 1,
                                         "asignado_a": "maria-perez"}).execute()
    alejo = _c()
    alejo.post("/admin/cadete/login", json={"email": "alejo@example.com", "password": "clave-larga-123"})
    assert alejo.post("/admin/tareas-entrega/t1/visto").status_code == 403
    assert alejo.put("/admin/tareas-entrega/t1/derivar", json={"derivado": False}).status_code == 403


def test_aviso_de_asignacion_va_solo_al_mail_de_ese_cadete(fake, monkeypatch):
    from web import push_cadete
    admin = _con_maria_aprobada(fake, monkeypatch)
    enviados = _mails(monkeypatch)
    fake.table("tareas_entrega").insert({"id": "t1", "fecha_entrega": "2026-11-20", "titulo": "N", "orden": 1}).execute()
    admin.put("/admin/tareas-entrega/t1/derivar", json={"derivado": True, "cadete": "maria-perez"})
    assert [d for d, _, _ in enviados] == ["maria@example.com"]


def test_saldo_y_pagos_son_por_cadete(fake, monkeypatch):
    admin = _con_maria_aprobada(fake, monkeypatch)
    enviados = _mails(monkeypatch)
    for mid, cad, monto in (("m1", "alejo", 6000), ("m2", "maria-perez", 4000)):
        fake.table("movimientos_cadete").insert({"id": mid, "cadete": cad, "tipo": "entrega", "referencia_id": mid,
                                                 "descripcion": "E", "monto_ars": monto, "creado_en": "2026-11-18T10:00:00+00:00"}).execute()
    assert "$ 4.000" in admin.get("/admin/cadete/saldo?cadete=maria-perez").text
    assert "$ 6.000" not in admin.get("/admin/cadete/saldo?cadete=maria-perez").text.split("saldo-total")[1].split("</strong>")[0]
    r = admin.post("/admin/cadete/movimientos/pagar?cadete=maria-perez")
    assert r.status_code == 200, r.text
    movs = {m["id"]: m for m in fake.table("movimientos_cadete").select("*").execute().data}
    assert movs["m2"].get("pagado_en") and not movs["m1"].get("pagado_en")
    assert [d for d, _, _ in enviados][-1] == "maria@example.com"
    maria = _c()
    maria.post("/admin/cadete/login", json={"email": "maria@example.com", "password": "clave-maria-123"})
    assert maria.get("/admin/cadete/saldo").status_code == 200
