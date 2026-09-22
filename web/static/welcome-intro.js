/* The renderer is loaded only when the welcome is actually shown. */
(() => {
  const root = document.documentElement;
  const intro = document.getElementById('rc-portada-ingreso');
  if (!intro) return;
  if (!root.classList.contains('ttra-welcome-pending')) { intro.hidden = true; return; }
  const enter = document.getElementById('btn-portada-ingreso');
  const skip = intro.querySelector('.ttra-intro-skip');
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const siblings = [...document.body.children].filter(el => el !== intro && !['SCRIPT', 'STYLE'].includes(el.tagName));
  const inertBefore = siblings.map(el => el.inert);
  siblings.forEach(el => { el.inert = true; });
  document.body.classList.add('rc-portada-activa');
  let scene, frame, finished = false, closed = false, last = 0, elapsed = 0;
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
    if (intro.contains(document.activeElement)) enter.focus({preventScroll: true});
  };
  const watchdog = setTimeout(() => ready(true), 25000);
  function tick(now) {
    if (closed || finished) return;
    if (!document.hidden && last) elapsed += Math.min((now - last) / 1000, .1);
    last = now;
    scene.render(elapsed);
    const reveal = smooth((elapsed - 7.8) / 1.2);
    const fade = smooth((elapsed - 10.2) / 1.4);
    intro.style.setProperty('--scene-opacity', String(1 - fade));
    intro.style.setProperty('--title-opacity', String(reveal * (1 - fade)));
    intro.style.setProperty('--title-scale', String(.72 + .28 * reveal));
    intro.style.setProperty('--title-blur', `${12 * (1 - reveal)}px`);
    intro.dataset.phase = elapsed < 3.5 ? 'spin' : elapsed < 5.8 ? 'explode' : elapsed < 7.8 ? 'freeze' : elapsed < 10.2 ? 'welcome' : 'fade';
    if (elapsed >= 12.2) ready();
    else frame = requestAnimationFrame(tick);
  }
  function smooth(t) { t = Math.max(0, Math.min(1, t)); return t*t*(3-2*t); }
  const reduce = () => { if (motion.matches) ready(true); };
  motion.addEventListener('change', reduce);
  skip.addEventListener('click', () => ready());
  intro.addEventListener('keydown', event => {
    if (event.key === 'Escape') ready();
    if (event.key === 'Tab') { event.preventDefault(); (finished ? enter : skip).focus(); }
  });
  enter.addEventListener('click', () => {
    closed = true;
    clearTimeout(watchdog);
    dispose();
    motion.removeEventListener('change', reduce);
    try { sessionStorage.setItem('ttra_portada_vista', '1'); } catch {}
    const url = new URL(location.href); url.searchParams.delete('intro');
    history.replaceState(history.state, '', url);
    intro.hidden = true;
    root.classList.remove('ttra-welcome-pending');
    root.classList.add('ttra-welcome-dismissed');
    document.body.classList.remove('rc-portada-activa');
    siblings.forEach((el, i) => { el.inert = inertBefore[i]; });
    const heading = document.querySelector('.ttra-hero h1');
    if (heading) { heading.tabIndex = -1; heading.focus({preventScroll: true}); }
  });
  if (motion.matches) { ready(true); return; }
  import('/welcome-scene.js').then(({createScene}) => {
    if (closed || finished) return;
    scene = createScene(intro.querySelector('.ttra-intro-scene'));
    frame = requestAnimationFrame(tick);
  }).catch(() => ready(true));
})();
