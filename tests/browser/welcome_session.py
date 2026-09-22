"""Verify welcome visibility against real session response semantics."""
import os
from playwright.sync_api import sync_playwright, expect
from cart_flow import api
BASE=os.environ.get('TTRA_TEST_URL','http://127.0.0.1:8027')
with sync_playwright() as p:
    browser=p.chromium.launch()
    context=browser.new_context(reduced_motion='reduce',service_workers='block')
    context.route('**/api/**',api)
    page=context.new_page()
    page.goto(BASE,wait_until='domcontentloaded')
    enter=page.locator('#btn-portada-ingreso')
    expect(enter).to_be_visible()
    # A reload during the welcome must also count as the same visit.
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#rc-portada-ingreso')).to_be_hidden()
    page.goto(BASE+'/catalogo',wait_until='domcontentloaded')
    page.goto(BASE,wait_until='domcontentloaded')
    expect(page.locator('#rc-portada-ingreso')).to_be_hidden()
    page.close()
    page=context.new_page()
    page.goto(BASE,wait_until='domcontentloaded')
    expect(page.locator('#btn-portada-ingreso')).to_be_visible()
    page.locator('#btn-portada-ingreso').click()
    expect(page.locator('body > header')).to_be_visible()
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#rc-portada-ingreso')).to_be_hidden()
    context.close()
    for status in [200,503]:
        context=browser.new_context(reduced_motion='reduce',service_workers='block')
        context.route('**/api/**',api)
        context.route('**/api/me',lambda route:route.fulfill(status=status,json={'nombre':'Prueba','apellido':'Usuario','tipo_cliente':'minorista'}))
        for visit in range(2):
            page=context.new_page()
            requests=[]
            page.on('request',lambda req:requests.append(req.url))
            page.goto(BASE,wait_until='domcontentloaded')
            expect(page.locator('#rc-portada-ingreso')).to_be_hidden(timeout=5000)
            expect(page.locator('body > header')).to_be_visible()
            assert not page.locator('body > header').evaluate('(el)=>el.inert')
            assert not any('/welcome-scene.js' in url for url in requests)
            page.close()
        # An explicit preview remains replayable, including for a signed-in owner.
        page=context.new_page()
        page.goto(BASE+'/?intro=1',wait_until='domcontentloaded')
        expect(page.locator('#btn-portada-ingreso')).to_be_visible()
        context.close()
    browser.close()
print('Welcome sessions: guest once per visit, new visit replay, login bypass, unavailable auth and explicit preview passed')
