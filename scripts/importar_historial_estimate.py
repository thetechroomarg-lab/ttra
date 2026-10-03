"""Import a legacy estimate CSV as private dated archive records, never customers.

Dry run by default. --apply inserts missing records only; stable IDs and exact
source comparison make retries safe and reject conflicting reimports.
"""
import argparse
import csv
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import uuid

FIELDS = ['#', 'Date', 'Customer', 'Customer Email', 'Additional Info.', 'Subtotal', 'Tax1', 'Tax2', 'Invoice Amount']


def preparar(path):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != FIELDS:
            raise ValueError('Columnas inesperadas; no se importó nada')
        rows = list(reader)
    ids = set()
    records = []
    archived_at = datetime.now(timezone.utc).isoformat()
    for line, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f'Fila incompleta: {line}')
        number = row['#']
        if not number or number in ids or not row['Customer'].strip():
            raise ValueError(f'Número duplicado o cliente vacío: {line}')
        ids.add(number)
        day = datetime.strptime(row['Date'], '%Y-%m-%d').date().isoformat()
        for field in ['Subtotal', 'Invoice Amount']:
            if not Decimal(row[field]).is_finite():
                raise ValueError(f'Importe inválido: {line}')
        records.append({
            'id': str(uuid.uuid5(uuid.NAMESPACE_URL, 'ttra:legacy:estimate:' + number)),
            'fecha_entrega': day,
            'titulo': f'Histórico importado #{number}',
            'cliente_id': None,
            'cliente_nombre': row['Customer'],
            'asignado_a': None,
            'completada_en': archived_at,
            'nota': json.dumps({'tipo': 'historial_importado', 'version': 1,
                'fuente': 'estimate.csv', 'fuente_sha256': digest, 'fila_original': line,
                'moneda': None, 'datos_originales': row}, ensure_ascii=False),
        })
    return digest, records


def verificar(actual, esperado):
    assert actual['fecha_entrega'] == esperado['fecha_entrega']
    assert actual['cliente_id'] is None and actual.get('asignado_a') is None
    assert actual.get('completada_en') and not actual.get('borrado_en')
    assert actual['cliente_nombre'] == esperado['cliente_nombre']
    actual_nota = json.loads(actual['nota'])
    esperado_nota = json.loads(esperado['nota'])
    for campo in ['tipo', 'version', 'fuente', 'fuente_sha256', 'fila_original', 'datos_originales']:
        assert actual_nota[campo] == esperado_nota[campo]


def importar(client, records, apply=False):
    pending = []
    for start in range(0, len(records), 100):
        chunk = records[start:start+100]
        existing = client.table('tareas_entrega').select('*').in_('id', [r['id'] for r in chunk]).execute().data
        by_id = {r['id']:r for r in existing}
        for record in chunk:
            if record['id'] in by_id:
                verificar(by_id[record['id']], record)
            else:
                pending.append(record)
    if apply:
        for start in range(0, len(pending), 100):
            client.table('tareas_entrega').insert(pending[start:start+100]).execute()
        # Re-read every record, not only the write acknowledgement.
        for start in range(0, len(records), 100):
            chunk = records[start:start+100]
            existing = client.table('tareas_entrega').select('*').in_('id', [r['id'] for r in chunk]).execute().data
            by_id = {r['id']:r for r in existing}
            assert len(by_id) == len(chunk)
            for record in chunk:
                verificar(by_id[record['id']], record)
    return {'registros':len(records), 'existentes':len(records)-len(pending),
            'insertados':len(pending) if apply else 0, 'pendientes':0 if apply else len(pending),
            'verificado':apply, 'clientes_creados':0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('csv', type=Path)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    digest, records = preparar(args.csv)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / 'web' / '.env')
    from web.supabase_client import get_client
    client = get_client()
    before = client.table('clientes').select('id', count='exact', head=True).execute().count
    result = importar(client, records, apply=args.apply)
    after = client.table('clientes').select('id', count='exact', head=True).execute().count
    result.update({'fuente_sha256':digest, 'clientes_antes':before, 'clientes_despues':after,
        'fecha_min':min(r['fecha_entrega'] for r in records), 'fecha_max':max(r['fecha_entrega'] for r in records)})
    args.report.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    main()
