from bands import monto_por_banda, calcular_precio


def test_monto_por_banda_limites():
    assert monto_por_banda(0) == 40
    assert monto_por_banda(300) == 40       # límite superior inclusive
    assert monto_por_banda(300.01) == 40
    assert monto_por_banda(600) == 40
    assert monto_por_banda(900) == 40
    assert monto_por_banda(1300) == 60
    assert monto_por_banda(1600) == 75
    assert monto_por_banda(2000) == 120
    assert monto_por_banda(2400) == 150
    assert monto_por_banda(2400.01) == 190
    assert monto_por_banda(99999) == 190


def test_calcular_precio_suma_y_redondea_arriba_a_5():
    assert calcular_precio(100) == 140       # 100 + 40 = 140
    assert calcular_precio(611) == 655       # 611 + 40 = 651 -> 655
    assert calcular_precio(615) == 655       # 615 + 40 = 655 -> 655
    assert calcular_precio(300) == 340       # 300 + 40 = 340
    assert calcular_precio(2500) == 2690  # 2500 + 190 = 2690
