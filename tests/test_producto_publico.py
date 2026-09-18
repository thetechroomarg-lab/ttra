import json

from fastapi.testclient import TestClient

import web.app as appmod


def _escribir_productos(tmp_path, productos):
    path = tmp_path / "productos.json"
    path.write_text(json.dumps(productos), encoding="utf-8")
    return path


def test_pagina_producto_publico_sin_login(tmp_path, monkeypatch):
    productos = [{
        "nombre": "S26 Ultra 5G 12GB 256GB",
        "categoria": "Samsung",
        "usd": 1065,
        "pesos": 1672050,
        "transferencia": 1723763,
        "colores": ["Black", "Colbat Violet"],
    }]
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", _escribir_productos(tmp_path, productos))
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.get("/p/s26-ultra-5g-12gb-256gb")

    assert r.status_code == 200
    assert "S26 Ultra 5G 12GB 256GB" in r.text
    assert "1065" in r.text
    assert "wa.me" in r.text


def test_pagina_producto_publico_no_encontrado(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", _escribir_productos(tmp_path, []))
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.get("/p/no-existe")

    assert r.status_code == 404
    assert "wa.me" in r.text
