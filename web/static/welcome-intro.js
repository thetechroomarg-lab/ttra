/* The renderer is loaded only when the welcome is actually shown. */
(() => {
  const root = document.documentElement;
  const intro = document.getElementById('rc-portada-ingreso');
  if (!intro) return;
  if (!root.classList.contains('ttra-welcome-pending')) { intro.hidden = true; return; }
  const enter = document.getElementById('btn-portada-ingreso');
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const siblings = [...document.body.children].filter(el => el !== intro && !['SCRIPT', 'STYLE'].includes(el.tagName));
  const inertBefore = siblings.map(el => el.inert);
  siblings.forEach(el => { el.inert = true; });
  document.body.classList.add('rc-portada-activa');
  intro.focus({preventScroll: true});
  let keyboardNavigation = false;
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
    if (keyboardNavigation && intro.contains(document.activeElement)) enter.focus({preventScroll: true});
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
    if (event.key === 'Tab' || event.key === 'Escape') keyboardNavigation = true;
    if (event.key === 'Escape') ready();
    if (event.key === 'Tab') { event.preventDefault(); (finished ? enter : intro).focus({preventScroll: true}); }
  });
  function dismiss(remember = true) {
    closed = true;
    clearTimeout(watchdog);
    dispose();
    motion.removeEventListener('change', reduce);
    document.removeEventListener('visibilitychange', resetClock);
    if (remember) {
      try { sessionStorage.setItem('ttra_portada_vista', '1'); } catch {}
    }
    const url = new URL(location.href); url.searchParams.delete('intro');
    history.replaceState(history.state, '', url);
    intro.hidden = true;
    root.classList.remove('ttra-welcome-pending');
    root.classList.add('ttra-welcome-dismissed');
    document.body.classList.remove('rc-portada-activa');
    siblings.forEach((el, i) => { el.inert = inertBefore[i]; });
    const heading = document.getElementById('ttra-hero-title');
    if (heading) { heading.tabIndex = -1; heading.focus({preventScroll: true}); }
  }
  enter.addEventListener('click', () => dismiss());
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
    // A visit lasts for this tab: internal navigation and reloads do not replay it.
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
