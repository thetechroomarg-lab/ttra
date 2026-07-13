from normalize import normalizar


def test_normaliza_mayusculas_acentos_y_espacios():
    assert normalizar("  iPhone  13   Pro ") == "iphone 13 pro"
    assert normalizar("Cámara") == "camara"


def test_quita_puntuacion():
    assert normalizar("iPhone-13 (128GB)") == "iphone 13 128gb"


def test_nombres_equivalentes_normalizan_igual():
    assert normalizar("MOTOROLA g54") == normalizar("motorola   G54")
