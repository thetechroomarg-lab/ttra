import json,re,sys
from pathlib import Path
from collections import Counter
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
from web.productos import escribir_productos_json,_excluido
from consolidate import consolidar
stage=Path(__file__).parent
out=root/'outputs/catalogo_1575_oh1535';out.mkdir(parents=True,exist_ok=True)
master={'items':[],'filtrados':[],'dudas_precio':[]};changes=[]
for supplier in ('az','fr','nexi','oh','ba','em','va'):
 d=json.loads((stage/f'entrada_{supplier}.json').read_text())
 for item in d['items']:
  before=item['nombre'];name=before
  # Expand an unambiguous supplier abbreviation so accessory pricing applies.
  name=re.sub(r'^CARG ORIGINAL ', 'Cargador Original ', name,flags=re.I)
  # Formatting only: virtual RAM annotations are not physical configurations.
  name=re.sub(r'\s*\(\d+\s*(?:GB)?\s*\+\s*\d+\s*(?:GB)?\)', '',name,flags=re.I)
  name=re.sub(r'\s*Caja Indica \d+GB\+\d+GB','',name,flags=re.I)
  name=re.sub(r'\bREDMI(?=\d)','REDMI ',name,flags=re.I)
  name=re.sub(r'\bS25FE\b','S25 FE',name,flags=re.I)
  name=re.sub(r'\bAPPLEWATCH\b','Apple Watch',name,flags=re.I)
  name=re.sub(r'\s+',' ',name).strip()
  item['nombre']=name
  if before!=name:changes.append({'proveedor':supplier,'antes':before,'despues':name})
  if _excluido(name):
   master['filtrados'].append({'nombre':name,'proveedor':supplier,'motivo':'exclusión vigente del catálogo'});continue
  assert isinstance(item['costo'],(int,float)) and item['costo']>0
  master['items'].append(item)
 master['filtrados']+=d['filtrados'];master['dudas_precio']+=d['dudas_precio']
# Merge only identical product names/costs within a supplier, preserving options.
merged={}
for item in master['items']:
 key=(item['proveedor'],item['nombre'].casefold(),item['costo'])
 if key not in merged:merged[key]=item
 else:
  dest=merged[key]
  for color in item.get('colores',[]):
   if color not in dest.setdefault('colores',[]):dest['colores'].append(color)
master['items']=list(merged.values())
(out/'entrada_master.json').write_text(json.dumps(master,ensure_ascii=False,indent=2))
(out/'normalizaciones.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2))
products=escribir_productos_json(master['items'],1575,out/'productos.json')
providers=json.loads((out/'proveedores.json').read_text());costs=json.loads((out/'costos.json').read_text())
assert len({x['nombre'] for x in products})==len(products),'duplicate output names'
for item in products:
 assert item['pesos']==round(item['usd']*1575)
 assert item['transferencia']==round(item['pesos']/0.97)
 assert item['nombre'] in providers and item['nombre'] in costs
 assert not any(k in item for k in ('costo','proveedor'))
 if 'iphone' in item['nombre'].lower() and 'usad' in item['nombre'].lower():
  assert item.get('colores') and all('%' in v for v in item['colores'])
assert all(abs(x['costo_usd']*1535-x['costo_ars'])<1e-6 for x in json.loads((stage/'oh_conversiones.json').read_text()))
for model,cost in [('iPhone 17 256GB',960),('iPhone 17 Pro 256GB',1190),('iPhone 17 Pro Max 256GB',1260)]:
 assert providers[model]=='nexi' and costs[model]==cost
summary={'entradas':len(master['items']),'productos':len(products),'filtrados':len(master['filtrados']),'dudas_precio':master['dudas_precio'],'por_proveedor_elegido':dict(Counter(providers.values())),'cotizacion':1575,'cotizacion_oh':1535}
(out/'resumen.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False))
