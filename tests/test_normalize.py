from normalize import normalizar


def test_normaliza_mayusculas_acentos_y_espacios():
    assert normalizar("  iPhone  13   Pro ") == "iphone 13 pro"
    assert normalizar("Cámara") == "camara"


def test_quita_puntuacion():
    assert normalizar("iPhone-13 (128GB)") == "iphone 13 128gb"


def test_nombres_equivalentes_normalizan_igual():
    assert normalizar("MOTOROLA g54") == normalizar("motorola   G54")


def test_el_signo_mas_distingue_pro_de_pro_plus():
    # "PRO+" y "PRO" son productos distintos: no deben normalizar igual.
    assert normalizar("Redmi Note 15 Pro+") != normalizar("Redmi Note 15 Pro")
    assert "plus" in normalizar("Redmi Note 15 Pro+")


def test_ordena_capacidades_sin_importar_orden_ni_formato():
    # 64/2GB, 2GB 64GB y 64GB 2GB son el mismo equipo: deben normalizar igual.
    base = normalizar("Moto E15 2GB 64GB")
    assert normalizar("Moto E15 64/2GB") == base
    assert normalizar("Moto E15 64GB 2GB") == base
