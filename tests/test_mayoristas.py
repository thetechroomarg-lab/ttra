import math

import pytest

from web.mayoristas import catalogo_mayorista, descuento_mayorista


@pytest.mark.parametrize(("ganancia", "esperado"), [
    (0, None), (30, None), (39, None), (40, 20), (41, 20), (42, 21), (70, 35),
    (71, 35), (100, 50), (200, 100),
])
def test_descuento_es_la_mitad_de_la_ganancia_y_piso_de_20(ganancia, esperado):
    """Catches a discount that isn't 50% of profit, or products under the 20 floor."""
    assert descuento_mayorista(500 + ganancia, 500) == esperado


def test_mayorista_nunca_muestra_descuento_menor_a_20_ni_ganancia_menor_a_20():
    """Catches showing a wholesale product that leaves less than 20 profit or discount."""
    for ganancia in range(0, 300):
        d = descuento_mayorista(500 + ganancia, 500)
        if d is None:
            continue
        assert d >= 20
        assert ganancia - d >= 20


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
    assert resultado[0]["usd"] == 100 + 40


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


def test_catalogo_mayorista_oculta_productos_que_no_dejan_20_de_ganancia():
    productos = [
        {"nombre": "Justo", "usd": 140},
        {"nombre": "Corto", "usd": 139},
    ]
    resultado = catalogo_mayorista(productos, {"Justo": 100, "Corto": 100})

    assert [p["nombre"] for p in resultado] == ["Justo"]
    assert resultado[0]["usd"] == 120
    assert resultado[0]["usd_publico"] == 140
