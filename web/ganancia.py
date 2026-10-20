"""Libro financiero privado en USD. No se usa para calcular precios al cliente."""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

TABLA = 'ganancia_movimientos'
CAMPOS = ('ingreso_usd', 'costo_usd', 'comision_usd', 'gasto_usd')


def numero(valor):
    if isinstance(valor, bool) or valor is None:
        raise ValueError('Ingresá un importe válido en USD.')
    try:
        n = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('Ingresá un importe válido en USD.') from None
    if not n.is_finite() or abs(n) > Decimal('1000000000000'):
        raise ValueError('Importe fuera del rango permitido.')
    return n


def dinero(valor):
    return format(numero(valor).quantize(Decimal('.01'), rounding=ROUND_HALF_UP), '.2f')


def fecha_local(valor):
    if len(str(valor)) == 10:
        return date.fromisoformat(str(valor)).isoformat()
    instante = datetime.fromisoformat(str(valor).replace('Z', '+00:00'))
    if instante.tzinfo is None:
        raise ValueError('La fecha de la operación necesita zona horaria.')
    return instante.astimezone(ZoneInfo('America/Argentina/Cordoba')).date().isoformat()


def convertir_usd(monto, moneda, cotizacion):
    valor = numero(monto)
    if moneda == 'USD':
        return valor
    if moneda != 'ARS' or cotizacion is None:
        return None
    cambio = numero(cotizacion)
    return valor / cambio if cambio > 0 else None


def calcular_venta(pedido, costos, comisiones=None):
    if not pedido.get('recibo_enviado_en'):
        raise ValueError('El recibo todavía no fue enviado.')
    costo = Decimal(0); faltantes = []
    for item in pedido.get('detalle') or []:
        unitario = costos.get(item.get('nombre'))
        if unitario is None:
            faltantes.append(item.get('nombre') or 'Producto sin identificar'); continue
        valor = numero(unitario); cantidad = numero(item.get('cantidad'))
        if valor < 0 or cantidad <= 0:
            faltantes.append(item.get('nombre')); continue
        costo += valor * cantidad
    if not pedido.get('detalle'):
        faltantes.append('Detalle de productos ausente')
    metodos = (pedido.get('recibo_pago') or {}).get('metodos') or []
    # total_usd ya es el precio neto comercial. Los ajustes de medios de pago
    # no acreditan la comisión real; no se restan una segunda vez.
    estimado = comisiones is None and (not metodos or any(p.get('metodo') != 'usd' for p in metodos))
    estado = 'pendiente' if faltantes else 'estimado' if estimado else 'confirmado'
    return dict(fuente_tipo='venta', fuente_id=str(pedido['id']),
        fecha_operacion=fecha_local(pedido.get('recibo_emitido_en') or pedido['recibo_enviado_en']),
        tipo='venta', concepto=f"Recibo {pedido.get('recibo_id') or pedido['id']}",
        ingreso_usd=dinero(pedido['total_usd']), costo_usd=None if faltantes else dinero(costo),
        comision_usd=dinero(0 if comisiones is None else comisiones), gasto_usd='0.00',
        estado_evidencia=estado, version_calculo=1,
        evidencia={'recibo_id':pedido.get('recibo_id'), 'faltantes':faltantes,
                   'costos_unitarios':{k:str(v) for k,v in costos.items()},
                   'comision':'informada' if comisiones is not None else 'incluida en neto comercial; verificar costo real' if estimado else 'contado USD',
                   'total_neto_comercial':str(pedido['total_usd'])})


def listar_todos(client, tabla):
    filas=[]; inicio=0
    while True:
        pagina=client.table(tabla).select('*').order('id').range(inicio,inicio+499).execute().data or []
        filas.extend(pagina)
        if len(pagina)<500: return filas
        inicio+=500


def registrar_movimiento(client, movimiento):
    datos={'id':str(uuid.uuid4()), **movimiento}
    # UNIQUE + ON CONFLICT DO NOTHING: idempotente incluso con requests paralelos.
    client.table(TABLA).upsert(datos, on_conflict='fuente_tipo,fuente_id', ignore_duplicates=True).execute()
    filas=(client.table(TABLA).select('*').eq('fuente_tipo',datos['fuente_tipo'])
           .eq('fuente_id',datos['fuente_id']).execute().data)
    if not filas: raise RuntimeError('No se confirmó el registro financiero.')
    return filas[0]


def resumen(client, desde, hasta):
    inicio=date.fromisoformat(desde); fin=date.fromisoformat(hasta)
    if inicio>fin: raise ValueError('La fecha desde debe ser anterior o igual a hasta.')
    grupos={s:{c:Decimal(0) for c in CAMPOS} for s in ('confirmado','estimado')}
    filas=[]; pendientes=0
    for fila in listar_todos(client,TABLA):
        if fila.get('anulado_en') or not desde <= fila['fecha_operacion'] <= hasta: continue
        copia={k:fila.get(k) for k in ('id','fecha_operacion','tipo','concepto','estado_evidencia','version','fuente_tipo',*CAMPOS)}
        copia['motivos']=(fila.get('evidencia') or {}).get('faltantes') or []
        incompleto=any(fila.get(c) is None for c in CAMPOS)
        estado='pendiente' if incompleto else fila['estado_evidencia']
        copia['estado_evidencia']=estado
        if estado=='pendiente': pendientes+=1; copia['neto_usd']=None
        else:
            for campo in CAMPOS: grupos[estado][campo]+=numero(fila[campo])
            copia['neto_usd']=dinero(numero(fila['ingreso_usd'])-sum(numero(fila[c]) for c in CAMPOS[1:]))
        filas.append(copia)
    salida={'desde':desde,'hasta':hasta,'pendientes':pendientes,'movimientos':sorted(filas,key=lambda x:(x['fecha_operacion'],x['id']),reverse=True)}
    for estado,valores in grupos.items():
        salida[estado]={c:dinero(v) for c,v in valores.items()}
        salida[estado]['neto_usd']=dinero(valores['ingreso_usd']-sum(valores[c] for c in CAMPOS[1:]))
    return salida
