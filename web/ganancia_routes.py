"""Rutas privadas del libro USD, compartiendo la sesión del panel."""
import uuid
from datetime import date
from fastapi import APIRouter, Request, HTTPException
from web import ganancia

router=APIRouter()


def cliente(request):
    from web import app as appmod
    if not appmod._clientes_admin_activo(request):
        raise HTTPException(401,'Sesión de admin requerida')
    return appmod.get_client()


@router.get('/admin/ganancia')
def obtener(request:Request,desde:str,hasta:str):
    c=cliente(request)
    try: return ganancia.resumen(c,desde,hasta)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    except Exception as exc: raise HTTPException(503,'No se pudo consultar Ganancia. Revisá la conexión y la configuración del libro.') from exc


def datos_manual(entrada):
    if not isinstance(entrada,dict): raise ValueError('Revisá el movimiento.')
    concepto=str(entrada.get('concepto') or '').strip()
    if not 1<=len(concepto)<=300: raise ValueError('Ingresá un concepto de hasta 300 caracteres.')
    fecha=date.fromisoformat(entrada.get('fecha') or '').isoformat()
    monto=ganancia.numero(entrada.get('monto_usd'))
    if monto<=0 or monto!=monto.quantize(ganancia.Decimal('.01')): raise ValueError('Ingresá un importe positivo con hasta dos decimales.')
    tipo=entrada.get('tipo')
    if tipo not in ('ingreso','gasto'): raise ValueError('Elegí ingreso o gasto.')
    return dict(fecha_operacion=fecha,concepto=concepto,tipo=tipo,ingreso_usd=ganancia.dinero(monto if tipo=='ingreso' else 0),
                gasto_usd=ganancia.dinero(monto if tipo=='gasto' else 0),costo_usd='0.00',comision_usd='0.00')


@router.post('/admin/ganancia/manual')
async def crear(request:Request):
    c=cliente(request)
    try:
        entrada=await request.json(); datos=datos_manual(entrada)
        clave=str(uuid.UUID(str(entrada.get('clave'))))
    except (ValueError,TypeError,AttributeError) as exc: raise HTTPException(400,str(exc)) from exc
    movimiento={**datos,'fuente_tipo':'manual','fuente_id':clave,'estado_evidencia':'confirmado','evidencia':{'origen':'carga manual admin'},'version_calculo':1}
    try:
        guardado=ganancia.registrar_movimiento(c,movimiento)
        if any(str(guardado.get(k))!=str(v) for k,v in datos.items()):
            # Valores monetarios JSON pueden volver como números, comparar como Decimal.
            if any(ganancia.numero(guardado[k])!=ganancia.numero(datos[k]) for k in ganancia.CAMPOS) or any(guardado[k]!=datos[k] for k in ('concepto','fecha_operacion','tipo')):
                raise HTTPException(409,'Esta operación ya existe con otros datos. Actualizá antes de continuar.')
        return {'ok':True,'id':guardado['id']}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(503,'No se pudo confirmar el registro. Reintentá sin cambiar los datos para evitar duplicados.') from exc


@router.patch('/admin/ganancia/manual/{movimiento_id}')
async def corregir(movimiento_id:str,request:Request):
    c=cliente(request)
    try:
        uuid.UUID(movimiento_id); entrada=await request.json()
        version=entrada.get('version')
        if type(version) is not int or version<1: raise ValueError('Versión inválida.')
        cambios={'anular':True} if entrada.get('anular') is True else datos_manual(entrada)
        # El tipo queda fijo: cambiarlo requiere anular y registrar otro movimiento.
        filas=c.table(ganancia.TABLA).select('*').eq('id',movimiento_id).execute().data
        if not filas or filas[0]['fuente_tipo']!='manual': raise HTTPException(404,'Movimiento manual no encontrado')
        if 'tipo' in cambios and cambios.pop('tipo')!=filas[0]['tipo']: raise ValueError('Para cambiar ingreso por gasto, anulá y cargá otro movimiento.')
        resultado=c.rpc('editar_ganancia_manual',{'p_id':movimiento_id,'p_version':version,'p_cambios':cambios}).execute().data
        if not resultado: raise HTTPException(409,'El movimiento cambió. Actualizá antes de editar.')
        return {'ok':True}
    except HTTPException: raise
    except (ValueError,TypeError,AttributeError) as exc: raise HTTPException(400,str(exc)) from exc
    except Exception as exc: raise HTTPException(503,'No se pudo confirmar la corrección.') from exc


@router.patch('/admin/ganancia/{movimiento_id}/completar')
async def completar(movimiento_id:str,request:Request):
    c=cliente(request)
    try:
        uuid.UUID(movimiento_id); entrada=await request.json()
        version=entrada.get('version'); motivo=str(entrada.get('motivo') or '').strip()
        if type(version) is not int or version<1: raise ValueError('Versión inválida.')
        if not 5<=len(motivo)<=1000: raise ValueError('Indicá la fuente o motivo de la corrección (5 a 1000 caracteres).')
        estado=entrada.get('estado_evidencia')
        if estado not in ('estimado','confirmado'): raise ValueError('Indicá si los importes son estimados o comprobados.')
        cambios={}
        for campo in ganancia.CAMPOS:
            monto=ganancia.numero(entrada.get(campo))
            if monto<0 or monto!=monto.quantize(ganancia.Decimal('.01')): raise ValueError('Usá importes no negativos, con hasta dos decimales.')
            cambios[campo]=ganancia.dinero(monto)
        cambios.update(estado_evidencia=estado,motivo=motivo)
        filas=c.rpc('completar_ganancia',{'p_id':movimiento_id,'p_version':version,'p_cambios':cambios}).execute().data
        if not filas: raise HTTPException(409,'El movimiento cambió o no admite completar datos. Actualizá antes de continuar.')
        return {'ok':True}
    except HTTPException: raise
    except (ValueError,TypeError,AttributeError) as exc: raise HTTPException(400,str(exc)) from exc
    except Exception as exc: raise HTTPException(503,'No se pudo confirmar la corrección.') from exc
