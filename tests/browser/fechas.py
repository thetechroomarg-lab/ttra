from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.mark.parametrize('locale',['en-US','es-AR'])
def test_fecha_visible_iso_interno_y_calendario(locale):
    with sync_playwright() as p:
        b=p.chromium.launch(); page=b.new_page(locale=locale,viewport={'width':390,'height':800})
        page.set_content('<form><label for="fecha">Fecha</label><input id="fecha" name="fecha" type="date" value="2026-10-20" required min="2024-01-01"><button type="reset">Restablecer</button></form>')
        page.add_script_tag(path=str(Path('web/static/fechas.js').resolve()))
        visible=page.get_by_role('textbox',name='Fecha',exact=True)
        expect(visible).to_have_value('20/10/2026')
        visible.fill('29/02/2025');visible.blur()
        assert not page.locator('form').evaluate('(f)=>f.checkValidity()')
        visible.fill('29/02/2024');visible.blur()
        assert page.locator('form').evaluate('(f)=>f.checkValidity()')
        assert page.locator('#fecha').input_value()=='2024-02-29'
        assert page.locator('form').evaluate('(f)=>new FormData(f).get("fecha")')=='2024-02-29'
        page.locator('#fecha').evaluate('(e)=>{e.value="2026-12-31"}')
        expect(visible).to_have_value('31/12/2026')
        page.get_by_role('button',name='Restablecer').click()
        expect(visible).to_have_value('20/10/2026')
        page.locator('#fecha').evaluate('(e)=>{e.showPicker=()=>{e.dataset.abierto="si"}}')
        page.get_by_role('button',name='Abrir calendario').click()
        expect(page.locator('#fecha')).to_have_attribute('data-abierto','si')
        page.locator('#fecha').evaluate('(e)=>{e.disabled=true}')
        expect(visible).to_be_disabled()
        page.locator('#fecha').evaluate('(e)=>{e.disabled=false}')
        visible.fill('01/01/2023');visible.blur()
        assert not page.locator('form').evaluate('(f)=>f.checkValidity()')
        page.evaluate("()=>{const e=document.createElement('input');e.type='date';e.id='dinamica';e.value='2026-01-02';document.body.append(e)}")
        expect(page.locator('#dinamica-visible')).to_have_value('02/01/2026')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        b.close()
