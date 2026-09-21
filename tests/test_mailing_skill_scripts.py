from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import sys

import pytest
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "mailing" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import aprobar
import enviar
import preparar


VERSION_ID = "2c1c82e4-73e5-46d2-a77e-921c21ef82d3"


@dataclass
class Llamada:
    path: str


class FakeApi:
    def __init__(self):
        self.calls = []

    def post_file(self, path, file_path):
        self.calls.append(Llamada(path))
        return {
            "url": f"https://thetechroomarg.com/mailing/assets/{VERSION_ID}/abc.jpg",
            "sha256": "a" * 64, "width": 1200, "height": 600,
        }

    def post(self, path, **kwargs):
        self.calls.append(Llamada(path))
        if path == "/admin/mailing/campanias":
            return {"id": VERSION_ID, "campaign_id": VERSION_ID, "estado": "previsualizado"}
        return {"id": VERSION_ID, "estado": "aprobado"}

    def get(self, path):
        self.calls.append(Llamada(path))
        return {"campaign_id": VERSION_ID, "estado": "previsualizado"}


def imagen_jpeg(tmp_path):
    salida = BytesIO()
    Image.new("RGB", (1200, 600), "#1a1a1a").save(salida, format="JPEG")
    path = tmp_path / "hero.jpg"
    path.write_bytes(salida.getvalue())
    return path


def test_preparar_sube_asset_antes_de_crear_campania(tmp_path):
    api = FakeApi()
    resultado = preparar.ejecutar(
        api=api, imagen=imagen_jpeg(tmp_path), productos=["IPHONE 16 128GB"],
        brief="premium", asunto="Semana Apple", preheader="Novedades", alt="iPhone en estudio",
    )
    assert [llamada.path for llamada in api.calls] == [
        f"/admin/mailing/assets/{resultado['campaign_id']}", "/admin/mailing/campanias"
    ]


def test_regenerar_reutiliza_campaign_id_del_padre(tmp_path):
    api = FakeApi()
    resultado = preparar.ejecutar(
        api=api, imagen=imagen_jpeg(tmp_path), productos=["IPHONE 16 128GB"],
        brief="más contraste", asunto="Semana Apple", preheader="Novedades",
        alt="iPhone en estudio", parent_id=VERSION_ID,
    )
    assert resultado["campaign_id"] == VERSION_ID
    assert api.calls[0].path == f"/admin/mailing/campanias/{VERSION_ID}"
    assert api.calls[1].path == f"/admin/mailing/assets/{VERSION_ID}"


def test_aprobar_no_invoca_endpoint_de_envio():
    api = FakeApi()
    aprobar.ejecutar(api, VERSION_ID)
    assert [llamada.path for llamada in api.calls] == [
        f"/admin/mailing/campanias/{VERSION_ID}/aprobar"
    ]


def test_enviar_rechaza_confirmacion_inexacta():
    api = FakeApi()
    with pytest.raises(ValueError):
        enviar.ejecutar(api, VERSION_ID, "dale")
    assert api.calls == []


def test_enviar_solo_llama_con_confirmacion_exacta():
    api = FakeApi()
    enviar.ejecutar(api, VERSION_ID, f"ENVIAR {VERSION_ID}")
    assert [llamada.path for llamada in api.calls] == [
        f"/admin/mailing/campanias/{VERSION_ID}/enviar"
    ]
