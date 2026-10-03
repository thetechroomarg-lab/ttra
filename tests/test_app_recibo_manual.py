from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _login_cadete(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "CADETE_PASSWORD", "clave-cadete")
    cliente = TestClient(appmod.app, base_url="https://testserver")
    cliente.post("/admin/cadete/login", json={"password": "clave-cadete"})
    return fake, cliente


def test_recibo_manual_envia_mail_y_persiste(monkeypatch):
    fake, cliente = _login_cadete(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-20", "titulo": "Entrega en Nva Cordoba",
        "orden": 1, "asignado_a": "alejo",
    }).execute()

    correos_enviados = []
    monkeypatch.setattr(
        appmod, "enviar_email",
        lambda destinatario, asunto, html, adjuntos=None: correos_enviados.append((destinatario, asunto)),
    )

    respuesta = cliente.post(
        "/admin/tareas-entrega/t1/recibo-manual",
        data={
            "nombre": "Ana Lopez",
            "email": "ana@example.com",
            "items": '[{"nombre": "iPhone 11 128GB", "precio_usd": 425}]',
        },
    )
    assert respuesta.status_code == 200, respuesta.text
    cuerpo = respuesta.json()
    assert cuerpo["ok"] is True
    assert cuerpo["recibo_id"]

    assert correos_enviados == [("ana@example.com", f"Recibo {cuerpo['recibo_id']} — The Tech Room Arg")]
    registro = fake.table("recibos_manuales").select("*").eq("tarea_id", "t1").execute().data[0]
    assert registro["nombre_cliente"] == "Ana Lopez"
    assert registro["total_usd"] == 425.0
    assert registro["enviado_en"] is not None

    tarea = fake.table("tareas_entrega").select("*").eq("id", "t1").execute().data[0]
    assert tarea["completada_en"] is not None


def test_recibo_manual_rechaza_items_vacios(monkeypatch):
    fake, cliente = _login_cadete(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-20", "titulo": "Entrega", "orden": 1, "asignado_a": "alejo",
    }).execute()

    respuesta = cliente.post(
        "/admin/tareas-entrega/t1/recibo-manual",
        data={"nombre": "Ana", "email": "ana@example.com", "items": "[]"},
    )
    assert respuesta.status_code == 400


def test_recibo_manual_bloquea_nota_ajena(monkeypatch):
    fake, cliente = _login_cadete(monkeypatch)
    fake.table("tareas_entrega").insert({
        "id": "t1", "fecha_entrega": "2026-09-20", "titulo": "Entrega", "orden": 1, "asignado_a": None,
    }).execute()

    respuesta = cliente.post(
        "/admin/tareas-entrega/t1/recibo-manual",
        data={"nombre": "Ana", "email": "ana@example.com", "items": '[{"nombre":"X","precio_usd":10}]'},
    )
    assert respuesta.status_code == 403
