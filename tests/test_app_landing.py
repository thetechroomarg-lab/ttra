from fastapi.testclient import TestClient

import web.app as appmod
from tests.fakes_supabase import FakeSupabaseClient


def test_todas_las_paginas_html_incluyen_una_unica_etiqueta_google_al_inicio_del_head():
    for nombre in ("index.html", "login.html", "perfil.html", "catalogo.html"):
        html = (appmod.BASE / "static" / nombre).read_text()
        etiqueta = 'https://www.googletagmanager.com/gtag/js?id=G-ZPQR91G145'

        assert html.count(etiqueta) == 1
        assert html.index(etiqueta) < html.index("<meta charset")


def test_landing_descarta_descuento_mailing_persistido_fuera_de_un_link():
    script = (appmod.BASE / "static" / "landing.js").read_text()

    assert 'if (!new URLSearchParams(location.search).get("codigo")) {' in script
    assert "localStorage.removeItem(CLAVE_DESCUENTO_MAILING);" in script


def test_checkout_envia_codigo_mailing_y_no_lo_preconsume():
    script = (appmod.BASE / "static" / "landing.js").read_text(encoding="utf-8")
    inicio = script.index("async function registrarPedidoEnClientes")
    fin = script.index('document.getElementById("btn-whatsapp")', inicio)
    checkout = script[inicio:fin]

    assert "codigo_descuento" in checkout
    assert 'fetch("/api/descuentos/consumir"' not in script


def test_checkout_envia_codigo_regalo_y_no_lo_preconsume():
    """Catches consuming a gift before the order transaction commits."""
    script = (appmod.BASE / "static" / "landing.js").read_text(encoding="utf-8")
    inicio = script.index("async function registrarPedidoEnClientes")
    fin = script.index('document.getElementById("btn-whatsapp")', inicio)
    checkout = script[inicio:fin]

    assert "codigo_promo" in checkout
    assert 'fetch("/api/codigos-promo/consumir"' not in script
    assert "async function consumirCodigoPromo()" not in script
    assert 'tipo: "regalo_promocional"' not in checkout


def test_checkout_409_muestra_mensaje_recarga_y_exige_confirmacion_nueva():
    """Catches stale-value retry or WhatsApp continuation after a price conflict."""
    script = (appmod.BASE / "static" / "landing.js").read_text(encoding="utf-8")
    inicio = script.index("async function registrarPedidoEnClientes")
    fin = script.index('document.getElementById("btn-whatsapp")', inicio)
    checkout = script[inicio:fin]

    conflicto = checkout.index("if (respuesta.status === 409)")
    mostrar = checkout.index("alert(body.error", conflicto)
    recargar = checkout.index("await cargarCatalogo()", mostrar)
    reabrir = checkout.index("abrirCarrito()", recargar)
    detener = checkout.index("return false", reabrir)
    assert conflicto < mostrar < recargar < reabrir < detener
    assert checkout.count("registrarPedidoEnClientes(") == 1
    assert "Revisá el carrito y confirmá nuevamente" in checkout


def test_recarga_por_conflicto_reconcilia_carrito_antes_de_habilitar_checkout():
    script = (appmod.BASE / "static" / "landing.js").read_text(encoding="utf-8")
    inicio = script.index("async function cargarCatalogo()")
    fin = script.index("function refrescarPreciosCarrito()", inicio)
    carga = script[inicio:fin]

    assert "return false;" in carga
    assert "return true;" in carga
    assert carga.index("refrescarPreciosCarrito();") < carga.index("catalogoListo = true;")


def test_modo_mayorista_muestra_insignia_y_anula_descuentos_minoristas():
    html = (appmod.BASE / "static" / "index.html").read_text(encoding="utf-8")
    js = (appmod.BASE / "static" / "landing.js").read_text(encoding="utf-8")

    assert 'id="indicador-mayorista"' in html
    assert 'modoPrecioActual === "mayorista"' in js
    assert "borrarDescuentoMailing()" in js
    assert 'return modoPrecioActual === "mayorista" ? null' in js


def test_acciones_monetarias_esperan_catalogo_reconciliado_antes_de_abrirse():
    js = (appmod.BASE / "static" / "landing.js").read_text(encoding="utf-8")

    assert "let catalogoListo = false;" in js
    inicio_carga = js.index("async function cargarCatalogo()")
    fin_carga = js.index("function refrescarPreciosCarrito()", inicio_carga)
    carga_catalogo = js[inicio_carga:fin_carga]
    assert carga_catalogo.index('modoPrecioActual = datos.modo_precio === "mayorista"') < carga_catalogo.index("refrescarPreciosCarrito();") < carga_catalogo.index("catalogoListo = true;")

    def cuerpo_de(funcion):
        inicio = js.index(funcion)
        siguientes = [
            js.find("\nfunction ", inicio + len(funcion)),
            js.find("\nasync function ", inicio + len(funcion)),
        ]
        fin = min((posicion for posicion in siguientes if posicion != -1), default=len(js))
        return js[inicio:fin]

    for funcion in (
        "function calcularDescuento(carrito)",
        "function descuentoMailingAplicado(carrito)",
        "function abrirCarrito()",
        "function armarMensajeWhatsapp(carrito, fechaEntrega)",
        "async function aplicarCodigoMailing()",
        "async function aplicarCodigoMailingPorValor(codigo)",
        "async function procesarCheckoutPendiente()",
        "async function asegurarSesionParaCheckout()",
        "async function derivarCheckoutAWhatsapp(carrito)",
        "async function registrarPedidoEnClientes(carrito, fecha_entrega, direccion_entrega)",
    ):
        assert "if (!catalogoListo)" in cuerpo_de(funcion)

    inicio_codigo = js.index('document.getElementById("btn-aplicar-codigo").addEventListener')
    fin_codigo = js.index("async function registrarPedidoEnClientes", inicio_codigo)
    assert "if (!catalogoListo) return;" in js[inicio_codigo:fin_codigo]
    inicio_checkout = js.index('document.getElementById("btn-whatsapp").addEventListener')
    fin_checkout = js.index('document.getElementById("btn-volver")', inicio_checkout)
    assert "if (!catalogoListo) return;" in js[inicio_checkout:fin_checkout]
    assert "if (!(await registrarPedidoEnClientes(carrito, fechaEntrega, direccionEntrega))) return false;" in cuerpo_de("async function derivarCheckoutAWhatsapp(carrito)")


def test_render_y_mutaciones_del_carrito_esperan_catalogo_listo():
    js = (appmod.BASE / "static" / "landing.js").read_text(encoding="utf-8")

    inicio_render = js.index("function renderCarrito()")
    fin_render = js.index("function sincronizarLimiteCarrito()", inicio_render)
    render = js[inicio_render:fin_render]
    barrera = render.index("if (!catalogoListo)")
    lectura_carrito = render.index("const carrito = cargarCarrito();")
    tramo_previo = render[barrera:lectura_carrito]

    assert 'el.innerHTML = \'<p class="mensaje-vacio">Actualizando carrito...</p>\';' in tramo_previo
    assert 'totalEl.textContent = "";' in tramo_previo
    assert "totales(" not in tramo_previo
    assert "itemCarritoHtml" not in tramo_previo
    assert "querySelectorAll" not in tramo_previo

    for funcion in (
        "function cambiarCantidad(nombre, color, delta)",
        "function quitarDelCarrito(nombre, color)",
        "function vaciarCarrito()",
    ):
        inicio = js.index(funcion)
        fin = js.find("\nfunction ", inicio + len(funcion))
        assert "if (!catalogoListo) return;" in js[inicio:fin]


def test_configuracion_publica_expone_solo_la_clave_de_maps_configurada(monkeypatch):
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "maps-key-de-prueba")
    cliente = TestClient(appmod.app, base_url="https://testserver")

    respuesta = cliente.get("/api/configuracion-publica")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"google_maps_api_key": "maps-key-de-prueba"}


def test_configuracion_publica_no_inventa_una_clave_de_maps(monkeypatch):
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    cliente = TestClient(appmod.app, base_url="https://testserver")

    respuesta = cliente.get("/api/configuracion-publica")

    assert respuesta.status_code == 200
    assert respuesta.json() == {"google_maps_api_key": ""}


def test_checkout_ofrece_sugerencias_de_direccion_de_google_maps_en_argentina():
    html = (appmod.BASE / "static" / "index.html").read_text()
    script = (appmod.BASE / "static" / "landing.js").read_text()

    assert 'id="sugerencias-direccion"' in html
    assert 'fetch("/api/configuracion-publica")' in script
    assert "AutocompleteSuggestion.fetchAutocompleteSuggestions" in script
    assert 'includedRegionCodes: ["ar"]' in script
    assert 'place.fetchFields({ fields: ["formattedAddress"] })' in script


def test_autocomplete_de_direccion_se_comparte_con_el_carrito_fallout():
    script = (appmod.BASE / "static" / "landing.js").read_text()
    css = (appmod.BASE / "static" / "landing.css").read_text()
    inicio = script.index("async function cargarApiPlaces()")
    fin = script.index("function abrirPanelSecundario", inicio)
    autocomplete = script[inicio:fin]

    assert "modoVisual" not in autocomplete
    assert ".sugerencias-direccion" in css
    assert 'html[data-modo="fallout"] #panel-carrito {' in css


def test_registro_pide_domicilio_y_lo_autocompleta_con_google_maps():
    login_html = (appmod.BASE / "static" / "login.html").read_text()
    login_js = (appmod.BASE / "static" / "login.js").read_text()

    assert 'id="registro-direccion"' in login_html
    assert 'id="registro-sugerencias-direccion"' in login_html
    assert "AutocompleteSuggestion.fetchAutocompleteSuggestions" in login_js
    assert 'includedRegionCodes: ["ar"]' in login_js


def test_checkout_ofrece_domicilios_guardados_como_desplegable():
    index_html = (appmod.BASE / "static" / "index.html").read_text()
    landing_js = (appmod.BASE / "static" / "landing.js").read_text()

    assert 'id="lista-domicilios-entrega"' in index_html
    assert "fetch(\"/api/domicilios\")" in landing_js
    assert '"+ Agregar nueva dirección"' in landing_js


def test_checkout_va_directo_al_formulario_sin_domicilios_guardados():
    landing_js = (appmod.BASE / "static" / "landing.js").read_text()

    inicio = landing_js.index("async function abrirSelectorDireccion")
    fin = landing_js.index("document.getElementById(\"btn-abrir-direccion\")", inicio)
    abrir_selector = landing_js[inicio:fin]
    assert "abrirFormularioNuevaDireccion();" in abrir_selector
    assert "!domiciliosCliente.length" in abrir_selector

    inicio_guardar = landing_js.index('document.getElementById("btn-guardar-direccion")')
    fin_guardar = landing_js.index('document.getElementById("btn-abrir-codigo")', inicio_guardar)
    guardar_direccion = landing_js[inicio_guardar:fin_guardar]
    assert 'fetch("/api/domicilios", {' in guardar_direccion
    assert 'method: "POST"' in guardar_direccion


def test_domicilios_de_registro_y_checkout_tambien_funcionan_en_fallout():
    login_js = (appmod.BASE / "static" / "login.js").read_text()
    landing_js = (appmod.BASE / "static" / "landing.js").read_text()
    inicio_registro = login_js.index("async function cargarApiPlacesRegistro")
    fin_registro = login_js.index("registroDireccionInput.addEventListener", inicio_registro)
    registro_autocomplete = login_js[inicio_registro:fin_registro]
    inicio_checkout = landing_js.index("async function abrirSelectorDireccion")
    fin_checkout = landing_js.index('document.getElementById("btn-abrir-codigo")', inicio_checkout)
    checkout_domicilio = landing_js[inicio_checkout:fin_checkout]

    assert "modoFallout" not in registro_autocomplete
    assert "modoVisual" not in checkout_domicilio


def test_perfil_permite_gestionar_hasta_cinco_domicilios_con_autocomplete():
    perfil_html = (appmod.BASE / "static" / "perfil.html").read_text()
    perfil_js = (appmod.BASE / "static" / "perfil.js").read_text()

    assert 'id="lista-domicilios"' in perfil_html
    assert 'id="domicilio-alias"' in perfil_html
    assert 'id="domicilio-direccion"' in perfil_html
    assert 'id="perfil-sugerencias-direccion"' in perfil_html
    assert "AutocompleteSuggestion.fetchAutocompleteSuggestions" in perfil_js
    assert 'includedRegionCodes: ["ar"]' in perfil_js
    assert "btnGuardarDomicilio.disabled = domicilios.length >= 5" in perfil_js


def test_compartir_producto_abre_siempre_el_panel_compartible():
    script = (appmod.BASE / "static" / "landing.js").read_text()
    inicio = script.index("async function compartirProducto(nombre)")
    fin = script.index("let pipboyApagado", inicio)
    compartir = script[inicio:fin]

    assert "abrirPanelCompartir(url, nombre);" in compartir
    assert "navigator.share" not in compartir
    assert "navigator.clipboard" not in compartir
    assert "catalogoPlano" not in compartir
    assert "Object.values(SECCIONES_DATA).flat().find" in compartir


def test_compartir_producto_abre_un_panel_visible_si_el_navegador_no_puede_compartir():
    script = (appmod.BASE / "static" / "landing.js").read_text()
    css = (appmod.BASE / "static" / "landing.css").read_text()

    assert "function abrirPanelCompartir(url, nombre)" in script
    assert 'panel.id = "rc-panel-compartir";' in script
    assert "Compartir por WhatsApp" in script
    assert "Copiar enlace" in script
    assert "abrirPanelCompartir(url, nombre);" in script
    assert "#rc-panel-compartir" in css


def test_panel_compartir_usa_botones_iguales_y_redondeados_en_ambos_modos():
    script = (appmod.BASE / "static" / "landing.js").read_text()
    css = (appmod.BASE / "static" / "landing.css").read_text()
    inicio = css.index(".rc-panel-compartir-acciones > * {")
    fin = css.index(".rc-panel-compartir-cerrar", inicio)
    botones = css[inicio:fin]

    assert "border-radius: 9px;" in botones
    assert "border: 1px solid var(--rc-green);" in botones
    assert "background: transparent;" in botones
    assert "appearance: none;" in botones
    assert "box-sizing: border-box;" in botones
    assert 'class="rc-panel-compartir-accion rc-panel-compartir-copiar"' in script
    assert 'class="rc-panel-compartir-accion rc-panel-compartir-whatsapp"' in script
    assert '<a class="rc-panel-compartir-whatsapp"' not in script


def test_landing_mobile_muestra_una_sola_card_recomendada_completa():
    script = (appmod.BASE / "static" / "landing.js").read_text()

    assert "function tarjetaRecomendadoMobileHtml()" in script
    assert "carrousel-recomendados-mobile-track" not in script
    assert "pintarCarrouselRecomendadosMobile(el);" in script


def test_cards_recomendadas_no_muestran_etiqueta_de_recomendacion():
    script = (appmod.BASE / "static" / "landing.js").read_text()

    inicio = script.index("function tarjetaRecomendadoHtml(p)")
    fin = script.index("function esClassicDesktopActivo()", inicio)
    tarjeta = script[inicio:fin]
    assert "tarjeta-recomendado-etiqueta" not in tarjeta
    assert "Recomendado para vos" not in tarjeta


def test_login_fallout_conserva_el_tema_y_el_retorno_a_la_landing():
    login = (appmod.BASE / "static" / "login.js").read_text()
    landing = (appmod.BASE / "static" / "landing.js").read_text()

    assert 'const modoFallout = paramsPantalla.get("modo") === "fallout";' in login
    assert 'document.documentElement.setAttribute("data-modo", "fallout")' in login
    assert 'modoFallout ? "/?modo=fallout" : "/"' in login
    assert 'params.set("modo", "fallout")' in landing


def test_selector_de_provincia_tiene_estilo_fallout_en_login():
    css = (appmod.BASE / "static" / "login.css").read_text()

    assert 'html[data-modo="fallout"] #registro-provincia {' in css
    assert 'html[data-modo="fallout"] #registro-provincia option {' in css


def test_busqueda_por_marca_muestra_un_selector_visual_solo_con_logos():
    script = (appmod.BASE / "static" / "landing.js").read_text()
    css = (appmod.BASE / "static" / "landing.css").read_text()

    inicio = script.index("function pintarSelectorMarcas(el)")
    fin = script.index("function", inicio + len("function pintarSelectorMarcas(el)"))
    selector = script[inicio:fin]

    assert 'modoVisual === "classic"' in selector
    assert 'class="selector-marcas${selectorLogosClase}"' in selector
    assert 'class="btn-categoria btn-marca-logo"' in selector
    assert 'marcaLogoHtml(m, "marca-logo-selector")' in selector
    assert 'aria-label="Ver productos de ${escapeHtml(etiquetaMarca(m))}"' in selector
    assert 'class="btn-categoria" data-marca="${escapeHtml(m)}" type="button">${escapeHtml(etiquetaMarca(m))}</button>' in selector
    assert 'html[data-modo="classic"] .selector-marcas.selector-marcas-logos' in css
    assert 'html[data-modo="classic"] .marca-logo-selector' in css


def test_busqueda_por_marca_deja_otras_marcas_al_final_del_selector():
    script = (appmod.BASE / "static" / "landing.js").read_text()

    inicio = script.index("function todasLasMarcasDelCatalogo()")
    fin = script.index("function pintarSelectorMarcas(el)", inicio)
    orden = script[inicio:fin]

    assert 'return [...sinOtrasMarcas, ...(presentes.has("Otras marcas") ? ["Otras marcas"] : [])];' in orden


def test_carrito_fallout_mobile_permite_scroll_cuando_el_footer_es_mas_alto_que_el_panel():
    css = (appmod.BASE / "static" / "landing.css").read_text()
    selector = 'html[data-modo="fallout"] #panel-carrito {'
    inicio = css.index(selector)
    regla = css[inicio : css.index("}", inicio)]

    assert "@media (max-width: 900px)" in css
    assert "left: 12px;" in regla
    assert "right: 12px;" in regla
    assert "width: auto;" in regla
    assert "max-width: calc(100vw - 24px);" in regla
    assert "min-width: 0;" in regla
    assert "overflow-y: auto;" in regla
    assert "overscroll-behavior: contain;" in regla


def test_classic_tiene_alternancia_light_persistente_dentro_del_menu_de_perfil():
    html = (appmod.BASE / "static" / "index.html").read_text()
    script = (appmod.BASE / "static" / "landing.js").read_text()
    css = (appmod.BASE / "static" / "classic.css").read_text()

    dropdown_inicio = html.index('id="rc-perfil-dropdown"')
    dropdown_fin = html.index("</div>", dropdown_inicio)
    dropdown = html[dropdown_inicio:dropdown_fin]

    assert 'id="btn-classic-theme"' in dropdown
    assert 'const CLAVE_TEMA_CLASSIC = "ttra_classic_theme";' in script
    assert 'document.documentElement.setAttribute("data-classic-theme", temaNormalizado);' in script
    assert 'localStorage.setItem(CLAVE_TEMA_CLASSIC, temaNormalizado);' in script
    assert 'html[data-modo="classic"][data-classic-theme="light"]' in css
    assert "--rc-bg: #c7dbe7;" in css
    assert "--rc-bg-panel: #e2ebf0;" in css
    assert "--cl-azul-francia: #102a43;" in css


def test_perfil_recupera_el_tema_light_classic_antes_de_cargar_estilos():
    perfil = (appmod.BASE / "static" / "perfil.html").read_text()

    assert 'localStorage.getItem("ttra_classic_theme") === "light"' in perfil
    assert 'document.documentElement.setAttribute("data-classic-theme", "light")' in perfil


def test_login_recupera_el_tema_light_classic_antes_de_cargar_estilos():
    login = (appmod.BASE / "static" / "login.html").read_text()

    assert 'localStorage.getItem("ttra_classic_theme") === "light"' in login
    assert 'document.documentElement.setAttribute("data-classic-theme", "light")' in login


def test_landing_y_catalogo_recuperan_el_tema_light_classic_antes_de_cargar_estilos():
    landing = (appmod.BASE / "static" / "index.html").read_text()
    catalogo = (appmod.BASE / "static" / "catalogo.html").read_text()
    catalogo_css = (appmod.BASE / "static" / "catalogo.css").read_text()

    for pagina in (landing, catalogo):
        assert 'localStorage.getItem("ttra_classic_theme") === "light"' in pagina
        assert 'document.documentElement.setAttribute("data-classic-theme", "light")' in pagina
    assert 'html[data-classic-theme="light"]' in catalogo_css


def test_classic_light_usa_botones_de_categoria_gris_oscuro_con_tipografia_blanca():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    selector = 'html[data-modo="classic"][data-classic-theme="light"] .btn-categoria {'
    inicio = css.index(selector)
    regla = css[inicio : css.index("}", inicio)]

    assert "background: #3b4650;" in regla
    assert "color: #ffffff;" in regla


def test_classic_light_saca_el_modulo_de_descuento_del_fondo_oscuro():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    selector = 'html[data-modo="classic"][data-classic-theme="light"] .descuento-mailing {'
    inicio = css.index(selector)
    regla = css[inicio : css.index("}", inicio)]

    assert "background: #dce8ef;" in regla
    assert 'html[data-modo="classic"][data-classic-theme="light"] .descuento-mailing input {' in css


def test_classic_light_muestra_el_icono_de_perfil_en_blanco_sobre_el_header():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    selector = 'html[data-modo="classic"][data-classic-theme="light"] .rc-perfil-boton {'
    inicio = css.index(selector)
    regla = css[inicio : css.index("}", inicio)]

    assert "color: #ffffff;" in regla


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


def test_classic_mobile_ajusta_carrousel_recomendados_al_alto_disponible():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    selector = 'html[data-modo="classic"] .carrousel-recomendados-grid-mobile {'
    inicio = css.index(selector)
    regla = css[inicio : css.index("}", inicio)]

    assert "width: min(400px, 100%);" in regla
    assert "height: 100%;" in regla
    assert "margin: 0 auto;" in regla


def test_classic_mobile_ajusta_tipografia_para_entrar_sin_scroll_y_abre_color_hacia_arriba():
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
    bloque_precios = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado-precio {"
    )
    acciones = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado-acciones .dropdown-color-boton,"
    )
    acciones_contenedor = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".tarjeta-recomendado-acciones {"
    )
    lista_color = regla(
        'html[data-modo="classic"] .carrousel-recomendados-mobile-card '
        ".dropdown-color-lista {"
    )

    assert "font-size: 12.6px;" in etiqueta
    assert "font-size: 18px;" in titulo
    assert "font-size: 18px;" in precio_principal
    assert "line-height: 1.05;" in precio_principal
    assert "font-size: 11px;" in precio_secundario
    assert "line-height: 1.1;" in precio_secundario
    assert "margin-top: 4px;" in bloque_precios
    assert "font-size: 11px;" in acciones
    assert "margin-top: auto;" in acciones_contenedor
    assert "top: auto;" in lista_color
    assert "bottom: 100%;" in lista_color


def test_classic_mobile_recomendados_no_renderiza_puntos_y_conserva_swipe():
    script = (appmod.BASE / "static" / "landing.js").read_text()
    inicio = script.index("function pintarCarrouselRecomendadosMobile(el)")
    fin = script.index("function pintarCarrouselRecomendados(el)", inicio)
    pintar = script[inicio:fin]

    assert "carrousel-recomendados-mobile-puntos" not in pintar
    assert "data-indice" not in pintar
    assert 'viewport.addEventListener("touchend"' in pintar
    assert "iniciarCicloRecomendadosMobile(el);" in pintar


def test_classic_mobile_home_usa_el_viewport_sin_scroll_de_pagina():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    selector = 'html[data-modo="classic"] body#rc-body-landing:not(.rc-vista-seccion) {'
    inicio = css.index(selector)
    regla = css[inicio : css.index("}", inicio)]

    assert "\n    height: 100dvh;" in regla
    assert "overflow: hidden;" in regla


def test_classic_mobile_sin_scroll_no_se_filtra_a_otras_paginas():
    # El "home sin scroll" es exclusivo de index.html: el selector de
    # classic.css exige el id de su body. Si alguna otra página lo usara
    # (perfil, login, catálogo), les recortaría el contenido sin poder
    # scrollear — regresión real que rompió el perfil en producción.
    css = (appmod.BASE / "static" / "classic.css").read_text()
    assert 'body:not(.rc-vista-seccion)' not in css
    assert 'body#rc-body-landing:not(.rc-vista-seccion)' in css

    index_html = (appmod.BASE / "static" / "index.html").read_text()
    assert '<body id="rc-body-landing">' in index_html

    for nombre in ("perfil.html", "login.html", "catalogo.html"):
        html = (appmod.BASE / "static" / nombre).read_text()
        assert 'id="rc-body-landing"' not in html


def test_classic_mobile_card_recomendada_ocupa_el_alto_libre_sin_un_tope_fijo():
    css = (appmod.BASE / "static" / "classic.css").read_text()
    selector = 'html[data-modo="classic"] .carrousel-recomendados-grid-mobile {'
    inicio = css.index(selector)
    regla = css[inicio : css.index("}", inicio)]

    assert "height: 100%;" in regla
    assert "height: 350px;" not in regla


def test_classic_mobile_mantiene_iconos_y_espaciado_de_acciones_compactos():
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
    assert "margin: 2px 0;" in iconos
    assert "width: 20px;" in svg
    assert "height: 20px;" in svg
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
    assert "#btn-guardar-direccion," in css
    assert "#btn-vaciar-carrito," in css
    assert "#btn-whatsapp {" in css
    assert "height: var(--carrito-boton-altura);" in css


def test_modal_codigo_es_solo_titulo_input_y_aplicar():
    html = (appmod.BASE / "static" / "index.html").read_text()
    script = (appmod.BASE / "static" / "landing.js").read_text()
    modal = html[html.index('<div id="modal-codigo"'):html.index('<button id="btn-whatsapp"')]

    assert "Aplicá tu código" in modal
    assert 'id="input-codigo-mailing"' in modal
    assert 'id="btn-aplicar-codigo"' in modal
    assert "rc-codigo-header" not in modal
    assert "descuento-mailing" not in modal
    assert 'id="btn-cerrar-codigo"' not in modal
    assert 'getElementById("btn-cerrar-codigo")' not in script
    assert "#modal-codigo input {" in (appmod.BASE / "static" / "landing.css").read_text()


def test_carrito_muestra_un_solo_panel_secundario_y_cierra_al_tocar_afuera():
    script = (appmod.BASE / "static" / "landing.js").read_text()

    assert "function abrirPanelSecundario(idPanel)" in script
    assert 'panelDireccionEntrega.classList.toggle("oculto", idPanel !== "direccion-entrega-wrap")' in script
    assert 'panelCodigoPromocional.classList.toggle("oculto", idPanel !== "modal-codigo")' in script
    assert 'document.addEventListener("pointerdown", (evento) =>' in script
    assert "panelSecundarioAbierto.contains(evento.target)" in script


def test_direccion_entrega_cierra_sin_boton_x():
    html = (appmod.BASE / "static" / "index.html").read_text()
    script = (appmod.BASE / "static" / "landing.js").read_text()
    direccion = html[html.index('<div id="direccion-entrega-wrap"'):html.index('<button id="btn-vaciar-carrito"')]

    assert 'id="btn-cerrar-direccion"' not in direccion
    assert 'getElementById("btn-cerrar-direccion")' not in script


def test_carrito_y_whatsapp_muestran_los_cinco_precios_de_las_cards():
    script = (appmod.BASE / "static" / "landing.js").read_text()
    css = (appmod.BASE / "static" / "landing.css").read_text()

    assert 'class="item-precios"' in script
    assert "function preciosCarritoHtml(precios, signo = \"\")" in script
    assert "function preciosWhatsapp(precios, signo = \"\")" in script
    assert "Dólar banco USA" in script
    assert "Pesos transf" in script
    assert "#items-carrito .item-precios" in css


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
    assert "overflow-y: auto;" in regla_modal
    assert "flex: 0 0 auto;" in regla_items
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
    assert "THE TECH ROOM ARG — iPhones, celulares y notebooks en Córdoba" in r.text


def test_landing_con_sesion_muestra_index(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    r = c.get("/")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — iPhones, celulares y notebooks en Córdoba" in r.text


def test_index_html_directo_sin_sesion_sirve_la_landing(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    r = c.get("/index.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — iPhones, celulares y notebooks en Córdoba" in r.text


def test_index_html_directo_con_sesion_sigue_funcionando(monkeypatch):
    fake = FakeSupabaseClient()
    monkeypatch.setattr(appmod, "get_client", lambda: fake)
    c = TestClient(appmod.app, base_url="https://testserver")
    c.post("/registro", json={
        "nombre": "Juan", "apellido": "Pérez", "celular": "3511234567",
        "email": "juan@x.com", "password": "clave1234",
    "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    r = c.get("/index.html")
    assert r.status_code == 200
    assert "THE TECH ROOM ARG — iPhones, celulares y notebooks en Córdoba" in r.text


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
    assert "THE TECH ROOM ARG — iPhones, celulares y notebooks en Córdoba" in r.text


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
    assert "THE TECH ROOM ARG — iPhones, celulares y notebooks en Córdoba" in r.text


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
    "provincia": "Córdoba", "direccion": "Av. Colón 123, Córdoba",})
    r = c.post("/chat", json={"mensaje": "hola", "sesion": "s1"})
    assert r.status_code == 200
    assert "respuesta" in r.json()
