from fastapi.testclient import TestClient

import web.app as appmod


def _preparar(monkeypatch, costo):
    appmod._gasto.clear()
    monkeypatch.setattr(appmod, "_cargar_productos",
                        lambda: [{"nombre": "x", "usd": 1, "pesos": 1, "transferencia": 1}])
    monkeypatch.setattr(appmod, "_cliente", lambda: None)
    monkeypatch.setattr(appmod, "responder", lambda *a, **k: ("respuesta bot", costo, None))
    return TestClient(appmod.app)


def test_tope_por_sesion_corta_al_superar_limite(monkeypatch):
    # un mensaje que ya supera el tope (0.30 > 0.25)
    c = _preparar(monkeypatch, 0.30)
    r1 = c.post("/chat", json={"mensaje": "hola", "sesion": "s1"})
    assert r1.json()["respuesta"] == "respuesta bot"       # el 1º sí responde
    r2 = c.post("/chat", json={"mensaje": "otra", "sesion": "s1"})
    assert "WhatsApp" in r2.json()["respuesta"]            # el 2º ya está cortado


def test_tope_es_por_sesion_no_global(monkeypatch):
    c = _preparar(monkeypatch, 0.30)
    c.post("/chat", json={"mensaje": "hola", "sesion": "s1"})   # s1 supera el tope
    c.post("/chat", json={"mensaje": "otra", "sesion": "s1"})   # s1 cortada
    # una sesión distinta sigue funcionando
    r = c.post("/chat", json={"mensaje": "hola", "sesion": "s2"})
    assert r.json()["respuesta"] == "respuesta bot"
