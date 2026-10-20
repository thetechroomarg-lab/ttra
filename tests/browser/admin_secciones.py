"""Panel integrado: navegación, carga manual, corrección y anulación, sin datos reales."""
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.test_pagos_entrega import entorno


@pytest.mark.parametrize('theme',['dark','light'])
@pytest.mark.parametrize('width',[390,1280])
def test_secciones(entorno,width,theme):
    client,fake,_=entorno
    from web import ganancia
    from tests.test_ganancia import venta
    ganancia.registrar_movimiento(fake,ganancia.calcular_venta(venta(),{}))
    with sync_playwright() as p:
        browser=p.chromium.launch()
        context=browser.new_context(viewport={'width':width,'height':900})
        def responder(route):
            req=route.request
            if not req.url.startswith('https://testserver/'): route.abort(); return
            res=client.request(req.method,req.url,content=req.post_data_buffer,headers={'content-type':req.headers.get('content-type','text/html')})
            route.fulfill(status=res.status_code,body=res.content,headers={'content-type':res.headers.get('content-type','text/html')})
        context.route('**/*',responder)
        page=context.new_page(); errores=[]
        page.on('pageerror',lambda e:errores.append(str(e)))
        context.add_init_script(f"localStorage.setItem('ttra_classic_theme', '{theme}')")
        page.goto('https://testserver/admin/clientes')
        expect(page.locator('.panel-header-acciones > *')).to_have_count(1)
        nav=page.get_by_role('navigation',name='Secciones de administración')
        nav.get_by_role('link',name='Clientes',exact=True).click()
        expect(page.locator('#filtro-clientes')).to_be_visible()
        page.locator('#filtro-clientes').fill('no existe')
        expect(page.locator('.cliente-fila:visible')).to_have_count(0)
        page.locator('#filtro-clientes').fill('Ana')
        expect(page.locator('.cliente-fila:visible')).to_have_count(1)
        page.get_by_role('button',name='+ Nuevo cliente',exact=True).click()
        expect(page.locator('#alta-cliente')).to_be_visible()
        page.keyboard.press('Escape')
        page.reload()
        expect(page.locator('#filtro-clientes')).to_be_visible()
        nav.get_by_role('link',name='Borrados',exact=True).click()
        expect(page.locator('#borrados-listado')).to_contain_text('No hay elementos borrados')
        from datetime import datetime, timezone
        fake.table('tareas_entrega').insert({'id':'restaurar-demo','titulo':'Nota para restaurar','borrado_en':datetime.now(timezone.utc).isoformat(),'borrado_por':'Vlad'}).execute()
        page.get_by_role('button',name='Actualizar',exact=True).click()
        expect(page.locator('#borrados-listado')).to_contain_text('Nota para restaurar')
        expect(nav.locator('[aria-current=page]')).to_have_text('Borrados')
        expect(nav.locator('[aria-current=page]')).to_have_css('background-color','rgb(213, 47, 39)')
        from pathlib import Path
        Path('tmp/admin-navegacion').mkdir(parents=True,exist_ok=True)
        page.screenshot(path=f'tmp/admin-navegacion/{theme}-{width}.png',full_page=True)
        page.get_by_role('button',name='Restaurar',exact=True).click()
        expect(page.locator('#borrados-listado')).to_contain_text('No hay elementos borrados')
        assert fake.table('tareas_entrega').select('*').eq('id','restaurar-demo').execute().data[0]['borrado_en'] is None
        page.get_by_role('link',name='Ganancia',exact=True).click()
        expect(page.locator('#admin-seccion-pedidos')).to_be_hidden()
        expect(page.locator('#ganancia-totales')).to_contain_text('Ganancia confirmada')
        assert page.locator('#ganancia-desde-visible').evaluate('''e=>{const s=getComputedStyle(e),c=document.createElement('canvas').getContext('2d');c.font=s.font;return e.clientWidth-parseFloat(s.paddingLeft)-parseFloat(s.paddingRight)>=c.measureText(e.value).width}''')
        page.locator('#ganancia-carga summary').click()
        page.locator('#ganancia-fecha').fill('2026-10-20')
        page.locator('#ganancia-concepto').fill('Trabajo de prueba')
        page.locator('#ganancia-monto').fill('35,50')
        page.get_by_role('button',name='Guardar movimiento',exact=True).click()
        expect(page.locator('#ganancia-manual-estado')).to_have_text('Movimiento guardado en USD.')
        page.locator('#ganancia-desde').fill('2026-10-20');page.locator('#ganancia-hasta').fill('2026-10-20')
        page.get_by_role('button',name='Consultar',exact=True).click()
        fila=page.locator('.ganancia-fila').filter(has_text='Trabajo de prueba')
        expect(fila).to_contain_text('35,50')
        fila.get_by_role('button',name='Editar',exact=True).click()
        page.locator('#ganancia-monto').fill('50')
        page.get_by_role('button',name='Guardar corrección').click()
        expect(fila).to_contain_text('50,00')
        page.on('dialog',lambda d:d.accept())
        fila.get_by_role('button',name='Anular').click()
        expect(fila).to_have_count(0)
        page.get_by_role('button',name='Completar o corregir').click()
        page.locator('#ganancia-costo_usd').fill('400')
        page.locator('#ganancia-comision_usd').fill('5')
        page.locator('#ganancia-motivo').fill('Costo estimado de prueba')
        page.get_by_role('button',name='Guardar importes',exact=True).click()
        expect(page.locator('#ganancia-listado')).to_contain_text('95,00')
        page.get_by_role('navigation',name='Secciones de administración').get_by_role('link',name='Cotización del dólar',exact=True).click()
        expect(page.locator('#cotizacion-valor')).to_be_visible()
        page.go_back();expect(page.locator('#admin-seccion-ganancia')).to_be_visible()
        page.reload();expect(page.locator('#admin-seccion-ganancia')).to_be_visible()
        assert len(context.pages)==1
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not errores
        browser.close()
