/* Presentation only. Catalog selection delegates to the existing controls. */
(() => {
  'use strict';
  const root = document.documentElement;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const mobile = window.matchMedia('(max-width: 700px)');
  const isClassic = () => root.dataset.modo === 'classic';
  const layers = [...document.querySelectorAll('[data-parallax]')];
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
    // Reuse the same theme persistence and profile-menu label as the app.
    if (typeof aplicarTemaClassic === 'function') {
      aplicarTemaClassic(root.dataset.classicTheme === 'light' ? 'dark' : 'light', true);
    }
  });
  updateThemeLabel();
  new MutationObserver(() => { updateThemeLabel(); scheduleFrame(); }).observe(root, {
    attributes: true, attributeFilter: ['data-classic-theme', 'data-modo'],
  });

  let frame = 0;
  function renderParallax() {
    frame = 0;
    const active = isClassic() && !reducedMotion.matches && !mobile.matches;
    for (const layer of layers) {
      if (!active) { layer.style.removeProperty('--parallax-y'); continue; }
      const rect = layer.parentElement.getBoundingClientRect();
      if (rect.bottom < -100 || rect.top > window.innerHeight + 100) continue;
      const travel = Math.max(-700, Math.min(700, window.innerHeight * .35 - rect.top));
      layer.style.setProperty('--parallax-y', `${(travel * Number(layer.dataset.parallax)).toFixed(1)}px`);
    }
  }
  function scheduleFrame() {
    if (!frame) frame = requestAnimationFrame(renderParallax);
  }
  window.addEventListener('scroll', scheduleFrame, { passive: true });
  window.addEventListener('resize', scheduleFrame, { passive: true });
  reducedMotion.addEventListener('change', scheduleFrame);
  mobile.addEventListener('change', scheduleFrame);
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
