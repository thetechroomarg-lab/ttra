import sys,json
from pathlib import Path
sys.path.insert(0,'.');sys.path.insert(0,'tests/browser')
from cart_flow import api
from playwright.sync_api import sync_playwright,expect
from fastapi.testclient import TestClient
from pytest import MonkeyPatch
from tests.fakes_supabase import FakeSupabaseClient
import web.app as appmod
from datetime import date
out=Path('outputs/responsive');out.mkdir(parents=True,exist_ok=True)
with MonkeyPatch.context() as m:
 fake=FakeSupabaseClient();m.setattr(appmod,'get_client',lambda:fake);m.setattr(appmod,'ADMIN_CLIENTES_PASSWORD','responsive-fixture')
 fake.table('clientes').insert({'id':'responsive-client','nombre':'Cliente de prueba con nombre extenso','apellido':'Apellido de prueba','email':'cliente.responsive@example.com','celular':'3511234567','provincia':'Córdoba','direccion':'Avenida de prueba 1234, Córdoba','tipo_cliente':'minorista'}).execute()
 fake.table('pedidos').insert({'id':'responsive-order','cliente_id':'responsive-client','productos':['Samsung Galaxy de prueba con nombre largo 512GB'],'total_usd':1240,'fecha_entrega':date.today().isoformat(),'fecha':date.today().isoformat(),'direccion_entrega':'Avenida de prueba 1234, Córdoba'}).execute()
 client=TestClient(appmod.app,base_url='https://testserver');client.post('/admin/clientes/login',json={'password':'responsive-fixture'})
 admin_pages={path:client.get(path).text for path in ['/admin/clientes','/admin/clientes/lista','/admin/clientes/responsive-client/historial']}
issues=[]
with sync_playwright() as p:
 b=p.chromium.launch()
 for width,height in [(320,740),(390,844),(844,390),(1440,900)]:
  c=b.new_context(viewport={'width':width,'height':height},reduced_motion='reduce',service_workers='block');c.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
  def route(r):
   if r.request.url.endswith('/api/me'):r.fulfill(json={'nombre':'Cliente','apellido':'Prueba','email':'prueba@example.com','tipo_cliente':'minorista'})
   else:api(r)
  c.route('**/api/**',route)
  page=c.new_page();page.goto('http://127.0.0.1:8027/',wait_until='domcontentloaded')
  page.locator('#btn-perfil-toggle').click();page.locator('#link-ir-a-perfil').click()
  panel=page.locator('#panel-perfil');expect(panel).to_be_visible();r=panel.bounding_box()
  if r['x']<0 or r['x']+r['width']>width+1 or r['y']<0 or r['y']+r['height']>height+1:issues.append([width,height,'profile-bounds',r])
  if width in (390,1440):page.screenshot(path=str(out/f'panel-perfil-{width}.png'))
  page.locator('#btn-cerrar-panel-perfil').click()
  page.goto('http://127.0.0.1:8027/catalogo',wait_until='domcontentloaded');page.locator('.ttra-site-cart').click()
  frame=page.frame_locator('.ttra-cart-dialog iframe');expect(page.locator('.ttra-cart-dialog')).to_be_visible();expect(page.locator('.ttra-cart-loading')).to_be_hidden();expect(frame.locator('#panel-carrito')).to_be_visible()
  r=frame.locator('#panel-carrito').bounding_box()
  if r['x']<0 or r['x']+r['width']>width+1 or r['y']<0 or r['y']+r['height']>height+1:issues.append([width,height,'cart-bounds',r])
  if width in (390,1440):page.screenshot(path=str(out/f'panel-carrito-{width}.png'))
  for index,(path,html) in enumerate(admin_pages.items()):
   page.route('http://127.0.0.1:8027'+path,lambda r,request,html=html:r.fulfill(content_type='text/html',body=html))
   page.goto('http://127.0.0.1:8027'+path,wait_until='domcontentloaded')
   dimensions=page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
   if dimensions['scroll']>width+1:issues.append([width,height,path,dimensions])
   if width in (390,1440):page.screenshot(path=str(out/f'admin-{index}-{width}.png'),full_page=True)
  print(width,height,'panels and admin checked',flush=True);c.close()
 b.close()
(out/'panel-issues.json').write_text(json.dumps(issues,indent=2))
print(json.dumps(issues,indent=2),flush=True)
assert not issues, 'Panel layout issues: see outputs/responsive/panel-issues.json'
