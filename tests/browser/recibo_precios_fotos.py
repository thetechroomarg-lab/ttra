"""Precio, cámara y galería con backend real y cámara simulada de Chromium."""
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.test_pagos_entrega import entorno
from tests.test_recibos import _jpeg_minimo


@pytest.mark.parametrize("width", [390, 1280])
def test_edicion_y_fotos(entorno, tmp_path, width):
    client, fake, enviados = entorno
    archivos = {}
    class Storage:
        def from_(self, bucket):
            return self
        def upload(self, ruta, contenido, options):
            archivos[ruta] = contenido
    fake.storage = Storage()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--use-fake-device-for-media-stream", "--use-fake-ui-for-media-stream"])
        context = browser.new_context(viewport={"width": width, "height": 850}, permissions=["camera"])
        def local(route):
            req = route.request
            if not req.url.startswith("https://testserver/"):
                route.abort()
                return
            headers = {k: v for k, v in req.headers.items() if k not in ("host", "cookie", "content-length")}
            res = client.request(req.method, req.url, headers=headers, content=req.post_data_buffer)
            route.fulfill(status=res.status_code, body=res.content,
                          headers={k: v for k, v in res.headers.items() if k not in ("content-length", "content-encoding")})
        context.route("**/*", local)
        page = context.new_page()
        errores = []
        page.on("pageerror", lambda e: errores.append(str(e)))
        page.goto("https://testserver/admin/clientes")
        page.locator('[data-pedido-id="pago"]').get_by_role("button", name="Enviar recibo").click()
        precio = page.locator("#pago-precio-0")
        expect(precio).to_have_value("410")
        page.locator("#metodo-usd").check()
        precio.fill("500")
        expect(page.locator("#pago-enviar")).to_be_disabled()
        expect(page.locator("#pago-total")).to_contain_text("1.000")
        expect(page.locator("#metodo-usd")).to_be_checked()
        expect(page.locator("#importe-usd")).to_have_value("1000")
        expect(page.locator("#pago-enviar")).to_be_enabled()
        expect(page.locator("#metodo-ars").locator("..")).to_contain_text("$ 0")
        page.locator(".pago-scroll").evaluate("(el) => { el.scrollTop = 0; }")
        assert page.locator("#modal-pago").evaluate("(el) => el.scrollWidth <= el.clientWidth")
        page.screenshot(path=str(tmp_path / f"precios-{width}.png"))
        page.locator("#metodo-usd").check()
        page.get_by_role("button", name="Agregar foto", exact=True).click()
        page.evaluate("""() => {
            window.camaraOriginal = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
            navigator.mediaDevices.getUserMedia = () => Promise.reject(new DOMException('Denied', 'NotAllowedError'));
        }""")
        page.get_by_role("button", name="Sacar foto", exact=True).click()
        expect(page.locator("#pago-error")).to_contain_text("Permití el acceso")
        expect(page.get_by_role("button", name="Elegir de la galería", exact=True)).to_be_visible()
        page.evaluate("() => { navigator.mediaDevices.getUserMedia = window.camaraOriginal; }")
        page.get_by_role("button", name="Sacar foto", exact=True).click()
        page.wait_for_function("document.getElementById('pago-video').videoWidth > 0")
        page.evaluate("window.pistaCamara = document.getElementById('pago-video').srcObject.getTracks()[0]")
        page.get_by_role("button", name="Cerrar cámara", exact=True).click()
        page.wait_for_function("window.pistaCamara.readyState === 'ended'")
        page.get_by_role("button", name="Agregar foto", exact=True).click()
        page.get_by_role("button", name="Sacar foto", exact=True).click()
        page.wait_for_function("document.getElementById('pago-video').videoWidth > 0")
        page.evaluate("window.pistaCamara = document.getElementById('pago-video').srcObject.getTracks()[0]")
        page.get_by_role("button", name="Capturar foto", exact=True).click()
        expect(page.locator("#pago-fotos img")).to_have_count(1)
        page.wait_for_function("window.pistaCamara.readyState === 'ended'")
        page.get_by_role("button", name="Agregar foto", exact=True).click()
        with page.expect_file_chooser() as chooser:
            page.get_by_role("button", name="Elegir de la galería", exact=True).click()
        chooser.value.set_files({"name": "serie.jpg", "mimeType": "image/jpeg", "buffer": _jpeg_minimo()})
        expect(page.locator("#pago-fotos img")).to_have_count(2)
        page.screenshot(path=str(tmp_path / f"recibo-{width}.png"))
        page.locator("#pago-enviar").click()
        expect(page.locator('[data-pedido-id="pago"]')).to_have_count(0)
        assert len(archivos) == 2
        assert len(enviados) == 1 and "1.000" in enviados[0][2]
        assert len([a for a in enviados[0][3] if a["filename"].endswith(".jpg")]) == 2
        assert not errores
        browser.close()
