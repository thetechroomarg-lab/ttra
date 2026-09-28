from fastapi.testclient import TestClient
import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient
import json


def test_historial_importado_respeta_fecha_y_no_fabrica_recibo(monkeypatch):
    fake = FakeSupabaseClient()
    fake.table('tareas_entrega').insert({'id':'legacy-1','fecha_entrega':'2022-07-12','cliente_nombre':'Ana <Prueba>', 'titulo':'Histórico #1', 'completada_en':'2026-09-28T00:00:00Z', 'nota':json.dumps({'tipo':'historial_importado','version':1,'datos_originales':{'#':'1','Date':'2022-7-12','Customer':'Ana <Prueba>','Customer Email':'','Additional Info.':'','Subtotal':'400','Tax1':'','Tax2':'','Invoice Amount':'360'}})}).execute()
    monkeypatch.setattr(appmod,'get_client',lambda:fake)
    monkeypatch.setattr(appmod,'ADMIN_CLIENTES_PASSWORD','test-admin')
    c=TestClient(appmod.app,base_url='https://testserver')
    assert 'Ana &lt;Prueba&gt;' not in c.get('/admin/clientes?fecha_pedidos=2022-07-12').text
    c.post('/admin/clientes/login',json={'password':'test-admin'})
    body=c.get('/admin/clientes?fecha_pedidos=2022-07-12').text
    assert 'Histórico importado #1' in body
    assert 'Ana &lt;Prueba&gt;' in body
    assert 'Moneda no informada' in body
    assert 'Subtotal: 400' in body and 'Total: 360' in body
    assert 'Datos originales' in body
    assert 'Histórico importado #1' not in c.get('/admin/clientes?fecha_pedidos=2022-07-13').text


def test_importador_conserva_todos_los_campos_y_fecha_sin_crear_cliente(tmp_path):
    import csv
    from scripts.importar_historial_estimate import preparar, FIELDS
    path=tmp_path/'estimate.csv'
    row=['339','2022-7-12','Ana\nPrueba','','','0.00','','','-0.08']
    with path.open('w',newline='') as f:
        writer=csv.writer(f); writer.writerow(FIELDS); writer.writerow(row)
    digest, registros=preparar(path)
    item=registros[0]
    assert item['fecha_entrega']=='2022-07-12'
    assert item['cliente_id'] is None and item['asignado_a'] is None
    assert item['completada_en']
    assert json.loads(item['nota'])['datos_originales']==dict(zip(FIELDS,row))
    assert preparar(path)[1][0]['id']==item['id']
    with path.open('a',newline='') as f: csv.writer(f).writerow(row)
    import pytest
    with pytest.raises(ValueError,match='duplicado'): preparar(path)


def test_conversion_usd_usa_total_y_conserva_originales():
    from web.historial_importado import normalizar_moneda, tarjeta_importada
    from decimal import Decimal
    raw={'#':'1992','Date':'2026-8-26','Customer':'Club','Subtotal':'330750','Invoice Amount':'330750'}
    nota={'tipo':'historial_importado','version':1,'datos_originales':raw}
    convertido=normalizar_moneda(nota, Decimal('1575'))
    assert convertido['total_usd']=='210.00'
    assert convertido['subtotal_usd']=='210.00'
    assert convertido['moneda_original']=='ARS'
    assert convertido['datos_originales']==raw and 'moneda' not in nota
    assert normalizar_moneda(convertido,Decimal('1575'))==convertido
    assert 'Total: USD 210.00' in tarjeta_importada({'nota':json.dumps(convertido)})
    for amount,expected,currency in [('10000','10000.00','USD'),('10001','6.35','ARS'),('0','0.00','USD'),('-0.08','-0.08','USD')]:
        sample={**nota,'datos_originales':{**raw,'Subtotal':amount,'Invoice Amount':amount}}
        result=normalizar_moneda(sample,Decimal('1575'))
        assert (result['total_usd'],result['moneda_original'])==(expected,currency)
