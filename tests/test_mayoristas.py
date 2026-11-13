import math

import pytest

from web.mayoristas import catalogo_mayorista, descuento_por_margen


@pytest.mark.parametrize(("margen", "esperado"), [
    (34, None), (40, None), (44, None), (45, 5), (50, 10), (55, 15), (60, 20),
    (65, 25), (70, 30), (75, 35), (80, 40), (85, 45), (90, 50), (200, 50),
])
def test_descuento_por_banda_de_margen(margen, esperado):
    assert descuento_por_margen(500 + margen, 500) == esperado


def test_descuento_iphone_deja_25_limpios_con_entrega_20():
    assert descuento_por_margen(500 + 45, 500, 20) is None
    assert descuento_por_margen(500 + 50, 500, 20) == 5
    assert descuento_por_margen(500 + 90, 500, 20) == 45


def test_catalogo_mayorista_filtra_sin_costo_y_recalcula_monedas():
    productos = [
        {"nombre": "Elegible", "usd": 180, "pesos": 280800, "transferencia": 289485},
        {"nombre": "Sin costo", "usd": 180, "pesos": 280800, "transferencia": 289485},
    ]
    resultado = catalogo_mayorista(productos, {"Elegible": 100})
    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Elegible"
    assert resultado[0]["usd"] == 140
    assert resultado[0]["pesos"] == round(140 * (280800 / 180))
    assert resultado[0]["transferencia"] == round(140 * (289485 / 180))
    assert resultado[0]["usd"] >= 100 + 40


def test_catalogo_mayorista_omite_campos_privados():
    producto = {
        "nombre": "Elegible",
        "usd": 180,
        "pesos": 280800,
        "transferencia": 289485,
        "costo": 100,
        "margen": 80,
        "proveedor": "interno",
        "capacidad": "privada",
        "imagen": "publica",
    }

    resultado = catalogo_mayorista([producto], {"Elegible": 100})

    assert resultado == [{
        "nombre": "Elegible",
        "usd": 140,
        "pesos": round(140 * (280800 / 180)),
        "transferencia": round(140 * (289485 / 180)),
        "imagen": "publica",
        "usd_publico": 180,
        "pesos_publico": 280800,
        "transferencia_publico": 289485,
    }]


@pytest.mark.parametrize("costo", [None, "100", math.nan, math.inf, -1, 0])
def test_catalogo_mayorista_excluye_costos_invalidos(costo):
    producto = {"nombre": "Producto", "usd": 180, "pesos": 280800}

    assert catalogo_mayorista([producto], {"Producto": costo}) == []
