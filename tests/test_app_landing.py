from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_landing_mobile_muestra_una_sola_card_recomendada_completa():
    script = (appmod.BASE / "static" / "landing.js").read_text()

    assert "function tarjetaRecomendadoMobileHtml()" in script
    assert "carrousel-recomendados-mobile-track" not in script
    assert "pintarCarrouselRecomendadosMobile(el);" in script


def test_classic_css_mobile_no_desplaza_la_card_recomendada():
    css = (appmod.BASE / "static" / "classic.css").read_text()

    assert ".carrousel-recomendados-mobile-track" not in css
    assert "flex: 0 0 88%" not in css
    assert "transform .32s ease" not in css


def test_classic_header_desktop_limita_buscador_antes_del_bloque_derecho():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    selector = 'html[data-modo="classic"] .rc-header-centro {'
    inicio = css.index(selector)
    regla = css[inicio:css.index("}", inicio)]

    assert "width: clamp(420px, calc(100vw - 610px), 960px);" in regla
    assert "max-width: 100%;" in regla


def test_classic_header_mobile_conserva_ancho_de_busqueda_propio():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    inicio_mobile = css.index('@media (max-width: 700px)')
    css_mobile = css[inicio_mobile:]

    assert "width: var(--rc-mobile-classic-content-width);" in css_mobile


def test_classic_mobile_fija_carrousel_recomendados_a_400_por_350():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    selector = 'html[data-modo="classic"] .carrousel-recomendados-grid-mobile {'
    inicio = css.index(selector)
    regla = css[inicio : css.index("}", inicio)]

    assert "width: min(400px, 100%);" in regla
    assert "height: 350px;" in regla
    assert "margin: 0 auto;" in regla


def test_classic_mobile_aumenta_tipografia_y_abre_color_hacia_arriba():
    css = (appmod.BASE / "static" / "classic.css").read_text()

    def regla(selector):
        inicio = css.index(selector)
        return css[inicio : css.index("}", inicio)]

    etiqueta = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado-etiqueta {"
    )
    titulo = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado h3 {"
    )
    precio_principal = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado-precio strong {"
    )
    precio_secundario = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado-precio span {"
    )
    acciones = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado-acciones .dropdown-color-boton,"
    )
    lista_color = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".dropdown-color-lista {"
    )

    assert "font-size: 14.4px;" in etiqueta
    assert "font-size: 16.1px;" in titulo
    assert "font-size: 30px;" in precio_principal
    assert "font-size: 20px;" in precio_secundario
    assert "font-size: 12px;" in acciones
    assert "top: auto;" in lista_color
    assert "bottom: 100%;" in lista_color


def test_classic_mobile_agranda_iconos_y_mantiene_espaciado_de_acciones():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    script = (appmod.BASE / "static" / "landing.js").read_text()

    def regla(selector):
        inicio = css.index(selector)
        return css[inicio : css.index("}", inicio)]

    precio = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado-precio {"
    )
    iconos = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado .tarjeta-recomendado-iconos {"
    )
    svg = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado .btn-foto svg {"
    )

    assert "flex: 0 0 auto;" in precio
    assert "margin: 6px 0;" in iconos
    assert "width: 24.2px;" in svg
    assert "height: 24.2px;" in svg
    assert 'class="btn-agregar" type="button" data-color="" disabled' in script
    assert "btnAgregar.disabled = false;" in script


def test_classic_desktop_abre_colores_recomendados_hacia_arriba():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    selector = (
        '@media (min-width: 701px) {\n'
        '  html[data-modo="classic"] .tarjeta-recomendado .dropdown-color-lista {'
    )
    inicio = css.index(selector)
    regla = css[inicio : css.index("}", inicio)]

    assert '.tarjeta-recomendado .dropdown-color-lista {' in regla
    assert "top: auto;" in regla
    assert "bottom: 100%;" in regla


def test_classic_muestra_acciones_recomendadas_y_desactiva_agregar_sin_color():
    css = (appmod.BASE / "static" / "classic.css").read_text()

    def regla(selector):
        inicio = css.index(selector)
        return css[inicio : css.index("}", inicio)]

    acciones_classic = regla(
        'html[data-modo="classic"] .tarjeta-recomendado-acciones {'
    )
    agregar_deshabilitado = regla(
        ".tarjeta-recomendado-acciones .btn-agregar:disabled {"
    )

    assert "opacity: 1;" in acciones_classic
    assert "pointer-events: auto;" in acciones_classic
    assert "opacity: 0.4;" in agregar_deshabilitado
    assert "cursor: not-allowed;" in agregar_deshabilitado
    assert "filter: grayscale(1);" in agregar_deshabilitado


def test_carrito_muestra_disclaimer_y_alinea_altura_de_botones():
    html = (appmod.BASE / "static" / "index.html").read_text()
    css = (appmod.BASE / "static" / "landing.css").read_text()

    vaciar = html.index('id="btn-vaciar-carrito"')
    whatsapp = html.index('id="btn-whatsapp"')
    disclaimer = html.index('class="carrito-disclaimer"')

    assert vaciar < disclaimer
    assert whatsapp < disclaimer
    assert "no garantiza la reserva" in html
    assert "detalles finales se confirman por WhatsApp" in html
    assert "--carrito-boton-altura: 40px;" in css
    assert "#btn-aplicar-codigo," in css
    assert "#btn-vaciar-carrito," in css
    assert "#btn-whatsapp {" in css
    assert "height: var(--carrito-boton-altura);" in css


def test_carrito_es_modal_flotante_y_respeta_el_footer():
    css = (appmod.BASE / "static" / "landing.css").read_text()
    script = (appmod.BASE / "static" / "landing.js").read_text()

    inicio = css.index("#panel-carrito {\n  --carrito-boton-altura:")
    regla_modal = css[inicio : css.index("}", inicio)]
    inicio_items = css.index("#items-carrito {")
    regla_items = css[inicio_items : css.index("}", inicio_items)]

    assert "left: 50%;" in regla_modal
    assert "transform: translateX(-50%);" in regla_modal
    assert "border: 2px solid var(--rc-green-dim);" in regla_modal
    assert "bottom: var(--rc-carrito-separacion-footer);" in regla_modal
    assert "overflow: hidden;" in regla_modal
    assert "overflow-y: auto;" in regla_items
    assert "function sincronizarLimiteCarrito()" in script
    assert '"--rc-carrito-separacion-footer"' in script
    assert "sincronizarLimiteCarrito();" in script


def test_carrito_modal_se_ancla_a_la_derecha_en_desktop_y_deja_margenes_mobile():
    css = (appmod.BASE / "static" / "landing.css").read_text()

    selector_desktop = "@media (min-width: 701px) {\n  #panel-carrito {"
    inicio_desktop = css.index(selector_desktop)
    desktop = css[inicio_desktop : css.index("}", inicio_desktop)]
    selector_mobile = "@media (max-width: 700px) {\n  #panel-carrito {"
    inicio_mobile = css.index(selector_mobile)
    mobile = css[inicio_mobile : css.index("}", inicio_mobile)]

    assert "left: auto;" in desktop
    assert "right: 24px;" in desktop
    assert "transform: none;" in desktop
    assert "left: 12px;" in mobile
    assert "right: 12px;" in mobile
    assert "width: auto;" in mobile
    assert "transform: none;" in mobile


def test_landing_sin_sesion_muestra_index(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_landing_con_sesion_muestra_index(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_index_html_directo_sin_sesion_sirve_la_landing(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/index.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_index_html_directo_con_sesion_sigue_funcionando(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.get("/index.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_doble_barra_sin_sesion_no_sirve_la_landing(monkeypatch):
    """StaticFiles resuelve "//" igual que "/" y serviría index.html directo,
    evitando la ruta explícita GET "/" que sí chequea sesión."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    # httpx colapsa "//" si se pasa como path relativo — hay que mandar la
    # URL absoluta para que el "//" llegue tal cual al servidor.
    r = c.get("https://testserver//")
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/"


def test_triple_barra_sin_sesion_no_sirve_la_landing(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    r = c.get("https://testserver///")
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/"


def test_index_html_con_barra_final_sin_sesion_sirve_la_landing(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/index.html/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_catalogo_html_mayusculas_sin_sesion_no_sirve_la_landing(monkeypatch):
    """En un filesystem case-insensitive (macOS/Windows) StaticFiles serviría
    igual /CATALOGO.HTML — el chequeo tiene que ser case-insensitive."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    r = c.get("/CATALOGO.HTML")
    assert r.status_code in (302, 307)
    assert r.headers["location"] == "/"


def test_segmentos_punto_percent_encoded_sin_sesion_no_sirven_la_landing(monkeypatch):
    """uvicorn decodifica %2e/%2f antes de que la app vea el path, así que
    "/%2e/", "/foo/%2e%2e/" etc. llegan como "/./" y "/foo/../" — que
    posixpath.normpath resuelve a "/". Sin resolver esos segmentos, StaticFiles
    los serviría igual que "/" (index.html) sin pasar por ninguna gate."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver", follow_redirects=False)
    for ruta in ["/%2e/", "/%2E/", "/%2e%2f", "/%2e/%2e/", "/static/%2e%2e/", "/foo/%2e%2e/", "/x/%2e%2e/%2e/"]:
        r = c.get(ruta)
        assert r.status_code in (302, 307), f"{ruta} devolvió {r.status_code}"
        assert r.headers["location"] == "/"


def test_index_html_via_segmentos_punto_sin_sesion_sirve_la_landing(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/foo/%2e%2e/index.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Catálogo" in r.text


def test_login_html_con_barra_final_sigue_siendo_publico(monkeypatch):
    """La normalización no debe convertir /login.html/ en algo distinto de
    /login.html y bloquearlo por error."""
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/login.html/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Ingresar" in r.text


def test_login_html_es_publico_sin_sesion(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/login.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — Ingresar" in r.text


def test_chat_sin_sesion_devuelve_401(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.post("/chat", json={"mensaje": "hola", "sesion": "s1"})
    assert r.status_code == 401


def test_chat_con_sesion_sigue_funcionando(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    monkeypatch.setattr(appmod, "_cargar_productos",
                         lambda: [{"nombre": "x", "usd": 1, "pesos": 1, "transferencia": 1}])
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    })
    r = c.post("/chat", json={"mensaje": "hola", "sesion": "s1"})
    assert r.status_code == 200
    assert "respuesta" in r.json()
