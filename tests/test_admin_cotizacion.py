import json

import pytest
from fastapi.testclient import TestClient

import web.app as appmod


@pytest.fixture
def contexto(tmp_path, monkeypatch):
    monkeypatch.delenv("COTIZACION_PATH", raising=False)
    productos = tmp_path / "productos.json"
    productos.write_text(json.dumps([{
        "nombre": "iPhone 15", "categoria": "Apple - iPhone",
        "usd": 100, "pesos": 156500, "transferencia": 161340,
    }]))
    manifiesto = tmp_path / "catalogo-manifest.json"
    manifiesto.write_text('{"cotizacion":1565}')
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", productos)
    monkeypatch.setattr(appmod, "CATALOGO_MANIFEST_PATH", manifiesto)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    c = TestClient(appmod.app, base_url="https://testserver")
    return c, productos


def ingresar(c):
    assert c.post("/admin/clientes/login", json={"password": "clave-admin"}).status_code == 200


def test_solo_admin_puede_cambiar_cotizacion(contexto):
    c, productos = contexto
    assert c.post("/admin/cotizacion", json={"valor": "1600"}).status_code == 401
    assert not productos.with_name("cotizacion-admin.json").exists()


def test_guardado_persistente_actualiza_catalogo_y_conserva_original(contexto):
    c, productos = contexto
    original = productos.read_bytes()
    ingresar(c)
    r = c.post("/admin/cotizacion", json={"valor": "1600"})
    assert r.status_code == 200
    assert r.json()["valor"] == 1600
    nuevo_cliente = TestClient(appmod.app, base_url="https://testserver")
    assert nuevo_cliente.get("/api/cotizacion").json()["valor"] == 1600
    producto = nuevo_cliente.get("/api/catalogo").json()["secciones"]["Celulares"][0]
    assert (producto["usd"], producto["pesos"], producto["transferencia"]) == (100, 160000, 164948)
    assert productos.read_bytes() == original
    assert json.loads(productos.with_name("cotizacion-admin.json").read_text())["valor"] == 1600


@pytest.mark.parametrize("valor", ["", "0", "-10", "1.600", "1,600", "1e3", "abc", True, None, 1.5, "999999999999999999999"])
def test_rechaza_valores_invalidos_sin_cambiar_cotizacion(contexto, valor):
    c, _ = contexto
    ingresar(c)
    assert c.post("/admin/cotizacion", json={"valor": valor}).status_code == 400
    assert c.get("/api/cotizacion").json()["valor"] == 1565


def test_error_de_escritura_no_informa_exito(contexto, monkeypatch):
    from web import cotizacion
    c, _ = contexto
    ingresar(c)
    def fallar(*args):
        raise OSError("Disco no disponible")
    monkeypatch.setattr(cotizacion, "guardar", fallar)
    assert c.post("/admin/cotizacion", json={"valor": "1600"}).status_code == 503
    assert c.get("/api/cotizacion").json()["valor"] == 1565


def test_formulario_protegido_y_teclado_numerico(contexto):
    from html.parser import HTMLParser
    class Inputs(HTMLParser):
        campo = None
        def handle_starttag(self, tag, attrs):
            if tag == "input" and dict(attrs).get("id") == "cotizacion-valor":
                self.campo = dict(attrs)
    c, _ = contexto
    assert c.get("/admin/cotizacion", follow_redirects=False).status_code == 303
    ingresar(c)
    r = c.get("/admin/cotizacion")
    assert r.status_code == 200
    parser = Inputs()
    parser.feed(r.text)
    campo = parser.campo
    assert campo["inputmode"] == "numeric"
    assert campo["pattern"] == "[0-9]+"
    assert campo["value"] == "1565"


def test_actualizar_catalogo_no_pisa_cotizacion_manual_y_mail_la_reutiliza(contexto, monkeypatch):
    from web import mail_pedido
    c, productos = contexto
    ingresar(c)
    assert c.post("/admin/cotizacion", json={"valor": "1600"}).status_code == 200
    productos.write_text(json.dumps([{
        "nombre": "iPhone 15", "categoria": "Apple - iPhone",
        "usd": 200, "pesos": 300000, "transferencia": 309278,
    }]))
    monkeypatch.setattr(mail_pedido, "PRODUCTOS_PATH", productos)
    producto = c.get("/api/catalogo").json()["secciones"]["Celulares"][0]
    assert producto["pesos"] == 320000
    assert producto["transferencia"] == 329897
    assert mail_pedido.cotizacion_catalogo() == 1600


def test_mayorista_aplica_cotizacion_sin_romper_hashes_del_catalogo(contexto, monkeypatch):
    from tests.test_app_catalogo import _escribir_snapshot, _usar_snapshot
    c, productos = contexto
    paths = _escribir_snapshot(productos.parent, [{
        "nombre": "iPhone 15", "categoria": "Apple - iPhone",
        "usd": 180, "pesos": 281700, "transferencia": 290412,
    }], {"iPhone 15": 100})
    _usar_snapshot(monkeypatch, paths)
    monkeypatch.setattr(appmod, "_tipo_cliente_sesion", lambda request: "mayorista")
    ingresar(c)
    assert c.post("/admin/cotizacion", json={"valor": "1600"}).status_code == 200
    producto = c.get("/api/catalogo").json()["secciones"]["Celulares"][0]
    assert producto["usd"] == 130
    assert producto["pesos"] == 208000
    assert producto["pesos_publico"] == 288000
    assert producto["transferencia"] == 214433


def test_admin_tiene_acceso_desde_ambos_paneles(contexto, monkeypatch):
    from tests.fakes_supabase import FakeSupabaseClient
    c, _ = contexto
    monkeypatch.setattr(appmod, "get_client", lambda: FakeSupabaseClient())
    ingresar(c)
    for ruta in ["/admin/clientes", "/admin/clientes/lista"]:
        respuesta = c.get(ruta)
        assert respuesta.status_code == 200
        assert 'href="/admin/cotizacion"' in respuesta.text
