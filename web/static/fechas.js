/* Vista dd/mm/aaaa común; los controles originales conservan ISO para APIs y formularios. */
(() => {
  if (window.ttraFechas) return;
  const formato = iso => /^\d{4}-\d{2}-\d{2}$/.test(iso || '') ? iso.split('-').reverse().join('/') : '';
  function isoDesdeTexto(texto) {
    const partes = /^(\d{2})\/?(\d{2})\/?(\d{4})$/.exec(texto.trim());
    if (!partes) return '';
    const [,dia,mes,anio] = partes;
    const iso = `${anio}-${mes}-${dia}`, fecha = new Date(iso+'T00:00:00Z');
    return Number(anio)>0 && Number.isFinite(fecha.getTime()) && fecha.toISOString().slice(0,10)===iso ? iso : '';
  }
  window.ttraFechas = {formato};
  const estilo = document.createElement('style');
  estilo.textContent = `.fecha-local{position:relative;display:inline-flex;align-items:center;gap:6px;max-width:100%;vertical-align:middle}.fecha-local .fecha-texto{box-sizing:border-box;min-width:0;width:100%;padding-right:10px;font-size:16px}.fecha-local .fecha-nativa{position:absolute!important;width:1px!important;height:1px!important;min-height:0!important;padding:0!important;margin:0!important;opacity:0;pointer-events:none;bottom:0;right:0}.fecha-local .fecha-calendario{flex:none;min-width:44px;min-height:44px;margin:0;padding:8px;cursor:pointer;background:var(--op-surface-2,#333);color:var(--op-text,#fff);border:1px solid var(--op-border-strong,#777);border-radius:4px;font-size:18px}.fecha-local .fecha-calendario:focus-visible{outline:2px solid currentColor;outline-offset:2px}`;
  document.head.append(estilo);
  let contador=0;
  function preparar(nativo) {
    if (nativo.dataset.fechaLocal) return;
    nativo.dataset.fechaLocal='si';
    const caja=document.createElement('span'); caja.className='fecha-local';
    const texto=document.createElement('input'); texto.type='text'; texto.className=nativo.className+' fecha-texto';
    texto.id=(nativo.id || 'fecha-'+(++contador))+'-visible'; texto.placeholder='dd/mm/aaaa'; texto.inputMode='numeric'; texto.autocomplete='off'; texto.maxLength=10;
    for(const atributo of ['aria-label','aria-labelledby','aria-describedby','title']) if(nativo.hasAttribute(atributo))texto.setAttribute(atributo,nativo.getAttribute(atributo));
    for(const label of nativo.labels || []) if(label.htmlFor===nativo.id)label.htmlFor=texto.id;
    const boton=document.createElement('button');boton.type='button';boton.className='fecha-calendario';boton.textContent='▦';boton.setAttribute('aria-label','Abrir calendario');
    nativo.before(caja);caja.append(texto,boton,nativo);nativo.classList.add('fecha-nativa');nativo.tabIndex=-1;nativo.setAttribute('aria-hidden','true');
    let editando=false;
    function actualizar(){
      if(!editando){texto.value=formato(nativo.value);texto.setCustomValidity('');}
      texto.disabled=nativo.disabled;texto.required=nativo.required;texto.readOnly=nativo.readOnly;boton.disabled=nativo.disabled||nativo.readOnly;
    }
    // Los paneles asignan .value directamente al abrir diálogos o cambiar filtros.
    for(const propiedad of ['value','disabled','required','readOnly','min','max']){
      const descriptor=Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,propiedad);
      Object.defineProperty(nativo,propiedad,{configurable:true,get(){return descriptor.get.call(this);},set(valor){descriptor.set.call(this,valor);actualizar();}});
    }
    function aplicar(tipo){
      const bruto=texto.value.trim(),iso=isoDesdeTexto(bruto);
      let error=bruto&&!iso?'Usá una fecha válida en formato dd/mm/aaaa.':'';
      if(iso&&((nativo.min&&iso<nativo.min)||(nativo.max&&iso>nativo.max)))error='La fecha está fuera del período permitido.';
      texto.setCustomValidity(error);
      editando=true;nativo.value=iso;editando=false;
      if(!error&&(iso||!bruto)){
        if(tipo==='change')texto.value=formato(iso);
        nativo.dispatchEvent(new Event(tipo,{bubbles:true}));
      }
    }
    texto.addEventListener('input',()=>aplicar('input'));
    texto.addEventListener('change',()=>aplicar('change'));
    nativo.addEventListener('input',()=>{if(document.activeElement!==texto)actualizar();});
    nativo.addEventListener('change',()=>{if(document.activeElement!==texto)actualizar();});
    nativo.addEventListener('invalid',e=>{e.preventDefault();texto.focus();});
    boton.addEventListener('click',()=>{if(nativo.showPicker)nativo.showPicker();else nativo.click();});
    if(nativo.form)nativo.form.addEventListener('reset',()=>setTimeout(actualizar,0));
    new MutationObserver(actualizar).observe(nativo,{attributes:true,attributeFilter:['value','disabled','required','readonly','min','max']});
    actualizar();
  }
  function explorar(raiz){if(raiz.matches?.('input[type=date]'))preparar(raiz);raiz.querySelectorAll?.('input[type=date]').forEach(preparar);}
  function iniciar(){explorar(document);new MutationObserver(cambios=>{for(const c of cambios)for(const nodo of c.addedNodes)explorar(nodo);}).observe(document.body,{subtree:true,childList:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',iniciar);else iniciar();
})();
