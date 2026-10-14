/* Motion layer for the Classic home (see ttra-motion.css). Loaded in <head> so
   the hidden start state is in place before the first paint; everything else
   waits for the DOM and for the welcome intro to finish. */
(() => {
  'use strict';
  const root = document.documentElement;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (reducedMotion.matches || root.classList.contains('ttra-cart-embedded')) return;
  root.classList.add('ttra-motion-ready');

  const BRANDS = ['Apple', 'Samsung', 'Xiaomi', 'Motorola', 'POCO', 'Redmi', 'realme', 'Infinix', 'Haylou', 'Amazon'];
  const clamp01 = value => Math.min(1, Math.max(0, value));

  function buildMarquee() {
    const hero = document.querySelector('.ttra-hero');
    if (!hero || hero.querySelector('.ttra-mo-marquee')) return;
    const list = () => {
      const ul = document.createElement('ul');
      for (const brand of BRANDS) {
        const li = document.createElement('li');
        li.textContent = brand;
        ul.append(li);
      }
      return ul;
    };
    const marquee = document.createElement('div');
    marquee.className = 'ttra-mo-marquee';
    marquee.setAttribute('aria-label', `Marcas: ${BRANDS.join(', ')}`);
    const track = document.createElement('div');
    track.className = 'ttra-mo-marquee-track';
    const copy = list();
    copy.setAttribute('aria-hidden', 'true');
    track.append(list(), copy);
    marquee.append(track);
    hero.append(marquee);
  }

  function play() {
    // Force a style flush so the hidden state is committed before the transition
    // starts (no rAF: it never fires in a hidden tab and the page would stay blank).
    void document.body.offsetWidth;
    root.classList.add('ttra-motion-played');
    setTimeout(() => root.classList.add('ttra-motion-done'), 2200);
  }

  function playAfterWelcome() {
    if (!root.classList.contains('ttra-welcome-pending')) return play();
    const observer = new MutationObserver(() => {
      if (root.classList.contains('ttra-welcome-pending')) return;
      observer.disconnect();
      play();
    });
    observer.observe(root, {attributes: true, attributeFilter: ['class']});
  }

  function setupScrollScrub() {
    const headings = [...document.querySelectorAll('.ttra-home-only .ttra-section-heading')];
    for (const heading of headings) {
      const left = document.createElement('span');
      left.className = 'ttra-mo-line ttra-mo-line-left';
      left.setAttribute('aria-hidden', 'true');
      const right = left.cloneNode();
      right.className = 'ttra-mo-line ttra-mo-line-right';
      heading.prepend(left);
      heading.append(right);
      heading.classList.add('ttra-mo-lined');
    }
    const cards = [...document.querySelectorAll('.ttra-category, .ttra-garantia')];
    cards.forEach(card => card.classList.add('ttra-mo-fade'));

    // 0 = element top touches the viewport bottom, 1 = element bottom leaves the top.
    const progress = element => {
      const rect = element.getBoundingClientRect();
      const height = window.innerHeight;
      return clamp01((height - rect.top) / (height + rect.height));
    };
    let queued = false;
    function update() {
      queued = false;
      for (const heading of headings) {
        const p = progress(heading);
        heading.style.setProperty('--mo-line', clamp01(p / .5).toFixed(3));
        heading.style.setProperty('--mo-title', clamp01((p - .09) / .1).toFixed(3));
      }
      for (const card of cards) {
        const p = progress(card);
        const opacity = p < .4 ? p / .4 : p <= .6 ? 1 : 1 - clamp01((p - .6) / .3);
        card.style.setProperty('--mo-fade', opacity.toFixed(3));
      }
    }
    const queue = () => {
      if (queued) return;
      queued = true;
      requestAnimationFrame(update);
    };
    window.addEventListener('scroll', queue, {passive: true});
    window.addEventListener('resize', queue);
    update();
  }

  function start() {
    if (root.dataset.modo && root.dataset.modo !== 'classic') {
      root.classList.remove('ttra-motion-ready');
      return;
    }
    buildMarquee();
    setupScrollScrub();
    playAfterWelcome();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
