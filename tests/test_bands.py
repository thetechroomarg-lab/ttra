from bands import monto_por_banda, calcular_precio


def test_monto_por_banda_limites():
    assert monto_por_banda(0) == 30
    assert monto_por_banda(300) == 30       # límite superior inclusive
    assert monto_por_banda(300.01) == 40
    assert monto_por_banda(600) == 40
    assert monto_por_banda(900) == 50
    assert monto_por_banda(1300) == 70
    assert monto_por_banda(1600) == 85
    assert monto_por_banda(2000) == 130
    assert monto_por_banda(2400) == 160
    assert monto_por_banda(2400.01) == 200
    assert monto_por_banda(99999) == 200


def test_calcular_precio_suma_y_redondea_arriba_a_5():
    assert calcular_precio(100) == 130       # 100 + 30 = 130
    assert calcular_precio(611) == 665       # 611 + 50 = 661 -> 665
    assert calcular_precio(615) == 665       # 615 + 50 = 665 -> 665
    assert calcular_precio(300) == 330       # 300 + 30 = 330
    assert calcular_precio(2500) == 2700     # 2500 + 200 = 2700
