import json

from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_autenticado(tmp_path, monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave123",
    "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    return c


def test_api_catalogo_es_publica_sin_sesion(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [])
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/api/catalogo")
    assert r.status_code == 200


def test_pagina_catalogo_sin_sesion_redirige_a_login(tmp_path, monkeypatch):
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    r = c.get("/catalogo")
    assert r.status_code in (302, 307)
    assert "login" in r.headers["location"]


def test_api_catalogo_sin_productos(tmp_path, monkeypatch):
    c = _cliente_autenticado(tmp_path, monkeypatch)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [])
    r = c.get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["mensaje"] == "Estamos actualizando los precios"


def test_api_catalogo_con_productos(tmp_path, monkeypatch):
    c = _cliente_autenticado(tmp_path, monkeypatch)
    monkeypatch.setattr(
        appmod, "_cargar_productos",
        lambda: [{"nombre": "iPhone 15", "categoria": "Apple - iPhone"}],
    )
    r = c.get("/api/catalogo")
    assert r.status_code == 200
    secciones = r.json()["secciones"]
    assert secciones["Celulares"][0]["nombre"] == "iPhone 15"
    assert secciones["Gaming"] == []


def test_catalogo_publico_permanece_minorista(tmp_path, monkeypatch):
    """Catches a public catalog accidentally adopting wholesale prices."""
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [{"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180}],
    )

    r = TestClient(appmod.app, base_url="https://testserver").get("/api/catalogo")

    assert r.status_code == 200
    assert r.json()["modo_precio"] == "minorista"
    assert r.json()["secciones"]["Celulares"][0]["usd"] == 180


def test_catalogo_minorista_no_expone_campos_privados(tmp_path, monkeypatch):
    """Catches a contaminated public file leaking supplier-side calculations."""
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [{
            "nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180,
            "costo": 100, "margen": 80, "proveedor": "privado",
        }],
    )

    r = TestClient(appmod.app, base_url="https://testserver").get("/api/catalogo")

    assert r.status_code == 200
    producto = r.json()["secciones"]["Celulares"][0]
    assert "costo" not in producto
    assert "margen" not in producto
    assert "proveedor" not in producto


def test_catalogo_mayorista_filtra_y_descuenta_por_sesion(tmp_path, monkeypatch):
    """Catches ignoring the current client's wholesale status or private costs."""
    c = _cliente_autenticado(tmp_path, monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").execute().data[0]
    fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq("id", cliente["id"]).execute()
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [
            {
                "nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180,
                "costo": 100, "margen": 80, "proveedor": "privado",
            },
            {"nombre": "Sin costo", "categoria": "Apple - iPhone", "usd": 180},
        ],
    )
    monkeypatch.setattr(appmod, "COSTOS_PATH", tmp_path / "costos.json")
    (tmp_path / "costos.json").write_text('{"Elegible": 100}', encoding="utf-8")

    r = c.get("/api/catalogo")

    assert r.status_code == 200
    assert r.json()["modo_precio"] == "mayorista"
    assert r.json()["secciones"]["Celulares"] == [
        {"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 130, "marca": "Apple"}
    ]
    assert "costo" not in r.text
    assert "margen" not in r.text
    assert "proveedor" not in r.text


def test_catalogo_mayorista_con_costos_invalidos_devuelve_actualizacion(tmp_path, monkeypatch):
    """Catches a corrupt private cost file breaking the public catalog route."""
    c = _cliente_autenticado(tmp_path, monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").execute().data[0]
    fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq("id", cliente["id"]).execute()
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [{"nombre": "Elegible", "usd": 180}])
    monkeypatch.setattr(appmod, "COSTOS_PATH", tmp_path / "costos.json")
    (tmp_path / "costos.json").write_text("{no es json}", encoding="utf-8")

    r = c.get("/api/catalogo")

    assert r.status_code == 200
    assert r.json() == {
        "secciones": {s: [] for s in appmod.catalogo.SECCIONES},
        "mensaje": "Estamos actualizando los precios",
        "modo_precio": "mayorista",
    }


def test_admin_habilita_y_revoca_catalogo_mayorista_por_rutas_reales(tmp_path, monkeypatch):
    """Catches an admin access change that does not reach the catalog session."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    productos_path = tmp_path / "productos.json"
    costos_path = tmp_path / "costos.json"
    productos_path.write_text(json.dumps([
        {"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180},
        {"nombre": "Sin costo", "categoria": "Apple - iPhone", "usd": 180},
    ]), encoding="utf-8")
    costos_path.write_text(json.dumps({"Elegible": 100}), encoding="utf-8")
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", productos_path)
    monkeypatch.setattr(appmod, "COSTOS_PATH", costos_path)
    cliente = TestClient(appmod.app, base_url="https://testserver")

    registro = cliente.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
        "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",
    })
    assert registro.status_code == 200
    cliente_id = fake.table("clientes").select("*").execute().data[0]["id"]

    admin = TestClient(appmod.app, base_url="https://testserver")
    acceso_admin = admin.post("/admin/clientes/login", json={"password": "clave-admin"})
    habilitar = admin.post(f"/admin/clientes/{cliente_id}/mayorista", json={"habilitado": True})
    assert acceso_admin.status_code == 200
    assert habilitar.status_code == 200
    assert habilitar.json() == {"ok": True, "tipo_cliente": "mayorista"}

    catalogo_mayorista = cliente.get("/api/catalogo")
    assert catalogo_mayorista.status_code == 200
    assert catalogo_mayorista.json()["modo_precio"] == "mayorista"
    assert catalogo_mayorista.json()["secciones"]["Celulares"] == [
        {"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 130, "marca": "Apple"},
    ]

    revocar = admin.post(f"/admin/clientes/{cliente_id}/mayorista", json={"habilitado": False})
    assert revocar.status_code == 200
    assert revocar.json() == {"ok": True, "tipo_cliente": "minorista"}

    catalogo_minorista = cliente.get("/api/catalogo")
    assert catalogo_minorista.status_code == 200
    assert catalogo_minorista.json()["modo_precio"] == "minorista"
    assert catalogo_minorista.json()["secciones"]["Celulares"] == [
        {"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180, "marca": "Apple"},
        {"nombre": "Sin costo", "categoria": "Apple - iPhone", "usd": 180, "marca": "Apple"},
    ]


def test_flujo_completo_registro_logout_login_catalogo(tmp_path, monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod, "_cargar_productos",
        lambda: [{"nombre": "iPhone 15", "categoria": "Apple - iPhone"}],
    )
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave123",
    "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    assert r.status_code == 200

    r = c.post("/logout")
    assert r.status_code == 200

    r = c.post("/login", json={"email": "juan@x.com", "password": "clave123"})
    assert r.status_code == 200

    r = c.get("/catalogo")
    assert r.status_code == 200

    r = c.get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["secciones"]["Celulares"][0]["nombre"] == "iPhone 15"

    r = c.post("/logout")
    assert r.status_code == 200

    # /api/catalogo ahora es pública: sigue respondiendo 200 incluso sin sesión.
    r = c.get("/api/catalogo")
    assert r.status_code == 200
