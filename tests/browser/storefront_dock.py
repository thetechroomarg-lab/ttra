"""Shared dock replaces footer navigation and preserves account/cart flows."""
import os
BASE = os.environ.get('TTRA_TEST_URL', 'http://127.0.0.1:8027')
from playwright.sync_api import sync_playwright
from cart_flow import api

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (320, 390, 1440):
        context = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
        context.route('**/api/**', api)
        context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        for path in ('/', '/catalogo'):
            page.goto(BASE + path, wait_until='networkidle')
            dock = page.locator('.ttra-dock')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert page.locator('script[src="/home-cat.js"]').count() == 0
            assert page.locator('header .ttra-site-rate').is_visible() == (path != '/')
            assert page.locator('body > footer').count() == 0
            assert dock.is_visible()
            assert dock.locator('.ttra-dock-control').count() == 5
            controls = dock
            initial_y = dock.bounding_box()['y']
            page.evaluate("window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'})")
            page.wait_for_timeout(150)
            assert abs(dock.bounding_box()['y'] - initial_y) < 1
            page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")
            page.wait_for_timeout(150)
            assert abs(dock.bounding_box()['y'] - initial_y) < 1
            assert dock.bounding_box()['y'] + dock.bounding_box()['height'] <= 900

            contact = dock.get_by_role('button', name='Vías de contacto', exact=True)
            contact.click()
            contacts = page.locator('#ttra-dock-contact')
            assert contacts.is_visible()
            assert contacts.locator('a').count() == 4
            assert contacts.get_by_role('link', name='WhatsApp').get_attribute('href') == 'https://wa.me/543512145217'
            categories = dock.get_by_role('button', name='Categorías', exact=True)
            categories.click()
            assert not contacts.is_visible()
            panel = page.locator('#ttra-dock-categories')
            assert panel.is_visible()
            assert panel.locator('a').count() == 7
            page.keyboard.press('Escape')
            assert not panel.is_visible()
            profile = page.locator('header #btn-perfil-toggle, header .ttra-site-profile')
            assert profile.is_visible()
            if path != '/':
                assert profile.bounding_box()['y'] < page.locator('.ttra-site-rate').bounding_box()['y']
            assert page.locator('.ttra-catalog-cta').count() == 0
            profile.click()
            theme = page.locator('.ttra-theme')
            theme.wait_for(state='visible')
            before = page.locator('html').get_attribute('data-classic-theme')
            theme.click()
            assert before != page.locator('html').get_attribute('data-classic-theme')
            profile.click()
            url = page.url
            controls.locator('#btn-carrito, .ttra-site-cart').click()
            if path == '/':
                page.locator('#panel-carrito').wait_for(state='visible')
                page.locator('#btn-cerrar-carrito').click()
            else:
                page.locator('.ttra-cart-dialog[open]').wait_for(state='visible')
                page.locator('.ttra-cart-loading').wait_for(state='hidden')
                page.frame_locator('.ttra-cart-dialog iframe').locator('#btn-cerrar-carrito').click()
                page.locator('.ttra-cart-dialog[open]').wait_for(state='hidden')
            assert page.url == url
            if path == '/catalogo':
                dock.locator('.ttra-dock-search').click()
                search = page.locator('#catalog-search')
                search.fill('Cargador')
                assert page.locator('#contador-productos').inner_text() == '1 producto'
                search.fill('inexistentezz')
                assert page.locator('#contador-productos').inner_text() == '0 productos'
                search.fill('')
                assert page.locator('#contador-productos').inner_text() == '2 productos'
                categories.click()
                panel.get_by_role('link', name='Gaming', exact=True).click()
                page.wait_for_url('**/catalogo?categoria=Gaming')
                page.wait_for_function("document.getElementById('contador-productos').textContent === '0 productos'")
                assert page.locator('#tabs').count() == 0
                page.locator('.ttra-dock-home').click()
                page.wait_for_url(BASE + '/')
                assert page.locator('.ttra-dock').is_visible()
                assert page.locator('body > footer').count() == 0
            page.screenshot(path=f'outputs/dock-{width}-{"home" if path == "/" else "catalog"}.png')
            print('PASS', width, path, flush=True)
        assert not errors, errors
        context.close()
    browser.close()
