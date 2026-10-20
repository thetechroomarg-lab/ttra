from decimal import Decimal
import pytest
from web import ganancia
from tests.fakes_supabase import FakeSupabaseClient


def venta():
    return {'id':'venta-1','recibo_id':'0001-1','recibo_enviado_en':'2026-10-20T12:00:00Z','total_usd':500,
            'detalle':[{'nombre':'Equipo','cantidad':1,'usd_unitario':500,'usd_subtotal':500}]}


def test_calculo_neto_con_comision_y_costo_confirmados():
    r=ganancia.calcular_venta(venta(), {'Equipo':400}, Decimal('5'))
    assert r['ingreso_usd']=='500.00' and r['costo_usd']=='400.00' and r['comision_usd']=='5.00'
    assert r['estado_evidencia']=='confirmado'


def test_falta_costo_es_pendiente_no_ganancia_ficticia():
    r=ganancia.calcular_venta(venta(), {}, 0)
    assert r['estado_evidencia']=='pendiente' and r['costo_usd'] is None


def test_conversion_sin_cotizacion_no_usa_actual():
    assert ganancia.convertir_usd(15000,'ARS',1500)==Decimal('10')
    assert ganancia.convertir_usd(15000,'ARS',None) is None
    with pytest.raises(ValueError): ganancia.convertir_usd('NaN','USD',None)


def test_no_resta_dos_veces_comision_modelada_en_total_neto():
    p={**venta(),'recibo_pago':{'metodos':[{'metodo':'ars_transferencia'}]}}
    r=ganancia.calcular_venta(p, {'Equipo':400}, None)
    assert r['ingreso_usd']=='500.00' and r['comision_usd']=='0.00'
    assert r['estado_evidencia']=='estimado'


def test_libro_idempotente_y_resumen_no_mezcla_estimados():
    c=FakeSupabaseClient()
    m=ganancia.calcular_venta(venta(), {'Equipo':400}, 5)
    ganancia.registrar_movimiento(c,m); ganancia.registrar_movimiento(c,m)
    gasto={**m,'fuente_tipo':'alejo','fuente_id':'pago-1','tipo':'gasto','ingreso_usd':'0','costo_usd':'0','comision_usd':'0','gasto_usd':'10'}
    ganancia.registrar_movimiento(c,gasto)
    estimado={**m,'fuente_id':'venta-2','estado_evidencia':'estimado'}
    ganancia.registrar_movimiento(c,estimado)
    r=ganancia.resumen(c,'2026-10-20','2026-10-20')
    assert r['confirmado']['neto_usd']=='85.00' and r['estimado']['neto_usd']=='95.00'
    assert len(r['movimientos'])==3


def test_limite_de_fecha_argentina_y_anulados():
    c=FakeSupabaseClient(); p=venta(); p['recibo_enviado_en']='2026-10-21T01:00:00Z'
    m=ganancia.calcular_venta(p,{'Equipo':600},0)
    assert m['fecha_operacion']=='2026-10-20'
    ganancia.registrar_movimiento(c,m)
    assert ganancia.resumen(c,'2026-10-20','2026-10-20')['confirmado']['neto_usd']=='-100.00'
    with pytest.raises(ValueError): ganancia.resumen(c,'2026-10-22','2026-10-20')
