/* One picker implementation for catalog cards and legacy landing cards. */
(() => {
  let active = null, serial = 0;
  const normalize = value => String(value || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const ids = new Map();
  function productId(name) {
    if (!ids.has(name)) ids.set(name, crypto.subtle.digest('SHA-256', new TextEncoder().encode(name))
      .then(buffer => [...new Uint8Array(buffer)].map(byte => byte.toString(16).padStart(2, '0')).join('')));
    return ids.get(name);
  }
  function close(focus = false) {
    if (!active) return;
    const old = active; active = null;
    old.panel.remove(); old.button.setAttribute('aria-expanded', 'false');
    if (focus) old.button.focus();
  }
  const buttonHtml = () => `<button type="button" class="btn-foto btn-comparar" aria-label="Comparar producto" title="Comparar producto" aria-expanded="false"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="5" cy="5" r="3"/><circle cx="19" cy="19" r="3"/><path d="M5 8v6a5 5 0 0 0 5 5h3m-3-3 3 3-3 3M19 16v-6a5 5 0 0 0-5-5h-3m3-3-3 3 3 3"/></svg></button>`;
  const returnPrefix = 'ttra-comparison-return:';
  function readReturn(parameter = 'restaurar') {
    try {
      const token = new URLSearchParams(location.search).get(parameter);
      if (!token || !/^[a-zA-Z0-9-]{1,80}$/.test(token)) return null;
      const state = JSON.parse(sessionStorage.getItem(returnPrefix + token));
      const url = new URL(state.url, location.origin);
      if (url.origin !== location.origin || !['/', '/catalogo'].includes(url.pathname)) return null;
      return {...state, token};
    } catch { return null; }
  }
  function screenTop(card) {
    return card.getBoundingClientRect().top + (window.frameElement?.getBoundingClientRect().top || 0);
  }
  function restorePosition() {
    const state = readReturn();
    if (!state) return;
    const card = [...document.querySelectorAll('.card')].find(c => c.dataset.compareName === state.name);
    if (!card) return;
    const select = card.querySelector('select');
    if (select && state.color && [...select.options].some(o => o.value === state.color)) {
      select.value = state.color; select.dispatchEvent(new Event('change', {bubbles: true}));
    }
    let stopped = false;
    const stop = () => { stopped = true; observer.disconnect(); };
    const align = () => {
      if (stopped || !card.isConnected) return;
      const delta = screenTop(card) - state.top;
      if (Math.abs(delta) > 1) window.scrollBy({top: delta, behavior: 'instant'});
    };
    const observer = new ResizeObserver(align);
    observer.observe(document.body);
    for (const event of ['wheel', 'touchstart', 'pointerdown', 'keydown']) window.addEventListener(event, stop, {once: true, passive: true});
    requestAnimationFrame(() => requestAnimationFrame(align));
    document.fonts?.ready.then(align);
    setTimeout(stop, 2500);
  }
  function bind(container, products, sections, getContext = () => ({})) {
    container.querySelectorAll('.card').forEach((card, index) => {
      const product = products[index];
      const button = card.querySelector('.btn-comparar');
      if (!product || !button || button.dataset.compareBound) return;
      button.dataset.compareBound = '1';
      card.dataset.compareName = product.nombre;
      button.addEventListener('click', async event => {
        event.stopPropagation();
        if (active?.button === button) { close(true); return; }
        close();
        const returnState = {url: location.pathname + location.search, name: product.nombre,
          top: screenTop(card), color: card.querySelector('select')?.value || '', context: getContext()};
        const token = crypto.randomUUID();
        try { sessionStorage.setItem(returnPrefix + token, JSON.stringify(returnState)); } catch {}
        const section = Object.keys(sections).find(key => sections[key].some(p => p.nombre === product.nombre));
        const candidates = (sections[section] || []).filter(p => p.nombre !== product.nombre);
        const panel = document.createElement('section'); panel.className = 'compare-picker';
        const id = `compare-search-${++serial}`;
        panel.innerHTML = `<div class="compare-picker-heading"><label for="${id}">Comparar con</label><button type="button" class="compare-close" aria-label="Cerrar comparación">×</button></div><input id="${id}" type="search" role="combobox" aria-autocomplete="list" aria-expanded="true" aria-controls="${id}-results" placeholder="Buscá otro producto" autocomplete="off"><p class="compare-picker-message" role="status"></p><ul id="${id}-results" role="listbox" aria-label="Productos para comparar"></ul>`;
        panel.addEventListener('click', e => { if (!e.target.closest('a')) e.stopPropagation(); });
        card.append(panel); button.setAttribute('aria-expanded', 'true');
        const state = {panel, button}; active = state;
        panel.querySelector('.compare-close').addEventListener('click', () => close(true));
        const input = panel.querySelector('input'), results = panel.querySelector('ul'), message = panel.querySelector('[role="status"]');
        input.focus(); message.textContent = 'Preparando productos…';
        let options = [], selected = -1;
        function highlight(index) {
          selected = index;
          options.forEach((option, i) => option.setAttribute('aria-selected', String(i === index)));
          if (options[index]) { input.setAttribute('aria-activedescendant', options[index].id); options[index].scrollIntoView({block:'nearest'}); }
          else input.removeAttribute('aria-activedescendant');
        }
        input.addEventListener('keydown', event => {
          if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(true); }
          if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
            event.preventDefault(); highlight(options.length ? (selected + (event.key === 'ArrowDown' ? 1 : -1) + options.length) % options.length : -1);
          }
          if (event.key === 'Enter') { event.preventDefault(); options[selected]?.querySelector('a').click(); }
        });
        try {
          const originId = await productId(product.nombre);
          const matches = await Promise.all(candidates.map(async p => ({...p, id: await productId(p.nombre)})));
          if (active !== state) return;
          function render() {
            results.replaceChildren(); selected = -1; input.removeAttribute('aria-activedescendant');
            const query = normalize(input.value.trim());
            const filtered = matches.filter(p => normalize(`${p.nombre} ${p.marca || ''}`).includes(query));
            message.textContent = filtered.length ? `${filtered.length} productos en ${section}.` : 'No encontré productos de esta categoría.';
            filtered.slice(0, 12).forEach((p, i) => {
              const li = document.createElement('li'); li.id = `${id}-option-${i}`; li.setAttribute('role', 'option'); li.setAttribute('aria-selected', 'false');
              const a = document.createElement('a'); a.href = `/comparativa?${new URLSearchParams({a:originId, b:p.id, retorno:token})}`; a.textContent = p.nombre;
              li.append(a); results.append(li);
            });
            options = [...results.children];
          }
          input.addEventListener('input', render); render();
        } catch { if (active === state) message.textContent = 'No pude preparar la comparación. Cerrá y probá de nuevo.'; }
      });
    });
  }
  document.addEventListener('click', event => { if (active && !active.panel.contains(event.target) && !active.button.contains(event.target)) close(); });
  document.addEventListener('keydown', event => { if (active && event.key === 'Escape') { event.stopPropagation(); close(true); } });
  window.TTRAComparar = {buttonHtml, bind, readReturn, restorePosition};
  const saved = readReturn('retorno');
  document.querySelectorAll('[data-comparison-return]').forEach(link => {
    if (!saved) return;
    const url = new URL(saved.url, location.origin);
    url.searchParams.set('restaurar', saved.token);
    link.href = url.pathname + url.search;
  });
})();
