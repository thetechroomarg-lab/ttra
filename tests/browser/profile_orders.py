"""Orders remain reachable from account menus on the home and catalog."""
import os
from playwright.sync_api import sync_playwright, expect
from cart_flow import api
BASE = os.environ.get('TTRA_TEST_URL', 'http://127.0.0.1:8000')
with sync_playwright() as p:
    browser = p.chromium.launch()
    for width in [1440, 390]:
        context = browser.new_context(viewport={'width': width, 'height': 900}, service_workers='block')
        def routes(route):
            path = route.request.url.split('/api/',1)[-1].split('?')[0]
            if path == 'me':
                route.fulfill(json={'nombre':'Ana','apellido':'Prueba','email':'ana@example.com','debe_cambiar_password':False})
            elif path == 'pedidos':
                route.fulfill(json={'en_curso':[{'id':'prueba','fecha_entrega':'2026-09-30','productos':['Teléfono de prueba'],'total_usd':100}], 'historial':[]})
            else:
                api(route)
        context.route('**/api/**', routes)
        context.add_init_script("sessionStorage.setItem('ttra_portada_vista','1')")
        page = context.new_page()
        for path in ['/', '/catalogo']:
            page.goto(BASE+path, wait_until='domcontentloaded')
            toggle = page.locator('#btn-perfil-toggle' if path == '/' else '.ttra-site-account-toggle')
            if path != '/':
                toggle = page.locator('[aria-controls="ttra-site-menu"]')
            toggle.click()
            page.locator('#link-ir-a-pedidos' if path == '/' else '.ttra-site-pedidos-link').click()
            panel = page if path == '/' else page.frame_locator('.ttra-cart-dialog iframe')
            expect(panel.locator('#panel-pedidos')).to_be_visible()
            expect(panel.locator('#lista-pedidos-en-curso')).to_contain_text('Teléfono de prueba')
            panel.locator('#tab-pedidos-historial').click()
            expect(panel.locator('#lista-pedidos-historial')).to_contain_text('Todavía no tenés compras finalizadas')
            panel.locator('#btn-cerrar-panel-pedidos').click()
            print(f'PASS {width}px {path}: Pedidos, en curso, historial, cierre', flush=True)
        context.close()
    browser.close()
