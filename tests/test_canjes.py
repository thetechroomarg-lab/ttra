import re
from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

import web.app as appmod
from web import canjes
from tests.fakes_supabase import FakeSupabaseClient


class _Bucket:
    def __init__(self, guardados):
        self.guardados = guardados

    def upload(self, ruta, contenido, opciones=None):
        self.guardados[ruta] = contenido

    def download(self, ruta):
        return self.guardados[ruta]


class _Storage:
    def __init__(self):
        self.guardados = {}

    def from_(self, _bucket):
        return _Bucket(self.guardados)


def _jpeg():
    buf = BytesIO()
    Image.new("RGB", (40, 30), "red").save(buf, "JPEG")
    return buf.getvalue()


def _entorno(monkeypatch):
    fake = FakeSupabaseClient()
    fake.storage = _Storage()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    correos = []
    monkeypatch.setattr(
        appmod, "enviar_email",
        lambda destinatario, asunto, html, adjuntos=None, reply_to=None: correos.append(
            {"para": destinatario, "asunto": asunto, "html": html, "adjuntos": adjuntos or []}),
    )
    return fake, correos


def _cliente_logueado(fake):
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
        "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba"})
    cliente_id = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]["id"]
    return c, cliente_id


def _admin():
    a = TestClient(appmod.app, base_url="https://testserver")
    a.post("/admin/clientes/login", json={"password": "clave-admin"})
    return a


def _enviar(c, equipo="iphone-15-128gb", cantidad=len(canjes.ROTULOS_FOTOS)):
    return c.post("/api/canje/solicitudes", data={"equipo": equipo},
                  files=[("fotos", (f"{i}.jpg", _jpeg(), "image/jpeg")) for i in range(cantidad)])


def test_tabla_json_coincide_con_la_tabla_de_la_pagina():
    html = Path("web/static/plan-canje.html").read_text(encoding="utf-8")
    filas = re.findall(r'<th scope="row">([^<]+)</th><td>([^<]+)</td><td>US\$ ([\d.]+)</td>', html)
    en_pagina = [(m, c, int(v.replace(".", ""))) for m, c, v in filas]
    # Las opciones de 1 TB y 2 TB no tienen fila propia: se toman como 512 GB.
    en_datos = [(f["modelo"], f["capacidad"], f["valor_usd"]) for f in canjes.cargar_tabla() if not f.get("toma_como")]
    assert en_pagina == en_datos


def test_solicitud_requiere_sesion(monkeypatch):
    _entorno(monkeypatch)
    anonimo = TestClient(appmod.app, base_url="https://testserver")
    assert _enviar(anonimo).status_code == 401


def test_solicitud_pide_las_siete_fotos_y_un_equipo_de_la_tabla(monkeypatch):
    fake, correos = _entorno(monkeypatch)
    c, _ = _cliente_logueado(fake)
    assert _enviar(c, cantidad=4).status_code == 400
    assert _enviar(c, equipo="iphone-14-128gb").status_code == 400
    assert correos == [] and fake.table("canjes").select("*").execute().data == []


def test_solicitud_guarda_fotos_manda_mail_con_adjuntos_y_arma_whatsapp(monkeypatch):
    fake, correos = _entorno(monkeypatch)
    c, cliente_id = _cliente_logueado(fake)
    r = _enviar(c, "iphone-15-pro-128gb")
    assert r.status_code == 201
    assert r.json()["whatsapp_url"].startswith("https://wa.me/543512145217?text=")
    canje = fake.table("canjes").select("*").execute().data[0]
    assert canje["cliente_id"] == cliente_id and canje["estado"] == "pendiente"
    assert canje["valor_usd"] == 440 and len(canje["fotos"]) == 7
    assert set(canje["fotos"]) == set(fake.storage.guardados)
    assert len(correos) == 1 and len(correos[0]["adjuntos"]) == 7
    assert "iPhone 15 Pro 128 GB" in correos[0]["asunto"]


def test_limite_de_solicitudes_pendientes(monkeypatch):
    fake, _ = _entorno(monkeypatch)
    c, _ = _cliente_logueado(fake)
    for _ in range(3):
        assert _enviar(c).status_code == 201
    assert _enviar(c).status_code == 429


def test_panel_de_canjes_exige_admin(monkeypatch):
    fake, _ = _entorno(monkeypatch)
    anonimo = TestClient(appmod.app, base_url="https://testserver")
    assert anonimo.get("/admin/canjes?fragmento=1").status_code == 401
    assert anonimo.post("/admin/canjes/x/aprobar").status_code == 401
    assert anonimo.get("/admin/canjes/x/foto/0").status_code == 401


def test_admin_ve_la_solicitud_y_las_fotos(monkeypatch):
    fake, _ = _entorno(monkeypatch)
    c, _ = _cliente_logueado(fake)
    _enviar(c)
    canje = fake.table("canjes").select("*").execute().data[0]
    admin = _admin()
    pagina = admin.get("/admin/canjes?fragmento=1")
    assert pagina.status_code == 200 and "iPhone 15 128 GB" in pagina.text and "Juan Pérez" in pagina.text
    foto = admin.get(f"/admin/canjes/{canje['id']}/foto/0")
    assert foto.status_code == 200 and foto.headers["content-type"] == "image/jpeg"
    assert admin.get(f"/admin/canjes/{canje['id']}/foto/9").status_code == 404


def test_aprobar_crea_un_codigo_de_una_sola_vez_por_el_valor_de_la_tabla(monkeypatch):
    fake, correos = _entorno(monkeypatch)
    c, cliente_id = _cliente_logueado(fake)
    _enviar(c, "iphone-15-128gb")
    canje = fake.table("canjes").select("*").execute().data[0]
    r = _admin().post(f"/admin/canjes/{canje['id']}/aprobar")
    assert r.status_code == 200 and r.json()["valor_usd"] == 320
    codigo = r.json()["codigo"]
    fila = fake.table("codigos_descuento").select("*").eq("code", codigo).execute().data[0]
    assert fila["cliente_id"] == cliente_id and fila["activo"] and not fila.get("usado_en")
    assert fila["tope_total_usd"] == 320 and fila["productos"] == []
    assert correos[-1]["para"] == "juan@x.com" and codigo in correos[-1]["html"]
    # Una segunda aprobación no emite otro código.
    assert _admin().post(f"/admin/canjes/{canje['id']}/aprobar").status_code == 409
    assert len(fake.table("codigos_descuento").select("*").execute().data) == 1


def test_el_codigo_de_canje_descuenta_el_valor_de_la_tabla_en_el_carrito(monkeypatch):
    fake, _ = _entorno(monkeypatch)
    c, _ = _cliente_logueado(fake)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [
        {"nombre": "iPhone 17", "categoria": "Apple - iPhone", "usd": 1000, "pesos": 1560000, "transferencia": 1608248}])
    _enviar(c, "iphone-15-128gb")
    canje = fake.table("canjes").select("*").execute().data[0]
    codigo = _admin().post(f"/admin/canjes/{canje['id']}/aprobar").json()["codigo"]
    assert c.get("/api/me").json()["codigo_descuento_disponible"] == codigo
    r = c.post("/api/descuentos/validar", json={"codigo": codigo, "items": [{"nombre": "iPhone 17", "cantidad": 1}]})
    assert r.status_code == 200 and r.json()["descuento"]["usd"] == 320
    # El carrito explica de dónde sale el descuento: el iPhone en parte de pago.
    assert r.json()["canje_equipo"] == "iPhone 15 128 GB"


def test_un_codigo_que_no_es_de_canje_no_trae_equipo(monkeypatch):
    fake, _ = _entorno(monkeypatch)
    c, cliente_id = _cliente_logueado(fake)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [
        {"nombre": "iPhone 17", "categoria": "Apple - iPhone", "usd": 1000, "pesos": 1560000, "transferencia": 1608248}])
    fake.table("codigos_descuento").insert({
        "cliente_id": cliente_id, "code": "TTRA-MAIL1234", "productos": ["iPhone 17"],
        "descuento_usd": 5, "activo": True}).execute()
    r = c.post("/api/descuentos/validar", json={"codigo": "TTRA-MAIL1234", "items": [{"nombre": "iPhone 17", "cantidad": 1}]})
    assert r.status_code == 200 and r.json()["canje_equipo"] is None


def test_el_carrito_muestra_el_equipo_en_parte_de_pago():
    js = Path("web/static/landing.js").read_text(encoding="utf-8")
    assert "equipo: descuento.canje_equipo || null" in js
    assert "en parte de pago" in js and "textoCodigoAplicadoHtml(descuento)" in js


def test_el_codigo_de_canje_no_toca_los_saldos_de_referidos(monkeypatch):
    from web import referidos
    fake, _ = _entorno(monkeypatch)
    c, cliente_id = _cliente_logueado(fake)
    _enviar(c)
    canje = fake.table("canjes").select("*").execute().data[0]
    codigo = _admin().post(f"/admin/canjes/{canje['id']}/aprobar").json()["codigo"]
    fila = fake.table("codigos_descuento").select("*").eq("code", codigo).execute().data[0]
    assert referidos.aplicar_consumo(fake, fila) is None


def test_rechazar_avisa_con_motivo_y_no_crea_codigo(monkeypatch):
    fake, correos = _entorno(monkeypatch)
    c, _ = _cliente_logueado(fake)
    _enviar(c)
    canje = fake.table("canjes").select("*").execute().data[0]
    r = _admin().post(f"/admin/canjes/{canje['id']}/rechazar", json={"motivo": "La batería está baja"})
    assert r.status_code == 200
    assert fake.table("canjes").select("*").execute().data[0]["estado"] == "rechazado"
    assert fake.table("codigos_descuento").select("*").execute().data == []
    assert "La batería está baja" in correos[-1]["html"]
    assert _admin().post(f"/admin/canjes/{canje['id']}/aprobar").status_code == 409


def test_el_panel_de_admin_tiene_la_pestana_canjes(monkeypatch):
    _entorno(monkeypatch)
    pagina = _admin().get("/admin/clientes").text
    assert 'href="#canjes"' in pagina and 'id="admin-seccion-canjes"' in pagina
    assert "/admin/canjes?fragmento=1" in pagina


def test_1tb_y_2tb_se_toman_al_precio_de_512gb_del_mismo_modelo():
    tabla = canjes.cargar_tabla()
    precio_512 = {f["modelo"]: f["valor_usd"] for f in tabla if f["capacidad"] == "512 GB"}
    grandes = [f for f in tabla if f["capacidad"] in {"1 TB", "2 TB"}]
    assert {(f["modelo"], f["capacidad"]) for f in grandes} == {
        ("iPhone 15 Pro", "1 TB"), ("iPhone 16 Pro Max", "1 TB"),
        ("iPhone 17 Pro Max", "1 TB"), ("iPhone 17 Pro Max", "2 TB")}
    for f in grandes:
        assert f["toma_como"] == "512 GB" and f["valor_usd"] == precio_512[f["modelo"]]


def test_solicitud_de_2tb_aprueba_con_el_valor_de_512gb(monkeypatch):
    fake, correos = _entorno(monkeypatch)
    c, _ = _cliente_logueado(fake)
    assert _enviar(c, "iphone-17-pro-max-2tb").status_code == 201
    assert "precio de 512 GB" in correos[0]["html"]
    canje = fake.table("canjes").select("*").execute().data[0]
    assert canje["capacidad"] == "2 TB" and canje["valor_usd"] == 1100
    assert "precio de 512 GB" in _admin().get("/admin/canjes?fragmento=1").text
    assert _admin().post(f"/admin/canjes/{canje['id']}/aprobar").json()["valor_usd"] == 1100
