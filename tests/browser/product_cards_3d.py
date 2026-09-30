"""Rotating card products preserve navigation, continuous motion and static fallbacks."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
OUT=Path(__file__).resolve().parents[2]/'outputs'/'product-cards'
OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width in (390,1440):
        context=browser.new_context(viewport={'width':width,'height':1100})
        context.route('**/api/**',api)
        context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        page=context.new_page();errors=[]
        page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(BASE+'/',wait_until='networkidle')
        first=page.locator('.ttra-category-phone');first.scroll_into_view_if_needed()
        page.wait_for_function("document.querySelector('.ttra-category-phone').classList.contains('ttra-3d-ready')",timeout=30000)
        canvas=first.locator('canvas')
        before=canvas.evaluate('(el)=>el.toDataURL()');page.wait_for_timeout(500)
        assert before!=canvas.evaluate('(el)=>el.toDataURL()'),'Product must rotate'
        assert page.locator('.ttra-product-motion').count()==0
        continuing=canvas.evaluate('(el)=>el.toDataURL()');page.wait_for_timeout(500)
        assert continuing!=canvas.evaluate('(el)=>el.toDataURL()'),'Rotation must continue without controls'
        for kind in ('phone','tablet','laptop','gaming','audio'):
            card=page.locator('.ttra-category-'+kind);card.scroll_into_view_if_needed()
            page.wait_for_function('(kind)=>document.querySelector(".ttra-category-"+kind).classList.contains("ttra-3d-ready")',arg=kind)
            assert card.locator('canvas').evaluate('(el)=>getComputedStyle(el).pointerEvents')=='none'
            assert card.locator('canvas').evaluate('(el)=>{const a=el.getContext("2d").getImageData(0,0,el.width,el.height).data;return a.some((v,i)=>i%4===3&&v>0)}')
            card.screenshot(path=str(OUT/f'{width}-{kind}.png'))
        assert page.locator('.ttra-category-brands canvas').count()==0
        assert page.locator('.ttra-brand-lens').is_visible()
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        page.locator('.ttra-category-gaming canvas').click(force=True)
        page.wait_for_url('**/catalogo?categoria=Gaming')
        assert not errors,errors
        context.close();print('PASS continuous rotation, five products and navigation',width,flush=True)
    for mode in ('reduce','failure'):
        context=browser.new_context(viewport={'width':1440,'height':1100},reduced_motion='reduce')
        context.route('**/api/**',api);context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        if mode=='failure':context.route('**/product-card-scenes.js',lambda route:route.abort())
        page=context.new_page();page.goto(BASE+'/',wait_until='networkidle');page.locator('#ttra-explorar').scroll_into_view_if_needed()
        if mode=='reduce':
            page.wait_for_function("document.querySelectorAll('.ttra-3d-ready').length===5")
            canvas=page.locator('.ttra-category-phone canvas');before=canvas.evaluate('(el)=>el.toDataURL()');page.wait_for_timeout(400);assert before==canvas.evaluate('(el)=>el.toDataURL()');assert page.locator('.ttra-product-motion').count()==0
            page.locator('.ttra-collection-grid').screenshot(path=str(OUT/'grid-static.png'))
        else:
            page.wait_for_timeout(500);assert page.locator('.ttra-mini-phone').is_visible();assert page.locator('.ttra-product-motion').count()==0
        context.close();print('PASS',mode,flush=True)
    browser.close()
