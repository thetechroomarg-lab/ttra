from io import BytesIO

from PIL import Image
from fastapi.testclient import TestClient

from web import app as appmod


CAMPAIGN_ID = "2c1c82e4-73e5-46d2-a77e-921c21ef82d3"


def jpeg_valido():
    salida = BytesIO()
    Image.new("RGB", (1200, 600), "#1a1a1a").save(salida, format="JPEG")
    return salida.getvalue()


def test_upload_requiere_token(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    respuesta = TestClient(appmod.app).post(
        f"/admin/mailing/assets/{CAMPAIGN_ID}",
        files={"archivo": ("hero.jpg", jpeg_valido(), "image/jpeg")},
    )
    assert respuesta.status_code == 401


def test_upload_guarda_por_hash_y_se_puede_leer(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    client = TestClient(appmod.app)
    subida = client.post(
        f"/admin/mailing/assets/{CAMPAIGN_ID}",
        headers={"x-admin-token": "secreto"},
        files={"archivo": ("../../hero.jpg", jpeg_valido(), "image/jpeg")},
    )
    assert subida.status_code == 200
    assert ".." not in subida.json()["url"]
    lectura = client.get(subida.json()["url"])
    assert lectura.status_code == 200
    assert lectura.headers["content-type"] == "image/jpeg"


def test_upload_rechaza_bytes_que_no_son_imagen(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    respuesta = TestClient(appmod.app).post(
        f"/admin/mailing/assets/{CAMPAIGN_ID}",
        headers={"x-admin-token": "secreto"},
        files={"archivo": ("hero.jpg", b"no es una imagen", "image/jpeg")},
    )
    assert respuesta.status_code == 422


def test_upload_rechaza_mime_que_no_coincide_con_el_formato(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    respuesta = TestClient(appmod.app).post(
        f"/admin/mailing/assets/{CAMPAIGN_ID}",
        headers={"x-admin-token": "secreto"},
        files={"archivo": ("hero.png", jpeg_valido(), "image/png")},
    )
    assert respuesta.status_code == 422


def test_upload_rechaza_archivo_mayor_a_3_mib(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    monkeypatch.setattr(appmod, "ADMIN_TOKEN", "secreto")
    respuesta = TestClient(appmod.app).post(
        f"/admin/mailing/assets/{CAMPAIGN_ID}",
        headers={"x-admin-token": "secreto"},
        files={"archivo": ("hero.jpg", b"x" * (3 * 1024 * 1024 + 1), "image/jpeg")},
    )
    assert respuesta.status_code == 422


def test_url_publica_no_permite_listar_ni_archivos_desconocidos(monkeypatch, tmp_path):
    monkeypatch.setattr(appmod, "MAILING_ASSETS_PATH", tmp_path)
    client = TestClient(appmod.app)
    assert client.get(f"/mailing/assets/{CAMPAIGN_ID}/").status_code == 404
    assert client.get(f"/mailing/assets/{CAMPAIGN_ID}/" + "a" * 64 + ".jpg").status_code == 404
