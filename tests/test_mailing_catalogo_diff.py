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


def _productos(cantidad, prefijo="P"):
    return [{"nombre": f"{prefijo}{i}"} for i in range(cantidad)]


def test_seleccion_devuelve_diez_si_hay_diez_o_mas_nuevos():
    nuevos = _productos(12, "N")
    catalogo = nuevos + _productos(5, "C")

    seleccion = catalogo_diff.seleccionar_para_campania(nuevos, catalogo, cantidad=10)

    assert len(seleccion) == 10
    assert all(p in nuevos for p in seleccion)


def test_seleccion_completa_con_catalogo_si_faltan_nuevos():
    nuevos = _productos(3, "N")
    catalogo = nuevos + _productos(20, "C")

    seleccion = catalogo_diff.seleccionar_para_campania(nuevos, catalogo, cantidad=10)

    assert len(seleccion) == 10
    assert all(p in seleccion for p in nuevos)
    nombres_relleno = {p["nombre"] for p in seleccion} - {p["nombre"] for p in nuevos}
    assert len(nombres_relleno) == 7


def test_seleccion_sin_nuevos_completa_todo_de_relleno():
    catalogo = _productos(15, "C")

    seleccion = catalogo_diff.seleccionar_para_campania([], catalogo, cantidad=10)

    assert len(seleccion) == 10


def test_seleccion_no_alcanza_catalogo_devuelve_lo_disponible():
    nuevos = _productos(2, "N")
    catalogo = nuevos + _productos(3, "C")

    seleccion = catalogo_diff.seleccionar_para_campania(nuevos, catalogo, cantidad=10)

    assert len(seleccion) == 5
