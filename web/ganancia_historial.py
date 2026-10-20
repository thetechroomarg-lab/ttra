"""Reconstrucción conservadora: fuentes exactas, costos fechados y pendientes explícitos."""
import json
from web import ganancia
from web.ganancia_servicio import movimiento_pago
from web.historial_importado import datos_importados


def preparar_historial(recibos, importados, pagos_cadete, fuentes_costos, fuentes_cambio):
    movimientos=[]; vistos=set(); duplicados=0; omitidos=[]
    def agregar(m):
        nonlocal duplicados
        clave=(m['fuente_tipo'],m['fuente_id'])
        if clave in vistos: duplicados+=1; return
        vistos.add(clave); movimientos.append(m)
    recibos_ids={str(p['id']) for p in recibos if p.get('recibo_enviado_en')}
    for p in recibos:
        if not p.get('recibo_enviado_en') or p.get('borrado_en'): continue
        try:
            fecha=ganancia.fecha_local(p.get('recibo_emitido_en') or p['recibo_enviado_en'])
            candidatas=sorted((f for f in fuentes_costos if f['fecha']<=fecha),key=lambda f:f['fecha'])
            fuente=candidatas[-1] if candidatas else next((f for f in fuentes_costos if f.get('aproximacion_actual')), {})
            m=ganancia.calcular_venta(p,fuente.get('costos',{}))
            if m['estado_evidencia']!='pendiente': m['estado_evidencia']='estimado'
            m['evidencia']['fuente_costos']=fuente.get('fuente')
            m['evidencia']['criterio_costos']=('Costo de referencia actual; aproximación, no acredita el costo histórico.' if fuente.get('aproximacion_actual') else 'Lista documentada anterior al recibo; no acredita el costo efectivo de compra.')
            agregar(m)
        except (ValueError,TypeError,KeyError) as exc:
            omitidos.append({'fuente':'venta','id':str(p.get('id')),'motivo':str(exc)})
    for fila in importados:
        raw=datos_importados(fila)
        if raw is None: continue
        nota=json.loads(fila['nota'])
        if str(nota.get('pedido_id')) in recibos_ids:
            duplicados+=1; continue
        # No deducir identidad por nombre del cliente o un importe coincidente.
        try: fecha=ganancia.fecha_local(fila['fecha_entrega'])
        except (ValueError,TypeError,KeyError):
            omitidos.append({'fuente':'importado','id':str(fila.get('id')),'motivo':'Fecha original no verificable'}); continue
        ingreso=nota.get('total_usd') if nota.get('moneda')=='USD' else None
        agregar(dict(fuente_tipo='importado',fuente_id=str(raw.get('#') or fila['id']),fecha_operacion=fecha,
            tipo='venta',concepto=f"Histórico importado #{raw.get('#') or fila['id']}",ingreso_usd=ganancia.dinero(ingreso) if ingreso is not None else None,
            costo_usd=None,comision_usd=None,gasto_usd='0.00',estado_evidencia='pendiente',version_calculo=1,
            evidencia={'fila_id':str(fila['id']),'faltantes':['Costo y detalle de compra original','Comisiones e identidad frente a recibos actuales']+([] if ingreso is not None else ['Moneda e importe original verificados']),
                       'criterio_moneda':nota.get('criterio_moneda'),'origen':'historial importado'}))
    for pago in pagos_cadete:
        try: agregar(movimiento_pago(pago,fuentes_cambio.get(str(pago['id']))))
        except (ValueError,TypeError,KeyError) as exc:
            omitidos.append({'fuente':'alejo','id':str(pago.get('id')),'motivo':str(exc)})
    return {'version':1,'movimientos':movimientos,'duplicados':duplicados,'omitidos':omitidos,
            'primera_fecha':min((m['fecha_operacion'] for m in movimientos),default=None),
            'estados':{s:sum(m['estado_evidencia']==s for m in movimientos) for s in ('confirmado','estimado','pendiente')}}


def importar_historial(client,informe):
    if informe.get('version')!=1: raise ValueError('Informe incompatible')
    # Nunca modifica los recibos, las compras, ni vuelve a enviar correos.
    for movimiento in informe['movimientos']: ganancia.registrar_movimiento(client,movimiento)
    return {'procesados':len(informe['movimientos'])}
