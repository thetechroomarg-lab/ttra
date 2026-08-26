import pytest

from web.mayoristas import catalogo_mayorista, descuento_por_margen


@pytest.mark.parametrize(("margen", "esperado"), [
    (34, None), (35, 5), (40, 10), (45, 15), (50, 20),
    (55, 25), (60, 30), (65, 35), (70, 40), (75, 45), (80, 50), (200, 50),
])
def test_descuento_por_banda_de_margen(margen, esperado):
    assert descuento_por_margen(500 + margen, 500) == esperado


def test_catalogo_mayorista_filtra_sin_costo_y_recalcula_monedas():
    productos = [
        {"nombre": "Elegible", "usd": 180, "pesos": 280800, "transferencia": 289485},
        {"nombre": "Sin costo", "usd": 180, "pesos": 280800, "transferencia": 289485},
    ]
    resultado = catalogo_mayorista(productos, {"Elegible": 100})
    assert len(resultado) == 1
    assert resultado[0]["nombre"] == "Elegible"
    assert resultado[0]["usd"] == 130
    assert resultado[0]["pesos"] == round(130 * (280800 / 180))
    assert resultado[0]["transferencia"] == round(130 * (289485 / 180))
    assert resultado[0]["usd"] >= 100 + 27
