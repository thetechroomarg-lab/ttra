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
    [document.querySelector('.ttra-about'), document.querySelector('.rc-pie')],
  ].filter(([outgoing, incoming]) => outgoing && incoming);
  const themeButton = document.getElementById('ttra-theme');
  const glitchWord = document.querySelector('.ttra-glitch-word');

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
    themeButton?.setAttribute('aria-label', light ? 'Activar modo oscuro' : 'Activar modo claro');
    themeButton?.setAttribute('title', light ? 'Activar modo oscuro' : 'Activar modo claro');
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
        incoming.style.removeProperty('--section-enter-y');
        continue;
      }
      // Subtract the offset applied on the previous frame so the effect
      // follows the document position rather than feeding back on itself.
      const previousOffset = parseFloat(incoming.style.getPropertyValue('--section-enter-y')) || 0;
      const top = incoming.getBoundingClientRect().top - previousOffset;
      const travel = Math.max(360, window.innerHeight * .82);
      const progress = Math.max(0, Math.min(1, (window.innerHeight - top) / travel));
      const depth = mobile.matches ? .045 : .10;
      const offset = (1 - progress) * (mobile.matches ? 32 : 96);
      outgoing.style.setProperty('--section-scale', (1 - progress * depth).toFixed(3));
      outgoing.style.setProperty('--section-brightness', (1 - progress * .25).toFixed(3));
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

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      }
    }, { threshold: .08 });
    document.querySelectorAll('[data-reveal]').forEach(element => {
      element.classList.add('ttra-reveal-ready');
      observer.observe(element);
    });
  }
})();
