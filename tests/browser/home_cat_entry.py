"""The mascot enters from above on direct visits and after the welcome screen."""
import sys
sys.path.insert(0, 'tests/browser')
from cart_flow import api
from playwright.sync_api import sync_playwright, expect

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (390, 1440):
        for welcome in (False, True):
            context = browser.new_context(viewport={'width': width, 'height': 950}, service_workers='block')
            context.route('**/api/**', api)
            context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
            page = context.new_page()
            page.goto('http://127.0.0.1:8027/' + ('?intro=1' if welcome else ''), wait_until='domcontentloaded')
            cat = page.locator('#ttra-home-cat')
            if welcome:
                expect(cat).not_to_have_class('is-visible')
                page.locator('#btn-portada-ingreso').click(timeout=25000)
            expect(cat).to_have_attribute('data-state', 'peek', timeout=6000)
            expect(cat).to_have_attribute('data-entry-side', 'top')
            assert cat.evaluate('(el)=>getComputedStyle(el).transitionDuration') == '0s'
            cat.evaluate("el=>{window.entryStates=[];new MutationObserver(()=>entryStates.push(el.dataset.state)).observe(el,{attributes:true,attributeFilter:['data-state']})}")
            page.wait_for_function("entryStates.includes('drop') && entryStates.includes('land')", timeout=6000)
            page.wait_for_function("Boolean(document.querySelector('#ttra-home-cat').dataset.anchor)")
            assert cat.evaluate('(el)=>getComputedStyle(el).pointerEvents') == 'none'
            print(width, 'welcome' if welcome else 'direct', 'peek → drop → land passed', flush=True)
            context.close()
    context = browser.new_context(reduced_motion='reduce', service_workers='block')
    context.route('**/api/**', api)
    context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
    page = context.new_page()
    page.goto('http://127.0.0.1:8027/', wait_until='domcontentloaded')
    expect(page.locator('#ttra-home-cat')).to_have_class('is-visible')
    expect(page.locator('#ttra-home-cat')).to_have_attribute('data-state', 'rest')
    browser.close()
