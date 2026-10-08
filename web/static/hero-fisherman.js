// Easter egg: tocar la tilde de "Buscás" hace zoom hacia ella y ahí aparece
// un pescador diminuto sentado en su sillita sobre la tilde, con su fogata
// atrás, la línea colgando y el corchito flotando sobre la letra siguiente
// (como el nene pescando en la luna de DreamWorks). Pesca todo el tiempo (le
// pican, saca un pececito, vuelve a tirar) y dice su frase en un globo de
// historieta hasta que se toca "Volver". Fuera del zoom no se ve. Una sola
// vez por carga de página.
//
// No toca el <h2>: classic-editorial.js le reescribe el innerHTML al hacer
// rodar las letras, así que el pescador es una capa aparte dentro de
// .ttra-hero-copy, posicionada sobre la tilde real. Para encontrar la tilde se
// dibuja la letra en un canvas oculto con la misma tipografía y se busca la
// primera mancha de tinta desde arriba (funciona igual con "á" y con "Á").
(() => {
  'use strict';
  const root = document.documentElement;
  const title = document.getElementById('ttra-hero-title');
  const copy = title?.closest('.ttra-hero-copy');
  if (!title || !copy) return;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

  let told = false;
  const fisher = document.createElement('div');
  fisher.className = 'ttra-fisher';
  fisher.hidden = true;
  fisher.setAttribute('aria-hidden', 'true');
  // Dos dibujos: el muñequito (en unidades de 1/467 em, con el origen en la
  // cadera, que es donde se sienta) y el equipo de pesca -caña, línea,
  // corcho y lo que saca-, que se dibuja en px porque su largo depende de
  // dónde cae la letra siguiente. SVG y no cajas de CSS: Chrome redondea a
  // 1px cualquier caja más finita, y la línea tiene que ser un hilo.
  fisher.innerHTML = `
    <svg class="ttra-fisher-man" viewBox="-30 -48 68 60" focusable="false">
      <g class="ttra-fisher-fire">
        <ellipse class="ttra-fire-glow" cx="0" cy="-4" rx="12" ry="9"/>
        <g class="ttra-fire-flames">
          <path class="ttra-fire-red" d="M0-15C3-11 6-8 5-4 4-1 2 0 0 0S-4-1-5-4C-6-8-2-9 0-15Z"/>
          <path class="ttra-fire-yellow" d="M0-10C2-7 3.5-5 3-3 2.5-1 1.3-.4 0-.4S-2.5-1-3-3C-3.4-5-1.5-6 0-10Z"/>
        </g>
        <circle class="ttra-fire-spark" cx="-1.5" cy="-14" r=".7"/>
        <circle class="ttra-fire-spark" cx="2" cy="-15" r=".6"/>
        <path class="ttra-fire-log" d="M-6-3.8L5 .4"/>
        <path class="ttra-fire-log" d="M6-3.8L-5 .4"/>
        <path class="ttra-fire-log" d="M-7-.6H7"/>
      </g>
      <g class="ttra-fisher-chair">
        <path class="ttra-chair-frame" d="M-5-7L9 0M9-7L-5 0M-5-7L-8-24"/>
        <path class="ttra-chair-fabric" d="M-5-7.6H9.4M-5.6-9.5L-7.5-22.5"/>
      </g>
      <path class="ttra-fisher-body" d="M0-10l10 1M10-9l1 9" fill="none"/>
      <g class="ttra-fisher-upper">
        <circle cx="2" cy="-35" r="5"/>
        <path d="M-5-37.5h14M-3.5-37.8q0-6.4 5.5-6.4t5.5 6.4z"/>
        <path class="ttra-fisher-body" d="M1.5-29L0-12M2-24l8 6" fill="none"/>
      </g>
    </svg>
    <svg class="ttra-fisher-tackle" viewBox="0 0 1 1" focusable="false">
      <g class="ttra-fisher-gear">
      <path class="ttra-fisher-rod"/>
      <path class="ttra-fisher-line"/>
      <g class="ttra-fisher-hook"><g class="ttra-fisher-catch"><g class="ttra-fish"><path class="ttra-fish-fin" d="M4.6 6L8.4 8.6 4.8 11.4ZM-3.8 7.2L-6.4 10-3.5 9.9Z"/><path class="ttra-fish-body" d="M0 0C5 2 5.6 10 1.6 15L5.4 21.2 0 18.6-5.4 21.2-1.6 15C-5.6 10-5 2 0 0Z"/><path class="ttra-fish-gill" d="M-3 5.8Q0 7.4 3 5.8"/><circle class="ttra-fish-eye" cx="1.7" cy="3.4" r="1.15"/><circle class="ttra-fish-pupil" cx="1.9" cy="3.5" r=".5"/></g></g><circle class="ttra-fisher-bobber"/></g>
      </g>
    </svg>`;
  // Zona tocable sobre la tilde (al menos 44x44px, también con el dedo).
  const hit = document.createElement('span');
  hit.className = 'ttra-fisher-hit';
  hit.hidden = true;
  hit.setAttribute('aria-hidden', 'true');
  copy.append(fisher, hit);

  function ink(char, css) {
    const size = parseFloat(css.fontSize);
    const canvas = document.createElement('canvas');
    const pad = Math.ceil(size * .3), W = Math.ceil(size * 1.6), H = Math.ceil(size * 2);
    canvas.width = W; canvas.height = H;
    const ctx = canvas.getContext('2d', {willReadFrequently: true});
    ctx.font = `${css.fontStyle} ${css.fontWeight} ${size}px ${css.fontFamily}`;
    const base = Math.round(size * 1.5);
    ctx.fillText(char, pad, base);
    const data = ctx.getImageData(0, 0, W, H).data;
    const rowInk = y => { let a = W, b = -1; for (let x = 0; x < W; x++) if (data[(y * W + x) * 4 + 3] > 90) { a = Math.min(a, x); b = x; } return b < 0 ? null : [a, b]; };
    let top = -1, bottom = -1, left = W, right = -1;
    for (let y = 0; y < H; y++) {
      const row = rowInk(y);
      if (!row) { if (top >= 0) { bottom = y; break; } continue; }
      if (top < 0) top = y;
      left = Math.min(left, row[0]); right = Math.max(right, row[1]);
    }
    if (top < 0) return null;
    // Dónde empieza (a la izquierda) el borde de arriba: el "piso" disponible.
    const topLeft = rowInk(top)[0] - pad;
    const metrics = ctx.measureText(char);
    // Primera tinta desde arriba en una columna (para que el corcho se apoye
    // justo sobre la curva de la letra, no sobre su punto más alto).
    const topAt = x => { const col = Math.round(x + pad); if (col < 0 || col >= W) return top - base; for (let y = 0; y < H; y++) if (data[(y * W + col) * 4 + 3] > 90) return y - base; return top - base; };
    // Coordenadas relativas al origen del glifo (x) y a la línea de base (y).
    return {left: left - pad, right: right - pad, top: top - base, bottom: bottom - base, ascent: metrics.fontBoundingBoxAscent, topAt, topLeft};
  }

  function charRect(char) {
    const walker = document.createTreeWalker(title, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode, index = node.textContent.indexOf(char);
      if (index < 0) continue;
      const range = document.createRange();
      range.setStart(node, index); range.setEnd(node, index + 1);
      const next = document.createRange();
      next.setStart(node, index + 1); next.setEnd(node, Math.min(node.textContent.length, index + 2));
      return {glyph: range.getBoundingClientRect(), next: next.getBoundingClientRect(), nextChar: node.textContent[index + 1] || ''};
    }
    return null;
  }

  function place() {
    // Durante el zoom todo está agrandado: medir ahora lo correría de lugar.
    if (root.classList.contains('ttra-fisher-zooming')) return;
    if (root.dataset.modo !== 'classic' || title.classList.contains('ttra-text-rolling') || title.getAnimations().some(a => a.playState === 'running')) {
      fisher.hidden = true; hit.hidden = true; return;
    }
    const css = getComputedStyle(title);
    const upper = css.textTransform === 'uppercase';
    const found = charRect('á');
    const accent = found && ink(upper ? 'Á' : 'á', css);
    if (!accent || !found.glyph.width) { fisher.hidden = true; hit.hidden = true; return; }
    const nextChar = upper ? found.nextChar.toUpperCase() : found.nextChar;
    const water = nextChar && ink(nextChar, css);
    const parent = fisher.offsetParent || document.body;
    const p = parent.getBoundingClientRect();
    const baseline = found.glyph.top + accent.ascent;
    const size = parseFloat(css.fontSize), u = size / 467;
    // La sillita se apoya sobre el borde de arriba de la tilde, cerca de la
    // punta; la fogata va detrás (a la izquierda), sin salirse del borde si
    // entra.
    const seatX = found.glyph.left + accent.right - 12 * u;
    const floorLeft = (found.glyph.left + accent.topLeft - seatX) / u;
    fisher.querySelector('.ttra-fisher-fire').setAttribute('transform', `translate(${Math.min(-19, Math.max(-24, floorLeft + 7)).toFixed(1)} 0)`);
    const seatY = baseline + accent.top;
    // La punta de la caña queda sobre la letra siguiente, y el corcho flota
    // apoyado arriba de ella: esa letra es "el agua".
    const inWater = water ? water.left + (water.right - water.left) * .35 : 0;
    // En el celular la caña es más corta (con el zoom se salía de la pantalla):
    // termina cerca de él y la línea cae al lado de la tilde, hasta el "nivel
    // del agua" (la parte de arriba de la letra siguiente).
    const short = innerWidth <= 700;
    const tipX = water ? (short ? Math.min(40 * u, found.next.left + inWater - seatX) : found.next.left + inWater - seatX) : 34 * u;
    const tipY = short ? -30 * u : -34 * u;
    const overWater = water && seatX + tipX - found.next.left;
    const onLetter = water && overWater >= water.left && overWater <= water.right;
    const lineEnd = water ? baseline + (onLetter ? water.topAt(overWater) : water.top) - seatY - 1.2 * u : size * .12;
    const r = 3.6 * u, hand = [10 * u, -18 * u];
    fisher.style.fontSize = `${size}px`;
    fisher.style.left = `${(seatX - p.left - parent.clientLeft).toFixed(2)}px`;
    fisher.style.top = `${(seatY - p.top - parent.clientTop).toFixed(2)}px`;
    const f = n => n.toFixed(2);
    fisher.querySelector('.ttra-fisher-rod').setAttribute('d', `M${f(hand[0] - 4 * u)} ${f(hand[1] + 4 * u)}L${f(tipX)} ${f(tipY)}`);
    fisher.querySelector('.ttra-fisher-line').setAttribute('d', `M${f(tipX)} ${f(tipY)}V${f(lineEnd - r)}`);
    const bobber = fisher.querySelector('.ttra-fisher-bobber');
    bobber.setAttribute('cx', f(tipX)); bobber.setAttribute('cy', f(lineEnd - r)); bobber.setAttribute('r', f(r));
    // Lo que pesca: un pez colgando de la boca (cabeza arriba, cola abajo). El
    // dibujo está en unidades del pescador; acá solo se ubica y se escala.
    fisher.querySelector('.ttra-fisher-catch').setAttribute('transform', `translate(${f(tipX)} ${f(lineEnd)}) scale(${(u * 1.05).toFixed(4)})`);
    fisher.style.setProperty('--fisher-u', `${u}px`);
    fisher.style.setProperty('--fisher-tip', `${f(tipX)}px ${f(tipY)}px`);
    fisher.style.setProperty('--fisher-hip', `0px ${f(-12 * u)}px`);
    fisher.style.setProperty('--fisher-reel', `${f(tipY + 6 * u - lineEnd)}px`);
    fisher.style.setProperty('--fisher-reel-scale', String(Math.max(.02, (6 * u) / Math.max(1, lineEnd - tipY))));
    fisher.hidden = false;
    const ax = found.glyph.left + accent.left, aw = accent.right - accent.left;
    const ay = baseline + accent.top, ah = accent.bottom - accent.top;
    const hw = Math.max(44, aw + 12), hh = Math.max(44, ah + 12);
    Object.assign(hit.style, {
      left: `${(ax + aw / 2 - hw / 2 - p.left - parent.clientLeft).toFixed(2)}px`,
      top: `${(ay + ah / 2 - hh / 2 - p.top - parent.clientTop).toFixed(2)}px`,
      width: `${hw.toFixed(2)}px`, height: `${hh.toFixed(2)}px`,
    });
    hit.hidden = told;
  }

  let frame = 0;
  const schedule = () => { if (!frame) frame = requestAnimationFrame(() => { frame = 0; place(); }); };
  // --- Zoom hacia el pescador + globo de diálogo (una vez por carga) ---
  // Se queda agrandado hasta que se toca "Volver": es lo único que responde
  // (ni la página, ni el scroll, ni Escape; el foco no sale del botón).
  const QUOTE = ['A veces se puede encontrar a alguien viviendo su vida, tranquilo, y no es necesario molestarlo. Tenés que aprender a respetar la paz.', 'Te deseo buena vida.'];
  const ZOOM_MS = 1200;
  const stage = title.closest('.ttra-scroll-stage');
  // Header y gatitos pueden vivir en el documento de arriba (shell con
  // iframe): la clase va en los dos, cada hoja de estilos esconde lo suyo.
  const roots = () => { const list = [root]; try { if (window.parent !== window && window.parent.document) list.push(window.parent.document.documentElement); } catch {} return list; };
  function tell() {
    if (told || !stage) return;
    told = true;
    place();
    const seat = fisher.getBoundingClientRect(), man = fisher.querySelector('.ttra-fisher-man').getBoundingClientRect();
    // En el celular, para ver al pescador hay que agrandar con dos dedos: todo
    // se acomoda a la parte de la pantalla que se ve de verdad (visualViewport),
    // no a la página entera. Sin esto, el globo y "Volver" quedaban afuera de
    // la vista, y como "Volver" es lo único que responde, se quedaba trabado.
    const vv = window.visualViewport || {scale: 1, offsetLeft: 0, offsetTop: 0, width: innerWidth, height: innerHeight};
    const k = vv.scale || 1;
    const screenW = vv.width * k, screenH = vv.height * k;
    const small = screenW <= 700;
    // Dónde queda el pescador ya agrandado (coordenadas de la página), y
    // cuánto se agranda: unos 130px de alto en pantalla.
    const cx = vv.offsetLeft + vv.width * (small ? .3 : .36), cy = vv.offsetTop + vv.height * (small ? .66 : .62);
    const scale = Math.min(40, Math.max(2, Math.min(screenH * .17, 140) / Math.max(.1, man.height * k)));
    const s = stage.getBoundingClientRect();
    const zoomed = `translate(${(cx - seat.left).toFixed(1)}px, ${(cy - seat.top).toFixed(1)}px) scale(${scale.toFixed(2)})`;
    // La cabeza, en px de pantalla dentro de la capa del globo y el botón.
    const head = {x: (cx + (man.left + man.width * .45 - seat.left) * scale - vv.offsetLeft) * k,
                  y: (cy + (man.top - seat.top) * scale - vv.offsetTop) * k};

    const shield = document.createElement('div');
    shield.className = 'ttra-fisher-shield';
    // Capa del tamaño de lo visible, achicada en la misma proporción del zoom
    // de dos dedos: adentro, el globo y el botón se ven de tamaño normal.
    const ui = document.createElement('div');
    ui.className = 'ttra-fisher-ui';
    const fit = () => Object.assign(ui.style, {left: `${vv.offsetLeft}px`, top: `${vv.offsetTop}px`, width: `${screenW}px`, height: `${screenH}px`, transform: `scale(${1 / k})`});
    fit();
    window.visualViewport?.addEventListener('resize', fit);
    window.visualViewport?.addEventListener('scroll', fit);
    const bubble = document.createElement('div');
    bubble.className = 'ttra-fisher-bubble';
    bubble.setAttribute('role', 'status');
    for (const line of QUOTE) bubble.append(Object.assign(document.createElement('span'), {textContent: line}));
    const back = document.createElement('button');
    back.type = 'button';
    back.className = 'ttra-fisher-back';
    back.textContent = 'Volver';
    ui.append(bubble, back);
    document.body.append(shield, ui);
    // El globo arriba de la cabeza, con la colita apuntándole. Si no entra
    // arriba (pantallas bajas, celular acostado), va al costado.
    let width = Math.min(screenW - 32, 420);
    bubble.style.width = `${width}px`;
    const bh = bubble.offsetHeight;
    if (head.y - 26 - bh >= 12) {
      const left = Math.max(16, Math.min(screenW - width - 16, head.x - width * (small ? .25 : .18)));
      bubble.style.left = `${left}px`;
      bubble.style.bottom = `${Math.max(16, screenH - head.y + 26)}px`;
      bubble.style.setProperty('--tail-x', `${Math.max(24, Math.min(width - 24, head.x - left))}px`);
    } else {
      bubble.classList.add('is-side');
      width = Math.max(220, Math.min(width, screenW - head.x - 60));
      bubble.style.width = `${width}px`;
      const top = Math.max(12, Math.min(screenH - bubble.offsetHeight - 112, head.y - 20));
      bubble.style.left = `${Math.min(screenW - width - 16, head.x + 44)}px`;
      bubble.style.top = `${top}px`;
      bubble.style.setProperty('--tail-y', `${Math.max(18, head.y + 10 - top)}px`);
    }

    const scrollbar = innerWidth - root.clientWidth;
    root.style.setProperty('--fisher-scrollbar', `${scrollbar}px`);
    for (const r of roots()) r.classList.add('ttra-fisher-zooming');
    // El ciclo de pesca (10 s) se adelanta a la mitad: a los ~2 s de abrir
    // saca el pez y lo muestra un par de segundos.
    for (const a of fisher.getAnimations({subtree: true})) if (a.effect?.getTiming().duration === 10000) a.currentTime = 5000;
    // El teclado no se escapa del botón: Tab vuelve a él y Escape no cierra.
    const trap = event => {
      if (event.target === back && (event.key === 'Enter' || event.key === ' ')) return;
      event.preventDefault(); event.stopPropagation();
      back.focus({preventScroll: true});
    };
    document.addEventListener('keydown', trap, true);
    // Entrada animada y después el transform queda fijo, sin animación: así el
    // navegador redibuja todo nítido al tamaño grande (animado, la tilde se
    // veía pixelada porque se estiraba la imagen tomada al tamaño original).
    const motion = !reducedMotion.matches;
    const ease = 'cubic-bezier(.65,0,.25,1)';
    if (motion) {
      stage.style.transformOrigin = `${(seat.left - s.left).toFixed(1)}px ${(seat.top - s.top).toFixed(1)}px`;
      const zoomIn = stage.animate([{transform: 'none'}, {transform: zoomed}], {duration: ZOOM_MS, easing: ease});
      zoomIn.onfinish = () => { stage.style.transform = zoomed; zoomIn.cancel(); };
    }
    requestAnimationFrame(() => { bubble.classList.add('is-open'); back.classList.add('is-open'); });
    setTimeout(() => back.focus({preventScroll: true}), motion ? ZOOM_MS : 0);

    back.addEventListener('click', () => {
      if (back.disabled) return;
      back.disabled = true;
      bubble.classList.remove('is-open'); back.classList.remove('is-open');
      const finish = () => {
        stage.style.transform = '';
        stage.style.transformOrigin = '';
        for (const r of roots()) r.classList.remove('ttra-fisher-zooming');
        root.style.removeProperty('--fisher-scrollbar');
        document.removeEventListener('keydown', trap, true);
        window.visualViewport?.removeEventListener('resize', fit);
        window.visualViewport?.removeEventListener('scroll', fit);
        shield.remove(); ui.remove();
        hit.hidden = true;
        schedule();
      };
      if (!motion) { finish(); return; }
      stage.style.transform = '';
      const zoomOut = stage.animate([{transform: zoomed}, {transform: 'none'}], {duration: ZOOM_MS, easing: ease});
      zoomOut.onfinish = () => { zoomOut.cancel(); finish(); };
    });
  }
  hit.addEventListener('click', tell);
  title.addEventListener('animationend', schedule);
  new MutationObserver(schedule).observe(title, {attributes: true, attributeFilter: ['class'], childList: true});
  new MutationObserver(schedule).observe(root, {attributes: true, attributeFilter: ['data-modo', 'class']});
  new ResizeObserver(schedule).observe(title);
  new ResizeObserver(schedule).observe(copy);
  window.addEventListener('load', schedule);
  window.addEventListener('resize', schedule, {passive: true});
  document.fonts?.ready.then(schedule);
  schedule();
})();
