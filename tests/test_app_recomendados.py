from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _catalogo_demo():
    return [
        {"nombre": "iPhone 15 128GB", "categoria": "Apple - iPhone"},
        {"nombre": "iPhone 15 Plus 256GB", "categoria": "Apple - iPhone"},
        {"nombre": "iPhone 16 128GB", "categoria": "Apple - iPhone"},
        {"nombre": "Galaxy A56 256GB", "categoria": "Samsung"},
        {"nombre": "MacBook Air M2 13", "categoria": "Mac"},
        {"nombre": "iPhone 13 CPO 128GB", "categoria": "Apple - iPhone Usado"},
    ]


def test_api_recomendados_prioriza_producto_visto_y_similares(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_productos", _catalogo_demo)
    c = TestClient(appmod.app, base_url="https://testserver")

    c.post("/registro", json={
        "nombre": "Ana", "apellido": "Gómez", "celular": "3511234567",
        "email": "ana@x.com", "password": "clave1234",
    "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    cliente_id = fake.table("clientes").select("*").eq("email", "ana@x.com").execute().data[0]["id"]
    fake.table("interacciones_cliente").insert({
        "id": "int-1",
        "cliente_id": cliente_id,
        "anon_id": None,
        "session_id": "anon-1",
        "tipo_evento": "view_item",
        "producto_nombre": "iPhone 15 128GB",
        "categoria": "Celulares",
        "marca": "Apple",
        "metadata": {},
        "fecha": "2026-08-22T12:00:00+00:00",
    }).execute()

    r = c.get("/api/recomendados?limit=3")

    assert r.status_code == 200
    productos = r.json()["productos"]
    assert [p["nombre"] for p in productos][:2] == [
        "iPhone 15 128GB",
        "iPhone 15 Plus 256GB",
    ]
    assert productos[0]["motivo_recomendacion"] == "✨ Ya viste este producto"
    assert productos[1]["motivo_recomendacion"].startswith("✨ Similar a iPhone 15 128GB")


def test_api_recomendados_usa_historial_anonimo(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_productos", _catalogo_demo)
    c = TestClient(appmod.app, base_url="https://testserver")

    fake.table("interacciones_cliente").insert({
        "id": "int-2",
        "cliente_id": None,
        "anon_id": "anon-77",
        "session_id": "anon-77",
        "tipo_evento": "view_item",
        "producto_nombre": "MacBook Air M2 13",
        "categoria": "Notebooks y Macbooks",
        "marca": "Apple",
        "metadata": {},
        "fecha": "2026-08-22T12:00:00+00:00",
    }).execute()

    r = c.get("/api/recomendados?limit=2", headers={"X-TTRA-ANON-ID": "anon-77"})

    assert r.status_code == 200
    productos = r.json()["productos"]
    assert productos[0]["nombre"] == "MacBook Air M2 13"
    assert productos[0]["motivo_recomendacion"] == "✨ Ya viste este producto"


def test_api_recomendados_fallback_excluye_usados(monkeypatch):
    monkeypatch.setattr(appmod, "_cargar_productos", _catalogo_demo)
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.get("/api/recomendados?limit=5")

    assert r.status_code == 200
    productos = r.json()["productos"]
    assert len(productos) == 5
    assert all("cpo" not in p["nombre"].lower() for p in productos)


def test_api_recomendados_mayorista_hidrata_precios_y_filtra_catalogo_autorizado(
    monkeypatch,
):
    """Catches ranking output bypassing wholesale eligibility and hydration."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    productos = [
        {
            "nombre": "Filtrado", "categoria": "Samsung", "usd": 130,
            "costo": 100, "proveedor": "privado", "margen": 30,
        },
        {
            "nombre": "Elegible", "categoria": "Samsung", "usd": 180,
            "costo": 100, "proveedor": "privado", "margen": 80,
        },
    ]
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: productos)
    monkeypatch.setattr(
        appmod,
        "_cargar_snapshot_mayorista",
        lambda: (productos, {"Filtrado": 100, "Elegible": 100}),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Ana", "apellido": "Gómez", "celular": "3511234567",
        "email": "ana@x.com", "password": "clave1234",
        "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",
    })
    cliente = fake.table("clientes").select("*").execute().data[0]
    fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq(
        "id", cliente["id"]
    ).execute()
    fake.table("interacciones_cliente").insert({
        "cliente_id": cliente["id"],
        "tipo_evento": "view_item",
        "producto_nombre": "Filtrado",
        "fecha": "2026-08-26T12:00:00+00:00",
    }).execute()

    respuesta = c.get("/api/recomendados?limit=4")

    assert respuesta.status_code == 200
    recomendados = respuesta.json()["productos"]
    assert [producto["nombre"] for producto in recomendados] == ["Elegible"]
    assert recomendados[0]["usd"] == 130
    assert not ({"costo", "proveedor", "margen", "capacidad"} & recomendados[0].keys())


def test_api_recomendados_minorista_no_devuelve_campos_privados(monkeypatch):
    """Catches the recommendation route returning raw product dictionaries."""
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [{
        "nombre": "Producto", "categoria": "Samsung", "usd": 180,
        "costo": 100, "proveedor": "privado", "margen": 80,
        "capacidad": 53,
    }])

    respuesta = TestClient(appmod.app, base_url="https://testserver").get(
        "/api/recomendados?limit=1"
    )

    assert respuesta.status_code == 200
    producto = respuesta.json()["productos"][0]
    assert producto["nombre"] == "Producto"
    assert not ({"costo", "proveedor", "margen", "capacidad"} & producto.keys())
