"""The opt-in mascot persists across storefront documents and stays in the header."""
import os
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright,expect
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
OUT=Path('outputs/header-cat');OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width in (390,1440):
  ctx=browser.new_context(viewport={'width':width,'height':900},has_touch=width<700,service_workers='block')
  ctx.route('**/api/**',api);ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/',wait_until='networkidle')
  toggle=page.get_by_role('button',name='Dejar salir al gatito');expect(toggle).to_be_visible()
  cat=page.locator('#ttra-header-cat');expect(page.locator('#ttra-header-cat-portal')).to_be_hidden()
  page.evaluate('window.__catRoot=123;window.__catNode=document.getElementById("ttra-header-cat")')
  toggle.click();page.wait_for_timeout(550)
  assert page.locator('.ttra-cat-door').evaluate('(el)=>getComputedStyle(el).transform')!='none'
  page.wait_for_timeout(1700);expect(cat).to_be_visible()
  header=page.locator('header').bounding_box();r=cat.bounding_box()
  assert r['y']>=header['y'] and r['y']+r['height']<=header['y']+header['height']+10,(header,r)
  assert cat.evaluate('(el)=>getComputedStyle(el).pointerEvents')=='auto'
  # Real pointer/touch input must reach the cat while the surrounding header remains usable.
  r=cat.bounding_box()
  if width<700:page.touchscreen.tap(r['x']+r['width']/2,r['y']+r['height']*.7)
  else:page.mouse.click(r['x']+r['width']/2,r['y']+r['height']*.7)
  expect(cat).to_have_attribute('data-state','belly')
  expect(cat.locator('.cat-belly')).to_be_visible()
  page.wait_for_timeout(500)
  page.screenshot(path=str(OUT/f'belly-{width}.png'))
  cat.focus();page.keyboard.press('Enter');expect(cat).to_have_attribute('data-state','belly')
  page.wait_for_timeout(3200)
  expect(cat).not_to_have_attribute('data-state','belly')
  page.screenshot(path=str(OUT/f'home-{width}.png'))
  pending=[]
  def hold(route):
   if route.request.is_navigation_request() and urlparse(route.request.url).path=='/catalogo':pending.append(route)
   else:route.continue_()
  ctx.route('**/*',hold)
  page.locator('.ttra-dock-search').click()
  page.wait_for_timeout(250)
  before=cat.locator('.cat-tail').evaluate('(el)=>el.getAnimations()[0].currentTime')
  page.wait_for_timeout(600)
  after=cat.locator('.cat-tail').evaluate('(el)=>el.getAnimations()[0].currentTime')
  assert after>before+400,'Cat animation must continue while the next page loads'
  assert pending,('Internal navigation must load in the persistent host',errors,page.url,page.locator('#ttra-storefront-frame').count(),page.evaluate("sessionStorage.getItem('ttra_header_cat_state_v1')"))
  pending.pop().continue_();ctx.unroute('**/*',hold)
  page.wait_for_url('**/catalogo?buscar=1#catalog-search',timeout=30000)
  frame=page.frame_locator('#ttra-storefront-frame')
  expect(frame.locator('#catalog-search')).to_be_visible()
  assert page.evaluate('window.__catRoot===123 && window.__catNode===document.getElementById("ttra-header-cat")')
  assert frame.locator('#ttra-header-cat').count()==0
  expect(cat).to_be_visible()
  cat.focus();page.keyboard.press('Space');expect(cat).to_have_attribute('data-state','belly')
  phone=frame.locator('.card').filter(has_text='Teléfono de prueba')
  phone.get_by_label('Color').select_option('Azul');phone.get_by_role('button',name='Agregar al carrito').click()
  expect(cat).to_have_attribute('data-state','joy')
  assert cat.locator('.cat-happy-eyes').evaluate('(el)=>getComputedStyle(el).display')!='none'
  page.wait_for_timeout(1300)
  frame.locator('.ttra-site-cart').click();expect(frame.locator('.ttra-cart-dialog')).to_be_visible()
  checkout=frame.frame_locator('.ttra-cart-dialog iframe');checkout.locator('#btn-cerrar-carrito').click()
  expect(frame.locator('.ttra-cart-dialog')).to_have_count(0)
  expect(cat).to_be_visible()
  # Back/forward must use the host instead of resetting the original document.
  page.go_back();page.wait_for_url(BASE+'/')
  expect(frame.locator('#ttra-hero-title')).to_be_visible()
  page.go_forward();page.wait_for_url('**/catalogo?buscar=1#catalog-search')
  expect(frame.locator('#catalog-title')).to_be_visible()
  assert page.evaluate('window.__catRoot===123')
  page.screenshot(path=str(OUT/f'catalog-{width}.png'))
  # Account forms and their full-document redirects retain the same mascot host.
  signed_in=[False]
  def account(route):
   route.fulfill(status=200 if signed_in[0] else 401,content_type='application/json',body='{"nombre":"Vlad","apellido":"Prueba","email":"test@example.com"}' if signed_in[0] else '{}')
  def login(route):
   if route.request.method=='POST':
    signed_in[0]=True;route.fulfill(content_type='application/json',body='{}')
   else:route.continue_()
  def logout(route):
   signed_in[0]=False;route.fulfill(content_type='application/json',body='{}')
  ctx.route('**/api/me',account);ctx.route('**/login',login);ctx.route('**/logout',logout)
  frame.locator('.ttra-site-account').click()
  frame.get_by_role('link',name='Iniciar sesión',exact=True).click()
  expect(frame.locator('#login-email')).to_be_visible()
  frame.locator('#login-email').fill('test@example.com');frame.locator('#login-password').fill('test-password-123')
  frame.locator('#form-login button[type="submit"]').click()
  expect(frame.locator('#catalog-title')).to_be_visible()
  frame.locator('.ttra-site-account').click()
  expect(frame.get_by_role('link',name='Ir a perfil',exact=True)).to_be_visible()
  frame.get_by_role('button',name='Cerrar sesión',exact=True).click()
  expect(frame.locator('#ttra-hero-title')).to_be_visible()
  assert page.evaluate('window.__catRoot===123 && window.__catNode===document.getElementById("ttra-header-cat")')
  frame.get_by_role('button',name='Volver a guardar el gatito').click()
  expect(page.locator('#ttra-header-cat-portal')).to_be_hidden(timeout=7000)
  expect(frame.get_by_role('button',name='Dejar salir al gatito')).to_be_visible()
  assert page.evaluate("localStorage.getItem('ttra_header_cat_enabled')")=='0'
  assert not errors,errors
  print('PASS mascot bounds, persistent navigation, cart joy, back/forward and return',width,flush=True)
  ctx.close()
 browser.close()
