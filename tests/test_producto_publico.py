import json
from pathlib import Path

from fastapi.testclient import TestClient

import web.app as appmod
from web.slugs import resolver_producto, url_producto


def _escribir_productos(tmp_path, productos):
    path = tmp_path / "productos.json"
    path.write_text(json.dumps(productos), encoding="utf-8")
    return path


def test_links_p_ya_no_existen(tmp_path, monkeypatch):
    productos = [{"nombre": "Apple Watch S10 42mm GPS Aluminium Case", "categoria": "Apple - Watch", "usd": 400}]
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", _escribir_productos(tmp_path, productos))
    c = TestClient(appmod.app, base_url="https://testserver")

    r = c.get("/p/apple-watch-s10-42mm-gps-aluminium-case", follow_redirects=False)

    assert r.status_code == 404


def test_url_producto_arma_link_con_slug_legible():
    assert url_producto("iPhone 17 Pro 256GB") == "https://thetechroomarg.com/?producto=iphone-17-pro-256gb"


_CATALOGO = [
    {"nombre": "Xiaomi Redmi Note 15 PRO 5G 12GB 512GB", "usd": 430},
    {"nombre": "REDMI 17 4GB 128GB", "usd": 225},
    {"nombre": "REDMI 17 5G 4GB 128GB", "usd": 260},
    {"nombre": "MOTO G86 5G 8GB 256GB", "usd": 330},
    {"nombre": "MOTO G86 5G 8GB 256GB (s/ cargador)", "usd": 310},
    {"nombre": "iPhone 14 128GB (Usado)", "usd": 400},
    {"nombre": "IPHONE 18 PRO 1TB", "usd": 2000},
]


def test_resolver_por_slug_y_por_nombre_viejo_exacto():
    assert resolver_producto("xiaomi-redmi-note-15-pro-5g-12gb-512gb", _CATALOGO) == "Xiaomi Redmi Note 15 PRO 5G 12GB 512GB"
    assert resolver_producto("REDMI 17 4GB 128GB", _CATALOGO) == "REDMI 17 4GB 128GB"


def test_resolver_tolera_cambios_de_nombre_del_proveedor():
    # Mayúsculas, orden, marca adelante, "Dual", "RAM", "1 TB" vs "1TB".
    assert resolver_producto("Redmi Note 15 Pro 5G 12GB RAM 512GB Dual", _CATALOGO) == "Xiaomi Redmi Note 15 PRO 5G 12GB 512GB"
    assert resolver_producto("iphone-18-pro-1-tb", _CATALOGO) == "IPHONE 18 PRO 1TB"


def test_resolver_no_confunde_4g_con_5g_ni_pro_con_base():
    assert resolver_producto("Xiaomi Redmi 17 5G 4GB 128GB", _CATALOGO) == "REDMI 17 5G 4GB 128GB"
    assert resolver_producto("Xiaomi Redmi 17 4GB 128GB Dual", _CATALOGO) == "REDMI 17 4GB 128GB"
    assert resolver_producto("iPhone 14 Pro 128GB (Usado)", _CATALOGO) is None


def test_resolver_con_duplicados_elige_el_mas_barato():
    assert resolver_producto("Motorola Moto G86 5G 8GB 256GB Dual", _CATALOGO) == "MOTO G86 5G 8GB 256GB (s/ cargador)"


def test_resolver_producto_que_ya_no_esta():
    assert resolver_producto("samsung-s24-ultra-12gb-512gb", _CATALOGO) is None
    assert resolver_producto("", _CATALOGO) is None


def test_api_link_producto(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", _escribir_productos(tmp_path, _CATALOGO))
    c = TestClient(appmod.app, base_url="https://testserver")

    assert c.get("/api/link-producto", params={"ref": "XIAOMI Redmi Note 15 Pro 5g 12GB 512GB"}).json() == {"nombre": "Xiaomi Redmi Note 15 PRO 5G 12GB 512GB"}
    assert c.get("/api/link-producto", params={"ref": "no-existe-mas"}).json() == {"nombre": None}


def test_landing_resuelve_links_y_muestra_sin_stock():
    js = (Path(__file__).resolve().parents[1] / "web" / "static" / "landing.js").read_text(encoding="utf-8")
    assert "/api/link-producto?ref=" in js
    assert 'params.set("producto", producto?.slug || nombre)' in js
    assert 'src="/producto-sin-stock.webp"' in js
    assert 'class="rc-panel-sin-stock-volver">Volver</button>' in js
