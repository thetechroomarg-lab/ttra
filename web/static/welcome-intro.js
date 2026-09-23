/* The renderer is loaded only when the welcome is actually shown. */
(() => {
  const root = document.documentElement;
  const intro = document.getElementById('rc-portada-ingreso');
  if (!intro) return;
  if (!root.classList.contains('ttra-welcome-pending')) { intro.hidden = true; return; }
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const siblings = [...document.body.children].filter(el => el !== intro && !['SCRIPT', 'STYLE'].includes(el.tagName));
  const inertBefore = siblings.map(el => el.inert);
  siblings.forEach(el => { el.inert = true; });
  document.body.classList.add('rc-portada-activa');
  intro.focus({preventScroll: true});
  let scene, frame, watchdog, finished = false, closed = false, last = 0, elapsed = 0;
  const resetClock = () => { last = 0; };
  document.addEventListener('visibilitychange', resetClock);
  const dispose = () => { cancelAnimationFrame(frame); scene?.dispose(); scene = null; };
  const ready = (fallback = false) => {
    if (closed) return;
    finished = true;
    clearTimeout(watchdog);
    dispose();
    intro.style.setProperty('--scene-opacity', '0');
    intro.style.setProperty('--title-opacity', '0');
    if (fallback) intro.dataset.fallback = 'true';
    intro.dataset.phase = 'ready';
    // Sin CTA: tras quedar en negro, un instante después arranca solo el
    // fade-in hacia la home (ver fadeInHome).
    setTimeout(fadeInHome, fallback ? 0 : 550);
  };
  function tick(now) {
    if (closed || finished) return;
    if (!document.hidden && last) elapsed += (now - last) / 1000;
    last = now;
    try { scene.render(elapsed); } catch { ready(true); return; }
    const reveal = smooth((elapsed - 7.8) / 1.2);
    const fade = smooth((elapsed - 10.2) / 1.4);
    intro.style.setProperty('--scene-opacity', String(1 - fade));
    intro.style.setProperty('--title-opacity', String(reveal * (1 - fade)));
    intro.style.setProperty('--title-scale', String(.72 + .28 * reveal));
    intro.style.setProperty('--title-blur', `${12 * (1 - reveal)}px`);
    intro.dataset.phase = elapsed < 4.95 ? 'spin' : elapsed < 5.5 ? 'explode' : elapsed < 7.8 ? 'freeze' : elapsed < 10.2 ? 'welcome' : 'fade';
    if (elapsed >= 12.2) ready();
    else frame = requestAnimationFrame(tick);
  }
  function smooth(t) { t = Math.max(0, Math.min(1, t)); return t*t*(3-2*t); }
  const reduce = () => { if (motion.matches) ready(true); };
  motion.addEventListener('change', reduce);
  intro.addEventListener('keydown', event => {
    // Sin CTA que enfocar: Escape solo adelanta el cierre (salta el resto
    // de la animación y dispara el fade-in de una).
    if (event.key === 'Escape') ready();
  });
  function bookkeepingDismiss(remember) {
    closed = true;
    clearTimeout(watchdog);
    dispose();
    motion.removeEventListener('change', reduce);
    document.removeEventListener('visibilitychange', resetClock);
    if (remember) {
      try { sessionStorage.setItem('ttra_portada_vista', '1'); } catch {}
      // A completed welcome starts with Vaivén at home, even after a previous visit.
      window.__TTRA_CAT_RESET_AFTER_WELCOME = true;
      try { sessionStorage.removeItem('ttra_header_cat_state_v1'); localStorage.removeItem('ttra_header_cat_enabled'); } catch {}
      window.dispatchEvent(new Event('ttra:welcome-entered'));
    }
    const url = new URL(location.href); url.searchParams.delete('intro');
    history.replaceState(history.state, '', url);
  }
  // Salida instantánea (usuario ya logueado: ni se muestra la animación).
  function dismiss(remember = true) {
    bookkeepingDismiss(remember);
    intro.hidden = true;
    root.classList.remove('ttra-welcome-pending');
    root.classList.add('ttra-welcome-dismissed');
    document.body.classList.remove('rc-portada-activa');
    siblings.forEach((el, i) => { el.inert = inertBefore[i]; });
  }
  // Salida con fade: la animación ya terminó en negro (--scene-opacity y
  // --title-opacity en 0). Se saca el "pending" ya (la home reaparece
  // detrás, oculta por el overlay negro todavía opaco) y recién ahí se
  // dispara la transición CSS de opacity que revela la home.
  function fadeInHome() {
    if (closed) return;
    bookkeepingDismiss(true);
    root.classList.remove('ttra-welcome-pending');
    root.classList.add('ttra-welcome-dismissed');
    document.body.classList.remove('rc-portada-activa');
    siblings.forEach((el, i) => { el.inert = inertBefore[i]; });
    const heading = document.getElementById('ttra-hero-title');
    if (heading) { heading.tabIndex = -1; heading.focus({preventScroll: true}); }
    intro.dataset.phase = 'leaving';
    if (motion.matches) { intro.hidden = true; return; } // sin transición: corta directo
    intro.addEventListener('transitionend', () => { intro.hidden = true; }, { once: true });
    setTimeout(() => { intro.hidden = true; }, 1200); // fallback por si no llega a disparar transitionend
  }
  async function start() {
    const preview = new URLSearchParams(location.search).get('intro') === '1';
    if (!preview) {
      // Check the real session, never a localStorage flag that can outlive logout.
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 3000);
      let guest = false;
      try {
        const response = await fetch('/api/me', {cache: 'no-store', signal: controller.signal});
        guest = response.status === 401;
      } catch { /* If session verification is unavailable, keep the store usable. */ }
      finally { clearTimeout(timeout); }
      if (closed) return;
      if (!guest) { dismiss(false); return; }
    }
    if (closed || finished) return;
    // Internal navigation skips repeats; an ordinary reload checks the session again.
    // A newly opened tab starts fresh; signed-in customers are checked above first.
    try { sessionStorage.setItem('ttra_portada_vista', '1'); } catch {}
    watchdog = setTimeout(() => ready(true), 25000);
    if (motion.matches) { ready(true); return; }
    import('/welcome-scene.js').then(({createScene}) => {
      if (closed || finished) return;
      scene = createScene(intro.querySelector('.ttra-intro-scene'));
      clearTimeout(watchdog);
      frame = requestAnimationFrame(tick);
    }).catch(() => ready(true));
  }
  start();
})();
