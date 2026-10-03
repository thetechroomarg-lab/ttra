"""Private legacy records archived without customer accounts or new receipts.

Uses the existing free-name archive storage. completada_en is the archive
instant, not a claimed delivery date. fecha_entrega holds the source Date.
"""
import html
import json
from decimal import Decimal, ROUND_HALF_UP


def datos_importados(fila):
    try:
        data = json.loads(fila.get('nota') or '')
    except (ValueError, TypeError):
        return None
    if isinstance(data, dict) and data.get('tipo') == 'historial_importado' and data.get('version') == 1:
        raw = data.get('datos_originales')
        if isinstance(raw, dict):
            return raw
    return None


def normalizar_moneda(nota, cotizacion):
    cotizacion = Decimal(str(cotizacion))
    if not cotizacion.is_finite() or cotizacion <= 0:
        raise ValueError("Cotización inválida")
    raw = nota['datos_originales']
    pesos = Decimal(raw['Invoice Amount']) > Decimal('10000')
    divisor = cotizacion if pesos else Decimal('1')
    def usd(value):
        return str((Decimal(value) / divisor).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
    return {**nota, 'moneda': 'USD', 'moneda_original': 'ARS' if pesos else 'USD',
            'cotizacion_ars_usd': str(cotizacion), 'umbral_ars': '10000',
            'criterio_moneda': 'Invoice Amount > 10000 = ARS; resto USD',
            'subtotal_usd': usd(raw['Subtotal']), 'total_usd': usd(raw['Invoice Amount'])}


def tarjeta_importada(fila):
    raw = datos_importados(fila)
    if raw is None:
        return None
    esc = lambda value: html.escape(str(value or ''), quote=True)
    fields = ''.join(f'<dt>{esc(k)}</dt><dd>{esc(v) or "—"}</dd>' for k, v in raw.items())
    search = esc(' '.join(str(v) for v in raw.values()).lower())
    nota = json.loads(fila['nota'])
    importes = f'Subtotal: {esc(raw.get("Subtotal"))} · Total: {esc(raw.get("Invoice Amount"))}'
    estado = 'Moneda no informada'
    if nota.get('moneda') == 'USD':
        importes = f'Subtotal: USD {esc(nota["subtotal_usd"])} · Total: USD {esc(nota["total_usd"])}'
        estado = (f'Convertido de ARS a USD a {esc(nota["cotizacion_ars_usd"])} ARS/USD'
                  if nota.get('moneda_original') == 'ARS' else 'Importe original en USD')
    return (
        f'<div class="pedido-historico" data-busqueda-historial="{search}">'
        f'<strong>{esc(raw.get("Customer"))}</strong> · Histórico importado #{esc(raw.get("#"))}'
        f'<br>Fecha original: {esc(raw.get("Date"))}'
        f'<br>{importes}'
        f'<br><span class="estado-recibo">{estado} · Sin comprobante adjunto en el CSV</span>'
        f'<details><summary>Datos originales</summary><dl>{fields}</dl></details></div>'
    )
