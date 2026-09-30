"""Poop -> step aside -> paw at dirt -> mound and waste fade together."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
OUT=Path('outputs/header-cat');OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width,x,theme in [(390,0,'dark'),(1440,1,'dark'),(320,.5,'light')]:
  ctx=browser.new_context(viewport={'width':width,'height':900},service_workers='block')
  ctx.route('**/api/**',api)
  ctx.add_init_script('''(()=>{const now=Date.now();sessionStorage.setItem('ttra_portada_vista','1');
  const s={version:1,active:true,epoch:now,seed:42,x:XPOS,serial:1,phase:{kind:'poop',start:now+1500,duration:2800,from:XPOS,to:XPOS,serial:1},nextBathroom:now+99999,bathroom:'pee',sleepAt:now+99999,waste:[],joyAt:0};
  sessionStorage.setItem('ttra_header_cat_state_v1',JSON.stringify(s));localStorage.setItem('ttra_classic_theme','THEME');})();'''.replace('XPOS',str(x)).replace('THEME',theme))
  page=ctx.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(BASE+'/catalogo',wait_until='domcontentloaded')
  cat=page.locator('#ttra-header-cat');expect(cat).to_have_attribute('data-state','poop')
  start=cat.bounding_box()['x']
  waste=page.locator('.ttra-header-cat-waste[data-kind="poop"]');expect(waste).to_be_visible()
  expect(cat).to_have_attribute('data-behavior','bury-walk',timeout=7000)
  expect(cat).to_have_attribute('data-state','bury')
  end=cat.bounding_box()['x'];assert abs(end-start)<=41
  if width!=320:assert abs(end-start)>5,(start,end)
  expect(waste).to_have_attribute('data-burying','true')
  first=waste.evaluate('(el)=>Number(el.style.getPropertyValue("--earth-cover"))')
  page.wait_for_timeout(2200)
  cover=waste.evaluate('(el)=>Number(el.style.getPropertyValue("--earth-cover"))');assert cover>first and cover>.8
  page.screenshot(path=str(OUT/f'burial-{width}.png'),clip={'x':0,'y':0,'width':width,'height':180})
  mound=waste.locator('.cat-earth-mound').bounding_box();account=page.locator('.ttra-header-account').bounding_box()
  assert mound['x']>=0 and mound['x']+mound['width']<=account['x'],(mound,account)
  r=cat.bounding_box();assert r['x']>=0 and r['x']+r['width']<=width
  expect(waste).to_have_count(0,timeout=5000)
  assert not errors,errors
  print('PASS step aside, digging, earth coverage and cleanup',width,theme,flush=True)
  ctx.close()
 browser.close()
