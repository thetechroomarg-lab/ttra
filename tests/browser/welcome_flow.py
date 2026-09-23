"""TTRA_TEST_URL=http://127.0.0.1:8026 python tests/browser/welcome_flow.py"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from cart_flow import api

BASE = os.environ.get('TTRA_TEST_URL', 'http://127.0.0.1:8026')
OUT = Path(__file__).resolve().parents[2] / 'outputs' / 'welcome'

with sync_playwright() as p:
    browser = p.chromium.launch()
    OUT.mkdir(parents=True, exist_ok=True)
    for width in [1440, 390]:
        context = browser.new_context(viewport={'width': width, 'height': 900}, service_workers='block')
        context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        context.route('**/api/**', api)
        context.add_init_script("""window.introPhases = new Set();
          new MutationObserver(() => {
            const phase = document.querySelector('#rc-portada-ingreso')?.dataset.phase;
            if (phase) window.introPhases.add(phase);
          }).observe(document, {subtree:true, attributes:true, attributeFilter:['data-phase']});""")
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE + '/?intro=1', wait_until='domcontentloaded')
        intro = page.locator('#rc-portada-ingreso')
        expect(intro.locator('canvas')).to_be_visible(timeout=15000)
        assert intro.locator('.ttra-intro-signature, .ttra-intro-skip').count() == 0
        expect(page.locator('body > header')).to_be_hidden()
        assert page.locator('body > header').evaluate('(el) => el.inert')
        enter = page.locator('#btn-portada-ingreso')
        expect(enter).to_be_visible(timeout=20000)
        assert intro.get_attribute('data-fallback') is None
        phases = page.evaluate('Array.from(window.introPhases)')
        assert all(phase in phases for phase in ['spin', 'freeze', 'welcome', 'ready']), phases
        assert enter.evaluate('(el)=>getComputedStyle(el).outlineStyle') == 'none'
        style = enter.evaluate('(el) => { const s = getComputedStyle(el); return [s.backgroundColor, s.fontStyle, s.fontWeight, s.borderTopWidth]; }')
        assert style == ['rgba(0, 0, 0, 0)', 'normal', '800', '0px'], style
        assert enter.inner_text() == 'ENTRAR'
        brand = page.locator('.rc-logo-linea').first
        for prop in ['fontFamily', 'fontWeight', 'fontStyle']:
            assert page.locator('.ttra-intro-title strong').evaluate('(el, prop) => getComputedStyle(el)[prop]', prop) == brand.evaluate('(el, prop) => getComputedStyle(el)[prop]', prop)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / f'{width}-ready.png'))
        enter.click()
        expect(intro).to_be_hidden()
        expect(page.locator('body > header')).to_be_visible()
        assert not page.locator('body > header').evaluate('(el) => el.inert')
        assert page.locator('#rc-portada-ingreso canvas').count() == 0
        assert 'intro=' not in page.url
        page.reload()
        expect(intro).to_be_visible()
        assert not errors, errors
        context.close()
    for mode in ['reduce', 'failure', 'escape']:
        context = browser.new_context(reduced_motion='reduce' if mode == 'reduce' else 'no-preference', service_workers='block')
        context.route('**/api/**', api)
        if mode == 'failure':
            context.route('**/welcome-scene.js', lambda route: route.abort())
        context.add_init_script("""window.introPhases = new Set();
          new MutationObserver(() => {
            const phase = document.querySelector('#rc-portada-ingreso')?.dataset.phase;
            if (phase) window.introPhases.add(phase);
          }).observe(document, {subtree:true, attributes:true, attributeFilter:['data-phase']});""")
        page = context.new_page()
        page.goto(BASE + '/?intro=1', wait_until='domcontentloaded')
        if mode == 'escape':
            page.keyboard.press('Escape')
        expect(page.locator('#btn-portada-ingreso')).to_be_visible()
        page.locator('#btn-portada-ingreso').click()
        expect(page.locator('body > header')).to_be_visible()
        context.close()
    browser.close()
print('Welcome: desktop, mobile, session, reduced motion, failure and keyboard escape passed')
