from imagelink import google_image_link


def test_arma_link_reemplazando_espacios_por_mas():
    assert google_image_link("iPhone 13 128GB") == (
        "https://www.google.com/search?tbm=isch&q=iPhone+13+128GB"
    )


def test_colapsa_espacios_multiples_y_recorta():
    assert google_image_link("  Motorola  G54  ") == (
        "https://www.google.com/search?tbm=isch&q=Motorola+G54"
    )
