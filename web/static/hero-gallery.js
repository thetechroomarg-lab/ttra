/* Six native illustrations; advance only while the home artwork is on screen. */
(() => {
  const stage = document.querySelector('.ttra-stage');
  if (!stage) return;
  const slides = [...stage.querySelectorAll('.ttra-hero-slide')];
  const button = stage.querySelector('.ttra-gallery-pause');
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  let index = 0, generation = 0, timer, visible = false, paused = motion.matches;
  const loaded = [...stage.querySelectorAll('img')].map(img => img.decode().catch(() => null));
  function sync() {
    clearTimeout(timer);
    const cycle = ++generation;
    button.setAttribute('aria-label', paused ? 'Reproducir imágenes' : 'Pausar imágenes');
    button.title = button.getAttribute('aria-label');
    button.firstElementChild.textContent = paused ? '▷' : 'Ⅱ';
    if (paused || !visible || document.hidden || document.documentElement.classList.contains('ttra-welcome-pending')) return;
    timer = setTimeout(async () => {
      const next = (index + 1) % slides.length;
      if (next) await loaded[next - 1];
      if (cycle !== generation || paused || !visible || document.hidden) return;
      slides[index].classList.remove('is-active');
      index = next;
      slides[index].classList.add('is-active');
      stage.dataset.galleryIndex = String(index);
      sync();
    }, 5000);
  }
  button.addEventListener('click', () => { paused = !paused; sync(); });
  motion.addEventListener('change', () => { paused = motion.matches; sync(); });
  document.addEventListener('visibilitychange', sync);
  new MutationObserver(sync).observe(document.documentElement, {attributes: true, attributeFilter: ['class']});
  new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; sync(); }, {threshold: .15}).observe(stage);
  sync();
})();
