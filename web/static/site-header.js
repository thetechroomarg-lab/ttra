// Shared storefront navigation; the home keeps its existing account/cart panels.
(() => {
  const root = document.documentElement;
  if (document.body.classList.contains('vaiven-page') || /^\/vaiven\/?$/.test(location.pathname)) return;
  if (document.body.classList.contains('bitu-page') || /^\/bitu\/?$/.test(location.pathname)) return;
  if (document.body.classList.contains('fendi-page') || /^\/fendi\/?$/.test(location.pathname)) return;
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
  // login.html corriendo dentro del <dialog> de login-drawer.js: su propio
  // login.js maneja el postMessage de cierre/éxito, acá no hay nada más que
  // construir (el header/footer de esta página queda oculto por CSS).
  if (root.classList.contains('ttra-login-embedded')) return;
  const header = document.querySelector('body > header');
  if (!header || root.dataset.modo !== 'classic') return;
  header.classList.add('ttra-site-header');
  // Scroll progress: a thin fill sitting on the header's own bottom edge
  // (the "floor" the header-cat mascot walks on), tracking how far down
  // the page the visitor has scrolled. Lives here -not in a page-specific
  // script- so it mounts on every real storefront page and skips the
  // embedded cart/login sub-panels, which return before reaching this line.
  const scrollProgress = document.createElement('div');
  scrollProgress.className = 'ttra-scroll-progress';
  scrollProgress.setAttribute('aria-hidden', 'true');
  const scrollProgressFill = document.createElement('div');
  scrollProgressFill.className = 'ttra-scroll-progress-fill';
  scrollProgress.append(scrollProgressFill);
  header.append(scrollProgress);
  // Después de la primera navegación interna, cat-navigation.js mete el
  // resto del sitio dentro de un <iframe id="ttra-storefront-frame">
  // persistente -el header que se ve queda fijo afuera, con este script
  // corriendo en el documento de arriba, pero el scroll real pasa DENTRO
  // del iframe-. Enganchar listeners de scroll/resize al contentWindow de
  // ese iframe resultó poco confiable (cada navegación interna lo puede
  // reemplazar, y el evento 'load' no siempre llega a tiempo para
  // re-engancharlos), así que en vez de perseguir eventos entre ventanas
  // esto simplemente LEE el scroll actual en cada frame -mismo patrón que
  // ya usa el gatito del header (requestAnimationFrame continuo)-, que es
  // correcto sin importar qué documento sea el que scrollea de verdad.
  (function tick() {
    // Durante el instante de una navegación interna, el documento del
    // iframe puede quedar momentáneamente null/inaccesible -sin el
    // try/catch, esa excepción cortaba el loop entero (nunca se volvía a
    // pedir el próximo frame) y la barra quedaba congelada para siempre,
    // no solo desactualizada-.
    try {
      const frame = document.getElementById('ttra-storefront-frame');
      let doc = document.documentElement;
      if (frame && root.classList.contains('ttra-cat-shell') && frame.contentDocument) {
        doc = frame.contentDocument.documentElement;
      }
      const max = doc.scrollHeight - doc.clientHeight;
      const pct = max > 0 ? Math.min(100, Math.max(0, (doc.scrollTop / max) * 100)) : 0;
      scrollProgressFill.style.width = `${pct}%`;
      // header-cat.js lee esto para que los gatitos giren la cabeza y
      // sigan la puntita de la línea roja mientras avanza.
      window.__ttraScrollPct = pct;
    } catch {}
    requestAnimationFrame(tick);
  })();
  // The persistent host owns the masthead and mascot while page content navigates.
  let catHost;
  try { if (window.parent !== window) catHost = window.parent.TTRAHeaderCat; } catch { /* External embeds have no shared host. */ }
  if (catHost) {
    catHost.attach(document);
    if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',()=>catHost.ready?.(document),{once:true});
    else queueMicrotask(()=>catHost.ready?.(document));
  }
  else import('/header-cat.js');

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
  function mountDock(actions) {
    const profileContainer = actions.querySelector('.rc-perfil-menu, .ttra-site-account');
    const profileButton = profileContainer.querySelector('button');
    const dock = document.createElement('div');
    dock.className = 'ttra-dock';
    dock.setAttribute('role', 'navigation');
    dock.setAttribute('aria-label', 'Navegación principal');
    const svg = (paths) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
    const home = document.createElement('a');
    home.className = 'ttra-dock-home ttra-dock-control';
    home.href = '/';
    home.setAttribute('aria-label', 'Inicio');
    if (location.pathname === '/') home.setAttribute('aria-current', 'page');
    home.innerHTML = svg('<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>') + '<span class="ttra-dock-label">Inicio</span>';
    const categories = document.createElement('button');
    categories.type = 'button';
    categories.className = 'ttra-dock-categories ttra-dock-control';
    categories.setAttribute('aria-label', 'Categorías');
    categories.setAttribute('aria-expanded', 'false');
    categories.setAttribute('aria-controls', 'ttra-dock-categories');
    categories.innerHTML = svg('<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>') + '<span class="ttra-dock-label">Categorías</span>';
    const panel = document.createElement('div');
    panel.id = 'ttra-dock-categories';
    panel.className = 'ttra-dock-category-panel';
    panel.hidden = true;
    panel.setAttribute('aria-label', 'Categorías del catálogo');
    const links = [
      ['Todo el catálogo', '/catalogo'],
      ['Celulares', '/catalogo?categoria=Celulares'],
      ['Tablets', '/catalogo?categoria=Tablets'],
      ['Notebooks y Macbooks', '/catalogo?categoria=Notebooks%20y%20Macbooks'],
      ['Gaming', '/catalogo?categoria=Gaming'],
      ['Accesorios', '/catalogo?categoria=Accesorios%20Celulares'],
      ['Búsqueda por marca', '/catalogo?filtro=marca#catalog-filters'],
    ];
    for (const [title, href] of links) {
      const link = document.createElement('a');
      link.textContent = title; link.href = href; panel.append(link);
    }
    const contact = document.createElement('button');
    contact.type = 'button';
    contact.className = 'ttra-dock-contact ttra-dock-control';
    contact.setAttribute('aria-label', 'Vías de contacto');
    contact.setAttribute('aria-expanded', 'false');
    contact.setAttribute('aria-controls', 'ttra-dock-contact');
    contact.innerHTML = svg('<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4" ry="9"/><path d="M3 12h18M5 6.5h14M5 17.5h14"/>') + '<span class="ttra-dock-label">Contacto</span>';
    const contactPanel = document.createElement('div');
    contactPanel.id = 'ttra-dock-contact';
    contactPanel.className = 'ttra-dock-category-panel';
    contactPanel.hidden = true;
    contactPanel.setAttribute('aria-label', 'Vías de contacto');
    for (const source of document.querySelectorAll('body > footer .rc-redes a')) {
      const link = source.cloneNode(true);
      link.removeAttribute('class');
      const label = document.createElement('span');
      label.textContent = source.getAttribute('aria-label');
      link.append(label);
      contactPanel.append(link);
    }
    const closeContact = () => { contactPanel.hidden = true; contact.setAttribute('aria-expanded', 'false'); };
    contact.addEventListener('click', () => {
      const open = contactPanel.hidden;
      closeCategories();
      const profile = profileButton;
      if (profile?.getAttribute('aria-expanded') === 'true') profile.click();
      contactPanel.hidden = !open;
      contact.setAttribute('aria-expanded', String(open));
    });
    const closeCategories = () => { panel.hidden = true; categories.setAttribute('aria-expanded', 'false'); };
    profileButton.addEventListener('click', () => {
      closeCategories();
      closeContact();
    });
    categories.addEventListener('click', () => {
      const open = panel.hidden;
      closeContact();
      const profile = profileButton;
      if (profile?.getAttribute('aria-expanded') === 'true') profile.click();
      panel.hidden = !open;
      categories.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('click', event => {
      if (!contactPanel.contains(event.target) && !contact.contains(event.target)) closeContact();
      if (!panel.contains(event.target) && !categories.contains(event.target)) closeCategories();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !contactPanel.hidden) { closeContact(); contact.focus(); }
      if (event.key === 'Escape' && !panel.hidden) { closeCategories(); categories.focus(); }
    });
    dock.addEventListener('focusout', event => {
      if (event.relatedTarget && !dock.contains(event.relatedTarget)) { closeCategories(); closeContact(); }
    });
    const headerAccount = document.createElement('div');
    headerAccount.className = 'ttra-header-account';
    headerAccount.append(profileContainer, rate);
    header.append(headerAccount);
    const search = document.createElement('a');
    search.href = '/catalogo?buscar=1#catalog-search';
    search.className = 'ttra-dock-search ttra-dock-control';
    search.setAttribute('aria-label', 'Buscar productos');
    search.innerHTML = svg('<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>') + '<span class="ttra-dock-label">Buscar</span>';
    search.addEventListener('click', event => {
      const input = document.getElementById('catalog-search');
      if (input) { event.preventDefault(); input.closest('.catalog-search-wrap').hidden = false; input.scrollIntoView({block: 'center'}); input.focus({preventScroll: true}); }
    });
    actions.prepend(home, categories, search);
    actions.querySelector('#btn-carrito, .ttra-site-cart').before(contact);
    dock.append(actions, panel, contactPanel);
    const dockSection = document.createElement('section');
    dockSection.className = 'ttra-dock-section';
    dockSection.setAttribute('aria-label', 'Navegación del sitio');
    dockSection.append(dock);
    const footer = document.querySelector('body > footer');
    if (footer) footer.replaceWith(dockSection);
    else document.body.append(dockSection);
    document.body.classList.add('ttra-has-dock');
    for (const [selector, label] of [['#btn-carrito, .ttra-site-cart', 'Carrito']]) {
      const control = actions.querySelector(selector);
      control.classList.add('ttra-dock-control');
      const text = document.createElement('span');
      text.className = 'ttra-dock-label'; text.textContent = label; control.append(text);
    }
    // Pointer proximity reproduces the dock magnification without a framework.
    const controls = [...dock.querySelectorAll('.ttra-dock-control')];
    const reset = () => controls.forEach(control => control.style.removeProperty('--dock-lift'));
    dock.addEventListener('pointermove', event => {
      if (event.pointerType !== 'mouse' || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
      for (const control of controls) {
        const rect = control.getBoundingClientRect();
        const distance = Math.abs(event.clientX - rect.left - rect.width / 2);
        control.style.setProperty('--dock-lift', Math.max(0, 1 - distance / 100).toFixed(3));
      }
    });
    dock.addEventListener('pointerleave', reset);
  }
  const rate = document.createElement('span');
  rate.className = 'ttra-site-rate';
  const rateLabel = document.createElement('span');
  rateLabel.className = 'ttra-rate-label';
  rateLabel.textContent = 'Cotización dólar';
  const rateAmount = document.createElement('span');
  rateAmount.className = 'ttra-rate-amount';
  rateAmount.textContent = '…';
  rate.append(rateLabel, rateAmount);
  // This endpoint reads the exchange rate published with productos.json.
  async function updateRate() {
    try {
      const response = await fetch('/api/cotizacion', {cache: 'no-store'});
      if (!response.ok) throw new Error('cotizacion');
      const {valor} = await response.json();
      if (typeof valor !== 'number' || !Number.isFinite(valor) || valor <= 0) throw new Error('cotizacion');
      rateAmount.textContent = `$${new Intl.NumberFormat('es-AR', {maximumFractionDigits: 2}).format(valor)}`;
      rate.dataset.loaded = 'true';
    } catch {
      if (!rate.dataset.loaded) rateAmount.textContent = 'No disponible';
    }
  }
  updateRate();
  setInterval(() => { if (!document.hidden) updateRate(); }, 300000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) updateRate(); });
  if (document.body.id === 'rc-body-landing') {
    const homeActions = header.querySelector('.rc-modo-y-carrito');
    homeActions.prepend(rate);
    const theme = homeActions.querySelector('.ttra-theme');
    theme.classList.add('rc-perfil-opcion');
    theme.setAttribute('role', 'menuitem');
    homeActions.querySelector('#rc-perfil-dropdown').insertBefore(theme, homeActions.querySelector('#btn-logout-classic'));
    mountDock(homeActions);
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
        <a class="ttra-site-pedidos-link" href="/pedidos" hidden>Pedidos</a>
        <button type="button" class="ttra-site-logout" hidden>Cerrar sesión</button>
        <p class="ttra-site-error" role="status" hidden></p>
      </div>
    </div>
    <button class="ttra-theme" type="button" aria-label="Cambiar tema" title="Cambiar tema">◐</button>
    <button class="ttra-site-cart" type="button" aria-label="Abrir carrito" aria-haspopup="dialog">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="9" cy="21" r="1"/><circle cx="20" cy="21" r="1"/><path d="M1 1h4l2.68 13.39a2 2 0 0 0 2 1.61h9.72a2 2 0 0 0 2-1.61L23 6H6"/></svg>
      <span class="ttra-cart-label">Carrito</span> <span class="ttra-site-count">0</span>
    </button>`;
  const accountContainer = actions.querySelector('.ttra-site-account');
  const tools = document.createElement('div');
  tools.className = 'ttra-site-tools';
  actions.prepend(rate);
  actions.querySelector('.ttra-site-menu').insertBefore(actions.querySelector('.ttra-theme'), actions.querySelector('.ttra-site-logout'));
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
      const error = accountContainer.querySelector('.ttra-site-error');
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
    if (!accountContainer.contains(event.target)) closeMenu();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) closeMenu(true);
  });
  accountContainer.addEventListener('focusout', (event) => {
    // A disabled logout button temporarily loses focus while its request runs.
    // Keep the menu visible so request errors remain readable.
    if (event.relatedTarget && !accountContainer.contains(event.relatedTarget)) closeMenu();
  });

  const themeButton = actions.querySelector('.ttra-theme');
  function updateThemeLabel() {
    const label = root.dataset.classicTheme === 'light' ? 'Modo oscuro' : 'Modo claro';
    themeButton.setAttribute('aria-label', label);
    themeButton.title = label;
    themeButton.textContent = label;
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
  const pedidosLink = actions.querySelector('.ttra-site-pedidos-link');
  const logout = actions.querySelector('.ttra-site-logout');
  const loginParams = new URLSearchParams({ volver: location.pathname + location.search });
  profileLink.href = `/login.html?${loginParams}`;
  profileLink.textContent = 'Iniciar sesión';
  let sesionActiva = false;
  profileLink.addEventListener('click', (event) => {
    if (sesionActiva) return; // ya logueado: navega normal a /perfil
    event.preventDefault();
    closeMenu();
    import('/login-drawer.js').then(({ abrirLoginEnPagina }) => {
      abrirLoginEnPagina(profileLink, updateSession);
    });
  });
  async function updateSession() {
    try {
      const response = await fetch('/api/me');
      if (!response.ok) return;
      const account = await response.json();
      sesionActiva = true;
      profileLink.href = '/perfil';
      profileLink.textContent = 'Ir a perfil';
      accountContainer.querySelector('.ttra-site-initials').textContent =
        [account.nombre, account.apellido].map((name) => (name || '').trim().charAt(0).toUpperCase()).join('');
      if (pedidosLink) pedidosLink.hidden = false;
      logout.hidden = false;
    } catch { /* Public navigation remains usable if session lookup fails. */ }
  }
  logout.addEventListener('click', async () => {
    logout.disabled = true;
    const error = accountContainer.querySelector('.ttra-site-error');
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
  mountDock(actions);
})();
