"""Explicit catalog interactions reach the admin history endpoint once per product."""
import sys
sys.path.insert(0, 'tests/browser')
from cart_flow import api
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (390, 1440):
        context = browser.new_context(viewport={'width': width, 'height': 900}, service_workers='block')
        context.route('**/api/**', api)
        page = context.new_page()
        events = []
        page.on('request', lambda req: events.append(req) if '/api/interacciones' in req.url else None)
        page.goto('http://127.0.0.1:8027/catalogo', wait_until='domcontentloaded')
        phone = page.locator('.card').filter(has_text='Teléfono de prueba')
        phone.wait_for()
        assert not events, 'Rendering a catalog must not count all products as viewed'
        with page.expect_request('**/api/interacciones'):
            phone.get_by_label('Color').select_option('Azul')
        request = events[0]
        assert request.post_data_json['tipo_evento'] == 'view_item'
        assert request.post_data_json['producto_nombre'] == 'Teléfono de prueba'
        assert request.headers['x-ttra-anon-id'] == page.evaluate("localStorage.getItem('ttra_anon_id')")
        phone.get_by_role('button', name='Agregar al carrito').click()
        phone.get_by_label('Color').select_option('Negro')
        assert len(events) == 1
        page.locator('#marca-filter').select_option('Apple')
        phone = page.locator('.card').filter(has_text='Teléfono de prueba')
        phone.get_by_label('Color').select_option('Azul')
        assert len(events) == 1, 'Filtering must not duplicate the same product consultation'
        print(width, 'catalog → admin history endpoint, identity and deduplication passed', flush=True)
        context.close()
    browser.close()
