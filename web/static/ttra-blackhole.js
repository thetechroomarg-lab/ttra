// Entrada a /blackhole desde la home: el agujero en miniatura reacciona al cursor y, al tocarlo,
// se traga la pantalla antes de navegar. Sin JS (o con movimiento reducido) es un link común.
(() => {
  const link = document.querySelector('.ttra-blackhole-link');
  const egg = link && link.querySelector('.ttra-bh');
  if (!egg) return;
  const reducido = matchMedia('(prefers-reduced-motion: reduce)');
  const RADIO = 340; // px a partir de los cuales el agujero "siente" el cursor
  let cuadro = 0;
  let punto = null;

  function actualizar() {
    cuadro = 0;
    const r = egg.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    if (!punto) { link.style.setProperty('--pull', '0'); link.style.setProperty('--tx', '0px'); link.style.setProperty('--ty', '0px'); return; }
    const dx = punto.x - cx, dy = punto.y - cy, d = Math.hypot(dx, dy);
    const pull = Math.max(0, 1 - d / RADIO);
    const k = d ? Math.min(6, d * 0.04) * pull / Math.max(pull, 0.001) : 0; // se corre hasta 6 px hacia el cursor
    link.style.setProperty('--pull', (pull * pull * (3 - 2 * pull)).toFixed(3));
    link.style.setProperty('--tx', d ? `${((dx / d) * k * pull).toFixed(2)}px` : '0px');
    link.style.setProperty('--ty', d ? `${((dy / d) * k * pull).toFixed(2)}px` : '0px');
  }
  const pedir = () => { if (!cuadro) cuadro = requestAnimationFrame(actualizar); };
  if (matchMedia('(hover: hover)').matches) {
    window.addEventListener('pointermove', (e) => { punto = { x: e.clientX, y: e.clientY }; pedir(); }, { passive: true });
    document.addEventListener('pointerleave', () => { punto = null; pedir(); });
  }
  window.addEventListener('scroll', pedir, { passive: true });
  link.addEventListener('focus', () => { link.style.setProperty('--pull', '1'); });
  link.addEventListener('blur', pedir);

  link.addEventListener('click', (e) => {
    if (reducido.matches || e.button || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    e.preventDefault();
    if (document.querySelector('.ttra-bh-traga')) return;
    const core = egg.querySelector('.ttra-bh-core').getBoundingClientRect();
    const cx = core.left + core.width / 2, cy = core.top + core.height / 2;
    const lejos = Math.hypot(Math.max(cx, innerWidth - cx), Math.max(cy, innerHeight - cy));
    const boca = document.createElement('div');
    boca.className = 'ttra-bh-traga';
    boca.style.left = `${cx}px`; boca.style.top = `${cy}px`;
    boca.style.setProperty('--s0', String(core.width / 40));
    boca.style.setProperty('--s1', String((lejos * 2.4) / 40));
    document.body.append(boca);
    boca.getBoundingClientRect();
    boca.classList.add('va');
    setTimeout(() => location.assign(link.href), 980);
  });
  // Al volver con "atrás" la página puede venir del caché con la boca abierta.
  window.addEventListener('pageshow', () => document.querySelectorAll('.ttra-bh-traga').forEach((n) => n.remove()));
})();
