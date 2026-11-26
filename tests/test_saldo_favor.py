"""Saldo a favor: lo que el cliente pagó de más se descuenta en su próxima compra, con el recibo."""
import json
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import web.app as appmod
from web import saldo_favor
from tests.fakes_supabase import FakeSupabaseClient


@pytest.fixture
def entorno(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, 'get_client', lambda: fake)
    monkeypatch.setattr(appmod, 'ADMIN_CLIENTES_PASSWORD', 'prueba')
    monkeypatch.setattr(appmod, '_cargar_cotizacion_catalogo', lambda: 1500)
    enviados = []
    monkeypatch.setattr(appmod, 'enviar_email', lambda *args: enviados.append(args))
    fake.table('clientes').insert({'id': 'cli', 'nombre': 'Ana', 'email': 'ana@example.test'}).execute()
    fake.table('pedidos').insert({'id': 'ped', 'cliente_id': 'cli',
        'fecha_entrega': appmod.entregas.ahora_argentina().date().isoformat(),
        'detalle': [{'nombre': 'Teléfono de prueba', 'cantidad': 2, 'usd_unitario': 410, 'usd_subtotal': 820}],
        'productos': ['Teléfono de prueba'], 'total_usd': 820}).execute()
    c = TestClient(appmod.app, base_url='https://testserver')
    c.post('/admin/clientes/login', json={'password': 'prueba'})
    return c, fake, enviados


def enviar(c, pagos=({'metodo': 'usd'},)):
    return c.post('/admin/pedidos/ped/recibo', files={'pagos': (None, json.dumps({'metodos': list(pagos), 'cotizacion': 1500}))})


def pedido(fake):
    return fake.table('pedidos').select('*').eq('id', 'ped').execute().data[0]


def test_el_saldo_es_la_suma_de_movimientos_y_nunca_baja_de_cero(entorno):
    _, fake, _ = entorno
    assert saldo_favor.saldo(fake, 'cli') == 0
    assert saldo_favor.acreditar(fake, 'cli', 100, 'Pagó de más') == Decimal('100.00')
    assert saldo_favor.aplicable(fake, 'cli', 60) == Decimal('60.00')
    assert saldo_favor.aplicable(fake, 'cli', 500) == Decimal('100.00')
    with pytest.raises(ValueError):
        saldo_favor.acreditar(fake, 'cli', -150, 'Corrección')
    with pytest.raises(ValueError):
        saldo_favor.acreditar(fake, 'cli', 10, '')


def test_un_pedido_consume_el_saldo_una_sola_vez(entorno):
    _, fake, _ = entorno
    saldo_favor.acreditar(fake, 'cli', 100, 'Pagó de más')
    assert saldo_favor.consumir(fake, 'cli', 'ped', 60) is True
    assert saldo_favor.consumir(fake, 'cli', 'ped', 60) is False
    assert saldo_favor.saldo(fake, 'cli') == Decimal('40.00')


def test_con_saldo_el_cobro_es_el_total_menos_lo_que_tiene_a_favor(entorno):
    c, fake, _ = entorno
    saldo_favor.acreditar(fake, 'cli', 100, 'Pagó de más')
    datos = c.get('/admin/pedidos/ped/pagos').json()
    assert datos['total_pedido_usd'] == 820 and datos['saldo_favor_usd'] == 100 and datos['total_usd'] == 720
    assert {o['metodo']: o['monto'] for o in datos['opciones']}['usd'] == '720'


def test_el_saldo_se_gasta_recien_con_el_recibo_y_el_reenvio_no_lo_repite(entorno):
    c, fake, enviados = entorno
    saldo_favor.acreditar(fake, 'cli', 100, 'Pagó de más')
    assert saldo_favor.saldo(fake, 'cli') == Decimal('100.00')
    assert enviar(c).status_code == 200
    pago = pedido(fake)['recibo_pago']
    assert pago['total_usd'] == '720' and pago['saldo_favor_usd'] == '100' and pago['total_pedido_usd'] == '820'
    assert saldo_favor.saldo(fake, 'cli') == 0
    cuerpo = enviados[0][2]
    assert 'Saldo a favor aplicado: -US$ 100' in cuerpo and 'Total a pagar: US$ 720' in cuerpo
    assert c.post('/admin/pedidos/ped/recibo').status_code == 200
    assert saldo_favor.saldo(fake, 'cli') == 0
    assert len([m for m in saldo_favor.movimientos(fake, 'cli') if Decimal(str(m['monto_usd'])) < 0]) == 1


def test_si_el_saldo_cubre_todo_el_pedido_queda_el_resto_a_favor(entorno):
    c, fake, enviados = entorno
    saldo_favor.acreditar(fake, 'cli', 1000, 'Pagó de más')
    datos = c.get('/admin/pedidos/ped/pagos').json()
    assert datos['total_usd'] == 0 and datos['saldo_favor_usd'] == 820
    assert enviar(c).status_code == 200
    assert saldo_favor.saldo(fake, 'cli') == Decimal('180.00')
    assert 'Te quedan US$ 180 a favor para tu próxima compra' in enviados[0][2]


def test_sin_saldo_el_recibo_sale_como_siempre(entorno):
    c, fake, enviados = entorno
    assert enviar(c).status_code == 200
    assert 'saldo_favor_usd' not in pedido(fake)['recibo_pago']
    assert 'Saldo a favor' not in enviados[0][2]


def test_si_falla_la_tabla_de_saldos_la_entrega_sigue(entorno, monkeypatch):
    c, _, enviados = entorno
    def roto(*a, **k):
        raise RuntimeError('tabla inexistente')
    monkeypatch.setattr(saldo_favor, 'aplicable', roto)
    monkeypatch.setattr(saldo_favor, 'saldo', roto)
    assert enviar(c).status_code == 200 and enviados


def test_admin_carga_saldo_y_lo_ve_en_el_historial(entorno):
    c, fake, _ = entorno
    r = c.post('/admin/clientes/cli/saldo-favor', json={'monto_usd': 50, 'motivo': 'Pagó de más'})
    assert r.status_code == 200 and r.json()['saldo_usd'] == 50
    assert c.get('/admin/clientes/cli/saldo-favor').json()['saldo_usd'] == 50
    historial = c.get('/admin/clientes/cli/historial').text
    assert 'Saldo a favor' in historial and 'US$ 50' in historial and 'Pagó de más' in historial
    assert c.post('/admin/clientes/cli/saldo-favor', json={'monto_usd': 0, 'motivo': 'x'}).status_code == 400
    assert c.post('/admin/clientes/cli/saldo-favor', json={'monto_usd': 5, 'motivo': ''}).status_code == 400
    assert c.post('/admin/clientes/nadie/saldo-favor', json={'monto_usd': 5, 'motivo': 'x'}).status_code == 404


def test_cargar_saldo_exige_sesion_de_admin(entorno):
    _, fake, _ = entorno
    anonimo = TestClient(appmod.app, base_url='https://testserver')
    assert anonimo.post('/admin/clientes/cli/saldo-favor', json={'monto_usd': 5, 'motivo': 'x'}).status_code == 401
    assert anonimo.get('/admin/clientes/cli/saldo-favor').status_code == 401
