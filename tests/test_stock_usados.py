import json

import web.app as appmod
from tests.test_app_admin_clientes import _cliente_logueado
from web import stock_usados
from web.productos import _escribir_json_atomico
import hashlib


def _catalogo(tmp_path):
    productos = [
        {"nombre": "iPhone 14 128GB (Usado)", "categoria": "Apple - iPhone Usado", "usd": 400, "colores": ["Black 86%"]},
        {"nombre": "iPhone 13 128GB", "categoria": "Apple - iPhone", "usd": 500, "colores": ["Negro"]},
    ]
    ph = _escribir_json_atomico(tmp_path / "productos.json", productos)
    ch = _escribir_json_atomico(tmp_path / "costos.json", {"iPhone 14 128GB (Usado)": 400, "iPhone 13 128GB": 450})
    _escribir_json_atomico(tmp_path / "proveedores.json", {"iPhone 14 128GB (Usado)": "stock propio", "iPhone 13 128GB": "az"})
    _escribir_json_atomico(tmp_path / "catalogo-manifest.json", {
        "version": 1, "generacion": "vieja", "cotizacion": 1600,
        "productos_sha256": ph, "costos_sha256": ch})
    return tmp_path / "productos.json"


def test_dar_de_baja_saca_el_usado_y_mantiene_el_manifest_consistente(tmp_path):
    ruta = _catalogo(tmp_path)
    detalle = [{"nombre": "iPhone 14 128GB (Usado)", "color": "Black 86%", "cantidad": 1}]
    assert stock_usados.dar_de_baja(detalle, ruta) == ["iPhone 14 128GB (Usado)"]
    assert [p["nombre"] for p in json.loads(ruta.read_text())] == ["iPhone 13 128GB"]
    assert "iPhone 14 128GB (Usado)" not in json.loads((tmp_path / "costos.json").read_text())
    assert "iPhone 14 128GB (Usado)" not in json.loads((tmp_path / "proveedores.json").read_text())
    m = json.loads((tmp_path / "catalogo-manifest.json").read_text())
    assert m["generacion"] != "vieja" and m["cotizacion"] == 1600
    assert m["productos_sha256"] == hashlib.sha256(ruta.read_bytes()).hexdigest()
    assert m["costos_sha256"] == hashlib.sha256((tmp_path / "costos.json").read_bytes()).hexdigest()


def test_un_producto_nuevo_no_se_toca(tmp_path):
    ruta = _catalogo(tmp_path)
    antes = ruta.read_bytes()
    assert stock_usados.dar_de_baja([{"nombre": "iPhone 13 128GB", "cantidad": 1}], ruta) == []
    assert ruta.read_bytes() == antes


def test_enviar_recibo_da_de_baja_el_usado_solo_en_el_primer_envio(monkeypatch, tmp_path):
    ruta = _catalogo(tmp_path)
    monkeypatch.setattr(appmod, "PRODUCTOS_PATH", ruta)
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "pedido-usado", "cliente_id": cliente["id"], "productos": ["iPhone 14 128GB (Usado)"],
        "fecha_entrega": "2026-08-24",
        "detalle": [{"nombre": "iPhone 14 128GB (Usado)", "color": "Black 86%", "cantidad": 1,
                     "usd_unitario": 400, "usd_subtotal": 400}],
        "total_usd": 400, "descuento_usd": 0,
    }).execute()
    monkeypatch.setattr(appmod, "enviar_email", lambda *a: None)
    assert c.post("/admin/pedidos/pedido-usado/recibo").status_code == 200
    assert [p["nombre"] for p in json.loads(ruta.read_text())] == ["iPhone 13 128GB"]
