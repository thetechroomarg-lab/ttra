"""Every part of the brand toggles the cat; only dock Home navigates home."""
import os
from playwright.sync_api import sync_playwright,expect
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width in (390,1440):
  ctx=browser.new_context(viewport={'width':width,'height':900},has_touch=width<700,service_workers='block')
  ctx.route('**/api/**',api);ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
  page=ctx.new_page();page.goto(BASE+'/catalogo',wait_until='networkidle')
  def touch_logo(xf,yf):
   r=page.locator('.ttra-page-brand').bounding_box();x=r['x']+r['width']*xf;y=r['y']+r['height']*yf
   if width<700:page.touchscreen.tap(x,y)
   else:page.mouse.click(x,y)
  # Upper letters, far away from the former red-dot target.
  touch_logo(.2,.12)
  expect(page.get_by_role('button',name='Volver a guardar el gatito')).to_be_visible()
  assert page.url==BASE+'/catalogo'
  page.wait_for_timeout(2100)
  touch_logo(.3,.85)
  expect(page.locator('#ttra-header-cat-portal')).to_be_hidden(timeout=7000)
  assert page.url==BASE+'/catalogo'
  brand=page.locator('.ttra-page-brand');assert brand.get_attribute('href') is None
  toggle=page.locator('.ttra-cat-logo-toggle')
  r=toggle.bounding_box();b=brand.bounding_box()
  assert abs(r['width']-b['width'])<1 and abs(r['height']-b['height'])<1
  toggle.focus();page.keyboard.press('Enter');page.wait_for_timeout(2100)
  expect(toggle).to_have_attribute('aria-pressed','true')
  page.locator('.ttra-dock-home').click();page.wait_for_url(BASE+'/')
  home=page.frame_locator('#ttra-storefront-frame');expect(home.locator('#ttra-hero-title')).to_be_visible()
  page.get_by_role('button',name='Volver a guardar el gatito').click(position={'x':15,'y':15})
  expect(page.locator('#ttra-header-cat-portal')).to_be_hidden(timeout=7000)
  print('PASS complete logo toggle, keyboard, persistent navigation and dock home',width,flush=True)
  ctx.close()
 browser.close()
