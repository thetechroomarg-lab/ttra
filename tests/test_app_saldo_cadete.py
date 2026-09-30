from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _clientes(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "ADMIN_CLIENTES_PASSWORD", "clave-admin")
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    admin = TestClient(appmod.app, base_url="https://testserver")
    admin.post("/admin/clientes/login", json={"password": "clave-admin"})
    cadete = TestClient(appmod.app, base_url="https://testserver")
    cadete.post("/admin/cadete/login", json={"password": "clave-cadete"})
    return fake, admin, cadete


def _movimientos(fake):
    return fake.table("movimientos_cadete").select("*").execute().data


def test_completar_tarea_de_alejo_suma_6000_una_sola_vez(monkeypatch):
    fake, admin, cadete = _clientes(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-30", "titulo": "Llevar pago a NexPhone", "asignado_a": "alejo",
    }).execute()

    assert cadete.post("/admin/tareas-entrega/t1/completar").status_code == 200
    cadete.post("/admin/tareas-entrega/t1/completar")

    movimientos = _movimientos(fake)
    assert len(movimientos) == 1
    assert movimientos[0]["monto_ars"] == 6000
    assert movimientos[0]["descripcion"] == "Llevar pago a NexPhone"


def test_tarea_no_asignada_a_alejo_no_suma(monkeypatch):
    fake, admin, _ = _clientes(monkeypatch)
    fake.table("tareas_entrega").insert({"id": "t2", "fecha_entrega": "2026-09-30", "titulo": "Mía"}).execute()

    admin.post("/admin/tareas-entrega/t2/completar")

    assert _movimientos(fake) == []


def test_monto_especifico_de_la_tarea_reemplaza_el_fijo(monkeypatch):
    fake, admin, cadete = _clientes(monkeypatch)
    r = admin.post("/admin/tareas-entrega", json={
        "fecha_entrega": "2026-09-30", "titulo": "Viaje largo", "enviar_a_alejo": True, "monto_cadete": 9000,
    })
    tarea_id = r.json()["tarea"]["id"]

    cadete.post(f"/admin/tareas-entrega/{tarea_id}/completar")

    assert _movimientos(fake)[0]["monto_ars"] == 9000


def test_tarea_sin_monto_no_manda_la_columna(monkeypatch):
    fake, admin, _ = _clientes(monkeypatch)
    admin.post("/admin/tareas-entrega", json={"fecha_entrega": "2026-09-30", "titulo": "X"})
    assert "monto_cadete" not in fake.table("tareas_entrega").select("*").execute().data[0]


def test_saldo_del_cadete_lista_movimientos_y_total(monkeypatch):
    fake, _, cadete = _clientes(monkeypatch)
    fake.table("movimientos_cadete").insert({"id": "m1", "tipo": "tarea", "referencia_id": "a", "descripcion": "Pago NexPhone",
                                             "monto_ars": 6000, "creado_en": "2026-09-30T15:00:00+00:00"}).execute()
    fake.table("movimientos_cadete").insert({"id": "m2", "tipo": "tarea", "referencia_id": "b", "descripcion": "Viejo",
                                             "monto_ars": 6000, "creado_en": "2026-09-20T15:00:00+00:00",
                                             "pagado_en": "2026-09-21T15:00:00+00:00"}).execute()

    html = cadete.get("/admin/cadete/saldo").text

    assert "Total a cobrar" in html and "$ 6.000" in html
    assert "Pago NexPhone" in html and "1 movimientos sin pagar · 2 en total" in html
    assert "Registrar pago" not in html


def test_panel_cadete_tiene_boton_saldo(monkeypatch):
    _, _, cadete = _clientes(monkeypatch)
    assert 'href="/admin/cadete/saldo">Saldo</a>' in cadete.get("/admin/cadete").text


def test_panel_admin_muestra_resumen_y_registrar_pago_limpia_el_saldo(monkeypatch):
    fake, admin, cadete = _clientes(monkeypatch)
    for i in range(3):
        fake.table("movimientos_cadete").insert({"id": f"m{i}", "tipo": "tarea", "referencia_id": str(i),
                                                 "descripcion": "x", "monto_ars": 6000, "creado_en": f"2026-09-2{i}T10:00:00+00:00"}).execute()

    panel = admin.get("/admin/clientes").text
    assert "Movimientos de Alejo: <strong>3</strong> sin pagar" in panel
    assert "$ 18.000" in panel

    assert cadete.post("/admin/cadete/movimientos/pagar").status_code == 401
    assert admin.post("/admin/cadete/movimientos/pagar").json()["pagados"] == 3
    assert "Saldo a pagar: <strong>$ 0</strong>" in admin.get("/admin/clientes").text


def test_admin_suma_edita_y_borra_movimientos(monkeypatch):
    fake, admin, _ = _clientes(monkeypatch)
    mid = admin.post("/admin/cadete/movimientos", json={"descripcion": "Extra", "monto_ars": 3000}).json()["movimiento"]["id"]
    admin.put(f"/admin/cadete/movimientos/{mid}", json={"monto_ars": 4500})
    assert _movimientos(fake)[0]["monto_ars"] == 4500
    admin.delete(f"/admin/cadete/movimientos/{mid}")
    assert _movimientos(fake) == []


def test_si_falla_la_tabla_la_tarea_igual_se_completa(monkeypatch):
    fake, _, cadete = _clientes(monkeypatch)
    fake.table("tareas_entrega").insert({"id": "t9", "fecha_entrega": "2026-09-30", "titulo": "X", "asignado_a": "alejo"}).execute()
    original = fake.table

    def tabla(nombre):
        if nombre == "movimientos_cadete":
            raise RuntimeError("relation does not exist")
        return original(nombre)
    monkeypatch.setattr(fake, "table", tabla)

    assert cadete.post("/admin/tareas-entrega/t9/completar").status_code == 200
    assert "Total a cobrar" in cadete.get("/admin/cadete/saldo").text


def test_tarjetas_muestran_la_direccion_debajo_del_titulo(monkeypatch):
    fake, admin, cadete = _clientes(monkeypatch)
    hoy = appmod.entregas.ahora_argentina().date().isoformat()
    fake.table("tareas_entrega").insert({"id": "t1", "fecha_entrega": hoy, "titulo": "Llevar pago",
                                         "direccion": "Estrada 18, Córdoba", "asignado_a": "alejo", "orden": 1}).execute()

    for html in (cadete.get("/admin/cadete").text, admin.get("/admin/clientes").text):
        assert 'Llevar pago</strong><br><span class="direccion-entrega">Dirección: Estrada 18, Córdoba</span>' in html


def test_panel_cadete_muestra_cuanto_le_debo(monkeypatch):
    fake, _, cadete = _clientes(monkeypatch)
    for i in range(2):
        fake.table("tareas_entrega").insert({
            "id": f"d{i}", "fecha_entrega": "2026-09-30", "titulo": "Entrega", "asignado_a": "alejo",
        }).execute()
        cadete.post(f"/admin/tareas-entrega/d{i}/completar")
    html = cadete.get("/admin/cadete").text
    assert 'class="saldo-cadete-titulo"' in html
    assert "Te debo:" in html and "$ 12.000" in html


def test_solo_el_admin_edita_el_texto_de_una_tarea(monkeypatch):
    fake, admin, cadete = _clientes(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "e1", "fecha_entrega": "2026-09-30", "titulo": "Viejo", "nota": "nota vieja", "asignado_a": "alejo",
    }).execute()

    assert cadete.put("/admin/tareas-entrega/e1/texto", json={"titulo": "Hack"}).status_code == 401
    assert 'btn-editar-texto-tarea' not in cadete.get("/admin/cadete").text

    r = admin.put("/admin/tareas-entrega/e1/texto", json={"titulo": "  Nuevo  ", "nota": "otra"})
    assert r.status_code == 200
    tarea = fake.table("tareas_entrega").select("*").eq("id", "e1").execute().data[0]
    assert tarea["titulo"] == "Nuevo" and tarea["nota"] == "otra"
    assert admin.put("/admin/tareas-entrega/e1/texto", json={"titulo": "   "}).status_code == 400
    assert admin.put("/admin/tareas-entrega/nope/texto", json={"titulo": "x"}).status_code == 404
