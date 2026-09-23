/* Presentation only. Catalog selection delegates to the existing controls. */
(() => {
  'use strict';
  const root = document.documentElement;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const mobile = window.matchMedia('(max-width: 700px)');
  const isClassic = () => root.dataset.modo === 'classic';
  const layers = [...document.querySelectorAll('[data-parallax]')];
  const scrollStage = document.querySelector('.ttra-scroll-stage');
  const sectionTransitions = [
    [document.querySelector('.ttra-hero'), document.querySelector('.ttra-collection')],
    [document.querySelector('.ttra-collection'), document.querySelector('.ttra-about')],
  ].filter(([outgoing, incoming]) => outgoing && incoming);
  const themeButton = document.getElementById('ttra-theme');
  const glitchWord = document.querySelector('.ttra-glitch-word');

  const heroTitle = document.getElementById('ttra-hero-title');
  if (heroTitle) {
    const originalTitle = heroTitle.innerHTML;
    let played = false;
    let cleanupTimer;
    function finishRoll() {
      clearTimeout(cleanupTimer);
      heroTitle.innerHTML = originalTitle;
      heroTitle.classList.remove('ttra-text-rolling');
      heroTitle.removeAttribute('aria-label');
    }
    function startRoll() {
      if (played || !isClassic() || root.classList.contains('ttra-welcome-pending')) return;
      played = true;
      titleObserver.disconnect();
      if (reducedMotion.matches) return;
      heroTitle.setAttribute('aria-label', 'Lo Buscás? Lo tenés.');
      let index = 0;
      heroTitle.querySelectorAll('.ttra-cat-word').forEach(line => {
        const walker = document.createTreeWalker(line, NodeFilter.SHOW_TEXT);
        const nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        for (const node of nodes) {
          const fragment = document.createDocumentFragment();
          for (const letter of node.textContent) {
            const glyph = document.createElement('span');
            glyph.className = 'ttra-roll-glyph';
            glyph.setAttribute('aria-hidden', 'true');
            glyph.style.setProperty('--roll-delay', `${.18 + index++ * .055}s`);
            const outgoing = document.createElement('span');
            outgoing.className = 'ttra-roll-out';
            outgoing.textContent = letter === ' ' ? '\u00a0' : letter;
            const incoming = outgoing.cloneNode(true);
            incoming.className = 'ttra-roll-in';
            glyph.append(outgoing, incoming);
            fragment.append(glyph);
          }
          node.replaceWith(fragment);
        }
      });
      heroTitle.classList.add('ttra-text-rolling');
      // Restore the original text after the flourish: selection and mascot geometry
      // then use the same unfragmented heading as before.
      cleanupTimer = setTimeout(finishRoll, 850 + index * 55);
    }
    const titleObserver = new MutationObserver(startRoll);
    titleObserver.observe(root, {attributes: true, attributeFilter: ['class', 'data-modo']});
    reducedMotion.addEventListener('change', () => { if (reducedMotion.matches) finishRoll(); });
    startRoll();
  }

  if (glitchWord) {
    let showTu = true;
    window.setInterval(() => {
      if (!reducedMotion.matches) glitchWord.classList.add('is-glitching');
      window.setTimeout(() => {
        showTu = !showTu;
        const word = showTu ? 'TU' : 'EL';
        glitchWord.textContent = word;
        glitchWord.dataset.word = word;
      }, reducedMotion.matches ? 0 : 180);
      window.setTimeout(() => glitchWord.classList.remove('is-glitching'), 430);
    }, 5000);
  }

  function updateThemeLabel() {
    const light = root.dataset.classicTheme === 'light';
    themeButton?.setAttribute('aria-label', light ? 'Modo oscuro' : 'Modo claro');
    themeButton?.setAttribute('title', light ? 'Modo oscuro' : 'Modo claro');
    if (themeButton) themeButton.textContent = light ? 'Modo oscuro' : 'Modo claro';
  }
  themeButton?.addEventListener('click', () => {
    if (!isClassic()) return;
    // Reuse the app's theme persistence.
    if (typeof aplicarTemaClassic === 'function') {
      aplicarTemaClassic(root.dataset.classicTheme === 'light' ? 'dark' : 'light', true);
    }
  });
  updateThemeLabel();
  new MutationObserver(() => { updateThemeLabel(); scheduleFrame(); }).observe(root, {
    attributes: true, attributeFilter: ['data-classic-theme', 'data-modo'],
  });

  let frame = 0;
  function renderSectionTransitions() {
    const enabled = isClassic() && !reducedMotion.matches &&
      !document.body.classList.contains('rc-vista-seccion');
    for (const [outgoing, incoming] of sectionTransitions) {
      if (!enabled) {
        outgoing.style.removeProperty('--section-scale');
        outgoing.style.removeProperty('--section-brightness');
        outgoing.style.removeProperty('--section-blur');
        incoming.style.removeProperty('--section-enter-y');
        continue;
      }
      // Subtract the offset applied on the previous frame so the effect
      // follows the document position rather than feeding back on itself.
      const previousOffset = parseFloat(incoming.style.getPropertyValue('--section-enter-y')) || 0;
      const top = incoming.getBoundingClientRect().top - previousOffset;
      const travel = Math.max(360, window.innerHeight * .82);
      // A short intro may already reveal the next section at scrollY=0.
      // Use its initial position as the start, so visible content stays sharp
      // until the user actually scrolls and becomes sharp again on return.
      const start = Math.min(window.innerHeight, top + window.scrollY);
      const progress = Math.max(0, Math.min(1, (start - top) / travel));
      const depth = mobile.matches ? .045 : .10;
      const offset = (1 - progress) * (mobile.matches ? 32 : 96);
      outgoing.style.setProperty('--section-scale', (1 - progress * depth).toFixed(3));
      outgoing.style.setProperty('--section-brightness', (1 - progress * .25).toFixed(3));
      // Smoothstep follows scroll in both directions, with no one-shot state.
      const focusProgress = progress * progress * (3 - 2 * progress);
      outgoing.style.setProperty('--section-blur', `${(focusProgress * (mobile.matches ? 5 : 8)).toFixed(3)}px`);
      incoming.style.setProperty('--section-enter-y', `${offset.toFixed(1)}px`);
    }
  }
  function renderParallax() {
    frame = 0;
    const active = isClassic() && !reducedMotion.matches && !mobile.matches;
    const heroTravel = scrollStage
      ? Math.max(0, Math.min(700, -scrollStage.getBoundingClientRect().top))
      : 0;
    for (const layer of layers) {
      if (!active) { layer.style.removeProperty('--parallax-y'); continue; }
      const rect = layer.parentElement.getBoundingClientRect();
      if (rect.bottom < -100 || rect.top > window.innerHeight + 100) continue;
      const travel = layer.closest('.ttra-hero')
        ? heroTravel
        : Math.max(-700, Math.min(700, window.innerHeight * .35 - rect.top));
      layer.style.setProperty('--parallax-y', `${(travel * Number(layer.dataset.parallax)).toFixed(1)}px`);
    }
    renderSectionTransitions();
  }
  function scheduleFrame() {
    if (!frame) frame = requestAnimationFrame(renderParallax);
  }
  window.addEventListener('scroll', scheduleFrame, { passive: true });
  window.addEventListener('resize', scheduleFrame, { passive: true });
  reducedMotion.addEventListener('change', scheduleFrame);
  mobile.addEventListener('change', scheduleFrame);
  new MutationObserver(scheduleFrame).observe(document.body, {
    attributes: true, attributeFilter: ['class'],
  });
  scheduleFrame();

  const revealElements = [...document.querySelectorAll('[data-reveal]')];
  let revealObserver;
  function setupReveals() {
    revealObserver?.disconnect();
    if (!('IntersectionObserver' in window) || reducedMotion.matches) {
      revealElements.forEach(element => element.classList.add('is-visible'));
      return;
    }
    // Trigger inside the viewport, with a shorter inset on compact screens.
    const inset = Math.min(250, Math.round(innerHeight * (mobile.matches ? .16 : .25)));
    revealObserver = new IntersectionObserver(entries => {
      const entering = entries.filter(entry => entry.isIntersecting)
        .sort((a, b) => revealElements.indexOf(a.target) - revealElements.indexOf(b.target));
      let cardIndex = 0;
      for (const {target} of entering) {
        target.style.setProperty('--reveal-delay', `${target.matches('.ttra-category') ? cardIndex++ * .09 : 0}s`);
        target.classList.add('is-visible');
        revealObserver.unobserve(target);
      }
    }, {threshold: .01, rootMargin: `0px 0px -${inset}px 0px`});
    revealElements.forEach(element => {
      if (element.classList.contains('is-visible')) return;
      element.classList.add('ttra-reveal-ready');
      revealObserver.observe(element);
    });
  }
  setupReveals();
  reducedMotion.addEventListener('change', setupReveals);
  window.addEventListener('resize', setupReveals, {passive: true});
})();
