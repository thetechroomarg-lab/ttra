"""TTRA_TEST_URL=http://127.0.0.1:8026 python tests/browser/welcome_flow.py"""
import os
from playwright.sync_api import sync_playwright, expect
from cart_flow import api

BASE = os.environ.get('TTRA_TEST_URL', 'http://127.0.0.1:8026')
WATCH = """window.introPhases = [];
  new MutationObserver(() => {
    const phase = document.querySelector('#rc-portada-ingreso')?.dataset.phase;
    if (phase && !window.introPhases.includes(phase)) window.introPhases.push(phase);
  }).observe(document, {subtree:true, attributes:true, attributeFilter:['data-phase']});"""

with sync_playwright() as p:
    # Con GPU: en render por software los cuadros tardan tanto que la línea de tiempo saltea fases.
    browser = p.chromium.launch(args=['--use-angle=metal', '--enable-gpu', '--ignore-gpu-blocklist'])
    for width, height in [(1440, 900), (390, 844), (844, 390)]:
        context = browser.new_context(viewport={'width': width, 'height': height}, service_workers='block')
        context.route('**/api/**', api)
        context.add_init_script(WATCH)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE + '/?intro=1', wait_until='domcontentloaded')
        intro = page.locator('#rc-portada-ingreso')
        expect(intro.locator('canvas')).to_be_visible(timeout=15000)
        expect(page.locator('body > header')).to_be_hidden()
        assert intro.locator('audio, video').count() == 0
        expect(intro).to_be_hidden(timeout=20000)
        phases = page.evaluate('window.introPhases')
        assert [ph for ph in phases if ph != 'loading'] == ['office', 'enter', 'logo', 'lean', 'wave', 'hold', 'fade', 'ready', 'leaving'], phases
        assert intro.get_attribute('data-fallback') is None
        expect(page.locator('body > header')).to_be_visible()
        assert page.evaluate('[...document.body.children].every(el => !el.inert)')
        assert page.locator('#rc-portada-ingreso canvas').count() == 0
        assert 'intro=' not in page.url
        assert not errors, errors
        context.close()
    for mode in ['reduce', 'failure', 'escape']:
        context = browser.new_context(reduced_motion='reduce' if mode == 'reduce' else 'no-preference', service_workers='block')
        context.route('**/api/**', api)
        if mode == 'failure':
            context.route('**/welcome-scene.js', lambda route: route.abort())
        page = context.new_page()
        page.goto(BASE + '/?intro=1', wait_until='domcontentloaded')
        if mode == 'escape':
            expect(page.locator('#rc-portada-ingreso canvas')).to_be_visible(timeout=15000)
            page.keyboard.press('Escape')
        expect(page.locator('#rc-portada-ingreso')).to_be_hidden(timeout=5000)
        expect(page.locator('body > header')).to_be_visible()
        assert page.locator('#rc-portada-ingreso canvas').count() == 0
        context.close()
    browser.close()
print('Welcome: desktop, mobile portrait/landscape, reduced motion, failure and keyboard escape passed')
