"""Export exact product/color mappings and web-sized assets, preserving source originals."""
import json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'outputs/catalogo-imagenes'
target=ROOT/'web/static/catalog-images'
target.mkdir(parents=True,exist_ok=True)
existing_index=json.loads((target/'index.json').read_text()) if (target/'index.json').exists() else {}
m=json.loads((source/'manifest.json').read_text())
assets={a['id']:a for a in m['assets'] if a['estado']=='generada_pendiente_revision'}
index={};done=set()
for row in m['asignaciones']:
 a=assets.get(row['asset_id'])
 if not a:continue
 name=Path(a['archivo']).stem+'.webp'
 if name not in done and not (target/name).exists():
  with Image.open(source/a['archivo']) as img:
   img.thumbnail((640,640));img.save(target/name,'WEBP',quality=82,method=0)
 done.add(name)
 index.setdefault(row['nombre'],[]).append({'color':row['color_original'],'src':'/catalog-images/'+name})
# Las fotos reales de usados se administran fuera del manifest generado. Conservarlas
# y priorizarlas para que una exportación de imágenes reutilizables no las reemplace.
for product, variants in existing_index.items():
 manual=[variant for variant in variants if variant.get('fotos')]
 if manual:
  generated=index.get(product,[])
  index[product]=manual+[variant for variant in generated if variant.get('color') not in {row.get('color') for row in manual}]
(target/'index.json').write_text(json.dumps(index,ensure_ascii=False,separators=(',',':')))
print(f'{len(index)} products; {len(done)} reusable images; {sum(p.stat().st_size for p in target.iterdir())/1024/1024:.1f} MB')
