// Shared storefront navigation; the home keeps its existing account/cart panels.
(() => {
  const root = document.documentElement;
  const header = document.querySelector('body > header');
  if (!header || root.dataset.modo !== 'classic') return;
  header.classList.add('ttra-site-header');

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
    header.querySelector('.rc-header-derecha').appendChild(rate);
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
    <a class="ttra-site-cart" href="/?panel=carrito">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
      Carrito <span class="ttra-site-count">0</span>
    </a>`;
  const tools = document.createElement('div');
  tools.className = 'ttra-site-tools';
  tools.append(actions, rate);
  if (previousActions) previousActions.replaceWith(tools);
  else header.appendChild(tools);

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
