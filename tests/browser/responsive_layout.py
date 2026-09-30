import sys,json,re
from pathlib import Path
sys.path.insert(0,'.');sys.path.insert(0,'tests/browser')
from cart_flow import api
from web.slugs import slug
from playwright.sync_api import sync_playwright
OUT=Path('outputs/responsive');OUT.mkdir(parents=True,exist_ok=True)
issues=[]
scan="""() => {
 const bad=[];
 if(document.documentElement.scrollWidth>innerWidth+1)bad.push({type:'page-overflow',width:document.documentElement.scrollWidth});
 for(const el of document.querySelectorAll('h1,h2,h3,input,select,textarea,button,.ttra-catalog-cta,.ttra-product-cta,.ttra-page-brand,.rc-red-icono')) {
  const r=el.getBoundingClientRect(),s=getComputedStyle(el);
  if(!r.width||!r.height||s.visibility==='hidden'||el.closest('[hidden],.oculto,[aria-hidden="true"]'))continue;
  let clipped=false;for(let p=el.parentElement;p&&p!==document.body;p=p.parentElement){if(['auto','scroll'].includes(getComputedStyle(p).overflowX)){clipped=true;break;}}
  if(!clipped&&(r.left < -2 || r.right>innerWidth+2))bad.push({type:'element-overflow',tag:el.tagName,id:el.id,cls:el.className,text:el.textContent.slice(0,65),left:r.left,right:r.right});
  if(innerWidth<=700&&el.matches('input:not([type=checkbox]):not([type=radio]),select,textarea')&&parseFloat(s.fontSize)<16)bad.push({type:'small-field',id:el.id,size:s.fontSize});
 }
 return bad;
}"""
with sync_playwright() as p:
 b=p.chromium.launch()
 public=b.new_page();public.goto('http://127.0.0.1:8027/api/catalogo');data=json.loads(public.locator('body').inner_text());products=[v for group in data['secciones'].values() for v in group];product=max(products,key=lambda x:len(x['nombre']));public.close()
 for width,height in [(320,740),(390,844),(768,1024),(1024,768),(1440,900),(1920,1080),(844,390)]:
  c=b.new_context(viewport={'width':width,'height':height},reduced_motion='reduce',service_workers='block')
  c.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
  def route(r):
   if '/api/me'==r.request.url.split('8027')[-1] and authenticated[0]:
    r.fulfill(json={'nombre':'Cliente','apellido':'Prueba','email':'prueba@example.com','celular':'3511234567','tipo_cliente':'minorista'})
   else: api(r)
  authenticated=[False];c.route('**/api/**',route)
  c.route('**/perfil',lambda r:r.fulfill(content_type='text/html',body=Path('web/static/perfil.html').read_text()))
  page=c.new_page()
  for name,path in [('home','/'),('catalogo','/catalogo'),('login','/login'),('registro','/registro'),('perfil','/perfil'),('producto','/p/'+slug(product['nombre'])),('no-disponible','/p/no-disponible')]:
   authenticated[0]=name=='perfil'
   page.goto('http://127.0.0.1:8027'+path,wait_until='domcontentloaded');page.wait_for_timeout(250)
   if name=='registro':page.locator('#link-ir-a-registro').click() if page.locator('#form-registro').evaluate('(el)=>getComputedStyle(el).display')=='none' else None
   found=page.evaluate(scan)
   if found:issues.append({'size':[width,height],'page':name,'issues':found})
   if width in (390,1440):page.screenshot(path=str(OUT/f'{name}-{width}.png'),full_page=True)
  print(width,height,'pages scanned',flush=True)
  c.close()
 b.close()
(OUT/'issues.json').write_text(json.dumps(issues,ensure_ascii=False,indent=2))
print(json.dumps(issues,ensure_ascii=False,indent=2),flush=True)
assert not issues, 'Responsive layout issues: see outputs/responsive/issues.json'
