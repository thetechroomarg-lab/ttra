"""The secret album is reachable by real gestures and retains the mascot host."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
OUT=Path('outputs/vaiven');OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width,theme in [(390,'dark'),(1440,'dark'),(320,'light')]:
  ctx=browser.new_context(viewport={'width':width,'height':900},has_touch=width<700,service_workers='block')
  ctx.route('**/api/**',api)
  ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1');localStorage.setItem('ttra_classic_theme','"+theme+"')")
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/',wait_until='networkidle')
  page.get_by_role('button',name='Dejar salir al gatito').click();page.wait_for_timeout(2000)
  cat=page.locator('#ttra-header-cat');page.evaluate('window.__originalCat=document.getElementById("ttra-header-cat")')
  def discover():
   r=cat.bounding_box();x=r['x']+r['width']*.6;y=r['y']+r['height']*.7
   for i in range(10):
    if width<700:page.touchscreen.tap(x,y)
    else:page.mouse.click(x,y)
    page.wait_for_timeout(60)
    if i<9:expect(page.locator('#ttra-cat-introduction')).to_be_hidden()

  discover()
  bubble=page.locator('#ttra-cat-introduction');expect(bubble).to_be_visible()
  expect(cat).to_have_attribute('data-state','introduce')
  start=cat.bounding_box();page.wait_for_timeout(700);assert cat.bounding_box()==start
  br=bubble.bounding_box();assert br['x']>=0 and br['x']+br['width']<=width
  page.screenshot(path=str(OUT/f'bubble-{width}.png'))
  page.keyboard.press('Escape');expect(bubble).to_be_hidden()
  discover();bubble.get_by_role('link',name='Mirá, este soy yo').click()
  page.wait_for_url('**/vaiven');frame=page.frame_locator('#ttra-storefront-frame')
  expect(frame.locator('#vaiven-title')).to_be_visible()
  expect(frame.locator('header, .ttra-site-header, .ttra-dock')).to_have_count(0)
  expect(page.locator('#ttra-header-cat-portal')).to_be_hidden()
  mascot=frame.locator('#vaiven-mascot');expect(mascot.locator('svg')).to_be_visible()
  bounds=mascot.bounding_box();page.wait_for_timeout(400);assert mascot.bounding_box()==bounds
  mascot.evaluate('(el)=>el.getAnimations({subtree:true}).forEach(a=>a.currentTime=14000)')
  assert mascot.locator('.vaiven-scratch-paw').evaluate('(el)=>Number(getComputedStyle(el).opacity)')>0
  assert page.evaluate('window.__originalCat===document.getElementById("ttra-header-cat")')
  assert frame.locator('#ttra-header-cat').count()==0
  expect(frame.locator('#vaiven-album img')).to_have_count(6)
  assert frame.locator('html').evaluate('(el)=>el.scrollWidth<=innerWidth'),width
  page.screenshot(path=str(OUT/f'album-{width}-{theme}.png'))
  for photo in frame.locator('#vaiven-album img').all():
   photo.scroll_into_view_if_needed();expect(photo).to_be_visible()
   photo.evaluate('(img)=>img.decode()');assert photo.evaluate('(img)=>img.naturalWidth>0')
  back=frame.get_by_role('link',name='Volver a la Tienda');back.scroll_into_view_if_needed();page.wait_for_timeout(800)
  page.screenshot(path=str(OUT/f'goodbye-{width}.png'))
  back.click();page.wait_for_url(BASE+'/');expect(frame.locator('#ttra-hero-title')).to_be_visible()
  assert page.evaluate('window.__originalCat===document.getElementById("ttra-header-cat")')
  response=page.goto(BASE+'/vaiven',wait_until='domcontentloaded')
  assert response.status==403
  expect(page.get_by_role('heading',name='¡Tramposo! ¡Eso no se vale!')).to_be_visible()
  assert page.locator('#vaiven-album img').count()==0
  page.screenshot(path=str(OUT/f'denied-{width}.png'))
  assert not errors,errors
  print('PASS gesture, freeze, bubble, six photos, responsive story and return',width,theme,flush=True)
  ctx.close()
 browser.close()
