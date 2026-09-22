// Shared storefront navigation; the home keeps its existing account/cart panels.
(() => {
  const root = document.documentElement;
  import('/adaptive-dropdowns.js');
  if (root.classList.contains('ttra-cart-embedded')) {
    const panel = document.getElementById('panel-carrito');
    let opened = false;
    const syncPanel = () => {
      if (!panel.classList.contains('oculto')) {
        opened = true;
        parent.postMessage({type:'ttra:cart-ready'}, location.origin);
      } else if (opened) parent.postMessage({type:'ttra:cart-close'}, location.origin);
    };
    new MutationObserver(syncPanel).observe(panel, {attributes:true,attributeFilter:['class']});
    syncPanel();
    for (const id of ['btn-cerrar-carrito', 'overlay-carrito']) {
      document.getElementById(id).addEventListener('click', () => parent.postMessage({type:'ttra:cart-close'}, location.origin));
    }
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        parent.postMessage({type:'ttra:cart-close'}, location.origin);
      }
    });
    return;
  }
  const header = document.querySelector('body > header');
  if (!header || root.dataset.modo !== 'classic') return;
  header.classList.add('ttra-site-header');

  const forest = document.createElement('div');
  forest.className = 'ttra-ambient-bamboo';
  forest.setAttribute('aria-hidden', 'true');
  forest.setAttribute('inert', '');
  // Deterministic silhouettes: no image downloads or per-frame JavaScript.
  const bamboo = (x, index, distant) => {
    const width = distant ? 8 : 15;
    const top = -90 + (index % 4) * 48;
    const lean = (index % 3 - 1) * 22;
    const nodes = Array.from({length: 9}, (_, n) => {
      const y = 970 - n * 125;
      const branch = n > 2 && (n + index) % 2 === 0;
      const side = (n + index) % 3 === 0 ? -1 : 1;
      return `<path class="ttra-bamboo-node" d="M${-width / 2 - 2} ${y}Q0 ${y + 3} ${width / 2 + 2} ${y}"/>
        ${branch ? `<g transform="translate(0 ${y}) scale(${side} 1)">
          <g class="ttra-bamboo-leaves">
            <path class="ttra-bamboo-branch" d="M0 0Q43 -55 120 -78M35 -38Q60 -80 65 -107M69 -60Q106 -40 144 -48"/>
            <path d="M25 -29Q12 -67 17 -87Q38 -71 25 -29Z
              M41 -45Q35 -88 48 -108Q57 -77 41 -45Z
              M56 -54Q71 -96 94 -104Q83 -72 56 -54Z
              M77 -65Q104 -104 135 -108Q116 -79 77 -65Z
              M101 -74Q143 -94 163 -84Q133 -68 101 -74Z
              M43 -43Q75 -43 87 -19Q57 -22 43 -43Z
              M78 -54Q104 -42 111 -17Q88 -23 78 -54Z
              M106 -48Q138 -40 148 -20Q119 -23 106 -48Z
              M61 -87Q46 -119 53 -139Q70 -119 61 -87Z"/>
          </g>
        </g>` : ''}`;
    }).join('');
    return `<g transform="translate(${x} 0)">
      <g class="ttra-bamboo-stalk ${distant ? 'is-distant' : 'is-near'}" style="--bamboo-duration:${13 + index % 5 * 2}s;--bamboo-delay:-${index * 2.7}s;--bamboo-lean:${lean / 20}deg">
        <path class="ttra-bamboo-trunk" d="M${-width / 2} 1080Q${-width / 2 - 5} 550 ${lean - width / 3} ${top}L${lean + width / 3} ${top}Q${width / 2 - 5} 550 ${width / 2} 1080Z"/>
        <path class="ttra-bamboo-highlight" d="M${-width / 4} 1080Q${-width / 4 - 5} 550 ${lean} ${top}"/>
        ${nodes}
      </g>
    </g>`;
  };
  forest.innerHTML = `<svg viewBox="0 0 1440 1000" preserveAspectRatio="xMidYMid slice" focusable="false" xmlns="http://www.w3.org/2000/svg">
    ${Array.from({length: 13}, (_, i) => bamboo(25 + i * 119, i, true)).join('')}
    ${[65, 230, 405, 590, 790, 995, 1190, 1390].map((x, i) => bamboo(x, i + 13, false)).join('')}
  </svg>`;
  document.body.classList.add('ttra-has-bamboo');
  document.body.prepend(forest);
  const pauseForest = () => forest.classList.toggle('is-paused', document.hidden);
  document.addEventListener('visibilitychange', pauseForest);
  pauseForest();

  // Reuse the home contact footer on every storefront page, including products.
  const previousFooter = document.querySelector('body > .ttra-page-footer');
  if (previousFooter) {
    const template = document.createElement('template');
    template.innerHTML = `<footer class="rc-pie">
    <h2 class="ttra-footer-title ttra-editorial">Vías de contacto:</h2>
    <div class="rc-redes">
      <a href="https://instagram.com/thetechroomarg" target="_blank" rel="noopener" aria-label="Instagram" class="rc-red-icono">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" stroke-width="1.6"/>
          <circle cx="12" cy="12" r="4.2" fill="none" stroke="currentColor" stroke-width="1.6"/>
          <circle cx="17.4" cy="6.6" r="1.1" fill="currentColor"/>
        </svg>
      </a>
      <a href="https://tiktok.com/@thetechroomarg" target="_blank" rel="noopener" aria-label="TikTok" class="rc-red-icono">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path fill="currentColor" d="M16.5 3c.4 2.2 1.8 3.6 4 3.9v2.6c-1.4.1-2.8-.3-4-1.1v6.4c0 3.3-2.7 5.7-5.7 5.4-2.6-.2-4.7-2.4-4.8-5-.1-3 2.3-5.5 5.3-5.5.3 0 .6 0 .9.1v2.7a2.7 2.7 0 0 0-3.3 2.9c.1 1.3 1.2 2.4 2.5 2.5 1.6.1 2.9-1.1 2.9-2.7V3h2.2z"/>
        </svg>
      </a>
      <a href="https://wa.me/543512145217" target="_blank" rel="noopener" aria-label="WhatsApp" class="rc-red-icono">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path fill="currentColor" d="M12 2.5c-5.24 0-9.5 4.26-9.5 9.5 0 1.68.44 3.28 1.28 4.7L2.5 21.5l4.94-1.25a9.46 9.46 0 0 0 4.56 1.16c5.24 0 9.5-4.26 9.5-9.5s-4.26-9.41-9.5-9.41zm0 17.15c-1.46 0-2.86-.4-4.08-1.14l-.29-.17-3 .76.79-2.9-.19-.3a7.8 7.8 0 0 1-1.23-4.2c0-4.32 3.53-7.85 7.85-7.85S19.85 7.68 19.85 12 15.85 19.65 12 19.65zm4.3-5.85c-.24-.12-1.4-.69-1.62-.77-.22-.08-.38-.12-.54.12-.16.24-.62.77-.76.93-.14.16-.28.18-.52.06-.24-.12-1.01-.37-1.92-1.18-.71-.63-1.19-1.41-1.33-1.65-.14-.24-.01-.37.11-.49.11-.11.24-.28.36-.42.12-.14.16-.24.24-.4.08-.16.04-.3-.02-.42-.06-.12-.54-1.3-.74-1.78-.19-.46-.39-.4-.54-.41h-.46c-.16 0-.42.06-.64.3-.22.24-.84.82-.84 2s.86 2.32.98 2.48c.12.16 1.7 2.6 4.13 3.64.58.25 1.03.4 1.38.51.58.18 1.11.16 1.53.1.47-.07 1.4-.57 1.6-1.12.2-.55.2-1.02.14-1.12-.06-.1-.22-.16-.46-.28z"/>
        </svg>
      </a>
      <a href="mailto:thetechroomarg@gmail.com" aria-label="Email" class="rc-red-icono">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <rect x="3" y="5" width="18" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"/>
          <path d="M4 6.5 12 13 20 6.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </a>
    </div>
  </footer>`;
    previousFooter.replaceWith(template.content);
  }


  function measureHeader() {
    root.style.setProperty('--ttra-header-height', `${header.offsetHeight}px`);
  }
  new ResizeObserver(measureHeader).observe(header);
  measureHeader();

  // Returning from an internal page must not replay the welcome screen.
  header.addEventListener('click', (event) => {
    if (!event.target.closest('a[href]')) return;
    try { sessionStorage.setItem('ttra_portada_vista', '1'); } catch {}
  });
  const rate = document.createElement('span');
  rate.className = 'ttra-site-rate';
  rate.textContent = 'Dólar · …';
  // This endpoint reads the exchange rate published with productos.json.
  async function updateRate() {
    try {
      const response = await fetch('/api/cotizacion', {cache: 'no-store'});
      if (!response.ok) throw new Error('cotizacion');
      const {valor} = await response.json();
      if (typeof valor !== 'number' || !Number.isFinite(valor) || valor <= 0) throw new Error('cotizacion');
      rate.textContent = `Dólar · $${new Intl.NumberFormat('es-AR', {maximumFractionDigits: 2}).format(valor)}`;
      rate.dataset.loaded = 'true';
    } catch {
      if (!rate.dataset.loaded) rate.textContent = 'Dólar · no disponible';
    }
  }
  updateRate();
  setInterval(() => { if (!document.hidden) updateRate(); }, 300000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) updateRate(); });
  if (document.body.id === 'rc-body-landing') {
    const homeActions = header.querySelector('.rc-modo-y-carrito');
    homeActions.prepend(rate);
    homeActions.insertBefore(homeActions.querySelector('.ttra-theme'), homeActions.querySelector('.rc-perfil-menu'));
    return;
  }

  const previousActions = header.querySelector('.ttra-page-actions');
  const actions = document.createElement('nav');
  actions.className = 'ttra-site-actions';
  actions.setAttribute('aria-label', 'Mi cuenta y carrito');
  actions.innerHTML = `
    <div class="ttra-site-account">
      <button type="button" class="ttra-site-profile" aria-label="Mi cuenta" aria-expanded="false" aria-controls="ttra-site-menu">
        <span class="ttra-site-initials"></span>
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="11" fill="none" stroke="currentColor" stroke-width="1.4"/><circle cx="12" cy="9.5" r="3.6" fill="currentColor"/><path d="M4.8 19.2c1.1-3.4 3.9-5.2 7.2-5.2s6.1 1.8 7.2 5.2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
      </button>
      <div id="ttra-site-menu" class="ttra-site-menu" hidden>
        <a class="ttra-site-profile-link" href="/perfil">Ir a perfil</a>
        <a href="/catalogo">Explorar catálogo</a>
        <button type="button" class="ttra-site-logout" hidden>Cerrar sesión</button>
        <p class="ttra-site-error" role="status" hidden></p>
      </div>
    </div>
    <button class="ttra-theme" type="button" aria-label="Cambiar tema" title="Cambiar tema">◐</button>
    <button class="ttra-site-cart" type="button" aria-haspopup="dialog">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
      Carrito <span class="ttra-site-count">0</span>
    </button>`;
  const tools = document.createElement('div');
  tools.className = 'ttra-site-tools';
  actions.prepend(rate);
  actions.insertBefore(actions.querySelector('.ttra-theme'), actions.querySelector('.ttra-site-account'));
  tools.append(actions);
  if (previousActions) previousActions.replaceWith(tools);
  else header.appendChild(tools);

  const cartButton = actions.querySelector('.ttra-site-cart');
  cartButton.addEventListener('click', async () => {
    closeMenu();
    cartButton.disabled = true;
    try {
      const {abrirCarritoEnPagina} = await import('/cart-drawer.js');
      abrirCarritoEnPagina(cartButton);
    } catch {
      const error = actions.querySelector('.ttra-site-error');
      error.textContent = 'No pude abrir el carrito. Probá de nuevo.';
      error.hidden = false;
      menu.hidden = false;
    } finally { cartButton.disabled = false; }
  });

  const toggle = actions.querySelector('.ttra-site-profile');
  const menu = actions.querySelector('.ttra-site-menu');
  const overlay = document.createElement('div');
  overlay.id = 'overlay-perfil';
  overlay.className = 'oculto';
  overlay.setAttribute('aria-hidden', 'true');
  document.body.appendChild(overlay);

  function closeMenu(restoreFocus = false) {
    menu.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    overlay.classList.add('oculto');
    root.classList.remove('ttra-menu-open');
    if (restoreFocus) toggle.focus();
  }
  toggle.addEventListener('click', () => {
    if (!menu.hidden) { closeMenu(); return; }
    menu.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    overlay.classList.remove('oculto');
    root.classList.add('ttra-menu-open');
  });
  overlay.addEventListener('click', () => closeMenu(true));
  document.addEventListener('click', (event) => {
    if (!actions.querySelector('.ttra-site-account').contains(event.target)) closeMenu();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) closeMenu(true);
  });
  actions.addEventListener('focusout', () => {
    queueMicrotask(() => {
      if (!actions.querySelector('.ttra-site-account').contains(document.activeElement)) closeMenu();
    });
  });

  const themeButton = actions.querySelector('.ttra-theme');
  function updateThemeLabel() {
    const label = root.dataset.classicTheme === 'light' ? 'Activar modo oscuro' : 'Activar modo claro';
    themeButton.setAttribute('aria-label', label);
    themeButton.title = label;
  }
  themeButton.addEventListener('click', () => {
    root.dataset.classicTheme = root.dataset.classicTheme === 'light' ? 'dark' : 'light';
    try { localStorage.setItem('ttra_classic_theme', root.dataset.classicTheme); } catch {}
    updateThemeLabel();
  });
  updateThemeLabel();

  function updateCartCount() {
    let count = 0;
    try {
      const cart = JSON.parse(localStorage.getItem('ttra_carrito') || '[]');
      if (Array.isArray(cart)) count = cart.reduce((total, item) => total + Math.max(0, Number(item.cantidad) || 0), 0);
    } catch {}
    actions.querySelector('.ttra-site-count').textContent = count;
  }
  updateCartCount();
  window.addEventListener('ttra:cart-change', updateCartCount);
  window.addEventListener('storage', (event) => {
    if (event.key === 'ttra_carrito' || event.key === null) updateCartCount();
    if (event.key === 'ttra_classic_theme' || event.key === null) {
      root.dataset.classicTheme = event.newValue === 'light' ? 'light' : 'dark';
      updateThemeLabel();
    }
  });

  const profileLink = actions.querySelector('.ttra-site-profile-link');
  const logout = actions.querySelector('.ttra-site-logout');
  const loginParams = new URLSearchParams({ volver: location.pathname + location.search });
  profileLink.href = `/login.html?${loginParams}`;
  profileLink.textContent = 'Iniciar sesión';
  async function updateSession() {
    try {
      const response = await fetch('/api/me');
      if (!response.ok) return;
      const account = await response.json();
      profileLink.href = '/perfil';
      profileLink.textContent = 'Ir a perfil';
      actions.querySelector('.ttra-site-initials').textContent =
        [account.nombre, account.apellido].map((name) => (name || '').trim().charAt(0).toUpperCase()).join('');
      logout.hidden = false;
    } catch { /* Public navigation remains usable if session lookup fails. */ }
  }
  logout.addEventListener('click', async () => {
    logout.disabled = true;
    const error = actions.querySelector('.ttra-site-error');
    error.hidden = true;
    try {
      const response = await fetch('/logout', { method: 'POST' });
      if (!response.ok) throw new Error('logout');
      try { localStorage.removeItem('ttra_cliente'); } catch {}
      location.href = '/';
    } catch {
      error.textContent = 'No pude cerrar la sesión. Probá de nuevo.';
      error.hidden = false;
      logout.disabled = false;
    }
  });
  updateSession();
})();
