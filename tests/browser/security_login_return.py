"""Untrusted login return URLs cannot execute code or leave the storefront."""
import os
from urllib.parse import quote
from playwright.sync_api import sync_playwright, expect
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8034')
with sync_playwright() as p:
 browser=p.chromium.launch()
 context=browser.new_context(service_workers='block',reduced_motion='reduce')
 context.route('**/api/me',lambda r:r.fulfill(status=401,content_type='application/json',body='{}'))
 def login(route):
  if route.request.method=='POST':route.fulfill(content_type='application/json',body='{}')
  else:route.continue_()
 context.route('**/login',login)
 page=context.new_page()
 page.goto(BASE+'/login',wait_until='domcontentloaded')
 page.wait_for_function('typeof destinoInternoSeguro === "function"')
 for target in ['javascript:void(window.__security_probe=1)','JaVaScRiPt:alert(1)','data:text/html,hi','https://example.com/','//example.com/','\\\\example.com/','https://user:pass@'+BASE.split('://')[1]+'/']:
  assert page.evaluate('(target)=>destinoInternoSeguro(target)',target) is None,target
 for target in ['/catalogo?categoria=Tablets','/perfil','/']:
  assert page.evaluate('(target)=>destinoInternoSeguro(target)',target)==BASE+target
 # Double slash in a same-origin path must remain an absolute same-origin URL.
 assert page.evaluate('(base)=>destinoInternoSeguro(base+"//example.com/")',BASE)==BASE+'//example.com/'
 page.goto(BASE+'/login?volver='+quote('javascript:void(window.__security_probe=1)',safe=''),wait_until='domcontentloaded')
 page.locator('#login-email').fill('audit@example.com');page.locator('#login-password').fill('fictitious-password')
 page.locator('#form-login button[type=submit]').click()
 page.wait_for_url(BASE+'/')
 assert not page.evaluate('Boolean(window.__security_probe)')
 print('PASS unsafe schemes/origins rejected, internal URLs preserved, actual login safely returns home',flush=True)
 browser.close()
