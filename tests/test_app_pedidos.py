from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def _cliente_con_catalogo(monkeypatch, *, precio_publico=180, costo=100, mayorista=False):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [{"nombre": "Elegible", "categoria": "Apple - iPhone", "usd": precio_publico}],
    )
    monkeypatch.setattr(appmod, "_cargar_costos", lambda: {"Elegible": costo})
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
        "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",
    })
    if mayorista:
        cliente = fake.table("clientes").select("*").execute().data[0]
        fake.table("clientes").update({"tipo_cliente": "mayorista"}).eq(
            "id", cliente["id"]
        ).execute()
    return c, fake


def _cliente_mayorista_con_catalogo(monkeypatch, *, precio_publico=180, costo=100):
    return _cliente_con_catalogo(
        monkeypatch,
        precio_publico=precio_publico,
        costo=costo,
        mayorista=True,
    )


def test_pedido_sin_sesion_devuelve_401(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/api/pedidos", json={"productos": ["iPhone 13"], "fecha_entrega": "2026-08-24"})
    assert r.status_code == 401


def test_pedido_con_sesion_guarda_fecha_entrega_valida(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    r = c.post("/api/pedidos", json={"productos": ["iPhone 13", "AirPods"], "fecha_entrega": "2026-08-24"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["fecha_entrega"] == "2026-08-24"


def test_pedido_guarda_el_detalle_y_total_usd_del_checkout(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [{
        "nombre": "iPhone 13", "usd": 500, "colores": ["Negro"],
    }])
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})

    r = c.post("/api/pedidos", json={
        "productos": ["iPhone 13 (Negro)"],
        "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{
            "nombre": "iPhone 13", "color": "Negro", "cantidad": 2,
            "usd_unitario": 500, "usd_subtotal": 1000,
        }],
        "total_usd": 990,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["detalle"] == [{
        "nombre": "iPhone 13", "color": "Negro", "cantidad": 2,
        "usd_unitario": 500, "usd_subtotal": 1000,
        "proveedor": "Proveedor no identificado",
    }]
    assert pedido["total_usd"] == 990
    assert pedido["descuento_usd"] == 10
    assert pedido["direccion_entrega"] == "Av. Colón 123, Córdoba"


def test_pedido_guarda_el_proveedor_solo_resuelto_en_el_servidor(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod, "_cargar_productos", lambda: [{"nombre": "iPhone 13", "usd": 500}]
    )
    monkeypatch.setattr(appmod, "_cargar_proveedores", lambda: {"iPhone 13": "az"})
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})

    r = c.post("/api/pedidos", json={
        "productos": ["iPhone 13"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{"nombre": "iPhone 13", "cantidad": 1, "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
    })

    assert r.status_code == 200
    detalle = fake.table("pedidos").select("*").execute().data[0]["detalle"]
    assert detalle[0]["proveedor"] == "az"


def test_pedido_normaliza_el_nombre_antes_de_resolver_proveedor(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [{"nombre": "Xiaomi Redmi Note 14 8GB 256GB slim", "usd": 300}],
    )
    monkeypatch.setattr(appmod, "_cargar_proveedores", lambda: {"Xiaomi Redmi Note 14 8GB 256GB": "az"})
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})

    r = c.post("/api/pedidos", json={
        "productos": ["Xiaomi Redmi Note 14 8GB 256GB slim"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{"nombre": "Xiaomi Redmi Note 14 8GB 256GB slim", "cantidad": 1, "usd_unitario": 300, "usd_subtotal": 300}],
        "total_usd": 300,
    })

    assert r.status_code == 200
    detalle = fake.table("pedidos").select("*").execute().data[0]["detalle"]
    assert detalle[0]["proveedor"] == "az"


def test_pedido_del_mismo_cliente_y_entrega_se_consolida(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod,
        "_cargar_productos",
        lambda: [{"nombre": "iPhone 13", "usd": 500, "colores": ["Negro"]}],
    )
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 24, 10, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    pedido = {
        "productos": ["iPhone 13 (Negro)"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123, Córdoba",
        "detalle": [{"nombre": "iPhone 13", "color": "Negro", "cantidad": 1,
                     "usd_unitario": 500, "usd_subtotal": 500}],
        "total_usd": 500,
    }

    assert c.post("/api/pedidos", json=pedido).status_code == 200
    pedido["detalle"][0]["cantidad"] = 2
    pedido["detalle"][0]["usd_subtotal"] = 1000
    pedido["total_usd"] = 990
    assert c.post("/api/pedidos", json=pedido).status_code == 200

    filas = fake.table("pedidos").select("*").execute().data
    assert len(filas) == 1
    assert filas[0]["detalle"][0]["cantidad"] == 3
    assert filas[0]["detalle"][0]["usd_subtotal"] == 1500
    assert filas[0]["total_usd"] == 1490
    assert filas[0]["descuento_usd"] == 10


def test_pedido_rechaza_fecha_fuera_de_las_opciones(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(
        appmod.entregas,
        "ahora_argentina",
        lambda: datetime(2026, 8, 28, 17, 0, tzinfo=ZoneInfo("America/Argentina/Cordoba")),
    )
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234", "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})

    r = c.post("/api/pedidos", json={"productos": ["iPhone 13"], "fecha_entrega": "2026-08-29"})

    assert r.status_code == 400


def test_pedido_mayorista_recalcula_y_guarda_auditoria(monkeypatch):
    c, fake = _cliente_mayorista_con_catalogo(monkeypatch, precio_publico=180, costo=100)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 2,
            "usd_unitario": 130, "usd_subtotal": 260,
        }],
        "total_usd": 260, "descuento_usd": 0,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["modo_precio"] == "mayorista"
    assert pedido["descuento_mayorista_usd"] == 100
    assert pedido["total_usd"] == 260


def test_pedido_rechaza_precio_manipulado(monkeypatch):
    c, _fake = _cliente_mayorista_con_catalogo(monkeypatch, precio_publico=180, costo=100)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 1, "usd_subtotal": 1,
        }],
        "total_usd": 1,
    })

    assert r.status_code == 409
    assert "precios" in r.json()["error"].lower()


def test_pedido_minorista_guarda_precios_autorizados(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 2,
            "usd_unitario": 180, "usd_subtotal": 360,
        }],
        "total_usd": 350,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["modo_precio"] == "minorista"
    assert pedido["descuento_mayorista_usd"] == 0
    assert pedido["total_usd"] == 350
    assert pedido["descuento_usd"] == 10


def test_pedido_rechaza_subtotal_o_total_manipulado(monkeypatch):
    c, _fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    base = {
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 2,
            "usd_unitario": 180, "usd_subtotal": 1,
        }],
        "total_usd": 360,
    }

    assert c.post("/api/pedidos", json=base).status_code == 409
    base["detalle"][0]["usd_subtotal"] = 360
    base["total_usd"] = 1
    assert c.post("/api/pedidos", json=base).status_code == 409


def test_pedido_mayorista_sin_detalle_se_rechaza(monkeypatch):
    c, fake = _cliente_mayorista_con_catalogo(monkeypatch)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
    })

    assert r.status_code == 409
    assert fake.table("pedidos").select("*").execute().data == []


def test_pedido_no_acepta_descuento_usd_elegido_por_el_cliente(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 0, "descuento_usd": 180,
    })

    assert r.status_code == 409
    assert fake.table("pedidos").select("*").execute().data == []


def test_pedido_minorista_deriva_descuento_por_cantidad(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)

    r = c.post("/api/pedidos", json={
        "productos": ["Manipulado"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 2,
            "usd_unitario": 180, "usd_subtotal": 360,
        }],
        "total_usd": 350, "descuento_usd": 0,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["descuento_usd"] == 10
    assert pedido["total_usd"] == 350
    assert pedido["productos"] == ["Elegible"]


def test_pedido_minorista_deriva_banda_de_seis_unidades(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 6,
            "usd_unitario": 180, "usd_subtotal": 1080,
        }],
        "total_usd": 1035,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["descuento_usd"] == 45
    assert pedido["total_usd"] == 1035


def test_pedido_aplica_y_consume_codigo_mailing_despues_de_guardar(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    cliente_id = fake.table("clientes").select("*").execute().data[0]["id"]
    fake.table("codigos_descuento").insert({
        "cliente_id": cliente_id,
        "code": "TTRA-TEST1234",
        "productos": ["Elegible"],
        "descuento_usd": 5,
        "activo": True,
    }).execute()

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 175,
        "codigo_descuento": "ttra-test1234",
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["descuento_usd"] == 5
    codigo = fake.table("codigos_descuento").select("*").execute().data[0]
    assert codigo["usado_en"]
    assert fake.rpc_calls[-1][0] == "guardar_pedido_con_descuento_mailing"


def test_pedido_fallido_no_consume_codigo_mailing(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    cliente_id = fake.table("clientes").select("*").execute().data[0]["id"]
    fake.table("codigos_descuento").insert({
        "cliente_id": cliente_id,
        "code": "TTRA-TEST1234",
        "productos": ["Elegible"],
        "descuento_usd": 5,
        "activo": True,
    }).execute()

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 1,
        "codigo_descuento": "TTRA-TEST1234",
    })

    assert r.status_code == 409
    codigo = fake.table("codigos_descuento").select("*").execute().data[0]
    assert not codigo.get("usado_en")


def test_pedido_atomico_no_persiste_si_rpc_falla_antes_de_guardar(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    cliente_id = fake.table("clientes").select("*").execute().data[0]["id"]
    fake.table("codigos_descuento").insert({
        "cliente_id": cliente_id,
        "code": "TTRA-TEST1234",
        "productos": ["Elegible"],
        "descuento_usd": 5,
        "activo": True,
    }).execute()

    fake.atomic_order_failure_stage = "before_order"
    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 175,
        "codigo_descuento": "TTRA-TEST1234",
    })

    assert r.status_code == 503
    assert fake.table("pedidos").select("*").execute().data == []
    codigo = fake.table("codigos_descuento").select("*").execute().data[0]
    assert not codigo.get("usado_en")


@pytest.mark.parametrize("etapa_fallo", ["after_order", "after_consume"])
def test_pedido_atomico_revierte_transaccion_si_falla_consumo(
    monkeypatch, etapa_fallo
):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    cliente_id = fake.table("clientes").select("*").execute().data[0]["id"]
    fake.table("codigos_descuento").insert({
        "cliente_id": cliente_id,
        "code": "TTRA-TEST1234",
        "productos": ["Elegible"],
        "descuento_usd": 5,
        "activo": True,
    }).execute()
    fake.atomic_order_failure_stage = etapa_fallo

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 175,
        "codigo_descuento": "TTRA-TEST1234",
    })

    assert r.status_code == 503
    assert fake.table("pedidos").select("*").execute().data == []
    codigo = fake.table("codigos_descuento").select("*").execute().data[0]
    assert not codigo.get("usado_en")


def test_pedido_atomico_verifica_resultado_rpc(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    cliente_id = fake.table("clientes").select("*").execute().data[0]["id"]
    fake.table("codigos_descuento").insert({
        "cliente_id": cliente_id,
        "code": "TTRA-TEST1234",
        "productos": ["Elegible"],
        "descuento_usd": 5,
        "activo": True,
    }).execute()

    class ResultadoInvalido:
        data = None

        def execute(self):
            return self

    monkeypatch.setattr(fake, "rpc", lambda *_args, **_kwargs: ResultadoInvalido())
    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 175,
        "codigo_descuento": "TTRA-TEST1234",
    })

    assert r.status_code == 503
    assert fake.table("pedidos").select("*").execute().data == []
    codigo = fake.table("codigos_descuento").select("*").execute().data[0]
    assert not codigo.get("usado_en")


def test_dos_intentos_con_lectura_obsoleta_consumen_codigo_una_sola_vez(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    cliente_id = fake.table("clientes").select("*").execute().data[0]["id"]
    codigo_original = {
        "cliente_id": cliente_id,
        "code": "TTRA-TEST1234",
        "productos": ["Elegible"],
        "descuento_usd": 5,
        "activo": True,
    }
    fake.table("codigos_descuento").insert(codigo_original).execute()
    monkeypatch.setattr(
        appmod,
        "_descuento_codigo_row",
        lambda *_args, **_kwargs: dict(codigo_original),
    )
    payload = {
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 175,
        "codigo_descuento": "TTRA-TEST1234",
    }

    primero = c.post("/api/pedidos", json=payload)
    segundo = c.post("/api/pedidos", json=payload)

    assert primero.status_code == 200
    assert segundo.status_code == 409
    pedidos_guardados = fake.table("pedidos").select("*").execute().data
    assert len(pedidos_guardados) == 1
    assert pedidos_guardados[0]["total_usd"] == 175
    assert pedidos_guardados[0]["detalle"][0]["cantidad"] == 1


def test_pedido_rechaza_color_no_disponible(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [{
        "nombre": "Elegible", "usd": 180, "colores": ["Negro", "Azul"],
    }])

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible (Rojo)"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "color": "Rojo", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 180,
    })

    assert r.status_code == 409
    assert fake.table("pedidos").select("*").execute().data == []


def test_pedido_deriva_productos_del_detalle_y_color_validado(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [{
        "nombre": "Elegible", "usd": 180, "colores": ["Negro", "Azul"],
    }])

    r = c.post("/api/pedidos", json={
        "productos": ["Producto inyectado"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "color": "Negro", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
            "proveedor": "atacante",
        }],
        "total_usd": 180,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["productos"] == ["Elegible (Negro)"]
    assert pedido["detalle"][0]["color"] == "Negro"
    assert pedido["detalle"][0]["proveedor"] == "Proveedor no identificado"


def test_pedido_rechaza_catalogo_con_nombres_duplicados(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [
        {"nombre": "Elegible", "usd": 180},
        {"nombre": "Elegible", "usd": 180},
    ])

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 180,
    })

    assert r.status_code == 409
    assert fake.table("pedidos").select("*").execute().data == []


def test_pedido_calcula_precio_decimal_sin_perder_centavos(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=130.50)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 2,
            "usd_unitario": 130.50, "usd_subtotal": 261,
        }],
        "total_usd": 251,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["detalle"][0]["usd_subtotal"] == 261
    assert pedido["total_usd"] == 251


def test_pedido_compara_decimal_cero_uno_por_tres_exactamente(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=0.1)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 3,
            "usd_unitario": 0.1, "usd_subtotal": 0.3,
        }],
        "total_usd": 0,
    })

    assert r.status_code == 200
    pedido = fake.table("pedidos").select("*").execute().data[0]
    assert pedido["detalle"][0]["usd_subtotal"] == 0.3


def test_pedido_mayorista_ignora_descuentos_monetarios_enviados(monkeypatch):
    c, fake = _cliente_mayorista_con_catalogo(monkeypatch, precio_publico=180, costo=100)

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 130, "usd_subtotal": 130,
        }],
        "total_usd": 0, "descuento_usd": 130,
    })

    assert r.status_code == 409
    assert fake.table("pedidos").select("*").execute().data == []


def test_pedido_no_aplica_codigo_mailing_de_otro_cliente(monkeypatch):
    c, fake = _cliente_con_catalogo(monkeypatch, precio_publico=180)
    fake.table("codigos_descuento").insert({
        "cliente_id": "otro-cliente",
        "code": "TTRA-AJENO",
        "productos": ["Elegible"],
        "descuento_usd": 5,
        "activo": True,
    }).execute()

    r = c.post("/api/pedidos", json={
        "productos": ["Elegible"], "fecha_entrega": "2026-08-24",
        "direccion_entrega": "Av. Colón 123",
        "detalle": [{
            "nombre": "Elegible", "cantidad": 1,
            "usd_unitario": 180, "usd_subtotal": 180,
        }],
        "total_usd": 175, "codigo_descuento": "TTRA-AJENO",
    })

    assert r.status_code == 409
    assert fake.table("pedidos").select("*").execute().data == []
