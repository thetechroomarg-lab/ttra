from fastapi.testclient import TestClient

import web.app as appmod


def test_admin_productos_sin_token_configurado_da_503(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", None)
    c = TestClient(appmod.app)
    r = c.post("/admin/productos", json=[])
    assert r.status_code == 503


def test_admin_productos_con_token_incorrecto_da_401(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto123")
    c = TestClient(appmod.app)
    r = c.post("/admin/productos", json=[], headers={"X-Admin-Token": "otro"})
    assert r.status_code == 401


def test_admin_productos_sin_lista_da_400(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto123")
    c = TestClient(appmod.app)
    r = c.post("/admin/productos", json={"no": "es lista"}, headers={"X-Admin-Token": "secreto123"})
    assert r.status_code == 400


def test_admin_productos_guarda_y_api_catalogo_lo_refleja(tmp_path, monkeypatch):
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto123")
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", tmp_path / "productos.json")
    c = TestClient(appmod.app)

    nuevos = [{"nombre": "iPhone 15", "categoria": "Apple - iPhone"}]
    r = c.post("/admin/productos", json=nuevos, headers={"X-Admin-Token": "secreto123"})
    assert r.status_code == 200
    assert r.json() == {"ok": True, "productos": 1}

    r = c.get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["secciones"]["Celulares"][0]["nombre"] == "iPhone 15"
