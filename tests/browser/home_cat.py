"""Home mascot: grounded walking, image/button anchors, scroll return and gestures."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from cart_flow import api
BASE = os.environ.get('TTRA_TEST_URL', 'http://127.0.0.1:8027')
OUT = Path(__file__).resolve().parents[2] / 'outputs' / 'home-cat'
OUT.mkdir(parents=True, exist_ok=True)


def advance(page, steps):
    # Exercise state transitions without waiting for every idle second in real time.
    for _ in range(steps):
        page.clock.fast_forward(1000)
        page.clock.run_for(50)


with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in [1440, 390]:
        ctx = browser.new_context(viewport={'width': width, 'height': 1000}, service_workers='block')
        ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1');Math.random=()=>.9")
        ctx.route('**/api/**', api)
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE, wait_until='domcontentloaded')
        page.wait_for_timeout(3500)
        cat = page.locator('#ttra-home-cat')
        assert cat.get_attribute('aria-hidden') == 'true'
        assert cat.evaluate('(el)=>el.inert && getComputedStyle(el).pointerEvents === "none"')
        page.clock.install()
        page.evaluate("""window.catStates = new Set(); window.catAnchors = new Set(); window.catHops=[]; window.catHopStart=null;
          new MutationObserver(() => {
            const cat = document.querySelector('#ttra-home-cat');
            window.catStates.add(cat.dataset.state);
            const r=cat.getBoundingClientRect();
            if(cat.dataset.state==='crouch') window.catHopStart={x:r.x,y:r.y};
            if(cat.dataset.state==='land' && window.catHopStart) {
              window.catHops.push(Math.hypot(r.x-window.catHopStart.x,r.y-window.catHopStart.y));
              window.catHopStart=null;
            }
            window.catAnchors.add(cat.dataset.anchor);
          }).observe(document.querySelector('#ttra-home-cat'), {attributes:true, attributeFilter:['data-state', 'data-anchor']});""")
        advance(page, 70)
        states = page.evaluate('Array.from(window.catStates)')
        assert all(state in states for state in ['walk', 'scratch']), states
        hops=page.evaluate('window.catHops')
        assert not hops or max(hops) <= (106 if width == 390 else 141), hops
        anchors = page.evaluate('Array.from(window.catAnchors)')
        assert all(not anchor or anchor.startswith(('.ttra-stage:', '.ttra-catalog-cta:', '.ttra-category:', '.ttra-about-photo:', '.ttra-about-copy .ttra-button:', '.ttra-hero-description:text:', '.ttra-about-copy > p:not(.ttra-eyebrow):text:')) for anchor in anchors), anchors
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.screenshot(path=str(OUT / f'{width}-playful.png'))
        # A stable image-only section isolates the existing claw/gesture checks
        # from the newly preferred adjacent text and CTA surfaces.
        page.locator('.ttra-about-copy').evaluate("el=>el.style.display='none'")
        page.locator('.ttra-about').evaluate("el=>{el.style.setProperty('translate','none','important');el.style.setProperty('transform','none','important')}")
        page.set_viewport_size({'width':width,'height':600})
        advance(page, 2)
        page.locator('.ttra-about-photo').evaluate("el=>{document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,scrollY+el.getBoundingClientRect().top-280)}")
        for _ in range(4):
            page.wait_for_timeout(200)
            page.locator('.ttra-about-photo').evaluate("el=>window.scrollBy(0,el.getBoundingClientRect().top-280)")
        page.wait_for_timeout(700)
        advance(page, 8)
        states = page.evaluate('Array.from(window.catStates)')
        assert 'peek' in states and 'drop' in states, states
        expect(cat).to_have_class('is-visible')
        assert 'ttra-about' in cat.get_attribute('data-anchor')
        for _ in range(65):
            advance(page, 1)
            if page.locator('.ttra-cat-claws').count():
                break
        marks=page.locator('.ttra-cat-claws')
        assert marks.count()>0, page.evaluate('Array.from(window.catStates)')
        assert marks.first.evaluate('(el)=>getComputedStyle(el).pointerEvents')=='none'
        mark=marks.first.element_handle()
        page.screenshot(path=str(OUT / f'{width}-claws.png'))
        advance(page, 5)
        assert not mark.evaluate('(el)=>el.isConnected')
        for _ in range(100):
            advance(page, 1)
            if cat.get_attribute('data-state') == 'poop':
                break
        expect(cat).to_have_attribute('data-state','poop')
        assert cat.locator('.cat-strain-face').evaluate('(el)=>getComputedStyle(el).display')=='block'
        page.clock.run_for(1950)
        poop=page.locator('.ttra-cat-poop')
        expect(poop).to_have_count(1)
        assert poop.locator('.cat-steam path').count()==3
        assert poop.evaluate('(el)=>getComputedStyle(el).pointerEvents')=='none'
        pellet=poop.element_handle()
        page.screenshot(path=str(OUT / f'{width}-poop.png'))
        page.clock.fast_forward(4000)
        page.clock.run_for(50)
        assert pellet.evaluate('(el)=>el.isConnected')
        page.clock.fast_forward(1050)
        page.clock.run_for(50)
        assert not pellet.evaluate('(el)=>el.isConnected')
        box = cat.bounding_box()
        assert page.evaluate('([x,y])=>!document.elementFromPoint(x,y)?.closest("#ttra-cat-layer")', [box['x']+box['width']/2, box['y']+box['height']/2])
        page.locator('#btn-carrito').click()
        expect(cat).not_to_have_class('is-visible')
        page.locator('#btn-cerrar-carrito').click()
        advance(page, 5)
        expect(cat).to_have_class('is-visible')
        page.goto(BASE + '/catalogo', wait_until='domcontentloaded')
        expect(page.locator('#ttra-home-cat')).to_have_count(0)
        assert not errors, errors
        ctx.close()
    ctx = browser.new_context(reduced_motion='reduce', viewport={'width':1440,'height':1000}, service_workers='block')
    ctx.add_init_script("sessionStorage.setItem('ttra_portada_vista','1');Math.random=()=>.9")
    ctx.route('**/api/**', api)
    page = ctx.new_page()
    page.goto(BASE + '/?intro=1', wait_until='domcontentloaded')
    cat = page.locator('#ttra-home-cat')
    expect(cat).not_to_have_class('is-visible')
    page.locator('#btn-portada-ingreso').click()
    expect(cat).to_have_class('is-visible')
    expect(cat).to_have_attribute('data-state', 'rest')
    assert cat.locator('.cat-eyes').evaluate('(el)=>getComputedStyle(el).animationName') == 'none'
    browser.close()
print('Home cat: walking, jumping, scratching, scroll return, click-through, modal pause and reduced motion passed')
