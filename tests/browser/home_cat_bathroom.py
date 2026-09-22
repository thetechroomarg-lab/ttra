"""Bathroom cadence, effect cleanup and scroll-directed re-entry."""
import sys
sys.path.insert(0, 'tests/browser')
from cart_flow import api
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (1440, 390):
        context = browser.new_context(viewport={'width': width, 'height': 800}, service_workers='block')
        context.route('**/api/**', api)
        context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1');Math.random=()=>.9")
        page = context.new_page()
        page.goto('http://127.0.0.1:8027', wait_until='domcontentloaded')
        page.wait_for_timeout(1600)
        page.clock.install()
        page.evaluate("""window.catEvents=[];new MutationObserver(()=>{
          const el=document.querySelector('#ttra-home-cat');
          catEvents.push({state:el.dataset.state,side:el.dataset.entrySide,time:performance.now()});
        }).observe(document.querySelector('#ttra-home-cat'),{attributes:true,attributeFilter:['data-state']})""")
        def advance(n):
            for _ in range(n):
                page.clock.fast_forward(1000)
                page.clock.run_for(50)
        for kind in ('poop', 'pee', 'poop'):
            for _ in range(40):
                advance(1)
                if page.locator('#ttra-home-cat').get_attribute('data-state') == kind:
                    break
            else:
                raise AssertionError((width, kind, page.evaluate('catEvents')))
            page.clock.run_for(2000)
            effect = page.locator('.ttra-cat-' + kind)
            assert effect.count() == 1, (width, kind)
            assert effect.evaluate('(el)=>getComputedStyle(el).pointerEvents') == 'none'
            page.clock.run_for(5100)
            assert effect.count() == 0
        times = page.evaluate("catEvents.filter(e=>['poop','pee'].includes(e.state)).map(e=>e.time)")
        assert len(times) == 3, times
        assert all(27000 <= b-a <= 33000 for a,b in zip(times,times[1:])), times
        page.evaluate("document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,document.querySelector('.ttra-about-photo').getBoundingClientRect().top+scrollY-300)")
        page.wait_for_timeout(500)
        advance(7)
        assert page.evaluate("catEvents.some(e=>e.state==='peek'&&e.side==='top')"), page.evaluate('catEvents')
        page.evaluate('window.scrollTo(0,0)')
        page.wait_for_timeout(500)
        advance(8)
        assert page.evaluate("catEvents.some(e=>e.state==='peek'&&e.side==='bottom')"), page.evaluate('catEvents')
        assert page.locator('#ttra-home-cat').get_attribute('data-anchor')
        assert page.locator('#ttra-home-cat').evaluate('(el)=>el.classList.contains("is-visible")')
        print(width, 'bathroom intervals and both entry directions passed', times, flush=True)
        context.close()
    browser.close()
