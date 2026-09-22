"""The shared checkout opens over the current route and restores its scroll."""
import os
import json
from playwright.sync_api import sync_playwright, expect
from cart_flow import api, PRODUCTS
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width in [1440,390]:
        ctx=browser.new_context(viewport={'width':width,'height':900},service_workers='block')
        ctx.route('**/api/**',api)
        ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        page=ctx.new_page()
        errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        for path in ['/catalogo?categoria=Celulares','/login.html','/p/no-disponible']:
            page.goto(BASE+path,wait_until='domcontentloaded')
            page.evaluate('(items)=>localStorage.setItem("ttra_carrito",JSON.stringify(items))',[dict(PRODUCTS[0],cantidad=1,color='Azul')])
            page.evaluate('window.scrollTo(0,150)')
            page.wait_for_timeout(300)
            before=page.evaluate('scrollY')
            url=page.url
            page.locator('.ttra-site-cart').evaluate('(el)=>el.click()')
            drawer=page.locator('dialog[data-ttra-cart]')
            expect(drawer).to_be_visible()
            cart=page.frame_locator('.ttra-cart-dialog iframe')
            expect(cart.locator('#panel-carrito')).to_be_visible(timeout=15000)
            expect(cart.locator('#items-carrito')).to_contain_text('Teléfono de prueba')
            assert page.url==url
            expect(page.locator('html')).to_have_class(__import__('re').compile('ttra-scroll-locked'))
            assert drawer.evaluate('(el)=>getComputedStyle(el,"::backdrop").backdropFilter')=='blur(8px)'
            cart.locator('.btn-mas').click()
            expect(page.locator('.ttra-site-count')).to_have_text('2')
            assert page.evaluate('JSON.parse(localStorage.ttra_carrito)[0].cantidad')==2
            cart.locator('#btn-cerrar-carrito').click()
            expect(drawer).to_have_count(0)
            expect(page.locator('html')).not_to_have_class(__import__('re').compile('ttra-scroll-locked'))
            page.wait_for_timeout(100)
            assert abs(page.evaluate('scrollY')-before)<2, (before,page.evaluate('scrollY'))
            assert page.url==url
            page.locator('.ttra-site-cart').click()
            expect(cart.locator('#panel-carrito')).to_be_visible()
            # Wait until the iframe has installed its close handlers and the
            # loading overlay no longer blocks real user interaction.
            expect(page.locator('.ttra-cart-loading')).to_be_hidden()
            cart.locator('#btn-cerrar-carrito').focus()
            page.keyboard.press('Escape')
            expect(drawer).to_have_count(0)
            assert page.url==url
            print(width,path,'PASS',flush=True)
        assert not errors,errors
        ctx.close()
    browser.close()
