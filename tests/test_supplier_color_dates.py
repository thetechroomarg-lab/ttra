"""Supplier dates are part of a variant, never standalone color options."""
from normalize import separar_variantes as colors


def test_color_parser_preserves_dates_and_splits_real_variants():
    assert colors('Mist Blue 89% Grado A+ Cobertura 1/02/27') == ['Mist Blue 89% Grado A+ Cobertura 1/02/27']
    assert colors('Black/White, Blue / Red') == ['Black', 'White', 'Blue', 'Red']
    assert colors('Blue 89% Cobertura 1/02/27 / White 100% Cobertura 14/01/27') == [
        'Blue 89% Cobertura 1/02/27', 'White 100% Cobertura 14/01/27']


def test_used_variants_preserve_color_battery_and_condition_without_supplier_cost():
    from normalize import variantes_usadas_desde_detalles
    assert variantes_usadas_desde_detalles([
        'Blue 93%     4 unidades\t',
        'Gold 100% 1 unidad',
        'Grafito 95% 5 unidades',
        'Green 95% 6 unidades',
        'Green 100% 3 unidades',
        'Green 100% 2 unidades',
        'Blue 100% SIN FACE ID 550 DOLARES',
    ]) == ['Blue 93%', 'Gold 100%', 'Grafito 95%', 'Green 95%', 'Green 100%', 'Blue 100% SIN FACE ID']
