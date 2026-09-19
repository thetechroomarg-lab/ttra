from web.mailing import estado


def test_snapshot_no_existe_devuelve_none(tmp_path):
    assert estado.leer_snapshot(tmp_path) is None


def test_guardar_y_leer_snapshot(tmp_path):
    productos = [{"nombre": "IPHONE 11 128GB"}]
    estado.guardar_snapshot(tmp_path, productos)
    assert estado.leer_snapshot(tmp_path) == productos


def test_nota_pendiente_ciclo_completo(tmp_path):
    assert estado.leer_nota_pendiente(tmp_path) is None

    estado.guardar_nota_pendiente(tmp_path, "20% off en fundas")
    assert estado.leer_nota_pendiente(tmp_path) == "20% off en fundas"

    estado.limpiar_nota_pendiente(tmp_path)
    assert estado.leer_nota_pendiente(tmp_path) is None


def test_borrador_ciclo_completo(tmp_path):
    assert estado.leer_borrador(tmp_path) is None

    estado.guardar_borrador(tmp_path, {"productos": [], "usado": False})
    assert estado.leer_borrador(tmp_path)["usado"] is False

    estado.marcar_borrador_usado(tmp_path)
    assert estado.leer_borrador(tmp_path)["usado"] is True


def test_registrar_envio_agrega_lineas(tmp_path):
    estado.registrar_envio(tmp_path, "linea 1")
    estado.registrar_envio(tmp_path, "linea 2")
    contenido = (tmp_path / "enviados.log").read_text(encoding="utf-8")
    assert contenido == "linea 1\nlinea 2\n"
