"""Local comparison flow with synthetic sheets; no provider calls or customer writes."""
import os
from playwright.sync_api import sync_playwright, expect
BASE = os.environ.get('TTRA_TEST_BASE', 'http://127.0.0.1:8036')
with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in (320, 390, 1440):
        for theme in ('light', 'dark'):
            context = browser.new_context(viewport={'width': width, 'height': 900}, reduced_motion='reduce')
            context.add_init_script("localStorage.setItem('ttra_classic_theme', '" + theme + "')")
            def sheet(route):
                route.fulfill(json={'status': 'ready', 'sheet': {
                    'model': 'Synthetic fixture', 'fetched_at': 1780000000,
                    'attributes': [{'key': 'pantalla', 'label': 'Pantalla', 'value': 'Pantalla verificada de prueba', 'source_urls': ['https://example.com/specs']}],
                    'sources': [{'url': 'https://example.com/specs', 'title': 'Fuente de prueba'}]}})
            context.route('**/api/comparativa/ficha', sheet)
            page = context.new_page(); errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(BASE + '/catalogo?categoria=Celulares&marca=Apple', wait_until='domcontentloaded')
            page.locator('#condition-filter').select_option('usado')
            card = page.locator('.card').nth(2)
            card.scroll_into_view_if_needed()
            button = card.get_by_role('button', name='Comparar producto')
            expect(button).to_be_visible()
            box = button.bounding_box(); assert box['width'] >= 44 and box['height'] >= 44
            page.wait_for_function('!!window.TTRAHeaderCat')
            page.evaluate('window.originalHeader = document.querySelector("body > header")')
            color = card.locator('select option').nth(1).get_attribute('value')
            card.locator('select').select_option(color)
            origin_name = card.locator('h3').inner_text()
            origin_top = card.bounding_box()['y']
            button.click()
            search = card.get_by_role('combobox', name='Comparar con')
            search.fill('Samsung')
            results = card.locator('.compare-picker a')
            expect(results.first).to_be_visible()
            assert results.count() > 0
            assert page.evaluate("name => SECCIONES_DATA.Celulares.some(p => p.nombre === name && p.marca === 'Samsung')", results.first.inner_text())
            search.fill('noexist-0987654321')
            expect(card.locator('.compare-picker [role=status]')).to_have_text('No encontré productos de esta categoría.')
            search.fill('Samsung'); expect(results.first).to_be_visible()
            search.press('ArrowDown'); search.press('Enter')
            page.wait_for_url('**/comparativa?*')
            frame = page.frame_locator('#ttra-storefront-frame')
            expect(frame.locator('.comparison-product')).to_have_count(2)
            expect(frame.locator('.comparison-source').first).to_contain_text('Fuente de prueba')
            left, right = frame.locator('.comparison-product').all()
            lb, rb = left.bounding_box(), right.bounding_box()
            assert lb['x'] < rb['x'] and abs(lb['y'] - rb['y']) < 2
            assert frame.locator('body').evaluate('()=>document.documentElement.scrollWidth<=innerWidth')
            assert page.evaluate('window.originalHeader===document.querySelector("body > header")')
            if os.environ.get('TTRA_SCREENSHOTS'):
                from pathlib import Path
                target = Path(os.environ['TTRA_SCREENSHOTS']); target.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(target / f'comparativa-{width}-{theme}.png'), full_page=True)
            frame.get_by_role('link', name='Volver al Listado', exact=True).click()
            page.wait_for_url('**/catalogo?**restaurar=*')
            expect(frame.locator('#marca-filter')).to_have_value('Apple')
            expect(frame.locator('#condition-filter')).to_have_value('usado')
            returned = frame.locator('.card').filter(has=page.locator('h3', has_text=origin_name)).first
            expect(returned).to_be_visible()
            expect(returned.locator('select')).to_have_value(color)
            page.wait_for_timeout(600)
            assert abs(returned.bounding_box()['y'] - origin_top) < 5, (returned.bounding_box()['y'], origin_top)
            assert page.evaluate('window.originalHeader===document.querySelector("body > header")')
            assert not errors, errors
            print('PASS comparison flow, keyboard, sources, persistent header', width, theme, flush=True)
            context.close()
    browser.close()
