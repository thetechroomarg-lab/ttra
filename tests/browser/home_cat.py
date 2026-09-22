"""Visual and interaction checks for the home-only decorative cat."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8026')
OUT=Path(__file__).resolve().parents[2]/'outputs'/'home-cat'
OUT.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width in [1440,390]:
        ctx=browser.new_context(viewport={'width':width,'height':1000})
        ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        ctx.route('**/api/**',api)
        page=ctx.new_page()
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto(BASE,wait_until='domcontentloaded')
        cat=page.locator('#ttra-home-cat')
        expect(cat).to_have_class('is-visible',timeout=7000)
        assert cat.get_attribute('aria-hidden')=='true'
        assert cat.evaluate('(el)=>el.inert && getComputedStyle(el).pointerEvents === "none"')
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT/f'{width}-rest.png'))
        anchor=cat.get_attribute('data-anchor')
        expect(cat).to_have_attribute('data-state','jump',timeout=14000)
        page.wait_for_timeout(230)
        page.screenshot(path=str(OUT/f'{width}-jump.png'))
        expect(cat).to_have_attribute('data-state','land',timeout=3000)
        expect(cat).not_to_have_attribute('data-anchor',anchor)
        box=cat.bounding_box()
        assert page.evaluate('([x,y])=>!document.elementFromPoint(x,y)?.closest("#ttra-home-cat")',[box['x']+box['width']/2,box['y']+box['height']/2])
        page.locator('#btn-carrito').click()
        expect(cat).not_to_have_class('is-visible')
        page.locator('#btn-cerrar-carrito').click()
        expect(cat).to_have_class('is-visible',timeout=5000)
        page.locator('.ttra-about-photo').scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.goto(BASE+'/catalogo',wait_until='domcontentloaded')
        expect(page.locator('#ttra-home-cat')).to_have_count(0)
        assert not errors,errors
        ctx.close()
    ctx=browser.new_context(reduced_motion='reduce')
    ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
    ctx.route('**/api/**',api)
    page=ctx.new_page()
    page.goto(BASE+'/?intro=1',wait_until='domcontentloaded')
    cat=page.locator('#ttra-home-cat')
    expect(cat).not_to_have_class('is-visible')
    page.locator('#btn-portada-ingreso').click()
    expect(cat).to_have_class('is-visible')
    page.wait_for_timeout(4000)
    expect(cat).to_have_attribute('data-state','rest')
    browser.close()
print('Home cat: real jumps, click-through, cart pause, home-only and reduced motion passed')
