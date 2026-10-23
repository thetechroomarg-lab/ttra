/* Pizarra de la home: los cinco precios de productos
   reales del catálogo, en dígitos de paleta (split-flap). Solo presentación:
   usa el catálogo que ya descarga landing.js, y los precios salen de preciosDe()
   (precios.js), igual que en el catálogo. */
(() => {
  'use strict';
  const board = document.querySelector('.ttra-pizarra');
  if (!board) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const slot = key => board.querySelector(`[data-pz="${key}"]`);
  const PRICE_KEYS = ['dolares', 'bancoUsa', 'usdt', 'pesos', 'pesosTransf'];
  const CYCLE_MS = 6000;
  // Usados y equipos sin caja no se muestran salvo que el cliente los pida.
  const EXCLUIR = /usad|cpo|swap|sin caja|caja abierta|abollad/i;
  const DIGITS = '0123456789';
  const fmt = n => Number(n).toLocaleString('es-AR');

  // Each character is a cell; a changed cell runs a few random digits and
  // lands on its value, staggered left to right like a real board.
  function flapTo(el, text) {
    el.setAttribute('aria-label', text);
    const old = [...el.querySelectorAll('.ttra-flap-c')].map(c => c.textContent);
    if (!el.querySelector('.ttra-flap-c')) el.textContent = '';
    const chars = [...text];
    while (el.children.length > chars.length) el.lastElementChild.remove();
    chars.forEach((ch, i) => {
      let cell = el.children[i];
      if (!cell) {
        cell = document.createElement('span');
        cell.className = 'ttra-flap-c';
        cell.setAttribute('aria-hidden', 'true');
        el.append(cell);
      }
      cell.classList.toggle('is-sep', !DIGITS.includes(ch) && ch !== '—');
      if (old[i] === ch) return;
      if (reducedMotion.matches || !DIGITS.includes(ch)) { cell.textContent = ch; return; }
      let steps = 3 + Math.floor(Math.random() * 3);
      const tick = () => {
        cell.classList.remove('is-flipping');
        void cell.offsetWidth;
        cell.classList.add('is-flipping');
        cell.textContent = steps ? DIGITS[Math.floor(Math.random() * 10)] : ch;
        if (steps--) setTimeout(tick, 55);
      };
      setTimeout(tick, i * 40);
    });
  }

  // The whole featured block opens that product in the catalog, the same
  // "Ver en el catálogo" link the comparison page uses.
  // The name changes under a short blur so the swap reads as one board
  // update instead of two words replacing each other.
  function swapName(nombre) {
    const el = slot('name');
    if (el.textContent === nombre) return;
    if (reducedMotion.matches || !el.animate || !el.textContent.trim()) { el.textContent = nombre; return; }
    const out = el.animate([{ opacity: 1, filter: 'blur(0)' }, { opacity: 0, filter: 'blur(3px)' }], { duration: 120, easing: 'ease' });
    out.onfinish = () => {
      el.textContent = nombre;
      el.animate([{ opacity: 0, filter: 'blur(3px)' }, { opacity: 1, filter: 'blur(0)' }], { duration: 200, easing: 'cubic-bezier(.23, 1, .32, 1)' });
    };
  }

  function showProduct({ seccion, producto: p }) {
    const precios = window.preciosDe ? window.preciosDe(p) : { dolares: p.usd, pesos: p.pesos };
    swapName(p.nombre);
    slot('link').href = '/catalogo?' + new URLSearchParams({ categoria: seccion, buscar: '1', q: p.nombre });
    slot('link').setAttribute('aria-label', `Ver ${p.nombre} en el catálogo`);
    for (const key of PRICE_KEYS) flapTo(slot(key), precios[key] == null ? '—' : fmt(precios[key]));
  }

  // One product per section, in catalog order, so the board walks the store.
  function pickProducts(secciones) {
    const picks = [];
    for (const [seccion, lista] of Object.entries(secciones)) {
      const producto = (lista || []).find(x => x.usd != null && x.pesos != null && !EXCLUIR.test(x.nombre));
      if (producto) picks.push({ seccion, producto });
    }
    return picks;
  }

  function countCategories(secciones) {
    for (const card of document.querySelectorAll('.ttra-category[href*="categoria="]')) {
      const categoria = new URL(card.href, location.origin).searchParams.get('categoria');
      const total = (secciones[categoria] || []).length;
      if (!total) continue;
      let count = card.querySelector('.ttra-pz-count');
      if (!count) {
        count = document.createElement('span');
        count.className = 'ttra-flap ttra-pz-count';
        card.querySelector('.ttra-category-bottom')?.append(count);
      }
      flapTo(count, String(total));
      count.setAttribute('aria-label', `${total} productos`);
    }
  }

  let products = [];
  let index = 0;
  let timer = 0;
  let paused = false;
  function schedule() {
    clearTimeout(timer);
    // With reduced motion the board still walks the store: flapTo and
    // swapName already land on the new value without animating.
    if (products.length < 2) return;
    timer = setTimeout(() => {
      if (!paused && visible && !document.hidden) {
        index = (index + 1) % products.length;
        showProduct(products[index]);
      }
      schedule();
    }, CYCLE_MS);
  }
  // Off screen the board holds too: no flipping nobody is looking at.
  // On phones the board is display: contents and has no box of its own, so
  // observing it always reported "not intersecting" and the board never
  // moved; the product name is always laid out.
  let visible = true;
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }).observe(slot('name'));
  }
  // Reading or focusing the board holds the current product. Only a real
  // mouse or keyboard focus counts: on a phone a tap leaves the link focused
  // until the next tap elsewhere, and the board stayed on one product.
  board.addEventListener('pointerenter', e => { if (e.pointerType === 'mouse') paused = true; });
  board.addEventListener('pointerleave', e => { if (e.pointerType === 'mouse') paused = false; });
  board.addEventListener('focusin', e => { if (e.target.matches(':focus-visible')) paused = true; });
  board.addEventListener('focusout', () => { paused = false; });

  function load(datos) {
    const secciones = datos && datos.secciones;
    if (!secciones) return;
    countCategories(secciones);
    products = pickProducts(secciones);
    index = 0;
    if (!products.length) {
      slot('name').textContent = datos.mensaje || 'Ver el catálogo';
      return;
    }
    showProduct(products[0]);
    schedule();
  }
  // landing.js already downloads the catalog; reuse it instead of a second fetch.
  window.addEventListener('ttra:catalogo', event => load(event.detail));
  if (typeof catalogoListo !== 'undefined' && catalogoListo && typeof SECCIONES_DATA !== 'undefined') {
    load({ secciones: SECCIONES_DATA });
  }
})();
