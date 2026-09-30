"""Real rapid taps/clicks trigger bounded claws, then ordinary petting returns."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
OUT=Path('outputs/header-cat');OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width,motion in [(390,'no-preference'),(1440,'no-preference'),(320,'reduce')]:
  ctx=browser.new_context(viewport={'width':width,'height':900},has_touch=width<700,reduced_motion=motion,service_workers='block')
  ctx.route('**/api/**',api);ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/',wait_until='networkidle')
  page.get_by_role('button',name='Dejar salir al gatito').click();page.wait_for_timeout(2000)
  cat=page.locator('#ttra-header-cat')
  def touch():
   r=cat.bounding_box();x=r['x']+r['width']*.6;y=r['y']+r['height']*.7
   if width<700:page.touchscreen.tap(x,y)
   else:page.mouse.click(x,y)
  touch();expect(cat).to_have_attribute('data-state','belly')
  touch();touch();expect(cat).to_have_attribute('data-state','attack')
  expect(cat.locator('.cat-angry-face')).to_be_visible();expect(cat.locator('.cat-attack-paw')).to_be_visible()
  seq=cat.get_attribute('data-sequence');touch();assert cat.get_attribute('data-sequence')==seq
  page.wait_for_timeout(240)
  if motion=='reduce':assert cat.locator('.cat-attack-paw').evaluate('(el)=>el.getAnimations().length')==0
  else:assert cat.locator('.cat-attack-paw').evaluate('(el)=>el.getAnimations().length')>0
  page.screenshot(path=str(OUT/f'attack-{width}.png'))
  r=cat.bounding_box();h=page.locator('header').bounding_box()
  assert r['x']>=0 and r['x']+r['width']<=width and r['y']>=h['y']
  page.wait_for_timeout(2500);expect(cat).not_to_have_attribute('data-state','attack')
  touch();expect(cat).to_have_attribute('data-state','belly')
  page.get_by_role('button',name='Volver a guardar el gatito').click()
  expect(page.locator('#ttra-header-cat-portal')).to_be_hidden(timeout=7000)
  assert not errors,errors
  print('PASS rapid touch/click, claws, cooldown, petting and return',width,motion,flush=True)
  ctx.close()
 browser.close()
