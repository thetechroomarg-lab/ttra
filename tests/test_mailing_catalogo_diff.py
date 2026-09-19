from web.mailing import catalogo_diff


def test_detecta_producto_que_no_estaba_en_el_snapshot():
    actuales = [{"nombre": "A"}, {"nombre": "B"}]
    snapshot = [{"nombre": "A"}]

    nuevos = catalogo_diff.detectar_nuevos(actuales, snapshot)

    assert nuevos == [{"nombre": "B"}]


def test_no_detecta_nada_si_el_catalogo_no_cambio():
    actuales = [{"nombre": "A"}, {"nombre": "B"}]
    snapshot = [{"nombre": "A"}, {"nombre": "B"}]

    assert catalogo_diff.detectar_nuevos(actuales, snapshot) == []


def test_snapshot_vacio_todo_es_nuevo():
    actuales = [{"nombre": "A"}]

    assert catalogo_diff.detectar_nuevos(actuales, []) == [{"nombre": "A"}]
