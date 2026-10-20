"""Prueba local del formulario móvil, con backend real y archivos temporales."""
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient
appmod.get_client = lambda: FakeSupabaseClient()


with TemporaryDirectory() as directorio:
    os.environ["COTIZACION_PATH"] = str(Path(directorio) / "cotizacion-admin.json")
    appmod.PRODUCTOS_PATH = Path(directorio) / "productos.json"
    appmod.CATALOGO_MANIFEST_PATH = Path(directorio) / "catalogo-manifest.json"
    appmod.PRODUCTOS_PATH.write_text(json.dumps([{
        "nombre": "Teléfono de prueba", "categoria": "Apple - iPhone",
        "usd": 100, "pesos": 156500, "transferencia": 161340,
    }]))
    appmod.CATALOGO_MANIFEST_PATH.write_text('{"cotizacion":1565}')
    appmod.ADMIN_CLIENTES_PASSWORD = "clave-prueba-local"
    cliente = TestClient(appmod.app, base_url="https://testserver")
    assert cliente.post("/admin/clientes/login", json={"password": "clave-prueba-local"}).status_code == 200

    def responder(route):
        request = route.request
        respuesta = cliente.request(
            request.method, request.url, content=request.post_data,
            headers={"Content-Type": request.headers.get("content-type", "text/html")},
        )
        route.fulfill(status=respuesta.status_code,
                      headers={"Content-Type": respuesta.headers["content-type"]},
                      body=respuesta.content)

    with sync_playwright() as p:
        browser = p.chromium.launch()
        for ancho in (360, 390, 1280):
            contexto = browser.new_context(viewport={"width": ancho, "height": 850}, has_touch=ancho < 600)
            contexto.route("https://testserver/**", responder)
            page = contexto.new_page()
            page.goto("https://testserver/admin/clientes#cotizacion")
            campo = page.get_by_label("Nueva cotización en pesos")
            campo.tap() if ancho < 600 else campo.click()
            assert campo.get_attribute("inputmode") == "numeric"
            campo.fill("1.600")
            assert not campo.evaluate("(input) => input.checkValidity()")
            campo.fill("1700")
            page.get_by_role("button", name="Guardar cotización").click()
            page.get_by_role("status").filter(has_text="Cotización guardada").wait_for()
            page.reload()
            from playwright.sync_api import expect
            expect(campo).to_have_value("1700")
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            assert cliente.get("/api/catalogo").json()["secciones"]["Celulares"][0]["pesos"] == 170000
            if ancho == 390:
                destino = Path("outputs/cotizacion-admin")
                destino.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(destino / "movil.png"), full_page=True)
            print(f"{ancho}px: formulario, validación, guardado y recarga correctos")
            contexto.close()
        browser.close()
