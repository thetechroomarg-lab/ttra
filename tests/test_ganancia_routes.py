import uuid
from fastapi.testclient import TestClient
import web.app as appmod
from tests.test_pagos_entrega import entorno


def test_manual_idempotente_privado_y_filtro(entorno):
    c,fake,_=entorno
    cuerpo={'clave':str(uuid.uuid4()),'fecha':'2026-10-20','concepto':'Servicio técnico','tipo':'ingreso','monto_usd':'35.50'}
    assert TestClient(appmod.app).post('/admin/ganancia/manual',json=cuerpo).status_code==401
    assert c.post('/admin/ganancia/manual',json=cuerpo).status_code==200
    assert c.post('/admin/ganancia/manual',json=cuerpo).status_code==200
    r=c.get('/admin/ganancia?desde=2026-10-20&hasta=2026-10-20').json()
    assert r['confirmado']['neto_usd']=='35.50' and len(r['movimientos'])==1
    cuerpo['monto_usd']='NaN'; cuerpo['clave']=str(uuid.uuid4())
    assert c.post('/admin/ganancia/manual',json=cuerpo).status_code==400


def test_panel_integra_secciones_y_cotizacion_redirige(entorno):
    c,_,_=entorno
    r=c.get('/admin/cotizacion',follow_redirects=False)
    assert r.status_code==303 and r.headers['location']=='/admin/clientes#cotizacion'
    pagina=c.get('/admin/clientes').text
    assert 'id="admin-seccion-ganancia"' in pagina and 'id="admin-seccion-cotizacion"' in pagina


def test_correccion_auditada_y_version(entorno):
    c,fake,_=entorno
    datos={'clave':str(uuid.uuid4()),'fecha':'2026-10-20','concepto':'Servicio','tipo':'ingreso','monto_usd':'40'}
    id=c.post('/admin/ganancia/manual',json=datos).json()['id']
    nuevo={**datos,'monto_usd':'50','version':1}
    assert c.patch('/admin/ganancia/manual/'+id,json=nuevo).status_code==200
    assert c.patch('/admin/ganancia/manual/'+id,json=nuevo).status_code==409
    assert len(fake.table('ganancia_revisiones').select('*').execute().data)==1
    assert c.patch('/admin/ganancia/manual/'+id,json={'version':2,'anular':True}).status_code==200
    assert c.get('/admin/ganancia?desde=2026-10-20&hasta=2026-10-20').json()['confirmado']['neto_usd']=='0.00'


def test_completar_pendiente_auditado_sin_duplicar(entorno):
    from web import ganancia
    from tests.test_ganancia import venta
    c,fake,_=entorno
    m=ganancia.registrar_movimiento(fake,ganancia.calcular_venta(venta(),{}))
    cuerpo={'version':1,'ingreso_usd':'500','costo_usd':'400','comision_usd':'5','gasto_usd':'0','estado_evidencia':'estimado','motivo':'Costo aproximado según lista conservada'}
    assert c.patch('/admin/ganancia/'+m['id']+'/completar',json=cuerpo).status_code==200
    assert c.patch('/admin/ganancia/'+m['id']+'/completar',json=cuerpo).status_code==409
    r=c.get('/admin/ganancia?desde=2026-10-20&hasta=2026-10-20').json()
    assert r['estimado']['neto_usd']=='95.00' and r['pendientes']==0 and len(r['movimientos'])==1
    assert len(fake.table('ganancia_revisiones').select('*').execute().data)==1
