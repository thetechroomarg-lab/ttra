import base64,json,zlib,subprocess
from pathlib import Path
out=Path('outputs/catalogo_1575_oh1535')
files={n:(out/n).read_text() for n in ('productos.json','costos.json','proveedores.json','catalogo-manifest.json')}
payload=base64.b64encode(zlib.compress(json.dumps(files).encode())).decode()
script='''import base64,zlib,json,os,hashlib,tempfile,shutil,uuid
from pathlib import Path
files=json.loads(zlib.decompress(base64.b64decode(PAYLOAD)))
p=Path(os.environ.get("PRODUCTOS_PATH","/data/productos.json"))
paths={"productos.json":p,"costos.json":Path(os.environ.get("COSTOS_PATH",str(p.with_name("costos.json")))),"proveedores.json":Path(os.environ.get("PROVEEDORES_PATH",str(p.with_name("proveedores.json")))),"catalogo-manifest.json":Path(os.environ.get("CATALOGO_MANIFEST_PATH",str(p.with_name("catalogo-manifest.json"))))}
oldmanifest=json.loads(paths["catalogo-manifest.json"].read_text())
assert oldmanifest["generacion"]=="622e459b-19e4-454a-99c1-ae6f0fb3e16d", "El catálogo cambió; revisar antes de publicar"
manifest=json.loads(files["catalogo-manifest.json"])
assert manifest["cotizacion"]==1575
for n,k in [("productos.json","productos_sha256"),("costos.json","costos_sha256")]:assert hashlib.sha256(files[n].encode()).hexdigest()==manifest[k]
products=json.loads(files["productos.json"]);providers=json.loads(files["proveedores.json"]);costs=json.loads(files["costos.json"])
assert len(products)==537 and len({x["nombre"] for x in products})==537
for x in products:
 assert x["pesos"]==round(x["usd"]*1575) and x["transferencia"]==round(x["pesos"]/0.97)
 assert x["nombre"] in providers and x["nombre"] in costs
backup=p.parent/("backup-catalogo-"+str(uuid.uuid4()));backup.mkdir()
for n,path in paths.items():shutil.copy2(path,backup/n)
def write(path,data):
 with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as f:
  f.write(data);f.flush();os.fsync(f.fileno());temp=f.name
 os.replace(temp,path)
try:
 for n in ("productos.json","costos.json","proveedores.json","catalogo-manifest.json"):write(paths[n],files[n].encode())
 for n,path in paths.items():assert path.read_text()==files[n]
except BaseException:
 for n,path in paths.items():write(path,(backup/n).read_bytes())
 raise
print(json.dumps({"publicado":True,"productos":len(products),"cotizacion":1575,"generacion":manifest["generacion"],"respaldo":str(backup),"sha256":{n:hashlib.sha256(path.read_bytes()).hexdigest() for n,path in paths.items()}}))
'''.replace('PAYLOAD',repr(payload))
encoded=base64.b64encode(script.encode()).decode()
command="import base64; exec(base64.b64decode("+repr(encoded)+"))"
r=subprocess.run(['railway','ssh','--service','ttra','--environment','production','--','python','-c',command],capture_output=True,text=True)
print(r.stdout);print(r.stderr)
if r.returncode:raise SystemExit(r.returncode)
(out/'publicacion.log').write_text(r.stdout+r.stderr)
