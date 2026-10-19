"""Search links reproduce results in a fresh browser, without selecting a card."""
import os
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright, expect

BASE = os.environ.get('TTRA_TEST_BASE', 'http://127.0.0.1:8048')
ROOT = Path(__file__).resolve().parents[2]
NAMES = ['Samsung S26 256GB', 'Samsung S26 Plus 512GB', 'Samsung S26 Ultra 256GB', 'Samsung S25 256GB']
PRODUCTS = [dict(nombre=name, marca='Samsung', categoria='Celulares', usd=price,
                 pesos=price * 100, transferencia=price * 110, colores=['Negro'])
            for name, price in zip(NAMES, [700, 900, 1100, 600])]

def setup(browser, width):
    ctx = browser.new_context(viewport={'width': width, 'height': 900}, service_workers='block')
    ctx.route('**/catalogo?*', lambda r: r.fulfill(path=str(ROOT / 'web/static/catalogo.html'), content_type='text/html'))
    ctx.route('**/api/**', lambda r: r.fulfill(json={'secciones': {'Celulares': PRODUCTS}} if '/api/catalogo' in r.request.url else {}))
    ctx.route('https://**', lambda r: r.abort())
    return ctx

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (390, 1440):
        ctx = setup(browser, width)
        page = ctx.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(BASE + '/catalogo?buscar=1')
        page.locator('#catalog-search').fill('s26')
        expect(page.locator('.card > h3')).to_have_text(NAMES[:3])
        page.get_by_role('button', name='Compartir búsqueda', exact=True).click()
        expect(page.locator('#catalog-share')).to_be_visible()
        link = page.get_by_role('textbox', name='Link de la búsqueda').input_value()
        assert parse_qs(urlparse(link).query)['q'] == ['s26']
        page.evaluate("Object.defineProperty(navigator, 'clipboard', {configurable: true, value: {writeText: async value => {window.copiedSearch = value;}}})")
        page.locator('.catalog-share-copy').click()
        expect(page.locator('#catalog-share [role=status]')).to_have_text('¡Enlace copiado!')
        assert page.evaluate('window.copiedSearch') == link
        page.evaluate("() => { navigator.clipboard.writeText = async () => {throw new Error('Denied');}; }")
        page.locator('.catalog-share-copy').click()
        expect(page.locator('#catalog-share [role=status]')).to_contain_text('puedas copiarlo')
        assert 'producto' not in parse_qs(urlparse(link).query)
        recipient = setup(browser, width)
        other = recipient.new_page()
        other.goto(link)
        expect(other.locator('#catalog-search')).to_be_visible()
        expect(other.locator('#catalog-search')).to_have_value('s26')
        expect(other.locator('.card > h3')).to_have_text(NAMES[:3])
        expect(other.locator('.card-del-link, .card-seleccionada, .card[aria-selected=true]')).to_have_count(0)
        page.locator('.catalog-share-close').click()
        page.locator('#marca-filter').select_option('Samsung')
        page.locator('input[value=precio-desc]').check()
        page.locator('label[for=cuotas-filter]').click()
        page.evaluate('precioMin=800; precioMax=1200; pintarSeccion(categoriaActiva)')
        expect(page.locator('.card > h3')).to_have_text([NAMES[2], NAMES[1]])
        page.get_by_role('button', name='Compartir búsqueda', exact=True).click()
        link = page.get_by_role('textbox', name='Link de la búsqueda').input_value()
        other.goto(link)
        expect(other.locator('.card > h3')).to_have_text([NAMES[2], NAMES[1]])
        expect(other.locator('#marca-filter')).to_have_value('Samsung')
        expect(other.locator('input[value=precio-desc]')).to_be_checked()
        expect(other.locator('#cuotas-filter')).to_be_checked()
        other.locator('#catalog-search').fill('nothing-matches')
        expect(other.locator('.card')).to_have_count(0)
        other.locator('#catalog-search').fill('ULTRA samsung s26')
        expect(other.locator('.card > h3')).to_have_text([NAMES[2]])
        other.locator('.btn-compartir').click()
        product_link = other.get_by_role('textbox', name='Link del producto').input_value()
        assert parse_qs(urlparse(product_link).query) == {'producto': [NAMES[2]]}
        other.locator('.catalog-share-close').click()
        assert other.evaluate('document.documentElement.scrollWidth <= innerWidth')
        other.screenshot(path=f'/tmp/ttra-search-{width}.png', full_page=True)
        assert not errors, errors
        print(f'PASS {width}: keywords, fresh recipient, filters/order, no highlighted card, product links')
        ctx.close(); recipient.close()
    browser.close()
