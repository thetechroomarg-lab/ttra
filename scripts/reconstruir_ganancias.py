"""Informe privado por defecto. --apply importa en la base configurada explícitamente."""
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv
from web.supabase_client import get_client
from web.ganancia import listar_todos
from web.ganancia_historial import preparar_historial, importar_historial


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--salida',required=True)
    parser.add_argument('--fuentes',help='JSON con costos fechados y cambios históricos documentados')
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    if args.apply and args.dry_run: parser.error('Elegí apply o dry-run')
    load_dotenv(Path(__file__).resolve().parents[1] / "web" / ".env")
    client=get_client()
    fuentes=json.loads(Path(args.fuentes).read_text()) if args.fuentes else {}
    informe=preparar_historial(listar_todos(client,'pedidos'),listar_todos(client,'tareas_entrega'),
        listar_todos(client,'pagos_cadete'),fuentes.get('costos',[]),fuentes.get('cambios',{}))
    destino=Path(args.salida); destino.parent.mkdir(parents=True,exist_ok=True)
    destino.write_text(json.dumps(informe,ensure_ascii=False,indent=2))
    destino.chmod(0o600)
    if args.apply:
        # Comprueba esquema antes de escribir: no migra ni cambia el destino.
        client.table('ganancia_movimientos').select('id').limit(1).execute()
        importar_historial(client,informe)
    print(json.dumps({k:v for k,v in informe.items() if k!='movimientos'},ensure_ascii=False))


if __name__=='__main__': main()
