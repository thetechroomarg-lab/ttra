from io import BytesIO
from uuid import UUID

import pytest
from PIL import Image

from tests.fakes_supabase import FakeSupabaseClient
from web.mailing import assets, campanias, envio, servicio


CAMPAIGN_ID = "2c1c82e4-73e5-46d2-a77e-921c21ef82d3"
CLIENTE_A = "11111111-1111-1111-1111-111111111111"
CLIENTE_B = "22222222-2222-2222-2222-222222222222"
PRODUCTO = {
    "nombre": "IPHONE 16 128GB", "usd": 800, "pesos": 1252000,
    "transferencia": 1214440,
}


def escenario_aprobado(tmp_path):
    fake = FakeSupabaseClient()
    salida = BytesIO()
    Image.new("RGB", (1200, 600), "#1a1a1a").save(salida, format="JPEG")
    asset = assets.guardar_asset(
        tmp_path, UUID(CAMPAIGN_ID), salida.getvalue(), "image/jpeg"
    )
    html = '<html><a href="https://thetechroomarg.com/mailing/baja/__CLIENTE_ID__">Baja</a></html>'
    manifiesto = {
        "campaign_id": CAMPAIGN_ID,
        "asunto": "Semana Apple",
        "productos": [PRODUCTO],
        "catalog_sha256": servicio.huella_comercial([PRODUCTO]),
        "html": html,
        "hero": {"url": f"https://thetechroomarg.com/mailing/assets/{CAMPAIGN_ID}/{asset.filename}",
                 "sha256": asset.sha256},
        "asset_url": f"https://thetechroomarg.com/mailing/assets/{CAMPAIGN_ID}/{asset.filename}",
        "asset_sha256": asset.sha256,
    }
    version = campanias.crear_version(fake, manifiesto)
    aprobada = campanias.transicionar(fake, version["id"], "previsualizado", "aprobado")
    return fake, aprobada, [PRODUCTO], tmp_path


def test_precio_cambiado_invalida_sin_enviar(tmp_path):
    fake, aprobada, _catalogo, assets_root = escenario_aprobado(tmp_path)
    llamados = []
    catalogo = [{**PRODUCTO, "usd": 801}]
    with pytest.raises(envio.CampaniaDesactualizada):
        envio.enviar_version(fake, aprobada["id"], catalogo, lambda *args: llamados.append(args),
                             assets_root=assets_root)
    assert llamados == []
    assert campanias.obtener_version(fake, aprobada["id"])["estado"] == "invalidado"


def test_asset_ausente_detiene_envio(tmp_path):
    fake, aprobada, catalogo, _assets_root = escenario_aprobado(tmp_path)
    root_vacio = tmp_path / "vacio"
    root_vacio.mkdir()
    with pytest.raises(envio.AssetAusente):
        envio.enviar_version(fake, aprobada["id"], catalogo, lambda *_: None,
                             assets_root=root_vacio)
    assert campanias.obtener_version(fake, aprobada["id"])["estado"] == "aprobado"


def test_fallo_parcial_se_registra_y_no_reenvia(tmp_path):
    fake, aprobada, catalogo, assets_root = escenario_aprobado(tmp_path)
    fake.table("clientes").insert({"id": CLIENTE_A, "email": "a@x.com"}).execute()
    fake.table("clientes").insert({"id": CLIENTE_B, "email": "b@x.com"}).execute()
    fake.table("clientes").insert({
        "id": "33333333-3333-3333-3333-333333333333", "email": "c@x.com", "no_mailing": True,
    }).execute()

    def sender(destinatario, asunto, html):
        if destinatario == "b@x.com":
            raise RuntimeError("resend caído")

    resultado = envio.enviar_version(fake, aprobada["id"], catalogo, sender,
                                     assets_root=assets_root)
    assert (resultado.total, resultado.ok, resultado.fallidos) == (2, 1, 1)
    filas = fake.table("mailing_envios_detalle").select("*").execute().data
    assert {(fila["cliente_id"], fila["estado"]) for fila in filas} == {
        (CLIENTE_A, "ok"), (CLIENTE_B, "fallido"),
    }
    assert campanias.obtener_version(fake, aprobada["id"])["estado"] == "enviado"
    with pytest.raises(campanias.InvalidTransition):
        envio.enviar_version(fake, aprobada["id"], catalogo, sender,
                             assets_root=assets_root)
