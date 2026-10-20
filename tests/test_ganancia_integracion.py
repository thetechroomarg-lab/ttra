from web import ganancia_servicio as servicio
from tests.fakes_supabase import FakeSupabaseClient
from tests.test_ganancia import venta


def test_costo_congelado_y_reenvio_sin_duplicar():
    c=FakeSupabaseClient(); p=venta(); c.table('pedidos').insert(p).execute()
    servicio.capturar_costos(c,p['id'],{'Equipo':400},'lista fechada')
    servicio.capturar_costos(c,p['id'],{'Equipo':490},'otra lista')
    servicio.conciliar_venta(c,p['id']); servicio.conciliar_venta(c,p['id'])
    filas=c.table('ganancia_movimientos').select('*').execute().data
    assert len(filas)==1 and filas[0]['costo_usd'] is None
    assert filas[0]['estado_evidencia']=='pendiente'
    assert filas[0]['evidencia']['costos_conflictivos']['Equipo']['anterior']=='400'


def test_pago_alejo_una_vez_y_conversion_fija():
    c=FakeSupabaseClient(); c.table('pagos_cadete').insert({'id':'p1','monto_ars':15000,'cotizacion_ars_usd':1500,'creado_en':'2026-10-20T12:00:00Z'}).execute()
    servicio.conciliar_pago_cadete(c,'p1'); servicio.conciliar_pago_cadete(c,'p1',2000)
    f=c.table('ganancia_movimientos').select('*').execute().data
    assert len(f)==1 and f[0]['gasto_usd']=='10.00'


def test_recibo_no_enviado_no_registra_ingreso():
    c=FakeSupabaseClient(); c.table('pedidos').insert({**venta(),'recibo_enviado_en':None}).execute()
    assert servicio.conciliar_venta(c,'venta-1') is None


def test_pago_nuevo_guarda_cambio_y_resta_anticipo_completo():
    from web import saldo_cadete
    c=FakeSupabaseClient()
    c.table('movimientos_cadete').insert({'id':'m1','monto_ars':15000,'tipo':'pedido','creado_en':'2026-10-20T12:00:00Z'}).execute()
    r=saldo_cadete.registrar_pago(c,monto_transferido=30000,cotizacion=1500)
    assert r['pago']['cotizacion_ars_usd']==1500
    f=c.table('ganancia_movimientos').select('*').execute().data
    assert len(f)==1 and f[0]['gasto_usd']=='20.00'


def test_agregar_producto_preserva_costo_anterior():
    c=FakeSupabaseClient(); p=venta(); c.table('pedidos').insert(p).execute()
    servicio.capturar_costos(c,p['id'],{'Equipo':400},'primera')
    c.table('pedidos').update({'detalle':p['detalle']+[{'nombre':'Funda','cantidad':1}]}).eq('id',p['id']).execute()
    servicio.capturar_costos(c,p['id'],{'Equipo':450,'Funda':5},'segunda')
    fila=c.table('ganancia_costos').select('*').execute().data[0]
    assert fila['costos']=={'Equipo':'400','Funda':'5'}


def test_reprogramar_con_costos_no_fusiona_ni_duplica():
    from datetime import date
    from web import pedidos
    c=FakeSupabaseClient()
    p={**venta(),'cliente_id':'c','recibo_enviado_en':None,'fecha_entrega':'2026-10-20'}
    q={**p,'id':'venta-2','fecha_entrega':'2026-10-21'}
    c.table('pedidos').insert(p).execute(); c.table('pedidos').insert(q).execute()
    servicio.capturar_costos(c,p['id'],{'Equipo':400},'primera')
    pedidos.editar_fecha_entrega(c,p['id'],date(2026,10,21))
    filas=c.table('pedidos').select('*').execute().data
    assert len(filas)==2 and all(f['total_usd']==500 for f in filas)
