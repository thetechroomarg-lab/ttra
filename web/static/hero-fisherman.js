// Easter egg: un pescador diminuto sentado sobre la tilde de "Buscás", con la
// línea colgando y el corchito flotando sobre la letra siguiente (como el
// nene pescando en la luna de DreamWorks). Mide un pelito: de tamaño normal
// es una manchita, solo se descubre haciendo zoom. Pesca todo el tiempo (le
// pican, saca un celular, vuelve a tirar). Tocarlo hace zoom hacia él y dice
// su frase en un globo de historieta hasta que se toca "Volver", una sola vez
// por carga de página.
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
      <g transform="translate(0 -8)">
        <circle cx="2" cy="-27" r="5"/>
        <path d="M-5-29.5h14M-3.5-29.8q0-6.4 5.5-6.4t5.5 6.4z"/>
        <path class="ttra-fisher-body" d="M1.5-21L0-4M2-16l8 6M0-2l10 1M10-1l1 9" fill="none"/>
      </g>
    </svg>
    <svg class="ttra-fisher-tackle" viewBox="0 0 1 1" focusable="false">
      <path class="ttra-fisher-rod"/>
      <path class="ttra-fisher-line"/>
      <g class="ttra-fisher-hook"><g class="ttra-fisher-catch"><rect/></g><circle class="ttra-fisher-bobber"/></g>
    </svg>`;
  copy.append(fisher);

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
      fisher.hidden = true; return;
    }
    const css = getComputedStyle(title);
    const upper = css.textTransform === 'uppercase';
    const found = charRect('á');
    const accent = found && ink(upper ? 'Á' : 'á', css);
    if (!accent || !found.glyph.width) { fisher.hidden = true; return; }
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
    const tipX = water ? found.next.left + inWater - seatX : 34 * u;
    const tipY = -34 * u;
    const lineEnd = water ? baseline + water.topAt(inWater) - seatY - 1.2 * u : size * .12;
    const r = 3.6 * u, hand = [10 * u, -18 * u];
    fisher.style.fontSize = `${size}px`;
    fisher.style.left = `${(seatX - p.left - parent.clientLeft).toFixed(2)}px`;
    fisher.style.top = `${(seatY - p.top - parent.clientTop).toFixed(2)}px`;
    const f = n => n.toFixed(2);
    fisher.querySelector('.ttra-fisher-rod').setAttribute('d', `M${f(hand[0] - 4 * u)} ${f(hand[1] + 4 * u)}L${f(tipX)} ${f(tipY)}`);
    fisher.querySelector('.ttra-fisher-line').setAttribute('d', `M${f(tipX)} ${f(tipY)}V${f(lineEnd - r)}`);
    const bobber = fisher.querySelector('.ttra-fisher-bobber');
    bobber.setAttribute('cx', f(tipX)); bobber.setAttribute('cy', f(lineEnd - r)); bobber.setAttribute('r', f(r));
    const phone = fisher.querySelector('.ttra-fisher-catch rect');
    Object.entries({x: tipX - 4.5 * u, y: lineEnd, width: 9 * u, height: 15 * u, rx: 2 * u}).forEach(([k, v]) => phone.setAttribute(k, f(v)));
    fisher.style.setProperty('--fisher-u', `${u}px`);
    fisher.style.setProperty('--fisher-tip', `${f(tipX)}px ${f(tipY)}px`);
    fisher.style.setProperty('--fisher-reel', `${f(tipY + 6 * u - lineEnd)}px`);
    fisher.style.setProperty('--fisher-reel-scale', String(Math.max(.02, (6 * u) / Math.max(1, lineEnd - tipY))));
    fisher.hidden = false;
  }

  let frame = 0;
  const schedule = () => { if (!frame) frame = requestAnimationFrame(() => { frame = 0; place(); }); };
  // --- Zoom hacia el pescador + globo de diálogo (una vez por carga) ---
  // Se queda agrandado hasta que se toca "Volver": es lo único que responde
  // (ni la página, ni el scroll, ni Escape; el foco no sale del botón).
  const QUOTE = 'A veces se puede encontrar a alguien viviendo su vida, tranquilo, y no es necesario molestarlo. Tenés que aprender a respetar la paz, te deseo buena vida.';
  const ZOOM_MS = 1200;
  const stage = title.closest('.ttra-scroll-stage');
  let told = false;
  // Header y gatitos pueden vivir en el documento de arriba (shell con
  // iframe): la clase va en los dos, cada hoja de estilos esconde lo suyo.
  const roots = () => { const list = [root]; try { if (window.parent !== window && window.parent.document) list.push(window.parent.document.documentElement); } catch {} return list; };
  function tell() {
    if (told || !stage) return;
    told = true;
    const seat = fisher.getBoundingClientRect(), man = fisher.querySelector('.ttra-fisher-man').getBoundingClientRect();
    const small = innerWidth <= 700;
    // Dónde queda el pescador ya agrandado, y cuánto se agranda: unos 130px de alto.
    const cx = innerWidth * (small ? .3 : .36), cy = innerHeight * (small ? .66 : .62);
    const scale = Math.min(40, Math.max(6, Math.min(innerHeight * .17, 140) / Math.max(1, man.height)));
    const s = stage.getBoundingClientRect();
    const zoomed = `translate(${(cx - seat.left).toFixed(1)}px, ${(cy - seat.top).toFixed(1)}px) scale(${scale.toFixed(2)})`;
    const head = {x: cx + (man.left + man.width * .45 - seat.left) * scale, y: cy + (man.top - seat.top) * scale};

    const shield = document.createElement('div');
    shield.className = 'ttra-fisher-shield';
    const bubble = document.createElement('div');
    bubble.className = 'ttra-fisher-bubble';
    bubble.setAttribute('role', 'status');
    bubble.textContent = QUOTE;
    const back = document.createElement('button');
    back.type = 'button';
    back.className = 'ttra-fisher-back';
    back.textContent = 'Volver';
    document.body.append(shield, bubble, back);
    // El globo arriba de la cabeza; la colita apunta a la cabeza.
    const width = Math.min(innerWidth - 32, 420);
    const left = Math.max(16, Math.min(innerWidth - width - 16, head.x - width * (small ? .25 : .18)));
    bubble.style.width = `${width}px`;
    bubble.style.left = `${left}px`;
    bubble.style.bottom = `${Math.max(16, innerHeight - head.y + 26)}px`;
    bubble.style.setProperty('--tail-x', `${Math.max(24, Math.min(width - 24, head.x - left))}px`);

    const scrollbar = innerWidth - root.clientWidth;
    root.style.setProperty('--fisher-scrollbar', `${scrollbar}px`);
    for (const r of roots()) r.classList.add('ttra-fisher-zooming');
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
        shield.remove(); bubble.remove(); back.remove();
        fisher.classList.add('is-told');
        schedule();
      };
      if (!motion) { finish(); return; }
      stage.style.transform = '';
      const zoomOut = stage.animate([{transform: zoomed}, {transform: 'none'}], {duration: ZOOM_MS, easing: ease});
      zoomOut.onfinish = () => { zoomOut.cancel(); finish(); };
    });
  }
  fisher.addEventListener('click', tell);
  title.addEventListener('animationend', schedule);
  new MutationObserver(schedule).observe(title, {attributes: true, attributeFilter: ['class'], childList: true});
  new MutationObserver(schedule).observe(root, {attributes: true, attributeFilter: ['data-modo', 'class']});
  new ResizeObserver(schedule).observe(title);
  window.addEventListener('resize', schedule, {passive: true});
  document.fonts?.ready.then(schedule);
  schedule();
})();
