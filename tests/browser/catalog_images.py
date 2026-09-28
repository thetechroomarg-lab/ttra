"""Artwork integration against a release snapshot; all API calls are local fixtures."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[2]
BASE=os.environ.get('TTRA_IMAGE_TEST_URL','http://127.0.0.1:8041')
products=json.loads((ROOT/'web/productos.json').read_text())
index=json.loads((ROOT/'web/static/catalog-images/index.json').read_text())
phone=next(p for p in products if 'MacBook Neo' in p['nombre'] and len(p.get('colores',[]))>1)
reference=next(p for p in products if p['nombre'] in index and not p.get('colores'))
missing=next(p for p in products if p['nombre'] not in index)
fixtures=[phone,reference,missing]
def api(route):
 path=route.request.url.split('/api/')[-1].split('?')[0]
 if path=='me':route.fulfill(status=401,json={});return
 data={'catalogo':{'secciones':{'Celulares':fixtures},'modo_precio':'minorista'},'recomendados':{'productos':[]},'noticias':{'titulares':[]},'cotizacion':{'valor':1500}}.get(path,{})
 route.fulfill(json=data)
with sync_playwright() as p:
 b=p.chromium.launch()
 for width in [320,390,1440]:
  ctx=b.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce',service_workers='block')
  ctx.route('**/api/**',api)
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/catalogo.html');expect(page.locator('.ai-card')).to_have_count(2)
  cards=page.locator('.card');expect(cards).to_have_count(3)
  card=cards.nth(0);expect(card.locator('.ai-price')).to_have_count(5)
  assert card.locator('.ai-price strong').first.inner_text()==page.evaluate('(n)=>"USD "+Number(n).toLocaleString("es-AR")',phone['usd'])
  assert card.locator('.btn-foto').count()==4
  card.locator('select').select_option(phone['colores'][-1]);expect(card.locator('.ai-color')).to_have_text(phone['colores'][-1])
  card.locator('.btn-agregar').click();page.wait_for_timeout(600)
  cart=page.evaluate('JSON.parse(localStorage.getItem("ttra_carrito"))');assert cart[0]['nombre']==phone['nombre'] and cart[0]['color']==phone['colores'][-1]
  ref=cards.nth(1);assert ref.locator('select').count()==0;ref.locator('.btn-agregar').click();page.wait_for_timeout(600)
  assert len(page.evaluate('JSON.parse(localStorage.getItem("ttra_carrito"))'))==2
  assert not cards.nth(2).evaluate('(c)=>c.classList.contains("ai-card")')
  card.locator('.btn-compartir').click();expect(page.locator('#catalog-share')).to_be_visible();page.locator('.catalog-share-close').click()
  card.locator('.btn-comparar').click();expect(card.locator('.compare-picker')).to_be_visible();page.keyboard.press('Escape')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  box=card.locator('.ai-face').bounding_box();assert abs(box['width']-box['height'])<2
  card.scroll_into_view_if_needed();page.screenshot(path=str(ROOT/f'outputs/catalogo-imagenes/integrated-{width}.png'))
  assert not errors,errors
  print(width,'prices, color, real cart, share, comparison, fallback, no overflow PASS',flush=True);ctx.close()
 # Landing uses the same real handlers but a custom color dropdown.
 for width in [390,1440]:
  ctx=b.new_context(viewport={'width':width,'height':1000},reduced_motion='reduce',service_workers='block')
  ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
  ctx.route('**/api/**',api);page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/index.html');page.wait_for_function('typeof pintarGrilla === "function"')
  page.evaluate("ps=>{modoVista='cards';pintarGrilla(document.getElementById('productos'),ps,'');}",fixtures)
  expect(page.locator('#productos .ai-card')).to_have_count(2)
  card=page.locator('#productos .card').first
  card.locator('.dropdown-color-lista li').last.evaluate('(e)=>e.click()')
  expect(card.locator('.ai-color')).to_have_text(phone['colores'][-1])
  expect(card.locator('.btn-agregar')).to_be_enabled()
  assert card.locator('.ai-price').count()==5 and card.locator('.btn-foto').count()==4
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors
  print(width,'landing integration PASS');ctx.close()
 # Broken assets must restore the old card without losing the product.
 ctx=b.new_context(service_workers='block');ctx.route('**/api/**',api);ctx.route('**/catalog-images/*.webp',lambda r:r.abort())
 page=ctx.new_page();page.goto(BASE+'/catalogo.html');page.wait_for_timeout(1800)
 expect(page.locator('.card')).to_have_count(3);expect(page.locator('.ai-card')).to_have_count(0)
 print('broken image fallback PASS');ctx.close();b.close()
