// Easter egg: arrastrar el header hacia abajo lo abre como una puerta con la
// bisagra en su borde inferior, y atrás aparece el titán espiando por el muro.
// Al soltar se cierra solo, con un golpe seco. Se puede repetir sin límite.
//
// No cambia nada de lo que ya hace el header: la puerta recién arranca cuando
// el arrastre va claramente hacia abajo (más de 8px). Un click o un toque
// normal siguen llegando a sus botones, y el click que llega al soltar después
// de abrir la puerta se descarta (para no abrir el logo o el carrito sin querer).
(() => {
  'use strict';
  // En el shell persistente el header vive en el documento de arriba.
  try { if (window.frameElement) return; } catch { return; }
  const root = document.documentElement;
  const header = document.querySelector('body > header.ttra-site-header');
  if (!header) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const IMAGE = '/texturas/header-titan.webp';
  const START = 8, MAX = 98;

  const backdrop = document.createElement('div');
  backdrop.className = 'ttra-hinge-backdrop';
  backdrop.hidden = true;
  backdrop.setAttribute('aria-hidden', 'true');
  header.before(backdrop);
  const shade = document.createElement('div');
  shade.className = 'ttra-hinge-shade';
  shade.setAttribute('aria-hidden', 'true');
  header.append(shade);
  // Precarga la imagen cuando el navegador está libre, así aparece al instante.
  (window.requestIdleCallback || (fn => setTimeout(fn, 2500)))(() => { new Image().src = IMAGE; });

  let drag = null, opened = false, angle = 0, closing = null, swallowClick = false;
  const eligible = () => root.dataset.modo === 'classic' && !root.classList.contains('ttra-menu-open') &&
    !root.classList.contains('ttra-scroll-locked') && !root.classList.contains('ttra-fisher-zooming') &&
    !document.querySelector('#rc-perfil-dropdown:not(.oculto)');
  const transform = deg => `perspective(${Math.max(320, header.offsetHeight * 5)}px) rotateX(${(-deg).toFixed(2)}deg)`;

  function open(event) {
    opened = true; swallowClick = true;
    closing?.cancel(); closing = null;
    const r = header.getBoundingClientRect();
    Object.assign(backdrop.style, {top: `${r.top}px`, left: `${r.left}px`, width: `${r.width}px`, height: `${r.height}px`});
    backdrop.hidden = false;
    root.classList.add('ttra-hinge-open');
    try { header.setPointerCapture(event.pointerId); } catch {}
  }
  function follow(dy) {
    // El borde de arriba sigue al dedo: a la altura del header, la puerta
    // queda acostada (90°); un poco más, apenas pasa.
    const h = header.offsetHeight || 1, d = Math.max(0, dy - START);
    angle = d <= h ? Math.acos(1 - d / h) * 180 / Math.PI : Math.min(MAX, 90 + (d - h) / h * 20);
    header.style.transform = transform(angle);
    header.style.setProperty('--hinge-shade', (angle / 90 * .55).toFixed(3));
  }
  function close() {
    const from = angle;
    const done = () => {
      closing = null; angle = 0;
      header.style.transform = '';
      header.style.removeProperty('--hinge-shade');
      backdrop.hidden = true;
      root.classList.remove('ttra-hinge-open');
    };
    if (reducedMotion.matches || from < 1) { done(); return; }
    // Cae como algo pesado (acelera) y rebota apenas al golpear el marco.
    const bounce = Math.min(6, from / 12);
    header.style.removeProperty('--hinge-shade');
    closing = header.animate([
      {transform: transform(from), easing: 'cubic-bezier(.5,0,.9,.4)'},
      {transform: transform(0), offset: .62, easing: 'ease-out'},
      {transform: transform(-bounce), offset: .8, easing: 'ease-in'},
      {transform: transform(0)},
    ], {duration: 260 + from * 3.2});
    header.style.transform = '';
    closing.onfinish = done;
    closing.oncancel = () => { if (!opened) done(); };
  }

  header.addEventListener('pointerdown', event => {
    if (drag || !eligible() || (event.pointerType === 'mouse' && event.button !== 0)) return;
    if (event.target.closest?.('[data-ttra-menu], input, textarea, select')) return;
    drag = {id: event.pointerId, x: event.clientX, y: event.clientY};
  });
  window.addEventListener('pointermove', event => {
    if (!drag || event.pointerId !== drag.id) return;
    const dx = event.clientX - drag.x, dy = event.clientY - drag.y;
    if (!opened) {
      if (dy > START && dy > Math.abs(dx)) open(event);
      else if (Math.abs(dx) > 14 || dy < -START) { drag = null; return; }
      else return;
    }
    event.preventDefault();
    follow(dy);
  }, {passive: false});
  const release = event => {
    if (!drag || event.pointerId !== drag.id) return;
    drag = null;
    if (!opened) return;
    opened = false;
    try { header.releasePointerCapture(event.pointerId); } catch {}
    close();
    // El click que dispara el navegador al soltar llega enseguida; si no llega
    // (soltó afuera), se libera igual para no comerse el próximo click real.
    setTimeout(() => { swallowClick = false; }, 350);
  };
  window.addEventListener('pointerup', release);
  window.addEventListener('pointercancel', release);
  header.addEventListener('click', event => {
    if (!swallowClick) return;
    swallowClick = false;
    event.preventDefault(); event.stopImmediatePropagation();
  }, true);
  // Arrastrar un link o el logo con el mouse no tiene que "levantarlos".
  header.addEventListener('dragstart', event => { if (root.dataset.modo === 'classic') event.preventDefault(); });
})();
