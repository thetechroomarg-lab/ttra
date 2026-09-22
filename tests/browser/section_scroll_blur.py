"""Section focus follows scroll down and back up; reduced motion stays sharp."""
import os
import sys
sys.path.insert(0, 'tests/browser')
from cart_flow import api
BASE = os.environ.get('TTRA_TEST_URL', 'http://127.0.0.1:8027')
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (390, 1440):
        context = browser.new_context(viewport={'width': width, 'height': 900}, service_workers='block')
        context.route('**/api/**', api)
        context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        page = context.new_page()
        page.goto(BASE + '/', wait_until='networkidle')
        page.evaluate('document.fonts.ready')
        page.wait_for_timeout(2200)
        page.evaluate("document.documentElement.style.scrollBehavior='auto'")
        for outgoing, incoming in [('.ttra-hero','.ttra-collection'),('.ttra-collection','.ttra-about')]:
            node = page.locator(outgoing)
            anchor = page.locator(incoming).evaluate("el=>el.getBoundingClientRect().top+scrollY-(parseFloat(el.style.getPropertyValue('--section-enter-y'))||0)")
            positions = [max(0,anchor-1000),max(0,anchor-650),max(0,anchor-300)]
            def sample(y):
                page.evaluate('(y)=>window.scrollTo(0,y)',y)
                page.wait_for_timeout(250)
                return node.evaluate("el=>parseFloat(getComputedStyle(el).getPropertyValue('--section-blur'))||0")
            forward = [sample(y) for y in positions]
            reverse = [sample(y) for y in reversed(positions)]
            assert forward[-1]>forward[0],(width,outgoing,forward)
            assert all(b>=a-.03 for a,b in zip(forward,forward[1:])),forward
            assert all(b<=a+.03 for a,b in zip(reverse,reverse[1:])),reverse
            assert abs(forward[0]-reverse[-1])<.15,(forward,reverse)
            assert 'blur(' in node.evaluate('(el)=>getComputedStyle(el).filter')
            print(width,outgoing,'forward',forward,'reverse',reverse,flush=True)
        page.emulate_media(reduced_motion='reduce')
        page.wait_for_timeout(100)
        assert page.locator('.ttra-hero,.ttra-collection,.ttra-about').evaluate_all("els=>els.every(el=>!el.style.getPropertyValue('--section-blur'))")
        context.close()
    browser.close()
