"""Run against the local preview to verify all six hero illustrations."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from cart_flow import api

BASE = os.environ.get('TTRA_TEST_URL', 'http://127.0.0.1:8026')
OUT = Path(__file__).resolve().parents[2] / 'outputs' / 'hero-gallery'
OUT.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in [1440, 390]:
        context = browser.new_context(viewport={'width': width, 'height': 1000})
        context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        context.route('**/api/**', api)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE, wait_until='domcontentloaded')
        stage = page.locator('.ttra-stage')
        stage.scroll_into_view_if_needed()
        expect(stage.locator('.ttra-hero-slide')).to_have_count(6)
        assert stage.locator('.ttra-stage-top, .ttra-stage-bottom, .ttra-stage-plus').count() == 0
        expect(stage.locator('.ttra-stage-word')).to_have_text('ttra.')
        for index in range(6):
            expect(stage).to_have_attribute('data-gallery-index', str(index), timeout=10000)
            page.wait_for_timeout(1100)
            stage.screenshot(path=str(OUT / f'{width}-{index}.png'))
        expect(stage).to_have_attribute('data-gallery-index', '0', timeout=10000)
        stage.get_by_role('button', name='Pausar imágenes').click()
        page.wait_for_timeout(5200)
        expect(stage).to_have_attribute('data-gallery-index', '0')
        stage.get_by_role('button', name='Reproducir imágenes').click()
        expect(stage).to_have_attribute('data-gallery-index', '1', timeout=7000)
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errors, errors
        context.close()
    context = browser.new_context(reduced_motion='reduce')
    context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
    context.route('**/api/**', api)
    page = context.new_page()
    page.goto(BASE, wait_until='domcontentloaded')
    stage = page.locator('.ttra-stage')
    stage.scroll_into_view_if_needed()
    page.wait_for_timeout(5200)
    expect(stage).to_have_attribute('data-gallery-index', '0')
    expect(stage.get_by_role('button', name='Reproducir imágenes')).to_have_count(1)
    browser.close()
print('Hero gallery: six slides, 5-second rotation, loop, pause, resume and reduced motion passed')
