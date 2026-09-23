"""Album return skips welcome once and always sends Vaivén running home."""
import os
from playwright.sync_api import sync_playwright,expect
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
with sync_playwright() as p:
 browser=p.chromium.launch()
 for signed_in,active in [(False,True),(True,True),(False,False)]:
  ctx=browser.new_context(viewport={'width':390,'height':900},reduced_motion='reduce',service_workers='block')
  ctx.route('**/api/**',api)
  if signed_in:ctx.route('**/api/me',lambda r:r.fulfill(content_type='application/json',body='{"nombre":"Vlad","apellido":"Prueba"}'))
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  access=ctx.request.post(BASE+'/vaiven/acceso').json()['access']
  page.goto(BASE+('/catalogo' if active else '/vaiven?access='+access),wait_until='networkidle')
  if active:
   page.get_by_role('button',name='Dejar salir al gatito').click();page.wait_for_timeout(2100)
   page.evaluate('(access)=>{const a=document.createElement("a");a.href="/vaiven?access="+access;a.id="test-album-link";a.textContent="Abrir álbum";document.body.append(a)}',access)
   page.locator('#test-album-link').click();page.wait_for_url('**/vaiven')
  album=page.frame_locator('#ttra-storefront-frame') if active else page
  album.get_by_role('link',name='Volver a la Tienda').click()
  page.wait_for_url(BASE+'/')
  home=page.frame_locator('#ttra-storefront-frame') if active else page
  expect(home.locator('#ttra-hero-title')).to_be_visible()
  expect(home.locator('#rc-portada-ingreso')).to_be_hidden()
  assert page.evaluate("sessionStorage.getItem('ttra_vaiven_return_once')") is None
  if active:
   expect(page.locator('#ttra-header-cat')).to_have_attribute('data-behavior','return')
   expect(page.locator('#ttra-header-cat')).to_have_attribute('data-running','true')
   expect(page.locator('#ttra-header-cat-portal')).to_be_hidden(timeout=7000)
   assert page.evaluate("localStorage.getItem('ttra_header_cat_enabled')")=='0'
  page.reload(wait_until='networkidle')
  if signed_in:expect(page.locator('#rc-portada-ingreso')).to_be_hidden()
  else:expect(page.locator('#rc-portada-ingreso')).to_be_visible()
  assert not errors,errors
  print('PASS album return and subsequent reload',signed_in,active,flush=True)
  ctx.close()
 # A guest who never opened the album also sees welcome again on normal reload.
 ctx=browser.new_context(reduced_motion='reduce',service_workers='block');ctx.route('**/api/**',api)
 page=ctx.new_page();page.goto(BASE+'/',wait_until='networkidle')
 expect(page.locator('#rc-portada-ingreso')).to_be_visible()
 page.get_by_role('button',name='Ingresar a TTRA').click()
 expect(page.locator('#rc-portada-ingreso')).to_be_hidden()
 page.reload(wait_until='networkidle');expect(page.locator('#rc-portada-ingreso')).to_be_visible()
 print('PASS ordinary guest reload without album visit',flush=True)
 browser.close()
