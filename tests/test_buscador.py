from web import buscador
from web.buscador import _buscar, _genero, responder_sin_ia

PRODS = [
    {"nombre": "iPhone 13 128GB", "usd": 560, "pesos": 862400, "transferencia": 889072},
    {"nombre": "iPhone 13 256GB", "usd": 610, "pesos": 939400, "transferencia": 968454},
    {"nombre": "Samsung A16 128GB", "usd": 170, "pesos": 261800, "transferencia": 269897},
]


def _reset():
    buscador.SESIONES.clear()


def test_genero_por_nombre():
    assert _genero("Maria") == "mujer"
    assert _genero("Carlos") == "hombre"
    assert _genero("Luca") == "hombre"       # excepción


def test_buscar_por_palabras():
    r = _buscar("iphone 13", PRODS)
    assert len(r) == 2 and r[0]["usd"] == 560   # ordenado por precio


def test_flujo_pide_nombre_luego_busca_y_arma_pedido():
    _reset()
    s = "s1"
    # 1) primer mensaje = nombre
    t, g, d = responder_sin_ia("hola soy Carlos", s, PRODS)
    assert "Carlos" in t and g == "hombre" and d["nombre"] == "Carlos"
    # 2) busca
    t, g, d = responder_sin_ia("iphone 13", s, PRODS)
    assert "1. iPhone 13 128GB" in t and "2. iPhone 13 256GB" in t
    # 3) elige el 1
    t, g, d = responder_sin_ia("1", s, PRODS)
    assert "A. Agregar al carrito" in t
    # 4) B = agregar y cerrar -> link de WhatsApp con el pedido
    t, g, d = responder_sin_ia("B", s, PRODS)
    assert "wa.me/543512145217?text=" in t
    assert "TOTAL" in t


def test_garantia_y_envios_sin_ia():
    _reset()
    s = "s2"
    responder_sin_ia("Ana", s, PRODS)              # da el nombre
    t, _, _ = responder_sin_ia("que garantia tiene el xiaomi?", s, PRODS)
    assert "3 meses" in t
    t, _, _ = responder_sin_ia("hacen envios?", s, PRODS)
    assert "cadetería" in t.lower() or "envíos" in t.lower()


def test_sin_resultados_avisa():
    _reset()
    s = "s3"
    responder_sin_ia("Pedro", s, PRODS)
    t, _, _ = responder_sin_ia("heladera samsung", s, PRODS)
    assert "no encontré" in t.lower()
