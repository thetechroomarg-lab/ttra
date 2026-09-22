"""Run against a local app: TTRA_TEST_URL=http://127.0.0.1:8018 python tests/browser/cart_flow.py."""
import json
import math
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('TTRA_TEST_URL', 'http://127.0.0.1:8018')
OUT = Path(__file__).resolve().parents[2] / 'outputs' / 'cart-flow'
PRODUCTS = [
    {'nombre': 'Teléfono de prueba', 'marca': 'Apple', 'usd': 100, 'pesos': 150000, 'transferencia': 155000, 'colores': ['Negro', 'Azul']},
    {'nombre': 'Cargador de prueba', 'marca': 'Apple', 'usd': 20, 'pesos': 30000, 'transferencia': 31000, 'colores': []},
]


def api(route):
    path = route.request.url.split('/api/', 1)[-1].split('?')[0]
    if path == 'me':
        route.fulfill(status=401, content_type='application/json', body='{}')
        return
    data = {
        'catalogo': {'secciones': {'Celulares': PRODUCTS}, 'modo_precio': 'minorista'},
        'recomendados': {'productos': []},
        'noticias': {'titulares': []},
        'cotizacion': {'valor': 1500},
        'domicilios': [],
    }.get(path, {})
    route.fulfill(content_type='application/json', body=json.dumps(data))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for width, motion, theme in [(1440, 'no-preference', 'dark'), (390, 'no-preference', 'dark'), (390, 'no-preference', 'light'), (320, 'reduce', 'light')]:
            context = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion=motion)
            context.add_init_script(f"sessionStorage.setItem('ttra_portada_vista','1'); localStorage.setItem('ttra_classic_theme','{theme}')")
            context.route('**/api/**', api)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(BASE + '/catalogo', wait_until='domcontentloaded')
            phone = page.locator('#secciones .card').filter(has_text='Teléfono de prueba')
            expect(phone).to_be_visible()
            add = phone.get_by_role('button', name='Agregar al carrito')
            assert add.count() == 1, 'Catalog product has no add-to-cart control'
            expect(add).to_be_disabled()
            phone.get_by_label('Color').select_option('Azul')
            expect(add).to_be_enabled()
            add.click()
            expect(page.locator('.ttra-site-count')).to_have_text('1')
            cart = page.evaluate("JSON.parse(localStorage.getItem('ttra_carrito'))")
            assert cart[0]['nombre'] == PRODUCTS[0]['nombre'] and cart[0]['color'] == 'Azul'
            assert cart[0]['usd'] == 100 and cart[0]['cantidad'] == 1
            if motion == 'reduce':
                assert page.locator('.ttra-cart-flight').count() == 0
            else:
                expect(page.locator('.ttra-cart-flight')).to_have_count(1)
                source = phone.bounding_box()
                target = page.locator('.ttra-site-cart svg').bounding_box()
                page.wait_for_timeout(300)
                flight = page.locator('.ttra-cart-flight').bounding_box()
                assert flight and flight['width'] < source['width'], 'Card is not shrinking'
                def distance(rect):
                    return math.hypot(rect['x'] + rect['width'] / 2 - target['x'] - target['width'] / 2,
                                      rect['y'] + rect['height'] / 2 - target['y'] - target['height'] / 2)
                assert distance(flight) < distance(source), 'Card is not moving toward the cart'
                page.screenshot(path=str(OUT / f'flight-{width}-{theme}.png'))
            expect(page.locator('.ttra-cart-flight')).to_have_count(0)
            expect(add).to_be_enabled()
            add.click()
            expect(page.locator('.ttra-site-count')).to_have_text('2')
            expect(add).to_be_enabled()
            phone.get_by_label('Color').select_option('Negro')
            add.click()
            expect(page.locator('.ttra-site-count')).to_have_text('3')
            charger = page.locator('#secciones .card').filter(has_text='Cargador de prueba')
            charger.get_by_role('button', name='Agregar al carrito').click()
            expect(page.locator('.ttra-site-count')).to_have_text('4')
            page.reload(wait_until='domcontentloaded')
            expect(page.locator('.ttra-site-count')).to_have_text('4')
            cart = page.evaluate("JSON.parse(localStorage.getItem('ttra_carrito'))")
            assert [(item['color'], item['cantidad']) for item in cart] == [('Azul', 2), ('Negro', 1), (None, 1)]
            # A failed write must not show the flight, increment the count or
            # claim success. Existing saved items must remain untouched.
            page.evaluate("""() => {
                const write = Storage.prototype.setItem;
                Storage.prototype.setItem = function(key, value) {
                    if (key === 'ttra_carrito') throw new DOMException('Storage full', 'QuotaExceededError');
                    return write.call(this, key, value);
                };
            }""")
            charger = page.locator('#secciones .card').filter(has_text='Cargador de prueba')
            charger.get_by_role('button', name='Agregar al carrito').click()
            expect(charger.get_by_role('status')).to_contain_text('No pude guardar')
            expect(page.locator('.ttra-site-count')).to_have_text('4')
            assert page.locator('.ttra-cart-flight').count() == 0
            page.locator('.ttra-site-cart').click()
            checkout = page.frame_locator('.ttra-cart-dialog iframe')
            expect(checkout.locator('#panel-carrito:not(.oculto)')).to_be_visible()
            expect(checkout.locator('#items-carrito')).to_contain_text('Teléfono de prueba')
            expect(checkout.locator('#items-carrito')).to_contain_text('Cargador de prueba')
            assert page.url == BASE + '/catalogo'
            checkout.locator('#btn-cerrar-carrito').click()
            # Deep links use the original home cards; they must share the same
            # cart and animate without opening a blocking checkout panel.
            page.goto(BASE + '/?producto=Tel%C3%A9fono%20de%20prueba', wait_until='domcontentloaded')
            legacy_card = page.locator('#productos .card').filter(has_text='Teléfono de prueba')
            expect(legacy_card).to_be_visible()
            legacy_card.locator('.dropdown-color-boton').click()
            legacy_card.get_by_role('option', name='Azul').click()
            legacy_card.get_by_role('button', name='Agregar al carrito').click()
            expect(page.locator('#carrito-contador')).to_have_text('5')
            expect(page.locator('#panel-carrito')).to_be_hidden()
            if motion != 'reduce':
                expect(page.locator('.ttra-cart-flight')).to_have_count(1)
            expect(page.locator('.ttra-cart-flight')).to_have_count(0)
            page.goto(BASE + '/?producto=Cargador%20de%20prueba', wait_until='domcontentloaded')
            legacy_charger = page.locator('#productos .card').filter(has_text='Cargador de prueba')
            legacy_charger.locator('.dropdown-color-boton').click()
            legacy_charger.get_by_role('option', name='Color único').click()
            legacy_charger.get_by_role('button', name='Agregar al carrito').click()
            expect(page.locator('#carrito-contador')).to_have_text('6')
            saved = page.evaluate("JSON.parse(localStorage.getItem('ttra_carrito'))")
            assert len(saved) == 3 and saved[2]['cantidad'] == 2, 'Color único creates a duplicate of the same product'
            assert not errors, errors
            context.close()
            print(f'PASS {width}px / {theme} / {motion}: add, colors, repeat, reload, storage errors, existing cart, home cards', flush=True)
        browser.close()


if __name__ == '__main__':
    main()
