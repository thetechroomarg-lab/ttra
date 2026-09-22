/* A small decorative mascot. Every landing point belongs to an actual page element. */
(() => {
  if (document.body.id !== 'rc-body-landing') return;
  const root = document.documentElement;
  const motion = matchMedia('(prefers-reduced-motion: reduce)');
  const cat = document.createElement('div');
  cat.id = 'ttra-home-cat';
  cat.setAttribute('aria-hidden', 'true');
  cat.setAttribute('inert', '');
  cat.innerHTML = `<svg viewBox="0 0 120 100" xmlns="http://www.w3.org/2000/svg" focusable="false">
    <ellipse class="cat-shadow" cx="63" cy="92" rx="34" ry="3" fill="#29231f" opacity=".15"/>
    <g class="cat-pose" stroke-linecap="round" stroke-linejoin="round">
      <path class="cat-tail" d="M40 76C19 76 14 62 19 48C23 36 11 30 8 40" fill="none" stroke="#c4a07c" stroke-width="12"/>
      <path d="M31 77C30 58 41 48 58 52C76 56 88 68 87 81L84 89H35Z" fill="#fffdf8" stroke="#d8cfc4" stroke-width="1.3"/>
      <ellipse cx="44" cy="78" rx="14" ry="12" fill="#f1eee7"/>
      <path d="M44 89H33C28 89 28 82 34 81L46 80M75 68L71 86C70 91 76 93 81 90L85 72" fill="#fffdf8" stroke="#d8cfc4" stroke-width="1.3"/>
      <path d="M54 40L50 15Q50 8 57 12L72 27M83 25L100 11Q105 9 104 17L103 45" fill="#c9a581" stroke="#b68e6b" stroke-width="1.2"/>
      <path d="M56 18L59 34L68 28M98 18L89 29L99 35" fill="#eac5b5"/>
      <path d="M48 49C47 30 60 23 78 24C98 23 108 34 107 51C107 70 94 77 77 76C59 76 47 66 48 49Z" fill="#fffdf9" stroke="#d8cfc4" stroke-width="1.3"/>
      <path d="M63 27L66 32M73 25L76 30M84 25L85 30" stroke="#e9e3d9" stroke-width="2"/>
      <g class="cat-eyes">
        <ellipse cx="65" cy="49" rx="9" ry="10" fill="#f3ca45" stroke="#ab8833" stroke-width="1"/>
        <ellipse cx="92" cy="49" rx="9" ry="10" fill="#f3ca45" stroke="#ab8833" stroke-width="1"/>
        <ellipse cx="67" cy="50" rx="4.2" ry="7.5" fill="#2c2920"/><ellipse cx="94" cy="50" rx="4.2" ry="7.5" fill="#2c2920"/>
        <circle cx="64" cy="46" r="2.4" fill="#fff"/><circle cx="91" cy="46" r="2.4" fill="#fff"/>
      </g>
      <ellipse cx="57" cy="61" rx="6" ry="3" fill="#efd2c9" opacity=".6"/><ellipse cx="101" cy="61" rx="5" ry="3" fill="#efd2c9" opacity=".6"/>
      <path d="M75 59Q79 56 83 59L79 63Z" fill="#c98c89"/>
      <path d="M79 63V66M79 66Q75 70 72 66M79 66Q82 70 86 66" fill="none" stroke="#8f7971" stroke-width="1.2"/>
      <path d="M58 61L42 59M58 65L42 67M99 61L115 59M99 65L114 68" stroke="#ab9b8d" stroke-width="1"/>
      <path d="M35 86V89M39 86V89M75 88V91M79 87V90" stroke="#d0c5b8" stroke-width="1"/>
    </g></svg>`;
  document.body.appendChild(cat);

  // Fractions are along a real edge, never arbitrary viewport coordinates.
  const surfaces = [];
  function add(selector, fractions, text = false, edge = 'top') {
    document.querySelectorAll(selector).forEach((element, i) => fractions.forEach((fraction, j) => {
      surfaces.push({element, fraction, text, edge, key: `${selector}:${edge}:${i}:${j}`, visits: 0});
    }));
  }
  add('.ttra-cat-word', [.22, .78], true);
  add('.ttra-stage', [.16, .52, .84]);
  add('.ttra-stage', [.08, .5, .92], false, 'bottom');
  add('.ttra-catalog-cta', [.22, .76]);
  add('.ttra-category', [.2, .7]);
  add('.ttra-about-photo', [.18, .7]);
  add('.ttra-about-copy h2', [.22, .7], true);
  add('.ttra-footer-title', [.35, .65], true);

  let current = null, target = null, state = 'rest', stateAt = 0, nextJump = 0;
  let settleTimer = 0;
  let frame = 0, lastScroll = -1000, lastFrame = 0, jumpDuration = 0, jumpHeight = 0;
  let size = {width: 76, height: 64};
  function measure() { size = {width: cat.offsetWidth, height: cat.offsetHeight}; }
  measure();
  function blocked() {
    return document.hidden || root.dataset.modo !== 'classic' ||
      root.classList.contains('ttra-welcome-pending') || root.classList.contains('ttra-scroll-locked') ||
      document.body.classList.contains('rc-vista-seccion');
  }
  function point(surface) {
    if (!surface || !surface.element.getClientRects().length) return null;
    let r = surface.element.getBoundingClientRect();
    if (surface.text) {
      const range = document.createRange();
      range.selectNodeContents(surface.element);
      r = range.getClientRects()[0] || r;
    }
    if (r.width < 30 || r.height < 5) return null;
    return {x: r.left + r.width*surface.fraction, y: surface.edge === 'bottom' ? r.bottom : r.top + (surface.text ? r.height*.20 : 1)};
  }
  function visible(p) {
    const header = document.querySelector('body > header');
    const ceiling = Math.max(0, header?.getBoundingClientRect().bottom || 0);
    return p && p.x > size.width*.55 && p.x < innerWidth-size.width*.55 &&
      p.y > ceiling+size.height+6 && p.y < innerHeight-12;
  }
  function pose(value, now) { state = value; stateAt = now; cat.dataset.state = value; }
  function place(p, progress = 0) {
    cat.style.transform = `translate3d(${(p.x-size.width*.5).toFixed(2)}px,${(p.y-size.height*.92).toFixed(2)}px,0)`;
    cat.style.setProperty('--cat-tilt', `${state === 'jump' ? -12+24*progress : 0}deg`);
    cat.dataset.anchor = current?.key || '';
    cat.classList.add('is-visible');
  }
  function hide() { cat.classList.remove('is-visible'); current = target = null; }
  function chooseNext(origin) {
    const maxDistance = innerWidth <= 700 ? 290 : 620;
    const ceiling = (document.querySelector('body > header')?.getBoundingClientRect().bottom || 0)+size.height*.92+4;
    return surfaces.filter(s => s !== current).map(surface => {
      const p = point(surface);
      const distance = p ? Math.hypot(p.x-origin.x, p.y-origin.y) : Infinity;
      const dy = p ? p.y-origin.y : 0;
      let height = Math.min(135,45+distance*.15);
      // Test the true apex of the parabola, including different platform heights.
      // Near the header, use a lower hop without cutting off the cat's head.
      const minimumHeight = Math.max(18,Math.abs(dy)/4+4);
      let clear = false;
      for (; height >= minimumHeight; height -= 2) {
        const apex = Math.max(0,Math.min(1,(4*height-dy)/(8*height)));
        if (origin.y+dy*apex-4*height*apex*(1-apex) > ceiling) { clear = true; break; }
      }
      return {surface, p, distance, height, clear, dy, score: distance+surface.visits*140};
    }).filter(v => visible(v.p) && v.clear && v.distance > 45 && v.distance < maxDistance && v.dy > -190 && v.dy < 310)
      .sort((a,b) => a.score-b.score)[0];
  }
  function tick(now) {
    frame = 0;
    if (blocked()) { hide(); return; }
    if (now-lastFrame < 30) { frame = requestAnimationFrame(tick); return; }
    lastFrame = now;
    if (!current) {
      if (now-lastScroll > 450) {
        current = surfaces.find(s => visible(point(s))) || null;
        if (current) { current.visits++; pose('rest',now); nextJump = now+3000; }
      }
    }
    const from = point(current);
    if (current && !visible(from)) hide();
    else if (current) {
      if (state === 'rest') {
        place(from);
        if (!motion.matches && now > nextJump && now-lastScroll > 600) {
          const next = chooseNext(from);
          if (next) {
            target = next.surface;
            jumpDuration = 620+next.distance*.7;
            jumpHeight = next.height;
            cat.style.setProperty('--cat-facing', next.p.x >= from.x ? '1' : '-1');
            pose('crouch',now);
          } else nextJump = now+1800;
        }
      } else if (state === 'crouch') {
        place(from);
        if (now-stateAt > 180) pose('jump',now);
      } else if (state === 'jump') {
        const to = point(target);
        if (!visible(to)) hide();
        else {
          const t = Math.min(1,(now-stateAt)/jumpDuration);
          place({x: from.x+(to.x-from.x)*t, y: from.y+(to.y-from.y)*t-4*jumpHeight*t*(1-t)},t);
          if (t === 1) { current = target; target = null; current.visits++; pose('land',now); }
        }
      } else {
        place(from);
        if (now-stateAt > 200) { pose('rest',now); nextJump = now+3200; }
      }
    }
    if (!motion.matches) frame = requestAnimationFrame(tick);
  }
  function wake() { if (!frame) frame = requestAnimationFrame(tick); }
  function sync() {
    if (blocked()) { cancelAnimationFrame(frame); frame = 0; hide(); }
    else wake();
  }
  window.addEventListener('scroll', () => {
    lastScroll = performance.now();
    clearTimeout(settleTimer);
    settleTimer = setTimeout(wake,500);
    if (state === 'jump' || state === 'crouch') hide();
    wake();
  }, {passive:true});
  window.addEventListener('resize', () => { measure(); hide(); wake(); }, {passive:true});
  document.addEventListener('visibilitychange', sync);
  motion.addEventListener('change', () => { pose('rest',performance.now()); target = null; wake(); });
  new MutationObserver(sync).observe(root, {attributes:true,attributeFilter:['class','data-modo']});
  new MutationObserver(sync).observe(document.body, {attributes:true,attributeFilter:['class']});
  document.fonts?.ready.then(wake);
  sync();
})();
