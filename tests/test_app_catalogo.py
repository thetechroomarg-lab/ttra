import json
import hashlib

from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _escribir_snapshot(tmp_path, productos, costos, *, version=1):
    productos_path = tmp_path / "productos.json"
    costos_path = tmp_path / "costos.json"
    manifiesto_path = tmp_path / "catalogo-manifest.json"
    productos_path.write_text(json.dumps(productos), encoding="utf-8")
    costos_path.write_text(json.dumps(costos), encoding="utf-8")
    manifiesto_path.write_text(json.dumps({
        "version": version,
        "generacion": "generacion-prueba",
        "productos_sha256": hashlib.sha256(productos_path.read_bytes()).hexdigest(),
        "costos_sha256": hashlib.sha256(costos_path.read_bytes()).hexdigest(),
    }), encoding="utf-8")
    return productos_path, costos_path, manifiesto_path


def _usar_snapshot(monkeypatch, paths):
    productos_path, costos_path, manifiesto_path = paths
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", productos_path)
    monkeypatch.setattr(appmod, "COSTOS_PATH", costos_path)
    monkeypatch.setattr(appmod, "CATALOGO_MANIFEST_PATH", manifiesto_path)


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
        "_cargar_snapshot_mayorista",
        lambda: ([
            {
                "nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180,
                "costo": 100, "margen": 80, "proveedor": "privado",
            },
            {"nombre": "Sin costo", "categoria": "Apple - iPhone", "usd": 180},
        ], {"Elegible": 100}),
    )

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
    paths = _escribir_snapshot(tmp_path, [{"nombre": "Elegible", "usd": 180}], {"Elegible": 100})
    _usar_snapshot(monkeypatch, paths)
    paths[1].write_text("{no es json}", encoding="utf-8")

    r = c.get("/api/catalogo")

    assert r.status_code == 200
    assert r.json() == {
        "secciones": {s: [] for s in appmod.catalogo.SECCIONES},
        "mensaje": "Estamos actualizando los precios",
        "modo_precio": "mayorista",
    }


def test_catalogo_mayorista_rechaza_costo_obsoleto_aunque_el_nombre_coincida(
    tmp_path, monkeypatch,
):
    """Catches name-only joins pairing a new retail row with a stale cost."""
    paths = _escribir_snapshot(
        tmp_path,
        [{"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180}],
        {"Elegible": 100},
    )
    _usar_snapshot(monkeypatch, paths)
    c = _cliente_autenticado(tmp_path, monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").execute().data[0]
    fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq(
        "id", cliente["id"]
    ).execute()

    paths[0].write_text(json.dumps([
        {"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 220},
    ]), encoding="utf-8")

    mayorista = c.get("/api/catalogo")
    assert mayorista.status_code == 200
    assert mayorista.json()["modo_precio"] == "mayorista"
    assert mayorista.json()["secciones"]["Celulares"] == []
    assert mayorista.json()["mensaje"] == "Estamos actualizando los precios"

    fake.table("clientes").update({"tipo_cliente": "minorista"}).eq(
        "id", cliente["id"]
    ).execute()
    minorista = c.get("/api/catalogo")
    assert minorista.status_code == 200
    assert minorista.json()["secciones"]["Celulares"][0]["usd"] == 220


def test_catalogo_mayorista_falla_cerrado_si_crash_deja_manifest_anterior(
    tmp_path, monkeypatch,
):
    """Catches a crash after individual replacements but before manifest commit."""
    paths = _escribir_snapshot(
        tmp_path,
        [{"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180}],
        {"Elegible": 100},
    )
    _usar_snapshot(monkeypatch, paths)
    c = _cliente_autenticado(tmp_path, monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").execute().data[0]
    fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq(
        "id", cliente["id"]
    ).execute()
    paths[0].write_text(json.dumps([
        {"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 240},
    ]), encoding="utf-8")
    paths[1].write_text(json.dumps({"Elegible": 190}), encoding="utf-8")

    respuesta = c.get("/api/catalogo")

    assert respuesta.status_code == 200
    assert respuesta.json()["secciones"]["Celulares"] == []
    assert respuesta.json()["mensaje"] == "Estamos actualizando los precios"


def test_catalogo_mayorista_rechaza_version_de_manifest_desconocida(
    tmp_path, monkeypatch,
):
    """Catches accepting a snapshot format whose consistency contract is unknown."""
    paths = _escribir_snapshot(
        tmp_path,
        [{"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180}],
        {"Elegible": 100},
        version=99,
    )
    _usar_snapshot(monkeypatch, paths)
    c = _cliente_autenticado(tmp_path, monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").execute().data[0]
    fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq(
        "id", cliente["id"]
    ).execute()

    respuesta = c.get("/api/catalogo")

    assert respuesta.status_code == 200
    assert respuesta.json()["secciones"]["Celulares"] == []


def test_admin_habilita_y_revoca_catalogo_mayorista_por_rutas_reales(tmp_path, monkeypatch):
    """Catches an admin access change that does not reach the catalog session."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    paths = _escribir_snapshot(tmp_path, [
        {"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": 180},
        {"nombre": "Sin costo", "categoria": "Apple - iPhone", "usd": 180},
    ], {"Elegible": 100})
    _usar_snapshot(monkeypatch, paths)
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
