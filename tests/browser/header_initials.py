"""Account initials precede the profile icon, including persistent navigation."""
from playwright.sync_api import sync_playwright,expect
from cart_flow import api
import os
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width in (320,390,1440):
  ctx=browser.new_context(viewport={'width':width,'height':900},service_workers='block')
  ctx.route('**/api/**',api)
  signed=[True]
  ctx.route('**/api/me',lambda r:r.fulfill(status=200 if signed[0] else 401,content_type='application/json',body='{"nombre":"Vlad","apellido":"Prueba"}' if signed[0] else '{}'))
  page=ctx.new_page();page.goto(BASE+'/catalogo',wait_until='networkidle')
  def check():
   initials=page.locator('body > header .rc-perfil-nombre, body > header .ttra-site-initials')
   expect(initials).to_have_text('VP');expect(initials).to_be_visible()
   icon=page.locator('body > header .rc-perfil-icono, body > header .ttra-site-profile svg')
   a,b=initials.bounding_box(),icon.bounding_box()
   assert a['x']+a['width']<b['x']
   assert b['x']+b['width']<=width
  check();page.locator('.ttra-cat-logo-toggle').wait_for()
  page.get_by_role('link',name='Inicio',exact=True).click()
  frame=page.frame_locator('#ttra-storefront-frame')
  expect(frame.locator('#ttra-hero-title')).to_be_visible();check()
  signed[0]=False
  frame.get_by_role('button',name='Categorías',exact=True).click()
  frame.get_by_role('link',name='Todo el catálogo',exact=True).click()
  page.wait_for_url(BASE+'/catalogo')
  expect(page.locator('body > header .rc-perfil-nombre, body > header .ttra-site-initials')).to_be_hidden()
  print('PASS initials position, navigation and guest state',width,flush=True)
  ctx.close()
 browser.close()
