"""Regresiones de la auditoría de seguridad de noviembre 2026 (datos ficticios)."""
import logging

import httpx
from fastapi.testclient import TestClient

import web.app as appmod


def _cliente():
    return TestClient(appmod.app, base_url="https://testserver", raise_server_exceptions=False)


def test_docs_y_openapi_no_se_publican_por_defecto():
    assert appmod._API_DOCS is False
    with _cliente() as c:
        for ruta in ("/docs", "/redoc", "/openapi.json"):
            assert c.get(ruta).status_code in (302, 303, 307, 404), ruta


def test_cuerpo_declarado_gigante_se_rechaza_sin_leerlo():
    with _cliente() as c:
        r = c.post("/chat", content=b"{}", headers={"content-length": str(appmod._MAX_BODY_BYTES + 1),
                                                    "content-type": "application/json"})
    assert r.status_code == 413


def test_link_de_noticia_solo_http_https():
    assert appmod._link_noticia_seguro("https://example.com/a") == "https://example.com/a"
    assert appmod._link_noticia_seguro("javascript:alert(1)") == ""
    assert appmod._link_noticia_seguro("data:text/html,x") == ""
    assert appmod._separar_titulo_y_fuente("Hola - Medio", "javascript:alert(1)")["link"] == ""


def test_feed_de_noticias_con_dtd_se_descarta(monkeypatch):
    appmod._noticias_cache.update({"titulares": [], "actualizado": 0.0})
    malicioso = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "bbbb">]><rss><channel><item><title>&a;</title><link>https://e.com</link></item></channel></rss>'
    monkeypatch.setattr(appmod.httpx, "get", lambda *a, **k: httpx.Response(200, text=malicioso, request=httpx.Request("GET", "https://x")))
    with _cliente() as c:
        assert c.get("/api/noticias").json() == {"titulares": []}


def test_cotizar_envio_tiene_tope_por_minuto(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "_intentos_login_fallidos", appmod.LoginAttemptStore(tmp_path / "l.sqlite3"))
    monkeypatch.setattr(appmod.zona_envio, "cotizar", lambda *a, **k: {"zona": "gratis"})
    with _cliente() as c:
        codigos = [c.post("/api/envio/cotizar", json={"lat": -31.4, "lng": -64.2}).status_code for _ in range(125)]
    assert codigos[:120] == [200] * 120
    assert set(codigos[120:]) == {429}


def test_login_admin_fallido_deja_registro_sin_la_clave(caplog):
    with caplog.at_level(logging.WARNING, logger="web.security"), _cliente() as c:
        r = c.post("/admin/clientes/login", json={"password": "clave-equivocada-xyz"})
    assert r.status_code in (401, 429)
    assert "clave-equivocada-xyz" not in caplog.text
