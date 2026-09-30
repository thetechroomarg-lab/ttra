"""Welcome never restores a previously active cat; a logo click is required."""
from playwright.sync_api import sync_playwright,expect
from cart_flow import api
import os
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width,slow in [(390,False),(1440,True)]:
  ctx=browser.new_context(viewport={'width':width,'height':900},reduced_motion='reduce',service_workers='block')
  ctx.route('**/api/**',api)
  ctx.add_init_script("""localStorage.setItem('ttra_header_cat_enabled','1');sessionStorage.setItem('ttra_header_cat_state_v1',JSON.stringify({version:1,active:true,epoch:Date.now(),seed:15,x:.4,serial:1,phase:{kind:'walk',start:Date.now(),duration:50000,from:.4,to:.5},nextBathroom:Date.now()+18000,bathroom:'pee',sleepAt:Date.now()+70000,waste:[],joyAt:0}));""")
  held=[]
  if slow:ctx.route('**/header-cat.js',lambda route:held.append(route))
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/?intro=1',wait_until='domcontentloaded')
  if not slow:page.locator('.ttra-cat-logo-toggle').wait_for(state='attached')
  page.locator('#btn-portada-ingreso').click()
  if slow:
   page.wait_for_timeout(200)
   assert held
   held.pop().continue_()
  toggle=page.get_by_role('button',name='Dejar salir al gatito')
  expect(toggle).to_be_visible()
  expect(page.locator('#ttra-header-cat-portal')).to_be_hidden()
  assert page.evaluate("JSON.parse(sessionStorage.getItem('ttra_header_cat_state_v1')).phase.kind")=='off'
  assert page.evaluate("localStorage.getItem('ttra_header_cat_enabled')") is None
  toggle.click()
  expect(page.get_by_role('button',name='Volver a guardar el gatito')).to_be_visible()
  expect(page.locator('#ttra-header-cat-portal')).to_be_visible()
  assert not errors,errors
  print('PASS welcome resets saved cat; logo opens it',width,'delayed module',slow,flush=True)
  ctx.close()
 browser.close()
