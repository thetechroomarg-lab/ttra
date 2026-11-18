from unificar_nombres import unificar


def _run(nombres, prev=()):
    items = [{"nombre": n} for n in nombres]
    rep = unificar(items, prev)
    return {i["nombre"] for i in items}, rep


def test_moto_e15_tres_proveedores():
    out, _ = _run(["MOTO E15 64GB", "MOTO E15 2GB 64GB", "Moto E15 2GB 64GB con Cargador"])
    assert out == {"MOTO E15 2GB 64GB"}


def test_orden_y_separadores_celular():
    out, _ = _run(["MOTO Edge 50 fusion 5g 256/8gb Slim", "MOTO EDGE 50 FUSION 5G 8GB 256GB slim"])
    assert len(out) == 1


def test_no_une_ram_distinta():
    out, _ = _run(["SAMSUNG A07 4GB 128GB", "SAMSUNG A07 6GB 128GB"])
    assert len(out) == 2


def test_generica_no_celular():
    out, _ = _run(["Notebook Lenovo IdeaPad 15 16GB RAM 512GB SSD", "NOTEBOOK LENOVO IDEAPAD 15 512GB 16GB"])
    assert len(out) == 1


def test_generica_no_une_modelos_distintos():
    out, _ = _run(["Auriculares JBL Tune 520BT", "Auriculares JBL Tune 720BT"])
    assert len(out) == 2
