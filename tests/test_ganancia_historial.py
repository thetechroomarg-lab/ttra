from web.ganancia_historial import preparar_historial, importar_historial
from tests.test_ganancia import venta
from tests.fakes_supabase import FakeSupabaseClient


def test_historial_estimado_pendiente_y_reimportacion():
    p=venta()
    informe=preparar_historial([p,{**p,'id':'otra','detalle':[{'nombre':'Desconocido','cantidad':1}]}],[],[
        {'id':'alejo','monto_ars':15000,'creado_en':'2026-10-20T12:00:00Z'}],
        [{'fecha':'2026-10-01','fuente':'lista original','costos':{'Equipo':400}}],{})
    assert informe['estados']=={'confirmado':0,'estimado':1,'pendiente':2}
    c=FakeSupabaseClient()
    importar_historial(c,informe); importar_historial(c,informe)
    assert len(c.table('ganancia_movimientos').select('*').execute().data)==3
    assert informe['movimientos'][0]['costo_usd']=='400.00'


def test_no_repite_fuentes_ni_infiere_moneda_legacy():
    import json
    p=venta()
    legacy={'id':'viejo','fecha_entrega':'2026-01-01','nota':json.dumps({'tipo':'historial_importado','version':1,'datos_originales':{'#':'1','Invoice Amount':'500'}})}
    informe=preparar_historial([p,p],[legacy,legacy],[],[],{})
    assert len(informe['movimientos'])==2
    assert informe['duplicados']==2
    assert informe['movimientos'][1]['ingreso_usd'] is None
