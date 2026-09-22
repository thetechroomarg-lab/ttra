import sys
sys.path.insert(0,'tests/browser')
from cart_flow import api
from playwright.sync_api import sync_playwright,expect
with sync_playwright() as p:
 b=p.chromium.launch()
 for width in [320,390,1440]:
  c=b.new_context(viewport={'width':width,'height':850},service_workers='block');c.route('**/api/**',api);c.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
  page=c.new_page()
  for path in ['/','/catalogo']:
   page.goto('http://127.0.0.1:8027'+path,wait_until='domcontentloaded')
   trigger=page.locator('#btn-perfil-toggle' if path=='/' else '.ttra-site-profile')
   menu=page.locator('#rc-perfil-dropdown' if path=='/' else '.ttra-site-menu')
   trigger.click();expect(menu).to_have_attribute('data-placement','bottom')
   r=trigger.bounding_box();m=menu.bounding_box();assert m['y']>=r['y']+r['height'] and m['x']>=0 and m['x']+m['width']<=width
   if width<700:assert menu.locator('a').first.evaluate('(el)=>parseFloat(getComputedStyle(el).fontSize)')>=16
   page.keyboard.press('Escape');expect(menu).to_be_hidden()
  page.goto('http://127.0.0.1:8027/?producto=Tel%C3%A9fono%20de%20prueba',wait_until='domcontentloaded')
  card=page.locator('#productos .card').first;expect(card).to_be_visible()
  # Move a real card near the viewport bottom to test actual fallback geometry.
  card.evaluate("el=>{el.style.position='fixed';el.style.top='auto';el.style.bottom='12px';el.style.left='12px';el.style.width='280px';el.style.zIndex='50';el.classList.add('expandida')}")
  button=card.locator('.dropdown-color-boton');button.click()
  button.evaluate("el=>{const r=el.getBoundingClientRect();el.style.transform=`translateY(${innerHeight-24-r.bottom}px)`;window.dispatchEvent(new Event('resize'))}")
  menu=card.locator('.dropdown-color-lista');expect(menu).to_have_attribute('data-placement','top')
  r=button.bounding_box();m=menu.bounding_box();assert m['y']+m['height']<=r['y']+1,(r,m)
  if width<700:
   assert abs(m['width']-r['width'])<1,(r,m)
   assert menu.locator('li').first.evaluate('(el)=>parseFloat(getComputedStyle(el).fontSize)')>=16
  menu.get_by_role('option',name='Azul').click();expect(button).to_have_text('Azul');expect(menu).to_be_hidden()
  print(width,'PASS',flush=True);c.close()
 b.close()
