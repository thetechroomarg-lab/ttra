"""Captura de evidencia privada y conciliación sin repetir efectos comerciales."""
import json
import logging
import os
from pathlib import Path
from web import ganancia

logger=logging.getLogger(__name__)


def capturar_costos(client, pedido_id, costos, fuente):
    pedido=(client.table('pedidos').select('*').eq('id',pedido_id).execute().data or [None])[0]
    if not pedido: return None
    evidencia={i['nombre']:(str(costos[i['nombre']]) if costos.get(i['nombre']) is not None else None) for i in pedido.get('detalle') or [] if i.get('nombre')}
    return client.rpc('capturar_ganancia_costos',{'p_id':pedido_id,'p_costos':evidencia,'p_fuente':fuente}).execute().data


def capturar_al_crear(client, pedido):
    try:
        base=Path(os.environ.get('PRODUCTOS_PATH') or Path(__file__).parent/'productos.json')
        ruta=Path(os.environ.get('COSTOS_PATH') or base.with_name('costos.json'))
        costos=json.loads(ruta.read_text()) if ruta.exists() else {}
        capturar_costos(client,pedido['id'],costos,'catálogo vigente al cargar el pedido')
    except Exception:
        logger.exception('Costos pendientes de captura para pedido %s',pedido.get('id'))
    return pedido


def conciliar_venta(client,pedido_id):
    pedido=(client.table('pedidos').select('*').eq('id',pedido_id).execute().data or [None])[0]
    if not pedido or not pedido.get('recibo_enviado_en') or pedido.get('borrado_en'): return None
    evidencia=(client.table('ganancia_costos').select('*').eq('id',pedido_id).execute().data or [None])[0]
    costos=dict((evidencia or {}).get('costos',{}))
    for nombre in (evidencia or {}).get('conflictos',{}): costos.pop(nombre,None)
    movimiento=ganancia.calcular_venta(pedido,costos)
    movimiento['evidencia']['costos_conflictivos']=(evidencia or {}).get('conflictos',{})
    movimiento['evidencia']['fuente_costos']=(evidencia or {}).get('fuente')
    return ganancia.registrar_movimiento(client,movimiento)


def movimiento_pago(pago,cotizacion=None):
    cambio=pago.get('cotizacion_ars_usd') or cotizacion
    monto=ganancia.convertir_usd(pago['monto_ars'],'ARS',cambio)
    return dict(fuente_tipo='alejo',fuente_id=str(pago['id']),fecha_operacion=ganancia.fecha_local(pago['creado_en']),
        tipo='gasto',concepto='Pago a Alejo',ingreso_usd='0.00',costo_usd='0.00',comision_usd='0.00',
        gasto_usd=ganancia.dinero(monto) if monto is not None else None,
        estado_evidencia='confirmado' if pago.get('cotizacion_ars_usd') else 'estimado' if monto is not None else 'pendiente',
        version_calculo=1,evidencia={'monto_original':str(pago['monto_ars']),'moneda_original':'ARS','cotizacion':str(cambio) if cambio else None,
           'faltantes':[] if monto is not None else ['Cotización histórica del pago a Alejo']})


def conciliar_pago_cadete(client,pago_id,cotizacion=None):
    pago=(client.table('pagos_cadete').select('*').eq('id',pago_id).execute().data or [None])[0]
    if not pago: return None
    return ganancia.registrar_movimiento(client,movimiento_pago(pago,cotizacion))


def intentar(funcion,*args):
    try: return funcion(*args)
    except Exception:
        logger.exception('Registro de ganancia pendiente de conciliación: %s',funcion.__name__)
        return None


def tiene_costos(client,pedido_id):
    try:
        filas=client.table('ganancia_costos').select('*').eq('id',pedido_id).execute().data or []
    except Exception as exc:
        if getattr(exc,'code',None) in ('42P01','PGRST205'): return False
        raise
    return bool(filas and any(v is not None for v in filas[0].get('costos',{}).values()))
