from decimal import Decimal

import pytest
import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient
from tests.test_app_pedidos import _cliente_con_catalogo
from web import remeras


@pytest.fixture(autouse=True)
def stock_aislado(tmp_path, monkeypatch):
    monkeypatch.setenv("REMERAS_PATH", str(tmp_path / "remeras.json"))


def test_stock_inicial_es_75_l_y_15_xl():
    assert remeras.leer_stock() == {"S": 0, "M": 0, "L": 75, "XL": 15}


def test_descontar_y_fijar_stock():
    remeras.descontar(["L", "XL", "L"])
    assert remeras.leer_stock()["L"] == 73 and remeras.leer_stock()["XL"] == 14
    remeras.fijar_stock("XL", 40)
    assert remeras.leer_stock()["XL"] == 40


def test_ganancia_limpia_resta_descuento_y_entrega():
    detalle = [{"nombre": "A", "cantidad": 2, "usd_subtotal": 400, "proveedor": "x"}]
    assert remeras.ganancia_limpia(detalle, {"A": 100}, 10) == Decimal("175")


def test_sin_costo_no_hay_remera():
    detalle = [{"nombre": "A", "cantidad": 1, "usd_subtotal": 400, "proveedor": "x"}]
    assert not remeras.merece_remera(detalle, {}, 0)


def test_umbral_60_limpios():
    detalle = [{"nombre": "A", "cantidad": 1, "usd_subtotal": 175, "proveedor": "x"}]
    assert remeras.merece_remera(detalle, {"A": 100}, 0)
    detalle[0]["usd_subtotal"] = 174
    assert not remeras.merece_remera(detalle, {"A": 100}, 0)


def test_cargador_promo_y_envio_no_suman_ganancia():
    detalle = [
        {"nombre": "A", "cantidad": 1, "usd_subtotal": 170, "proveedor": "x"},
        {"nombre": "Cargador Apple 20W Original (premio promocional)", "cantidad": 1,
         "usd_subtotal": 30, "proveedor": "stock propio"},
        {"nombre": "Envío", "cantidad": 1, "usd_subtotal": 10, "proveedor": "envío"},
    ]
    assert remeras.ganancia_limpia(detalle, {"A": 100}) == Decimal("55")


def test_reservadas_cuentan_pedidos_sin_recibo_y_no_borrados():
    fake = FakeSupabaseClient()
    base = {"detalle": [remeras.item_regalo("L")]}
    fake.table("pedidos").insert({"id": "1", **base}).execute()
    fake.table("pedidos").insert({"id": "2", **base, "recibo_enviado_en": "2026-01-01"}).execute()
    fake.table("pedidos").insert({"id": "3", **base, "borrado_en": "2026-01-01"}).execute()
    assert remeras.reservadas(fake)["L"] == 1
    assert remeras.disponibles(fake)["L"] == 74


def test_oferta_marca_talles_sin_stock_como_no_disponibles():
    oferta = remeras.oferta(FakeSupabaseClient())
    assert {t["talle"]: t["disponible"] for t in oferta["talles"]} == {
        "S": False, "M": False, "L": True, "XL": True}


def test_oferta_none_sin_stock():
    for talle in ("L", "XL"):
        remeras.fijar_stock(talle, 0)
    assert remeras.oferta(FakeSupabaseClient()) is None


def _pedido(c, precio=180, cantidad=1):
    total = precio * cantidad
    return c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{"nombre": "Elegible", "color": None, "cantidad": cantidad,
                     "usd_unitario": precio, "usd_subtotal": total}],
        "total_usd": total,
    })


def _cliente(monkeypatch, precio=180, costo=100):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=precio, costo=costo)
    monkeypatch.setattr(appmod, "_cargar_costos", lambda: {"Elegible": costo})
    return c, fake


def test_pedido_que_deja_60_limpios_ofrece_la_remera(monkeypatch):
    c, fake = _cliente(monkeypatch)
    r = _pedido(c)
    assert r.status_code == 200
    remera = r.json()["remera"]
    assert remera["pedido_id"] == fake.table("pedidos").select("*").execute().data[0]["id"]
    assert {t["talle"]: t["disponible"] for t in remera["talles"]} == {
        "S": False, "M": False, "L": True, "XL": True}


def test_pedido_con_poca_ganancia_no_ofrece_remera(monkeypatch):
    c, fake = _cliente(monkeypatch, costo=150)
    r = _pedido(c)
    assert r.json() == {"ok": True}


def test_elegir_talle_suma_la_remera_al_detalle_sin_cambiar_el_total(monkeypatch):
    c, fake = _cliente(monkeypatch)
    pedido_id = _pedido(c).json()["remera"]["pedido_id"]
    r = c.post(f"/api/pedidos/{pedido_id}/remera", json={"talle": "XL"})
    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert remeras.talles_del_detalle(pedido["detalle"]) == ["XL"]
    assert pedido["total_usd"] == 180
    assert c.post(f"/api/pedidos/{pedido_id}/remera", json={"talle": "L"}).status_code == 409


def test_no_se_puede_elegir_talle_sin_stock(monkeypatch):
    c, fake = _cliente(monkeypatch)
    pedido_id = _pedido(c).json()["remera"]["pedido_id"]
    for talle in ("S", "M"):
        r = c.post(f"/api/pedidos/{pedido_id}/remera", json={"talle": talle})
        assert r.status_code == 409
    assert c.post(f"/api/pedidos/{pedido_id}/remera", json={"talle": "XXL"}).status_code == 400


def test_no_se_puede_reclamar_remera_sin_ganancia_suficiente(monkeypatch):
    c, fake = _cliente(monkeypatch, costo=150)
    _pedido(c)
    pedido_id = fake.table("pedidos").select("*").execute().data[0]["id"]
    assert c.post(f"/api/pedidos/{pedido_id}/remera", json={"talle": "L"}).status_code == 409


def test_remera_pedida_queda_reservada_hasta_el_recibo(monkeypatch):
    c, fake = _cliente(monkeypatch)
    remeras.fijar_stock("XL", 1)
    pedido_id = _pedido(c).json()["remera"]["pedido_id"]
    assert c.post(f"/api/pedidos/{pedido_id}/remera", json={"talle": "XL"}).status_code == 200
    assert remeras.leer_stock()["XL"] == 1
    assert remeras.disponibles(fake)["XL"] == 0


def test_recibo_enviado_descuenta_la_remera_del_stock(monkeypatch):
    from tests.test_app_admin_clientes import _cliente_logueado
    c = _cliente_logueado(monkeypatch)
    fake = appmod.get_client()
    cliente = fake.table("clientes").select("*").eq("email", "juan@x.com").execute().data[0]
    fake.table("pedidos").insert({
        "id": "pedido-remera", "cliente_id": cliente["id"], "productos": ["iPhone 13"],
        "fecha_entrega": "2026-08-24",
        "detalle": [
            {"nombre": "iPhone 13", "color": "Negro", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500},
            remeras.item_regalo("L"),
        ],
        "total_usd": 500, "descuento_usd": 0,
    }).execute()
    monkeypatch.setattr(appmod, "enviar_email", lambda *args: None)
    assert c.post("/admin/pedidos/pedido-remera/recibo").status_code == 200
    assert remeras.leer_stock()["L"] == 74
    c.post("/admin/pedidos/pedido-remera/recibo")  # reenvío: no vuelve a restar
    assert remeras.leer_stock()["L"] == 74
