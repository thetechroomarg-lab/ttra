/* Optional artwork layer. Catalog data, prices and action handlers remain authoritative. */
(() => {
  const manifest = fetch('/catalog-images/index.json').then(r => r.ok ? r.json() : {}).catch(() => ({}));
  const placeholder='/catalog-images/placeholder-ttra-v2.png';
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
  const renders=new WeakMap();
  async function enhance(container, products) {
    const render={}; renders.set(container,render);
    const index = await manifest, keyed = await byKey;
    if (!container.isConnected || renders.get(container)!==render) return;
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
      const prices=text('div','ai-prices',''), amounts=preciosDe(p);
      [amounts.dolares,amounts.bancoUsa,amounts.usdt,amounts.pesos,amounts.pesosTransf].forEach((v,j)=>{
        const row=text('div','ai-price','');
        row.append(text('span','',labels[j]),text('strong','',(v==null?'Consultar':(j<2?'USD ':j===2?'USDT ':'$ ')+Number(v).toLocaleString('es-AR'))));prices.append(row);
      });
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
        const replacement=new Image(); replacement.alt='Imagen no disponible'; replacement.src=placeholder; replacement.onerror=fallback;
        picture.replaceChildren(replacement); color.textContent=c||'Imagen de referencia';
      }
      function selectColor(c, initial=false){
        const v=variants.find(v=>colorKey(v.color)===colorKey(c==='Color único'?null:c)) || (initial?variants[0]:null);
        if(!v){fallback();return;}
        const token=++serial;
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
