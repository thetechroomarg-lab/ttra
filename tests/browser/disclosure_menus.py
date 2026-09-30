"""Disclosure presentation preserves native selects, positioning and menu actions."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
OUT=Path('outputs/disclosure');OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch()
 for width in (390,1440):
  context=browser.new_context(viewport={'width':width,'height':900})
  context.route('**/api/**',api);context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  for theme in ('dark','light'):
   page.goto(BASE+'/catalogo',wait_until='networkidle')
   page.evaluate('(theme)=>document.documentElement.dataset.classicTheme=theme',theme)
   profile=page.locator('.ttra-site-profile');menu=page.locator('.ttra-site-menu')
   profile.click();expect(menu).to_be_visible()
   assert menu.evaluate('(el)=>el.getAnimations().length')>0,'Profile must animate on opening'
   page.wait_for_timeout(300)
   assert menu.evaluate('(el)=>getComputedStyle(el).borderRadius')=='8px'
   page.keyboard.press('Escape');expect(menu).to_be_hidden()
   categories=page.locator('.ttra-dock-categories');panel=page.locator('#ttra-dock-categories')
   categories.click();assert panel.evaluate('(el)=>el.getAnimations().length')>0
   page.wait_for_timeout(300);page.screenshot(path=str(OUT/f'categories-{width}-{theme}.png'))
   categories.click();assert panel.evaluate('(el)=>el.getAnimations().length')>0,'Panel must animate on closing'
   expect(panel).to_be_hidden()
   select=page.locator('#marca-filter');assert select.evaluate('(el)=>getComputedStyle(el).appearance')=='base-select'
   select.click();page.wait_for_timeout(300)
   picker_width=select.evaluate('(el)=>parseFloat(getComputedStyle(el,"::picker(select)").width)')
   assert abs(picker_width-select.bounding_box()['width'])<2,(picker_width,select.bounding_box())
   page.screenshot(path=str(OUT/f'brands-{width}-{theme}.png'))
   page.get_by_role('option',name='Apple',exact=True).click();expect(select).to_have_value('Apple')
   # The native input still controls catalog filtering and color selection.
   expect(page.locator('#contador-productos')).to_have_text('2 productos')
   color=page.locator('select[id^="catalog-color-"]').first
   color.click();page.get_by_role('option',name='Azul',exact=True).click();expect(color).to_have_value('Azul')
   expect(page.locator('.card').filter(has_text='Teléfono de prueba').get_by_role('button',name='Agregar al carrito')).to_be_enabled()
   # Exercise native flip-block positioning close to the bottom edge.
   select.evaluate("el=>{el.style.position='fixed';el.style.bottom='8px';el.style.left='12px';el.style.width='240px';el.style.zIndex='100'}")
   select.click();page.wait_for_timeout(300)
   option=page.get_by_role('option',name='Apple',exact=True).bounding_box();control=select.bounding_box()
   assert option['y']+option['height']<=control['y'],(option,control)
   page.keyboard.press('Escape')
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
   page.emulate_media(reduced_motion='reduce');profile.click();expect(menu).to_be_visible()
   assert menu.evaluate('(el)=>el.getAnimations().length')==0
   page.keyboard.press('Escape');page.emulate_media(reduced_motion='no-preference')
   print('PASS disclosure controls, native selections, placement and themes',width,theme,flush=True)
  assert not errors,errors
  context.close()
 browser.close()
