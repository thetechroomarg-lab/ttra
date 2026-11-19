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
  const Seleccion = window.TTRAPizarraSeleccion;
  const MANUAL_MS = 10000; // tras tocar una flecha, la pizarra espera más antes de avanzar sola
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

  // La foto del producto cambia con el mismo ritmo que el nombre: la nueva se
  // descarga antes de entrar, así el cuadro nunca queda vacío ni salta de tamaño.
  // Sin foto mapeada el cuadro se esconde y las cifras ocupan todo el ancho.
  let fotoSerie = 0;
  async function swapFoto(p) {
    const foto = slot('foto');
    const serie = ++fotoSerie;
    const v = window.ttraImagenProducto ? await window.ttraImagenProducto(p).catch(() => null) : null;
    if (serie !== fotoSerie) return;
    const caja = foto.parentElement;
    if (!v) { caja.hidden = true; board.classList.add('sin-foto'); return; }
    if (foto.getAttribute('src') === v.src) { caja.hidden = false; board.classList.remove('sin-foto'); return; }
    const nueva = new Image();
    nueva.src = v.src;
    try { await nueva.decode(); } catch { if (serie !== fotoSerie) return; caja.hidden = true; board.classList.add('sin-foto'); return; }
    if (serie !== fotoSerie) return;
    caja.hidden = false;
    board.classList.remove('sin-foto');
    const poner = () => { foto.src = v.src; };
    if (reducedMotion.matches || !foto.animate || !foto.getAttribute('src')) { poner(); return; }
    const sale = foto.animate([{ opacity: 1, scale: 1 }, { opacity: 0, scale: .96 }], { duration: 120, easing: 'ease' });
    sale.onfinish = () => {
      if (serie !== fotoSerie) return;
      poner();
      foto.animate([{ opacity: 0, scale: .96 }, { opacity: 1, scale: 1 }], { duration: 240, easing: 'cubic-bezier(.23, 1, .32, 1)' });
    };
  }

  function showProduct({ seccion, producto: p }) {
    try { Seleccion.marcarVisto(window.localStorage, p.nombre); } catch {}
    const precios = window.preciosDe ? window.preciosDe(p) : { dolares: p.usd, pesos: p.pesos };
    swapName(p.nombre);
    swapFoto(p);
    slot('link').href = '/catalogo?' + new URLSearchParams({ categoria: seccion, buscar: '1', q: p.nombre });
    slot('link').setAttribute('aria-label', `Ver ${p.nombre} en el catálogo`);
    for (const key of PRICE_KEYS) flapTo(slot(key), precios[key] == null ? '—' : fmt(precios[key]));
  }

  // Mazo al azar en cada visita (ver pizarra-seleccion.js): solo productos con
  // foto, sin usados, mezclando familias y sin repetir lo visto en visitas previas.
  async function armarMazo(secciones) {
    const todos = Object.values(secciones).flat();
    const conFoto = new Set();
    if (window.ttraImagenProducto) {
      await Promise.all(todos.map(p => window.ttraImagenProducto(p).then(v => { if (v && v.src && !/placeholder/.test(v.src)) conFoto.add(p.nombre); }).catch(() => {})));
    }
    let vistos;
    try { vistos = Seleccion.leerVistos(window.localStorage); } catch { vistos = new Set(); }
    return Seleccion.armarMazo({ secciones, tieneImagen: p => conFoto.has(p.nombre), vistos });
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
    countBrands(secciones);
  }

  // "Búsqueda por Marca": cuántas marcas hay y cuáles pesan más, salido del catálogo.
  function countBrands(secciones) {
    const card = document.querySelector('.ttra-category[href*="filtro=marca"]');
    if (!card) return;
    const porMarca = new Map();
    for (const lista of Object.values(secciones)) {
      for (const p of lista || []) {
        if (p.marca && p.marca !== 'Otras marcas') porMarca.set(p.marca, (porMarca.get(p.marca) || 0) + 1);
      }
    }
    if (!porMarca.size) return;
    const ranking = [...porMarca].sort((x, y) => y[1] - x[1]).map(([marca]) => marca);
    const bottom = card.querySelector('.ttra-category-bottom');
    let lista = bottom.querySelector('.ttra-brands-lista');
    if (!lista) {
      lista = document.createElement('p');
      lista.className = 'ttra-brands-lista';
      bottom.querySelector('div').append(lista);
    }
    const visibles = ranking.slice(0, 5);
    lista.textContent = visibles.join(' · ') + (ranking.length > visibles.length ? ' y más' : '');
    let count = bottom.querySelector('.ttra-pz-count');
    if (!count) {
      count = document.createElement('span');
      count.className = 'ttra-flap ttra-pz-count';
      bottom.append(count);
    }
    flapTo(count, String(ranking.length));
    count.setAttribute('aria-label', `${ranking.length} marcas`);
  }

  let products = [];
  let index = 0;
  let timer = 0;
  let paused = false;
  let ultimoDatos = null;
  function schedule(espera = CYCLE_MS) {
    clearTimeout(timer);
    // With reduced motion the board still walks the store: flapTo and
    // swapName already land on the new value without animating.
    if (products.length < 2) return;
    timer = setTimeout(() => {
      if (!paused && visible && !document.hidden) avanzar(1, false);
      else schedule();
    }, espera);
  }
  // Anterior / siguiente. Pasado el final del mazo se arma otro (nunca el mismo
  // recorrido); hacia atrás da la vuelta dentro del mazo actual.
  async function avanzar(paso, manual) {
    if (products.length < 2) return;
    if (paso > 0 && index >= products.length - 1 && ultimoDatos) {
      const actual = products[index];
      const nuevo = (await armarMazo(ultimoDatos.secciones)).filter(x => x.producto.nombre !== actual.producto.nombre);
      if (nuevo.length) { products = nuevo; index = 0; }
      else index = 0;
    } else {
      index = (index + paso + products.length) % products.length;
    }
    showProduct(products[index]);
    schedule(manual ? MANUAL_MS : CYCLE_MS);
  }
  board.querySelectorAll('[data-pz-paso]').forEach(boton => {
    boton.addEventListener('click', () => avanzar(Number(boton.dataset.pzPaso), true));
  });
  // Con el foco en una flecha, ← y → también navegan.
  board.addEventListener('keydown', e => {
    if (!e.target.closest('.ttra-pz-nav') || (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight')) return;
    e.preventDefault();
    avanzar(e.key === 'ArrowRight' ? 1 : -1, true);
  });
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

  async function load(datos) {
    const secciones = datos && datos.secciones;
    if (!secciones) return;
    ultimoDatos = datos;
    countCategories(secciones);
    products = await armarMazo(secciones);
    index = 0;
    board.classList.toggle('con-nav', products.length > 1);
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
