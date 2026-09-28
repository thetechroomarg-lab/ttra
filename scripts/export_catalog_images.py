"""Export exact product/color mappings and web-sized assets, preserving source originals."""
import json
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'outputs/catalogo-imagenes'
target=ROOT/'web/static/catalog-images'
target.mkdir(parents=True,exist_ok=True)
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
(target/'index.json').write_text(json.dumps(index,ensure_ascii=False,separators=(',',':')))
print(f'{len(index)} products; {len(done)} reusable images; {sum(p.stat().st_size for p in target.iterdir())/1024/1024:.1f} MB')
