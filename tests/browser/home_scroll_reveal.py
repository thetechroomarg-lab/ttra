"""Cards reveal once with blur/scale, stagger together and respect reduced motion."""
import sys
sys.path.insert(0, 'tests/browser')
from cart_flow import api
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (390, 1440):
        context = browser.new_context(viewport={'width': width, 'height': 900}, service_workers='block')
        context.route('**/api/**', api)
        context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        page = context.new_page()
        page.goto('http://127.0.0.1:8027/', wait_until='domcontentloaded')
        page.wait_for_timeout(1200)
        cards = page.locator('.ttra-category')
        assert cards.first.evaluate('(el)=>getComputedStyle(el).filter') == 'blur(10px)'
        assert cards.first.evaluate('(el)=>getComputedStyle(el).opacity') == '0'
        page.evaluate("document.documentElement.style.scrollBehavior='auto'")
        for i in range(cards.count()):
            card = cards.nth(i)
            card.evaluate('(el)=>window.scrollBy(0,el.getBoundingClientRect().top-240)')
            page.wait_for_function("Array.from(document.querySelectorAll('.ttra-category'))["+str(i)+"].classList.contains('is-visible')")
            page.wait_for_timeout(1400)
            assert card.evaluate('(el)=>getComputedStyle(el).filter') == 'none'
            assert card.evaluate('(el)=>getComputedStyle(el).opacity') == '1'
        if width == 1440:
            assert cards.evaluate_all("els=>els.some(el=>parseFloat(el.style.getPropertyValue('--reveal-delay'))>=.09)")
        page.evaluate('window.scrollTo(0,0)')
        page.wait_for_timeout(300)
        assert cards.evaluate_all("els=>els.every(el=>el.classList.contains('is-visible'))")
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        print(width, 'blur/scale, once-only reveal and layout passed', flush=True)
        context.close()
    context = browser.new_context(reduced_motion='reduce', service_workers='block')
    context.route('**/api/**', api)
    context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
    page = context.new_page()
    page.goto('http://127.0.0.1:8027/', wait_until='domcontentloaded')
    assert page.locator('.ttra-category').evaluate_all("els=>els.every(el=>getComputedStyle(el).opacity==='1'&&getComputedStyle(el).filter==='none')")
    print('Reduced motion: all cards visible', flush=True)
    browser.close()
