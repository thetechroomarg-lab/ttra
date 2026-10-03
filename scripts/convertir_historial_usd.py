"""Normalize the authorized legacy import, preserving every original field."""
import argparse
import json
from pathlib import Path
from decimal import Decimal
from scripts.importar_historial_estimate import preparar, verificar
from web.historial_importado import normalizar_moneda


def main():
    p=argparse.ArgumentParser()
    p.add_argument('csv',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1]/'web/.env')
    from web.supabase_client import get_client
    c=get_client()
    rate=Decimal('1575')
    digest,expected=preparar(args.csv)
    before=[]
    for start in range(0,len(expected),100):
        group=expected[start:start+100]
        actual=c.table('tareas_entrega').select('*').in_('id',[r['id'] for r in group]).execute().data
        byid={r['id']:r for r in actual}
        for item in group:
            verificar(byid[item['id']],item)
            before.append(byid[item['id']])
    args.output.mkdir(parents=True,exist_ok=True)
    backup=args.output/'respaldo-antes-conversion-usd.json'
    if not backup.exists(): backup.write_text(json.dumps(before,ensure_ascii=False,indent=2))
    updated=[]
    counts={'ARS':0,'USD':0}
    for record in before:
        nota=normalizar_moneda(json.loads(record['nota']),rate)
        counts[nota['moneda_original']]+=1
        updated.append({**record,'nota':json.dumps(nota,ensure_ascii=False)})
    changed=[r for r,old in zip(updated,before) if json.loads(r['nota'])!=json.loads(old['nota'])]
    if args.apply:
        for start in range(0,len(changed),100):
            c.table('tareas_entrega').upsert(changed[start:start+100],on_conflict='id').execute()
        for start in range(0,len(updated),100):
            group=updated[start:start+100]
            actual=c.table('tareas_entrega').select('*').in_('id',[r['id'] for r in group]).execute().data
            byid={r['id']:r for r in actual}
            for record in group:
                saved=byid[record['id']]
                assert json.loads(saved['nota'])==json.loads(record['nota'])
                for field in ['fecha_entrega','cliente_id','cliente_nombre','asignado_a','completada_en','titulo']:
                    assert saved[field]==record[field]
    report={'registros':len(updated),'convertidos_desde_ars':counts['ARS'],'originalmente_usd':counts['USD'],
            'cotizacion_ars_usd':str(rate),'umbral_ars':'mayor a 10000','actualizados':len(changed) if args.apply else 0,
            'pendientes':0 if args.apply else len(changed),'verificado':args.apply,'fuente_sha256':digest}
    (args.output/('resultado-conversion-usd.json' if args.apply else 'preflight-usd.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__': main()
