"""Checkout confirmation, recovery and sharing with the real storefront UI."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from cart_flow import api, PRODUCTS

BASE = os.environ.get('TTRA_TEST_URL', 'http://127.0.0.1:8000')
OUT = Path(__file__).resolve().parents[2] / 'outputs' / 'checkout-summary'

with sync_playwright() as p:
    browser = p.chromium.launch()
    for width, embedded in [(1440, False), (390, True)]:
        ctx = browser.new_context(viewport={'width': width, 'height': 900}, service_workers='block')
        saved = []
        fail = [True]
        def route_api(route):
            path = route.request.url.split('/api/', 1)[-1].split('?')[0]
            data = None
            if path == 'me':
                data = {'nombre': 'Ana', 'apellido': 'Prueba', 'email': 'ana@example.com', 'debe_cambiar_password': False}
            elif path == 'entregas-disponibles':
                data = {'opciones': [{'fecha': '2026-09-30', 'etiqueta': 'Miércoles'}]}
            elif path == 'pedidos':
                if fail[0]:
                    route.fulfill(status=500, json={'error': 'Fallo de prueba'})
                    return
                saved.append(route.request.post_data_json)
                data = {'ok': True}
            if data is not None:
                route.fulfill(json=data)
            else:
                api(route)
        ctx.route('https://api.whatsapp.com/**', lambda route: route.fulfill(body='WhatsApp de prueba'))
        ctx.route('**/api/**', route_api)
        if embedded:
            ctx.add_init_script('window.open = () => null')
        ctx.add_init_script("""sessionStorage.setItem('ttra_portada_vista','1');
            Object.defineProperty(navigator, 'share', {configurable:true, value:undefined});
            Object.defineProperty(navigator, 'clipboard', {configurable:true, value:{writeText:async text=>{window.copied=text}}});""")
        page = ctx.new_page()
        page.on('dialog', lambda d: d.accept())
        page.goto(BASE + ('/catalogo' if embedded else '/?panel=carrito'), wait_until='domcontentloaded')
        page.evaluate('(items)=>localStorage.setItem("ttra_carrito",JSON.stringify(items))', [dict(PRODUCTS[0], cantidad=2, color='Azul')])
        if embedded:
            page.locator('.ttra-site-cart').click()
            frame = page.frame_locator('.ttra-cart-dialog iframe')
            expect(page.locator('.ttra-cart-loading')).to_be_hidden()
        else:
            page.reload(wait_until='domcontentloaded')
            frame = page
            page.locator('#btn-carrito').click()
        expect(frame.locator('#items-carrito')).to_contain_text('Teléfono de prueba')
        frame.locator('#btn-abrir-direccion').click()
        frame.locator('#direccion-entrega').fill('Calle Prueba 123, Córdoba')
        with page.expect_response('**/api/pedidos') as response:
            frame.locator('#btn-whatsapp').click()
        assert response.value.status == 500
        expect(frame.locator('#btn-whatsapp')).to_be_enabled()
        assert page.evaluate('JSON.parse(localStorage.ttra_carrito).length') == 1
        fail[0] = False
        if not embedded:
            with ctx.expect_page():
                frame.locator('#btn-whatsapp').evaluate('(button)=>{button.click(); button.click();}')
        else:
            frame.locator('#btn-whatsapp').evaluate('(button)=>{button.click(); button.click();}')
        summary = frame.locator('#pedido-confirmado')
        expect(summary).to_be_visible()
        expect(summary).to_contain_text('Recibimos tu pedido')
        text = frame.locator('#pedido-confirmado-texto')
        expect(text).to_have_value(__import__('re').compile('Teléfono de prueba.*Azul.*x2', __import__('re').S))
        assert 'Calle Prueba 123' in text.input_value()
        assert '2026-09-30' in text.input_value()
        assert len(saved) == 1 and saved[0]['detalle'][0]['cantidad'] == 2
        assert page.evaluate('JSON.parse(localStorage.ttra_carrito).length') == 0
        if not embedded:
            ctx.pages[-1].wait_for_load_state('domcontentloaded')
            assert len(ctx.pages) == 2, 'Debe abrir WhatsApp automáticamente'
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(ctx.pages[-1].url).query)
            assert query['phone'] == ['543512145217']
            assert query['text'] == [text.input_value()]
            ctx.pages[-1].close()
        else:
            assert len(ctx.pages) == 1, 'Un popup bloqueado debe conservar el resumen'
        with ctx.expect_page() as whatsapp:
            frame.locator('#btn-whatsapp-pedido').click()
        whatsapp.value.wait_for_load_state('domcontentloaded')
        assert 'phone=543512145217' in whatsapp.value.url
        whatsapp.value.close()
        assert len(saved) == 1
        expect(frame.locator('#btn-compartir-pedido')).to_be_hidden()
        frame.locator('#btn-copiar-pedido').click()
        expect(frame.locator('#pedido-confirmado-estado')).to_contain_text('Copiado')
        assert text.evaluate('(el)=>window.copied') == text.input_value()
        # A failed clipboard still leaves selectable text.
        text.evaluate("()=>{navigator.clipboard.writeText=async()=>{throw Error('denied')}}")
        frame.locator('#btn-copiar-pedido').click()
        expect(frame.locator('#pedido-confirmado-estado')).to_contain_text('seleccionado')
        # Reopening preserves the receipt. Sharing cancellation cannot submit again.
        text.evaluate("""()=>{Object.defineProperty(navigator,'share',{configurable:true,value:async data=>{
            window.shared=data; throw new DOMException('cancel','AbortError');
        }});}""")
        frame.locator('#btn-cerrar-carrito').click()
        if embedded:
            # Receipt survives disposal of the embedded document.
            ctx.add_init_script("Object.defineProperty(navigator,'share',{configurable:true,value:async data=>{window.shared=data;throw new DOMException('cancel','AbortError')}})")
            page.locator('.ttra-site-cart').click()
        else:
            page.locator('#btn-carrito').click()
        expect(summary).to_be_visible()
        frame.locator('#btn-compartir-pedido').click()
        expect(summary).to_be_visible()
        assert text.evaluate('()=>window.shared.text') == text.input_value()
        assert len(saved) == 1
        # A platform failure retains the receipt; a successful share sends the same text.
        text.evaluate("()=>{Object.defineProperty(navigator,'share',{configurable:true,value:async()=>{throw new Error('unavailable')}})}")
        frame.locator('#btn-compartir-pedido').click()
        expect(frame.locator('#pedido-confirmado-estado')).to_contain_text('Podés copiar')
        text.evaluate("()=>{Object.defineProperty(navigator,'share',{configurable:true,value:async data=>{window.shared=data}})}")
        frame.locator('#btn-compartir-pedido').click()
        assert text.evaluate('()=>window.shared.text') == text.input_value()
        expect(summary).to_be_visible()
        assert len(saved) == 1
        OUT.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(OUT / f'{width}.png'))
        print(f'PASS {width}px embedded={embedded}: failure, retry, receipt, copy, share cancellation, reopen')
        ctx.close()
    browser.close()
