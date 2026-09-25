(() => {
  const params = new URLSearchParams(location.search);
  const a = params.get('a'), b = params.get('b');
  const content = document.getElementById('comparison-content'), message = document.getElementById('comparison-message');
  const controller = new AbortController();
  let products = [], fields = [], states = [], attempts = [0,0];
  const timers = new Set();
  window.addEventListener('pagehide', () => { controller.abort(); timers.forEach(clearTimeout); });
  window.addEventListener('pageshow', event => { if (event.persisted) location.reload(); });
  const el = (tag, text, className) => { const node = document.createElement(tag); if(text != null) node.textContent = text; if(className) node.className = className; return node; };
  function sourceLink(url, title) {
    try {
      const target = new URL(url);
      if (!['https:', 'http:'].includes(target.protocol) || target.username || target.password) return el('span', title);
      const link = el('a', title); link.href = target.href; link.target = '_blank'; link.rel = 'noopener noreferrer'; return link;
    } catch { return el('span', title); }
  }
  function renderFacts() {
    const facts = document.getElementById('comparison-facts'); facts.replaceChildren();
    fields.forEach(field => {
      const row = el('div', null, 'comparison-fact-row');
      products.forEach((product, i) => {
        const cell = el('section', null, 'comparison-fact'); cell.setAttribute('aria-label', `${field.label} de ${product.nombre}`);
        cell.append(el('h3', field.label)); const list = el('ul');
        const fact = product.sheet?.attributes.find(fact => fact.key === field.key);
        list.append(el('li', fact?.value || (states[i] === 'loading' ? 'Consultando fuentes…' : 'No confirmado')));
        cell.append(list);
        (fact?.source_urls || []).forEach((url, index) => cell.append(sourceLink(url, `Fuente ${index + 1}`)));
        row.append(cell);
      }); facts.append(row);
    });
    const sources = document.getElementById('comparison-sources'); sources.replaceChildren();
    products.forEach((product, i) => {
      const section = el('section', null, 'comparison-source'); section.setAttribute('aria-label', `Fuentes de ${product.nombre}`);
      section.append(el('h3', 'Fuentes consultadas'));
      const status = el('p', states[i] === 'loading' ? 'Buscando y verificando la ficha…' : ''); status.setAttribute('role', 'status'); section.append(status);
      if (product.sheet) {
        status.textContent = 'Consulta: ' + new Date(product.sheet.fetched_at * 1000).toLocaleDateString('es-AR');
        product.sheet.sources.forEach(source => section.append(sourceLink(source.url, source.title || new URL(source.url).hostname)));
        if (product.sheet.search_suggestions) {
          const widget = document.createElement('iframe'); widget.className = 'comparison-search-suggestions';
          widget.title = 'Sugerencias de Google Search';
          widget.setAttribute('sandbox', 'allow-popups allow-popups-to-escape-sandbox');
          widget.referrerPolicy = 'no-referrer';
          widget.srcdoc = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src https: data:; base-uri \'none\'; form-action \'none\'">' + product.sheet.search_suggestions;
          section.append(widget);
        }
      } else if (states[i] !== 'loading') {
        status.textContent = states[i]; const retry = el('button', 'Reintentar'); retry.type = 'button'; retry.addEventListener('click', () => { attempts[i] = 0; loadSheet(i); }); section.append(retry);
      }
      sources.append(section);
    });
  }
  async function loadSheet(index) {
    if (controller.signal.aborted) return;
    states[index] = 'loading'; renderFacts(); attempts[index]++;
    try {
      const response = await fetch('/api/comparativa/ficha', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({a,b,product:products[index].id}), signal:controller.signal});
      const data = await response.json();
      if (data.status === 'ready' && data.sheet) { products[index].sheet = data.sheet; states[index] = 'ready'; }
      else if (data.status === 'pending' && attempts[index] < 15) {
        const timer = setTimeout(() => { timers.delete(timer); loadSheet(index); }, 5000); timers.add(timer); return;
      } else states[index] = data.message || 'No pude verificar la ficha por el momento.';
    } catch (error) { if (error.name === 'AbortError') return; states[index] = 'No pude cargar la ficha. Probá nuevamente.'; }
    renderFacts();
  }
  function setupShare() {
    const button = document.getElementById('comparison-share');
    const title = `Comparativa: ${products[0].nombre} vs ${products[1].nombre} — The Tech Room Arg`;
    button.hidden = false;
    button.addEventListener('click', async () => {
      const url = location.href;
      if (navigator.share) {
        try { await navigator.share({title, text: title, url}); return; }
        catch (error) { if (error.name === 'AbortError') return; }
      }
      try { await navigator.clipboard.writeText(url); window.TTRACarrito?.notificar('Link copiado. Ya lo podés pegar donde quieras.'); }
      catch { window.prompt('Copiá este link para compartir la comparativa:', url); }
    });
  }
  function renderCart() {
    const section = document.getElementById('comparison-cart'); section.replaceChildren();
    products.forEach(p => {
      const block = el('div', null, 'comparison-cart-item');
      block.append(el('h3', p.nombre));
      const colores = Array.isArray(p.colores) ? p.colores : [];
      let select = null;
      if (colores.length > 1) {
        select = el('select'); select.setAttribute('aria-label', `Color de ${p.nombre}`);
        select.append(el('option', 'Elegí un color')); select.options[0].value = '';
        colores.forEach(color => { const option = el('option', color); option.value = color; select.append(option); });
        block.append(select);
      }
      const button = el('button', 'Agregar al carrito', 'comparison-add'); button.type = 'button';
      button.addEventListener('click', () => {
        if (!window.TTRACarrito) return;
        const color = select ? select.value : (colores[0] || null);
        if (select && !color) { window.TTRACarrito.notificar(`Elegí un color para ${p.nombre}.`, true); select.focus(); return; }
        try { window.TTRACarrito.agregar(p, color); window.TTRACarrito.animar(button); }
        catch { window.TTRACarrito.notificar('No pude guardar el producto en el carrito. Probá de nuevo.', true); }
      });
      block.append(button); section.append(block);
    });
  }
  async function init() {
    if (!/^[a-f0-9]{64}$/.test(a || '') || !/^[a-f0-9]{64}$/.test(b || '') || a === b) { message.textContent = 'Elegí dos productos de la misma categoría desde el catálogo.'; return; }
    try {
      const response = await fetch(`/api/comparativa?${new URLSearchParams({a,b})}`, {signal:controller.signal});
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'No pude abrir esta comparación.');
      products = data.products; fields = data.fields;
      states = products.map(p => p.sheet ? 'ready' : 'loading');
      const cards = document.getElementById('comparison-products');
      products.forEach((p, i) => {
        const card = el('article', null, 'comparison-product'); card.append(el('span', i === 0 ? 'TU PRIMER EQUIPO' : 'PARA COMPARAR', 'comparison-number'), el('h2', p.nombre));
        const prices = preciosDe(p), price = el('div', null, 'comparison-price');
        const amount = value => value == null ? '—' : Number(value).toLocaleString('es-AR');
        price.append(el('strong', `U$D ${amount(prices.dolares)} (contado)`));
        for (const text of [`U$D ${amount(prices.bancoUsa)} (Transf. USA)`, `USDT ${amount(prices.usdt)}`, `$ ${amount(p.pesos)} Pesos contado.`, `$ ${amount(p.transferencia)} Pesos transf.`]) price.append(el('div', text));
        card.append(price);
        if(p.colores?.length) card.append(el('p', p.colores.join(' · '), 'comparison-variants'));
        const link = el('a', 'Ver en el catálogo'); link.href = '/catalogo?' + new URLSearchParams({categoria:p.seccion, buscar:'1', q:p.nombre}); card.append(link); cards.append(card);
      });
      message.hidden = true; content.hidden = false; renderFacts(); renderCart(); setupShare();
      products.forEach((p, i) => { if (!p.sheet) loadSheet(i); });
    } catch (error) { if (error.name !== 'AbortError') message.textContent = error.message || 'No pude cargar los productos.'; }
  }
  init();
})();
