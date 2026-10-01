import json

from fastapi.testclient import TestClient

import web.app as appmod
from web.slugs import url_producto


def _escribir_productos(tmp_path, productos):
    path = tmp_path / "productos.json"
    path.write_text(json.dumps(productos), encoding="utf-8")
    return path


def test_link_viejo_p_redirige_al_producto_del_catalogo(tmp_path, monkeypatch):
    productos = [{"nombre": "Apple Watch S10 42mm GPS Aluminium Case", "categoria": "Apple - Watch", "usd": 400}]
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", _escribir_productos(tmp_path, productos))
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.get("/p/apple-watch-s10-42mm-gps-aluminium-case", follow_redirects=False)

    assert r.status_code == 301
    assert r.headers["location"] == "/?producto=Apple+Watch+S10+42mm+GPS+Aluminium+Case"


def test_link_viejo_p_inexistente_va_al_catalogo(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", _escribir_productos(tmp_path, []))
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.get("/p/no-existe", follow_redirects=False)

    assert r.status_code == 301
    assert r.headers["location"] == "/catalogo"


def test_url_producto_ya_no_arma_links_p():
    assert url_producto("iPhone 17 Pro 256GB") == "https://thetechroomarg.com/?producto=iPhone+17+Pro+256GB"
