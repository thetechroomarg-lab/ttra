"""Regenera las imágenes de sellos del mail del recibo (web/mail_sellos/).

Las dibuja el mismo código del perfil (perfil.js + perfil.css, modo Classic
claro) para que el mail muestre exactamente los sellos que el cliente ve en
la web, quietos: los mails no animan ni giran en 3D. Correr de nuevo si
cambia el diseño del sello en el perfil.

    .venv/bin/python scripts/generar_sellos_mail.py
"""
import tempfile
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parent.parent
STATIC = RAIZ / "web" / "static"
SALIDA = RAIZ / "web" / "mail_sellos"
LADO = 198  # 66 px a 3x: entra el sello más girado sin recortarse

PAGINA = f"""<!doctype html><html lang="es" data-modo="classic" data-classic-theme="light"><head><meta charset="utf-8">
<link rel="stylesheet" href="{(STATIC / 'theme.css').as_uri()}"><link rel="stylesheet" href="{(STATIC / 'classic.css').as_uri()}">
<link rel="stylesheet" href="{(STATIC / 'perfil.css').as_uri()}"><link rel="stylesheet" href="{(STATIC / 'classic-editorial.css').as_uri()}">
<style>html,body{{background:transparent!important}} .fidelidad-sellos{{--sello:56px!important}}</style></head>
<body><section id="seccion-fidelidad"><p id="fidelidad-premio"></p><div id="fidelidad-sellos" class="fidelidad-sellos"></div></section>
<script src="{(STATIC / 'perfil.js').as_uri()}"></script></body></html>"""


def _centrar_y_comprimir(ruta):
    imagen = Image.open(ruta).convert("RGBA")
    lienzo = Image.new("RGBA", (LADO, LADO), (0, 0, 0, 0))
    lienzo.paste(imagen, ((LADO - imagen.width) // 2, (LADO - imagen.height) // 2), imagen)
    lienzo.quantize(colors=64, method=Image.Quantize.FASTOCTREE).save(ruta, optimize=True)


def main():
    SALIDA.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        pagina = Path(tmp) / "sellos.html"
        pagina.write_text(PAGINA, encoding="utf-8")
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            # Sin animación: el sello "nuevo" queda de frente, como en un mail.
            pestana = navegador.new_page(device_scale_factor=3, reduced_motion="reduce")
            pestana.goto(pagina.as_uri())
            for sellos, tipo in ((5, "lleno"), (0, "vacio")):
                pestana.evaluate(f"mostrarTarjetaFidelidad({{sellos_fidelidad: {sellos}, tipo_cliente: 'minorista'}})")
                casilleros = pestana.locator(".fidelidad-sello")
                for i in range(casilleros.count()):
                    ruta = SALIDA / f"sello-{tipo}-{i + 1}.png"
                    casilleros.nth(i).screenshot(path=str(ruta), omit_background=True)
                    _centrar_y_comprimir(ruta)
            navegador.close()


if __name__ == "__main__":
    main()
