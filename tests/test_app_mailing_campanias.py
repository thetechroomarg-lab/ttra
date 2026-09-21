import json
from io import BytesIO
from unittest.mock import Mock

from PIL import Image
from fastapi.testclient import TestClient

from tests.fakes_supabase import FakeSupabaseClient
from web import app as appmod
from web.mailing import campanias


CAMPAIGN_ID = "2c1c82e4-73e5-46d2-a77e-921c21ef82d3"
PRODUCTO = {
    "nombre": "IPHONE 16 128GB", "usd": 800, "pesos": 1252000,
    "transferencia": 1214440, "colores": ["Black"],
}


def escribir_catalogo(tmp_path):
    path = tmp_path / "productos.json"
    path.write_text(json.dumps([PRODUCTO]), encoding="utf-8")
    return path


def jpeg_valido():
    salida = BytesIO()
    Image.new("RGB", (1200, 600), "#1a1a1a").save(salida, format="JPEG")
    return salida.getvalue()


def preparar_cliente(monkeypatch, tmp_path):
    fake = FakeSupabaseClient()
    monkeypatch.setenv("PUBLIC_APP_URL", "https://thetechroomarg.com")
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", escribir_catalogo(tmp_path))
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path / "assets")
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "enviar_email", Mock())
    return TestClient(appmod.app), fake


def subir_asset(client):
    respuesta = client.post(
        f"/admin/mailing/assets/{CAMPAIGN_ID}",
        headers={"x-admin-token": "secreto"},
        files={"archivo": ("hero.jpg", jpeg_valido(), "image/jpeg")},
    )
    assert respuesta.status_code == 200
    return respuesta.json()


def payload_campania(asset, productos=None):
    return {
        "campaign_id": CAMPAIGN_ID,
        "brief": "premium minimalista",
        "asunto": "Semana Apple",
        "preheader": "iPhone seleccionado",
        "nota": "",
        "productos": productos or [PRODUCTO["nombre"]],
        "hero": {
            "url": asset["url"], "sha256": asset["sha256"],
            "alt": "iPhone en estudio", "width": asset["width"], "height": asset["height"],
        },
    }


def test_preparar_no_envia_y_congela_productos(monkeypatch, tmp_path):
    client, _fake = preparar_cliente(monkeypatch, tmp_path)
    asset = subir_asset(client)
    respuesta = client.post(
        "/admin/mailing/campanias",
        headers={"x-admin-token": "secreto"},
        json=payload_campania(asset),
    )
    assert respuesta.status_code == 201
    datos = respuesta.json()
    assert datos["estado"] == "previsualizado"
    assert datos["manifest"]["productos"][0]["usd"] == 800
    assert "U$D 800" in datos["manifest"]["html"]
    assert appmod.enviar_email.call_count == 0


def test_preparar_rechaza_producto_inexistente(monkeypatch, tmp_path):
    client, _fake = preparar_cliente(monkeypatch, tmp_path)
    asset = subir_asset(client)
    respuesta = client.post(
        "/admin/mailing/campanias",
        headers={"x-admin-token": "secreto"},
        json=payload_campania(asset, productos=["NO EXISTE"]),
    )
    assert respuesta.status_code == 422
    assert appmod.enviar_email.call_count == 0


def test_aprobar_no_envia_y_rechaza_asset_ausente(monkeypatch, tmp_path):
    client, fake = preparar_cliente(monkeypatch, tmp_path)
    manifiesto = {
        "asunto": "Semana Apple", "productos": [], "html": "<html></html>",
        "asset_sha256": "a" * 64,
        "asset_url": f"https://thetechroomarg.com/mailing/assets/{CAMPAIGN_ID}/" + "a" * 64 + ".jpg",
    }
    version = campanias.crear_version(fake, manifiesto)
    respuesta = client.post(
        f"/admin/mailing/campanias/{version['id']}/aprobar",
        headers={"x-admin-token": "secreto"},
    )
    assert respuesta.status_code == 409
    assert appmod.enviar_email.call_count == 0


def test_aprobar_version_con_asset_correcto_no_envia(monkeypatch, tmp_path):
    client, _fake = preparar_cliente(monkeypatch, tmp_path)
    asset = subir_asset(client)
    creada = client.post(
        "/admin/mailing/campanias",
        headers={"x-admin-token": "secreto"},
        json=payload_campania(asset),
    ).json()
    aprobada = client.post(
        f"/admin/mailing/campanias/{creada['id']}/aprobar",
        headers={"x-admin-token": "secreto"},
    )
    assert aprobada.status_code == 200
    assert aprobada.json()["estado"] == "aprobado"
    repetida = client.post(
        f"/admin/mailing/campanias/{creada['id']}/aprobar",
        headers={"x-admin-token": "secreto"},
    )
    assert repetida.status_code == 409
    assert appmod.enviar_email.call_count == 0
