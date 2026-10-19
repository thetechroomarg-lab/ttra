"""Cobros reales: conversión, cierre y snapshot del recibo."""
import json
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
import web.app as appmod
from web import recibos
from tests.fakes_supabase import FakeSupabaseClient


@pytest.fixture
def entorno(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, 'get_client', lambda: fake)
    monkeypatch.setattr(appmod, 'ADMIN_CLIENTES_PASSWORD', 'prueba')
    monkeypatch.setattr(appmod, '_cargar_cotizacion_catalogo', lambda: 1500)
    enviados = []
    monkeypatch.setattr(appmod, 'enviar_email', lambda *args: enviados.append(args))
    fake.table('clientes').insert({'id': 'cliente-pago', 'nombre': 'Ana', 'email': 'ana@example.test', 'tipo_cliente': 'mayorista'}).execute()
    fake.table('pedidos').insert({'id': 'pago', 'cliente_id': 'cliente-pago',
        'fecha_entrega': appmod.entregas.ahora_argentina().date().isoformat(),
        'detalle': [{'nombre': 'Teléfono de prueba', 'cantidad': 2, 'usd_unitario': 410, 'usd_subtotal': 820}],
        'productos': ['Teléfono de prueba'], 'total_usd': 820}).execute()
    c = TestClient(appmod.app, base_url='https://testserver')
    c.post('/admin/clientes/login', json={'password': 'prueba'})
    return c, fake, enviados


def enviar(c, pagos, cotizacion=1500):
    return c.post('/admin/pedidos/pago/recibo', files={'pagos': (None, json.dumps({'metodos': pagos, 'cotizacion': cotizacion}))})


@pytest.mark.parametrize('metodo,monto,moneda', [
    ('usd', '820', 'USD'), ('usd_usa', '842', 'USD'), ('usdt', '829', 'USDT'),
    ('ars', '1230000', 'ARS'), ('ars_transferencia', '1268042', 'ARS'),
])
def test_un_metodo_calcula_total_sin_pedir_importe(entorno, metodo, monto, moneda):
    c, fake, enviados = entorno
    r = enviar(c, [{'metodo': metodo}])
    assert r.status_code == 200, r.text
    pago = fake.table('pedidos').select('*').eq('id', 'pago').execute().data[0]['recibo_pago']
    assert Decimal(pago['metodos'][0]['monto']) == Decimal(monto)
    assert pago['metodos'][0]['moneda'] == moneda
    assert enviados


def test_mixto_guarda_importes_y_reenvia_sin_recalcular(entorno, monkeypatch):
    c, fake, enviados = entorno
    r = enviar(c, [{'metodo': 'usd', 'monto': '800'}, {'metodo': 'ars_transferencia', 'monto': '30928'}])
    assert r.status_code == 200, r.text
    pedido = fake.table('pedidos').select('*').eq('id', 'pago').execute().data[0]
    pago = pedido['recibo_pago']
    assert Decimal(pago['cotizacion']) == 1500
    assert 'Transferencia pesos' in enviados[0][2] and '30.928' in enviados[0][2]
    assert '800' in enviados[0][2]
    monkeypatch.setattr(appmod, '_cargar_cotizacion_catalogo', lambda: 2000)
    assert c.post('/admin/pedidos/pago/recibo').status_code == 200
    assert '30.928' in enviados[1][2]
    assert fake.table('pedidos').select('*').eq('id', 'pago').execute().data[0]['recibo_pago'] == pago


@pytest.mark.parametrize('pagos', [[], [{'metodo':'desconocido'}],
    [{'metodo':'usd','monto':'800'}, {'metodo':'ars_transferencia','monto':'1000'}],
    [{'metodo':'usd','monto':'800'}, {'metodo':'ars_transferencia','monto':'999999'}],
    [{'metodo':'usd','monto':'NaN'}, {'metodo':'ars','monto':'30000'}],
    [{'metodo':'usd','monto':'-1'}, {'metodo':'ars','monto':'1231500'}],
    [{'metodo':'usd'}, {'metodo':'ars'}], [{'metodo':'usd'}, {'metodo':'usd'}],
])
def test_rechaza_cobros_invalidos_sin_enviar(entorno, pagos):
    c, fake, enviados = entorno
    assert enviar(c, pagos).status_code == 400
    assert not enviados
    assert not fake.table('pedidos').select('*').eq('id', 'pago').execute().data[0].get('recibo_enviado_en')


def test_cotizacion_cambiada_pide_actualizar_antes_de_enviar(entorno):
    c, _, enviados = entorno
    assert enviar(c, [{'metodo':'ars'}], cotizacion=1400).status_code == 409
    assert not enviados


def test_fallo_email_conserva_cobro_para_reintento(entorno, monkeypatch):
    c, fake, _ = entorno
    def fallar(*args):
        raise appmod.EnvioEmailError('Proveedor no disponible')
    monkeypatch.setattr(appmod, 'enviar_email', fallar)
    assert enviar(c, [{'metodo': 'usd'}]).status_code == 502
    pedido = fake.table('pedidos').select('*').eq('id', 'pago').execute().data[0]
    assert pedido['recibo_pago']['metodos'][0]['monto'] == '820'
    assert not pedido.get('recibo_enviado_en')


def test_panel_muestra_cinco_totales_por_entrega(entorno):
    c, _, _ = entorno
    r = c.get('/admin/clientes')
    assert r.status_code == 200
    for monto in ('820', '842', '829', '1.230.000', '1.268.042'):
        assert monto in r.text
    assert 'Dólar banco USA' in r.text and 'Transferencia pesos' in r.text


def test_reintento_tras_fallo_conserva_cotizacion_original(entorno, monkeypatch):
    c, fake, enviados = entorno
    def fallar(*args):
        raise appmod.EnvioEmailError('Temporal')
    monkeypatch.setattr(appmod, 'enviar_email', fallar)
    assert enviar(c, [{'metodo': 'ars'}]).status_code == 502
    monkeypatch.setattr(appmod, '_cargar_cotizacion_catalogo', lambda: 2000)
    monkeypatch.setattr(appmod, 'enviar_email', lambda *args: enviados.append(args))
    consulta = c.get('/admin/pedidos/pago/pagos').json()
    assert consulta['cotizacion'] == 1500
    assert enviar(c, [{'metodo': 'ars'}], cotizacion=1500).status_code == 200
    assert '1.230.000' in enviados[0][2]


def test_pago_unico_en_pesos_redondea_a_centavos():
    from web.pagos_entrega import validar
    pago = validar('820.01', '1500.25', {'metodos':[{'metodo':'ars'}]})
    assert pago['metodos'][0]['monto'] == '1230220'


def test_cambio_de_total_desde_abrir_modal_requiere_revision(entorno):
    c, fake, enviados = entorno
    payload = {'cotizacion':1500, 'total_usd':820, 'metodos':[{'metodo':'usd'}]}
    fake.table('pedidos').update({'total_usd':900}).eq('id','pago').execute()
    r = c.post('/admin/pedidos/pago/recibo', files={'pagos':(None,json.dumps(payload))})
    assert r.status_code == 409
    assert not enviados


def test_pdf_descargado_conserva_desglose_mixto(entorno, tmp_path):
    import shutil
    import subprocess
    if not shutil.which('pdftotext'):
        pytest.skip('Poppler requerido para extraer el PDF')
    c, _, _ = entorno
    assert enviar(c, [{'metodo':'usd','monto':'800'}, {'metodo':'ars_transferencia','monto':'30928'}]).status_code == 200
    respuesta = c.get('/admin/pedidos/pago/recibo.pdf')
    assert respuesta.status_code == 200
    archivo = tmp_path / 'recibo.pdf'
    archivo.write_bytes(respuesta.content)
    texto = subprocess.check_output(['pdftotext',str(archivo),'-'], text=True)
    assert 'Dólar contado: U$D 800' in texto
    assert 'Transferencia pesos: $ 30.928' in texto
    assert 'Cotización aplicada: $ 1.500 por USD' in texto


def test_consulta_pago_protege_sesion_y_pedido_borrado(entorno):
    c, fake, _ = entorno
    anon = TestClient(appmod.app, base_url='https://testserver')
    assert anon.get('/admin/pedidos/pago/pagos').status_code == 401
    fake.table('pedidos').update({'borrado_en':'2026-10-19T10:00:00Z'}).eq('id','pago').execute()
    assert c.get('/admin/pedidos/pago/pagos').status_code == 404


def test_reenvio_ignora_cambios_en_metodos_de_pago(entorno):
    c, fake, enviados = entorno
    assert enviar(c, [{'metodo':'usd'}]).status_code == 200
    original = fake.table('pedidos').select('*').eq('id','pago').execute().data[0]['recibo_pago']
    assert enviar(c, [{'metodo':'ars'}]).status_code == 200
    assert fake.table('pedidos').select('*').eq('id','pago').execute().data[0]['recibo_pago'] == original
    assert 'Dólar contado' in enviados[1][2]
