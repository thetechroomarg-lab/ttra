import pytest
from fastapi.testclient import TestClient
import web.app as appmod
from tests.test_pagos_entrega import entorno, enviar


def cambiar(c, precios, version=None):
    if version is None:
        version = c.get('/admin/pedidos/pago/pagos').json().get('version_precio')
    return c.post('/admin/pedidos/pago/precios', json={'precios': precios, 'version': version})


def test_actualiza_unitario_subtotal_total_y_todas_las_formas_de_pago(entorno):
    c, fake, enviados = entorno
    r = cambiar(c, ['500'])
    assert r.status_code == 200, r.text
    datos = c.get('/admin/pedidos/pago/pagos').json()
    assert datos['total_usd'] == 1000
    assert {p['metodo']: p['monto'] for p in datos['opciones']} == {
        'usd': '1000', 'usd_usa': '1026', 'usdt': '1011', 'ars': '1500000', 'ars_transferencia': '1546392'}
    pedido = fake.table('pedidos').select('*').eq('id', 'pago').execute().data[0]
    assert pedido['detalle'][0]['usd_unitario'] == 500
    assert pedido['detalle'][0]['usd_subtotal'] == 1000
    assert not enviados
    assert enviar(c, [{'metodo': 'usd'}]).status_code == 200
    assert '500' in enviados[0][2] and '1.000' in enviados[0][2]


def test_conserva_descuentos_y_los_otros_productos(entorno):
    c, fake, _ = entorno
    fake.table('pedidos').update({'total_usd': 830, 'descuento_usd': 20,
        'detalle': [{'nombre': 'Teléfono', 'cantidad': 2, 'usd_unitario': 410, 'usd_subtotal': 820},
                    {'nombre': 'Funda', 'cantidad': 1, 'usd_unitario': 30, 'usd_subtotal': 30}]}).eq('id', 'pago').execute()
    assert cambiar(c, ['500.25', '30']).status_code == 200
    pedido = fake.table('pedidos').select('*').eq('id', 'pago').execute().data[0]
    assert pedido['total_usd'] == 1010.5
    assert pedido['descuento_usd'] == 20
    assert pedido['detalle'][1]['usd_unitario'] == 30


@pytest.mark.parametrize('precios', [[], ['-1'], ['NaN'], ['Infinity'], [True], [None], ['1.001'], ['1000000000001'], ['500','600']])
def test_rechaza_importes_invalidos_sin_cambiar_pedido(entorno, precios):
    c, fake, _ = entorno
    assert cambiar(c, precios).status_code == 400
    assert fake.table('pedidos').select('*').eq('id', 'pago').execute().data[0]['total_usd'] == 820


def test_rechaza_precio_desactualizado(entorno):
    c, _, _ = entorno
    version = c.get('/admin/pedidos/pago/pagos').json().get('version_precio')
    assert cambiar(c, ['500'], version).status_code == 200
    assert cambiar(c, ['600'], version).status_code == 409


@pytest.mark.parametrize('campo', ['recibo_enviado_en', 'recibo_emitido_en', 'recibo_pago'])
def test_no_modifica_recibos_emitidos_o_cobros_registrados(entorno, campo):
    c, fake, _ = entorno
    fake.table('pedidos').update({campo: {'total_usd':'820', 'cotizacion':'1500', 'metodos':[]} if campo == 'recibo_pago' else '2026-10-20T12:00:00Z'}).eq('id','pago').execute()
    assert cambiar(c, ['500'], 'version').status_code == 409


def test_sin_sesion_no_permite_cambiar_precio(entorno):
    c = TestClient(appmod.app, base_url='https://testserver')
    assert cambiar(c, ['500'], 'version').status_code == 401


def test_pago_con_total_anterior_rechazado_despues_de_editar(entorno):
    import json
    c, _, enviados = entorno
    assert cambiar(c, ['500']).status_code == 200
    r = c.post('/admin/pedidos/pago/recibo', files={'pagos': (None, json.dumps({
        'total_usd':820,'cotizacion':1500,'metodos':[{'metodo':'usd'}]}))})
    assert r.status_code == 409
    assert not enviados


def test_pedido_sin_total_no_se_puede_editar(entorno):
    c, fake, _ = entorno
    fake.table('pedidos').update({'total_usd': None}).eq('id','pago').execute()
    from web import precios_recibo
    pedido = fake.table('pedidos').select('*').eq('id','pago').execute().data[0]
    assert cambiar(c, ['500'], precios_recibo.version(pedido)).status_code == 400


def test_edicion_concurrente_no_sobrescribe_otro_precio(entorno, monkeypatch):
    c, fake, _ = entorno
    tabla = fake.table('pedidos')
    original = tabla.update
    def cambiar_antes_de_guardar(payload):
        tabla._filas[:] = [{**p, 'total_usd': 1200} for p in tabla._filas]
        return original(payload)
    monkeypatch.setattr(tabla, 'update', cambiar_antes_de_guardar)
    assert cambiar(c, ['500']).status_code == 409
    assert tabla.select('*').execute().data[0]['total_usd'] == 1200


def test_cambio_concurrente_al_emitir_no_envia_importe_viejo(entorno, monkeypatch):
    c, fake, enviados = entorno
    tabla = fake.table('pedidos')
    original = tabla.update
    def cambiar_antes_de_reservar(payload):
        tabla._filas[:] = [{**p, 'total_usd': 1000} for p in tabla._filas]
        return original(payload)
    monkeypatch.setattr(tabla, 'update', cambiar_antes_de_reservar)
    assert enviar(c, [{'metodo':'usd'}]).status_code == 409
    assert not enviados
