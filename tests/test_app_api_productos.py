from fastapi.testclient import TestClient

import web.app as appmod


def test_api_productos_devuelve_el_catalogo(monkeypatch):
    productos_falsos = [{"nombre": "Producto de prueba", "usd": 100}]
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: productos_falsos)
    cliente = TestClient(appmod.app, base_url="https://testserver")

    respuesta = cliente.get("/api/productos")

    assert respuesta.status_code == 200
    assert respuesta.json() == productos_falsos
