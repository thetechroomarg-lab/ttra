"""Cotización y snapshot de cobros. Los importes son lo que entrega el cliente."""
from decimal import Decimal, InvalidOperation, ROUND_CEILING, ROUND_HALF_UP

METODOS = {
    'usd': ('Dólar contado', 'USD', Decimal('1')),
    'usd_usa': ('Dólar banco USA', 'USD', Decimal('0.975')),
    'usdt': ('USDT', 'USDT', Decimal('0.99')),
    'ars': ('Pesos contado', 'ARS', Decimal('1')),
    'ars_transferencia': ('Transferencia pesos', 'ARS', Decimal('0.97')),
}


def numero(valor):
    try:
        n = Decimal(str(valor))
    except (InvalidOperation, ValueError):
        raise ValueError('Ingresá un importe válido.') from None
    if not n.is_finite() or n < 0 or n > Decimal('1000000000000'):
        raise ValueError('Ingresá un importe válido y positivo.')
    return n


def texto(n):
    return format(n, 'f').rstrip('0').rstrip('.') if '.' in format(n, 'f') else format(n, 'f')


def formatear(monto, moneda='USD'):
    valor = f'{numero(monto):,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    if valor.endswith(',00'):
        valor = valor[:-3]
    return f'{dict(USD="U$D", ARS="$", USDT="USDT")[moneda]} {valor}'


def opciones(total, cotizacion):
    total, cotizacion = numero(total), numero(cotizacion)
    if not cotizacion:
        raise ValueError('No hay una cotización válida para cobrar.')
    resultado = []
    for metodo, (nombre, moneda, factor) in METODOS.items():
        escala = cotizacion if moneda == 'ARS' else Decimal(1)
        monto = total * escala / factor
        if metodo in ('usd_usa', 'usdt', 'ars_transferencia'):
            monto = monto.to_integral_value(rounding=ROUND_CEILING)
        monto = monto.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        resultado.append(dict(metodo=metodo, nombre=nombre, moneda=moneda,
                              factor=texto(factor), escala=texto(escala), monto=texto(monto)))
    return resultado


def validar(total, cotizacion, entrada):
    if not isinstance(entrada, dict):
        raise ValueError('Seleccioná al menos una forma de pago.')
    seleccion = entrada.get('metodos')
    if not isinstance(seleccion, list) or not 1 <= len(seleccion) <= 5:
        raise ValueError('Seleccioná entre una y cinco formas de pago.')
    disponibles = {p['metodo']: p for p in opciones(total, cotizacion)}
    resultado, vistos = [], set()
    neto, tolerancia = Decimal(0), Decimal('0.005')
    for pago in seleccion:
        if not isinstance(pago, dict) or pago.get('metodo') not in disponibles:
            raise ValueError('Forma de pago desconocida.')
        metodo = pago['metodo']
        if metodo in vistos:
            raise ValueError('No repitas una forma de pago.')
        vistos.add(metodo)
        opcion = disponibles[metodo]
        monto = numero(opcion['monto'] if len(seleccion) == 1 else pago.get('monto'))
        if (monto <= 0 and numero(total) > 0) or monto != monto.quantize(Decimal('.01')):
            raise ValueError('Cada importe debe ser positivo y tener hasta dos decimales.')
        factor, escala = numero(opcion['factor']), numero(opcion['escala'])
        neto += monto * factor / escala
        # Los precios publicados se redondean hacia arriba a la unidad.
        if metodo != 'usd':
            tolerancia += factor / escala
        resultado.append({**opcion, 'monto': texto(monto)})
    if len(seleccion) > 1:
        diferencia = neto - numero(total)
        if diferencia < Decimal('-.005') or diferencia >= tolerancia:
            raise ValueError('Los importes no coinciden con el total. Revisá el saldo pendiente.')
    return {'version': 1, 'total_usd': texto(numero(total)),
            'cotizacion': texto(numero(cotizacion)), 'metodos': resultado}


def resumen_html(total, cotizacion):
    if total is None:
        return ''
    filas = ''.join(f'<div><dt>{p["nombre"]}</dt><dd>{formatear(p["monto"], p["moneda"])}</dd></div>'
                    for p in opciones(total, cotizacion))
    return (f'<footer class="entrega-totales"><span class="entrega-totales-titulo">Total de la entrega por forma de pago</span>'
            f'<dl>{filas}</dl><small>Cotización: {formatear(cotizacion, "ARS")} por USD · Alternativas para pagar el total</small></footer>')


def lineas_recibo(pedido):
    pago = pedido.get('recibo_pago')
    if not pago:
        return []
    lineas = ['Pago recibido']
    for p in pago['metodos']:
        lineas.append(f'{p["nombre"]}: {formatear(p["monto"], p["moneda"])}')
    if any(p['moneda'] == 'ARS' for p in pago['metodos']):
        lineas.append(f'Cotización aplicada: {formatear(pago["cotizacion"], "ARS")} por USD')
    lineas.append('Pago completo · Sin saldo pendiente')
    return lineas
