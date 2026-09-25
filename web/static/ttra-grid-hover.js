// Grilla decorativa de "+" que reaccionan al pasar el cursor/dedo, debajo de
// la sección "DE CÓRDOBA. PARA TU MUNDO." Sin dependencias externas: la
// versión original (GSAP/Draggable/Tweakpane) solo las usaba para un panel
// de configuración de desarrollo, que acá no corresponde tener en producción.
(function () {
  const section = document.querySelector('.ttra-grid-hover');
  const grid = section?.querySelector('.ttra-grid-hover-grid');
  if (!section || !grid) return;
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  let cols = 0, rows = 0;

  // Blip corto por celda, sintetizado con WebAudio (sin asset de sonido).
  // El AudioContext se crea recién con el primer gesto real, por las
  // políticas de autoplay de los navegadores.
  let audioCtx = null, tickBuffer = null;
  function ensureAudio() {
    if (audioCtx || motion.matches) return audioCtx;
    try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch { return null; }
    // Un ruido blanco cortito de base, reutilizado en cada tick (más seco
    // que un oscilador con barrido de frecuencia, que suena a "laser").
    const length = Math.round(audioCtx.sampleRate * .02);
    tickBuffer = audioCtx.createBuffer(1, length, audioCtx.sampleRate);
    const data = tickBuffer.getChannelData(0);
    for (let i = 0; i < length; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / length);
    return audioCtx;
  }
  let lastBlip = 0;
  function playBlip() {
    const ctx = ensureAudio();
    if (!ctx || !tickBuffer) return;
    if (ctx.state === 'suspended') ctx.resume();
    const now = ctx.currentTime;
    if (now - lastBlip < .015) return;
    lastBlip = now;
    const source = ctx.createBufferSource();
    source.buffer = tickBuffer;
    const filter = ctx.createBiquadFilter();
    filter.type = 'highpass';
    filter.frequency.value = 2200 + Math.random() * 1200;
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(.16, now);
    gain.gain.exponentialRampToValueAtTime(.0001, now + .018);
    source.connect(filter).connect(gain).connect(ctx.destination);
    source.start(now);
    source.stop(now + .02);
  }
  grid.addEventListener('pointerdown', ensureAudio, { once: true });
  grid.addEventListener('pointerover', event => {
    if (event.pointerType !== 'mouse' && event.pointerType !== 'pen') return;
    if (event.target.tagName !== 'DIV') return;
    playBlip();
  });
  function buildGrid() {
    const rect = grid.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const cell = window.innerWidth < 700 ? 34 : 44;
    const nextCols = Math.max(6, Math.round(rect.width / cell));
    const nextRows = Math.max(4, Math.round(rect.height / cell));
    if (nextCols === cols && nextRows === rows) return;
    cols = nextCols; rows = nextRows;
    const cells = [];
    for (let i = 0; i < cols * rows; i++) {
      const grade = Math.floor(Math.random() * 12 - 6);
      const opacity = Math.min(Math.random(), .2);
      const hue = Math.floor(Math.random() * 30);
      cells.push(`<div style="--grade:${grade};--opacity:${opacity};--hue:${hue}">+</div>`);
    }
    grid.innerHTML = cells.join('');
    grid.style.setProperty('--cols', cols);
    grid.style.setProperty('--rows', rows);
  }
  buildGrid();
  let resizeTimer = 0;
  window.addEventListener('resize', () => { clearTimeout(resizeTimer); resizeTimer = setTimeout(buildGrid, 200); });
  if (window.matchMedia('(hover: none) and (pointer: coarse)').matches) {
    let prevCell = null;
    grid.addEventListener('pointermove', event => {
      const el = document.elementFromPoint(event.x, event.y);
      const cell = el && grid.contains(el) && el.tagName === 'DIV' ? el : null;
      if (cell === prevCell) return;
      prevCell?.removeAttribute('data-hover');
      if (cell) {
        cell.dataset.hover = 'true';
        // Vibración muy corta, solo mientras se recorre esta sección con el
        // dedo -no en el resto de la web-. iOS Safari no soporta la API, en
        // ese caso navigator.vibrate simplemente no existe y no hace nada.
        if (!motion.matches) navigator.vibrate?.(6);
      }
      prevCell = cell;
    }, true);
    grid.addEventListener('pointerleave', () => {
      prevCell?.removeAttribute('data-hover');
      prevCell = null;
    }, true);
  }
})();
