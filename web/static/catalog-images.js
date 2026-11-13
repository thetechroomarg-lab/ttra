/* Optional artwork layer. Catalog data, prices and action handlers remain authoritative. */
(() => {
  const manifest = fetch('/catalog-images/index.json').then(r => r.ok ? r.json() : {}).catch(() => ({}));
  const placeholder='/catalog-images/placeholder-ttra-v4.png';
  const norm = s => String(s || '').normalize('NFC').trim().toLocaleLowerCase('es');
  // Spelling-tolerant keys so a catalog refresh (another supplier wins) does not drop the artwork.
  const plain = s => norm(s).normalize('NFD').replace(/[̀-ͯ]/g, '');
  const colorKey = s => plain(s).replace(/\b(pantone|awesome|awesomw|cosmic|deep)\b/g, ' ').replace(/\s+/g, ' ').trim();
  const FILLER = new Set(['apple', 'samsung', 'xiaomi', 'redmi', 'motorola', 'moto', 'celular', 'smartphone', 'original', 'nuevo', 'dual']);
  const nameKey = s => plain(s).replace(/[^a-z0-9+]+/g, ' ').split(' ').filter(t => t && !FILLER.has(t)).sort().join(' ');
  const byKey = manifest.then(index => {
    const m = {};
    for (const k in index) { const kk = nameKey(k); if (!(kk in m)) m[kk] = index[k]; }
    return m;
  });
  const labels = ['Dólar contado', 'Dólar transf. USA', 'USDT', 'Pesos contado', 'Pesos transf.'];
  const text = (tag, cls, value) => { const e=document.createElement(tag); e.className=cls; e.textContent=value; return e; };
  // --- Fotos reales de equipos usados: carrusel en la card + visor ampliado. ---
  const SVG_FLECHA = dir => `<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false"><path d="${dir < 0 ? 'M15 5l-7 7 7 7' : 'M9 5l7 7-7 7'}" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
  const boton = (cls, etiqueta, html) => { const b = document.createElement('button'); b.type = 'button'; b.className = cls; b.setAttribute('aria-label', etiqueta); b.innerHTML = html; return b; };
  const esUsado = p => /usado/i.test(String(p?.categoria || ''));
  const mod = (i, n) => (i % n + n) % n;
  // Versión grande de una imagen del catálogo: /catalog-images/X.webp -> /catalog-images/zoom/X.webp (las fotos reales de usados ya son grandes).
  const zoomDe = src => /^\/catalog-images\/(?!zoom\/|usados\/)/.test(src || '') && !/placeholder/.test(src) ? src.replace('/catalog-images/', '/catalog-images/zoom/') : src;
  const UMBRAL_SWIPE = 40;
  // Swipe horizontal (táctil o arrastrando con el mouse). Devuelve true si el gesto fue un arrastre.
  function swipe(el, alCambiar) {
    let x0 = null, y0 = 0;
    el.addEventListener('pointerdown', e => { if (e.pointerType === 'mouse' && e.button) return; x0 = e.clientX; y0 = e.clientY; });
    el.addEventListener('pointercancel', () => { x0 = null; });
    el.addEventListener('pointerup', e => {
      if (x0 == null) return;
      const dx = e.clientX - x0, dy = e.clientY - y0; x0 = null;
      if (Math.abs(dx) >= UMBRAL_SWIPE && Math.abs(dx) > Math.abs(dy) * 1.2) { el.dataset.swipe = '1'; setTimeout(() => delete el.dataset.swipe, 350); alCambiar(dx < 0 ? 1 : -1); }
    });
  }
  let visorAbierto = null;
  function abrirVisor(fotos, inicio, alt, origen, respaldo, recorte) {
    if (visorAbierto) return;
    let i = mod(inicio, fotos.length);
    const dlg = document.createElement('dialog');
    dlg.className = 'ai-visor' + (recorte ? ' ai-visor-recorte' : ''); dlg.setAttribute('aria-label', (recorte ? 'Imagen de ' : 'Fotos de ') + alt);
    const escena = document.createElement('div'); escena.className = 'ai-visor-escena';
    const img = document.createElement('img'); img.className = 'ai-visor-img'; img.draggable = false; img.decoding = 'async';
    const prev = boton('ai-visor-flecha ai-visor-prev', 'Foto anterior', SVG_FLECHA(-1));
    const next = boton('ai-visor-flecha ai-visor-next', 'Foto siguiente', SVG_FLECHA(1));
    const cont = document.createElement('p'); cont.className = 'ai-visor-contador'; cont.setAttribute('aria-live', 'polite');
    const cerrar = document.createElement('button'); cerrar.type = 'button'; cerrar.className = 'ai-visor-cerrar'; cerrar.textContent = 'Cerrar';
    escena.append(img, prev, next); dlg.append(escena, cont, cerrar);
    const solo = fotos.length < 2; if (solo) { prev.hidden = next.hidden = cont.hidden = true; }
    // Si la versión grande no existe, se muestra la chica de la card (una sola vez por foto).
    img.addEventListener('error', () => { if (respaldo && img.dataset.respaldo !== String(i)) { img.dataset.respaldo = String(i); img.src = respaldo[i]; } });
    function ir(d) {
      if (solo && d) return;
      i = mod(i + d, fotos.length);
      img.classList.add('ai-visor-cambio');
      requestAnimationFrame(() => { img.src = fotos[i]; img.alt = solo ? alt : `${alt} · foto ${i + 1} de ${fotos.length}`; img.classList.remove('ai-visor-cambio'); });
      cont.textContent = `${i + 1} / ${fotos.length}`;
      [1, -1].forEach(k => { const pre = new Image(); pre.src = fotos[mod(i + k, fotos.length)]; });
    }
    function salir() { dlg.close(); }
    prev.addEventListener('click', () => ir(-1)); next.addEventListener('click', () => ir(1));
    cerrar.addEventListener('click', salir);
    swipe(escena, ir);
    // No se cierra tocando afuera: solo con "Cerrar". Escape sí cierra; las flechas del teclado navegan.
    dlg.addEventListener('keydown', e => {
      if (e.key === 'ArrowLeft') { e.preventDefault(); ir(-1); } else if (e.key === 'ArrowRight') { e.preventDefault(); ir(1); }
    });
    dlg.addEventListener('close', () => { visorAbierto = null; dlg.remove(); document.documentElement.classList.remove('ai-visor-abierto'); origen?.focus?.({ preventScroll: true }); });
    document.body.append(dlg); document.documentElement.classList.add('ai-visor-abierto');
    visorAbierto = dlg; dlg.showModal(); ir(0); cerrar.focus({ preventScroll: true });
  }
  function carrusel(fotos, alt) {
    let i = 0; const n = fotos.length;
    const caja = document.createElement('div'); caja.className = 'ai-carrusel';
    const ver = boton('ai-carrusel-foto', 'Ampliar foto', ''); const img = document.createElement('img'); img.draggable = false; img.loading = 'lazy'; img.decoding = 'async'; ver.append(img);
    const prev = boton('ai-carrusel-flecha ai-carrusel-prev', 'Foto anterior', SVG_FLECHA(-1));
    const next = boton('ai-carrusel-flecha ai-carrusel-next', 'Foto siguiente', SVG_FLECHA(1));
    const puntos = document.createElement('div'); puntos.className = 'ai-carrusel-puntos'; puntos.setAttribute('aria-hidden', 'true');
    fotos.forEach(() => puntos.append(document.createElement('i')));
    function ir(d) {
      i = mod(i + d, n); img.src = fotos[i]; img.alt = `${alt} · foto ${i + 1} de ${n}`;
      [...puntos.children].forEach((p, k) => p.classList.toggle('on', k === i));
    }
    prev.addEventListener('click', e => { e.stopPropagation(); ir(-1); });
    next.addEventListener('click', e => { e.stopPropagation(); ir(1); });
    ver.addEventListener('click', () => { if (caja.dataset.swipe) return; abrirVisor(fotos, i, alt, ver); });
    swipe(caja, d => { caja.dataset.swipe = '1'; setTimeout(() => delete caja.dataset.swipe, 350); ir(d); });
    caja.append(ver, prev, next, puntos); ir(0);
    return caja;
  }
  const renders=new WeakMap();
  async function enhance(container, products) {
    const render={}; renders.set(container,render);
    const index = await manifest, keyed = await byKey;
    if (!container.isConnected || renders.get(container)!==render) return;
    // Todas las caras miden lo mismo: se dimensionan para la card con más líneas de
    // precio de la grilla (5 + una por cuota), tenga o no cuotas la de al lado.
    const filasDe=p=>(filasMayoristaDe(p)?6:5)+cuotasDe(preciosDe(p)).length;
    const maxFilas=products.reduce((m,p)=>p?Math.max(m,filasDe(p)):m,0);
    container.querySelectorAll('.card').forEach((card, i) => {
      const p = products[i], entry = p && (index[p.nombre] || keyed[nameKey(p.nombre)]);
      if (!p || card.classList.contains('ai-card')) return;
      const grid=card.closest('.grilla');
      if (grid?.classList.contains('lista') && innerWidth>700) return;
      const colors = p.colores?.length ? p.colores : [null];
      // Keep shared model matching while giving missing colors the common placeholder.
      const variants = colors.map(c => entry?.find(v => colorKey(v.color)===colorKey(c))
        || (!p.colores?.length && entry?.length===1 ? {...entry[0],color:null} : {color:c,src:placeholder}));
      const title=card.querySelector('h3'), oldPrices=card.querySelector('.precios');
      const links=card.querySelector('.catalog-product-links, .tarjeta-recomendado-iconos');
      if (!title || !oldPrices || !links) return;
      const face=text('div','ai-face',''), logo=text('div','ai-logo','');
      logo.innerHTML='THE<br>TECH<br>ROOM<br>ARG<span>.</span>';
      const name=text('h3','ai-title',p.nombre), color=text('span','ai-color','');
      const picture=text('div','ai-picture',''), img=document.createElement('img');
      img.loading='lazy'; img.decoding='async'; picture.append(img);
      const prices=text('div','ai-prices',''), amounts=preciosDe(p), filasMay=filasMayoristaDe(p);
      if(filasMay){
        prices.classList.add('ai-prices-mayorista');
        const head=text('div','ai-price ai-price-head','');head.append(text('span','','Pago'),text('span','','Descuento'),text('span','','Tu precio'));prices.append(head);
      }
      const cuotas=cuotasDe(amounts);
      [amounts.dolares,amounts.bancoUsa,amounts.usdt,amounts.pesos,amounts.pesosTransf,...cuotas.map(c=>c.total)].forEach((v,j)=>{
        const label=j>=5?cuotas[j-5].etiqueta:labels[j];
        const row=text('div','ai-price',''), value=text('strong','',(v==null?'Consultar':(j<2?'USD ':j===2?'USDT ':'$ ')+Number(v).toLocaleString('es-AR')));
        if(filasMay)row.append(text('span','',label),text('span','ai-desc',filasMay[j].descuento?'-'+filasMay[j].descuento:'-'),value);
        else row.append(text('span','',label),value);
        prices.append(row);
      });
      // La cara está pensada para 5 precios (6 filas en mayorista). Si alguna card de la grilla
      // tiene líneas de cuotas, TODAS se estiran igual (una fila por precio extra).
      const base=filasMay?6:5, filas=Math.max(prices.children.length,maxFilas);
      if(filas>base){
        const fila=32/base;
        face.classList.add('ai-face-extra');
        face.style.setProperty('--alto-precios',`${filas*fila}cqw`);
        face.style.aspectRatio=`100 / ${(100+(filas-base)*fila).toFixed(2)}`;
      }
      const marker=document.createComment('original product actions');links.before(marker);
      face.append(logo,name,color,picture,prices,links); card.prepend(face);
      title.hidden=true; oldPrices.hidden=true; card.classList.add('ai-card');grid?.classList.add('has-ai-cards');
      let alive=true, serial=0;
      function fallback(){
        if(!alive)return;alive=false;marker.replaceWith(links);face.remove();title.hidden=false;oldPrices.hidden=false;card.classList.remove('ai-card');
        if(!grid?.querySelector('.ai-card'))grid?.classList.remove('has-ai-cards');
      }
      function showPlaceholder(c){
        if(!alive)return;
        actual=null; habilitarZoom(false);
        const replacement=new Image(); replacement.alt='Imagen no disponible'; replacement.src=placeholder; replacement.onerror=fallback;
        picture.replaceChildren(replacement); color.textContent=c||'Imagen de referencia';
      }
      // Tocar la imagen la amplía en el visor (fondo difuminado y un solo botón Cerrar), igual que los usados.
      let actual=null;
      function habilitarZoom(on){
        picture.classList.toggle('ai-picture-zoom',on);
        if(on){picture.setAttribute('role','button');picture.tabIndex=0;picture.setAttribute('aria-label','Ampliar imagen de '+p.nombre);}
        else{picture.removeAttribute('role');picture.removeAttribute('tabindex');picture.removeAttribute('aria-label');}
      }
      function ampliar(e){
        if(!actual||actual.src===placeholder||picture.classList.contains('ai-picture-fotos'))return;
        e.stopPropagation();
        abrirVisor([zoomDe(actual.src)],0,p.nombre+' · '+(actual.color||'Imagen de referencia'),picture,[actual.src],true);
      }
      picture.addEventListener('click',ampliar);
      picture.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();ampliar(e);}});
      habilitarZoom(true);
      function selectColor(c, initial=false){
        const v=variants.find(v=>colorKey(v.color)===colorKey(c==='Color único'?null:c)) || (initial?variants[0]:null);
        if(!v){fallback();return;}
        const token=++serial; actual=v;
        // Usados con fotos reales: carrusel que se amplía al tocarlo (solo equipos "Usado").
        if(esUsado(p)&&v.fotos?.length>1){
          picture.classList.add('ai-picture-fotos'); habilitarZoom(false);
          picture.replaceChildren(carrusel(v.fotos,p.nombre+' · '+(v.color||'')));
          color.textContent=v.color||'Imagen de referencia';return;
        }
        picture.classList.remove('ai-picture-fotos'); habilitarZoom(true);
        if(initial){img.src=v.src;img.alt=p.nombre+' · '+(v.color||'Imagen de referencia');img.onerror=()=>v.src===placeholder?fallback():showPlaceholder(v.color);color.textContent=v.color||'Imagen de referencia';return;}
        const next=new Image(); next.src=v.src;
        next.decode().then(()=>{
          if(!alive||token!==serial)return;
          next.alt=p.nombre+' · '+(v.color||'Imagen de referencia'); next.className='ai-enter';picture.append(next);
          requestAnimationFrame(()=>requestAnimationFrame(()=>next.classList.remove('ai-enter')));
          setTimeout(()=>{if(alive) [...picture.children].filter(n=>n!==picture.lastElementChild).forEach(n=>n.remove());},480);
          color.textContent=v.color||'Imagen de referencia';
        }).catch(()=>{if(token===serial)showPlaceholder(v.color);});
      }
      const select=card.querySelector('select'), dropdown=card.querySelector('.dropdown-color-boton');
      selectColor(select?.value||dropdown?.dataset.valor,true);
      select?.addEventListener('change',()=>selectColor(select.value));
      card.querySelectorAll('.dropdown-color-lista li').forEach(li=>li.addEventListener('click',()=>selectColor(li.dataset.valor)));
      // Keep original photo/specification links and all existing comparison/share handlers.
      const spec=[...links.querySelectorAll('a')].find(a=>a.href.includes('especificaciones'));
      if(spec)links.prepend(spec);
      if(!container.querySelector('.ai-notice')){
        const notice=text('p','ai-notice','Imágenes generadas por IA. Son ilustrativas y pueden diferir del producto real.');
        grid?.before(notice);
      }
    });
  }
  window.TTRACatalogImages={enhance};
})();
