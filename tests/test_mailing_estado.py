from tests.fakes_supabase import FakeSupabaseClient
from web.mailing import estado


def test_snapshot_no_existe_devuelve_none():
    fake = FakeSupabaseClient()
    assert estado.leer_snapshot(fake) is None


def test_guardar_y_leer_snapshot():
    fake = FakeSupabaseClient()
    productos = [{"nombre": "IPHONE 11 128GB"}]

    estado.guardar_snapshot(fake, productos)

    assert estado.leer_snapshot(fake) == productos


def test_guardar_snapshot_dos_veces_actualiza_en_vez_de_duplicar():
    fake = FakeSupabaseClient()

    estado.guardar_snapshot(fake, [{"nombre": "A"}])
    estado.guardar_snapshot(fake, [{"nombre": "B"}])

    assert estado.leer_snapshot(fake) == [{"nombre": "B"}]
    assert len(fake.table("mailing_estado")._filas) == 1


def test_nota_pendiente_ciclo_completo():
    fake = FakeSupabaseClient()
    assert estado.leer_nota_pendiente(fake) is None

    estado.guardar_nota_pendiente(fake, "20% off en fundas")
    assert estado.leer_nota_pendiente(fake) == "20% off en fundas"

    estado.limpiar_nota_pendiente(fake)
    assert estado.leer_nota_pendiente(fake) is None


def test_borrador_ciclo_completo():
    fake = FakeSupabaseClient()
    assert estado.leer_borrador(fake) is None

    estado.guardar_borrador(fake, {"productos": [], "usado": False})
    assert estado.leer_borrador(fake)["usado"] is False

    estado.marcar_borrador_usado(fake)
    assert estado.leer_borrador(fake)["usado"] is True


def test_registrar_envio_agrega_una_fila_por_envio():
    fake = FakeSupabaseClient()

    estado.registrar_envio(fake, productos=10, ok=34, fallidos=2)
    estado.registrar_envio(fake, productos=10, ok=36, fallidos=0)

    filas = fake.table("mailing_envios").select("*").execute().data
    assert len(filas) == 2
    assert filas[0]["ok"] == 34
    assert filas[1]["ok"] == 36
