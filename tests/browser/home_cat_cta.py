import sys
sys.path.insert(0,'tests/browser')
from cart_flow import api
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch()
 for width in [1440,390]:
  c=b.new_context(viewport={'width':width,'height':1000},service_workers='block');c.route('**/api/**',api);c.add_init_script("sessionStorage.setItem('ttra_portada_vista','1');Math.random=()=>.9")
  page=c.new_page();page.goto('http://127.0.0.1:8027',wait_until='domcontentloaded');page.wait_for_timeout(1500)
  page.clock.install();page.evaluate("window.anchors=new Set;new MutationObserver(()=>anchors.add(document.querySelector('#ttra-home-cat').dataset.anchor)).observe(document.querySelector('#ttra-home-cat'),{attributes:true,attributeFilter:['data-anchor']})")
  for _ in range(95):page.clock.fast_forward(1000);page.clock.run_for(50)
  page.locator('.ttra-about-photo').scroll_into_view_if_needed()
  for _ in range(5):page.clock.fast_forward(1000);page.clock.run_for(50)
  page.evaluate("document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,0)")
  for _ in range(8):page.clock.fast_forward(1000);page.clock.run_for(50)
  anchors=page.evaluate('Array.from(window.anchors)')
  assert '.ttra-catalog-cta:top:0' in anchors,anchors
  page.add_init_script('Math.random=()=>.1')
  page.reload(wait_until='domcontentloaded');page.wait_for_timeout(1600)
  assert page.locator('#ttra-home-cat').get_attribute('data-anchor')=='.ttra-hero-description:text:0'
  assert page.locator('#ttra-home-cat').evaluate('(el)=>getComputedStyle(el).pointerEvents')=='none'
  print(width,anchors,flush=True)
  page.screenshot(path=f'outputs/home-cat/{width}-cta.png');c.close()
 b.close()
