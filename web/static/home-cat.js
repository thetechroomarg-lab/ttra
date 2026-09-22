/* A small decorative mascot. Every landing point belongs to an actual page element. */
(() => {
  if (document.body.id !== 'rc-body-landing') return;
  const root = document.documentElement;
  if (root.classList.contains('ttra-cart-embedded')) return;
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
      <g class="cat-leg-rear"><path d="M42 73L35 88H45" fill="none" stroke="#d8cfc4" stroke-width="10"/><path d="M42 73L35 88H45" fill="none" stroke="#fffdf8" stroke-width="8"/></g>
      <g class="cat-leg-front"><path d="M78 70L75 89H84" fill="none" stroke="#d8cfc4" stroke-width="9"/><path d="M78 70L75 89H84" fill="none" stroke="#fffdf8" stroke-width="7"/></g>
      <g class="cat-head">
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
      <path class="cat-mouth" d="M79 63V66M79 66Q75 70 72 66M79 66Q82 70 86 66" fill="none" stroke="#8f7971" stroke-width="1.2"/>
      <path d="M58 61L42 59M58 65L42 67M99 61L115 59M99 65L114 68" stroke="#ab9b8d" stroke-width="1"/>
      <g class="cat-strain-face" fill="none" stroke="#775c4c" stroke-width="2.5" stroke-linecap="round">
        <path d="M59 44L69 49L59 53M98 44L88 49L98 53"/>
        <path d="M73 68Q79 62 85 68"/>
        <path d="M58 36L69 40M98 36L88 40" stroke-width="1.6"/>
      </g>
      </g>
      <path class="cat-scratch-paw" d="M43 79Q64 56 62 48" fill="none" stroke="#fffdf8" stroke-width="10"/>
      <g class="cat-back">
        <path d="M51 79Q19 82 30 48" fill="none" stroke="#c4a07c" stroke-width="10"/>
        <ellipse cx="66" cy="68" rx="23" ry="23" fill="#fffdf8" stroke="#d8cfc4"/>
        <path d="M47 36L43 13L59 25M76 24L92 12L87 39" fill="#c9a581" stroke="#b68e6b"/>
        <ellipse cx="66" cy="40" rx="26" ry="23" fill="#fffdf8" stroke="#d8cfc4"/>
        <path d="M56 36Q65 42 76 36" fill="none" stroke="#eee8df"/>
        <path class="cat-climb-left" d="M49 60L39 43M53 80L48 90" fill="none" stroke="#d8cfc4" stroke-width="9"/>
        <path class="cat-climb-right" d="M82 60L90 43M78 80L83 90" fill="none" stroke="#fffdf8" stroke-width="8"/>
      </g>
    </g></svg>`;
  const layer=document.createElement('div');
  layer.id='ttra-cat-layer'; layer.setAttribute('aria-hidden','true'); layer.setAttribute('inert','');
  layer.appendChild(cat); document.body.appendChild(layer);

  // Images, buttons and first lines of small copy are walkable; large headings remain obstacles.
  const surfaces = [];
  function add(selector, edge = 'top') {
    document.querySelectorAll(selector).forEach((element, i) => {
      surfaces.push({element, edge, key: `${selector}:${edge}:${i}`, visits: 0});
    });
  }
  add('.ttra-hero-description', 'text');
  add('.ttra-about-copy > p:not(.ttra-eyebrow)', 'text');
  add('.ttra-stage');
  add('.ttra-stage', 'bottom');
  add('.ttra-catalog-cta');
  add('.ttra-category');
  add('.ttra-about-photo');
  add('.ttra-about-copy .ttra-button');
  const inkContext = document.createElement('canvas').getContext('2d');
  const textElements = [...document.querySelectorAll('.ttra-hero-copy h2, .ttra-hero-copy p, .ttra-about-copy h2, .ttra-about-copy p, .ttra-about-photo > span, .ttra-footer-title, .ttra-catalog-cta, .ttra-button, .ttra-category h3, .ttra-category p')];
  let geometry = new Map(), obstacles = [], glyphCache = new WeakMap();
  const startedAt=performance.now();
  const preferSmallCopy=Math.random()<.35;
  let current = null, target = null, fraction = .25, targetFraction = .75;
  let state = 'rest', stateAt = 0, nextAction = 0, actions = 0;
  let frame = 0, lastFrame = 0, lastScroll = -1000, settleTimer = 0;
  let gripDepth = 0, lastClawAt = 0;
  const clawMarks = [];
  let poop = null, nextBathroom = performance.now()+30000, bathroomPlaced = false, bathroomKind = 'poop';
  let lastScrollY = window.scrollY, entrySide = 'top';
  let duration = 0, jumpHeight = 0, returning = true, returnStart = null, returnBend = null;
  let size = {width: 76, height: 64};
  function measure() { size = {width: cat.offsetWidth, height: cat.offsetHeight}; }
  measure();
  function ceiling() { return Math.max(0, document.querySelector('body > header')?.getBoundingClientRect().bottom || 0); }
  function blocked() {
    return document.hidden || root.dataset.modo !== 'classic' ||
      root.classList.contains('ttra-welcome-pending') || root.classList.contains('ttra-scroll-locked') ||
      document.body.classList.contains('rc-vista-seccion');
  }
  function textRects(element, glyphs = false) {
    const bounds = element.getBoundingClientRect();
    const cached = glyphCache.get(element);
    const content = element.textContent;
    if (glyphs && cached?.content === content && bounds.width && bounds.height) {
      return cached.rects.map(r => ({left:bounds.left+r.left*bounds.width, right:bounds.left+r.right*bounds.width,
        top:bounds.top+r.top*bounds.height, bottom:bounds.top+r.bottom*bounds.height, line:bounds.top+r.line*bounds.height}));
    }
    const results = [];
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    for (let node; (node = walker.nextNode());) {
      if (!node.textContent.trim()) continue;
      const style = getComputedStyle(node.parentElement);
      if (style.visibility === 'hidden' || style.display === 'none') continue;
      const range = document.createRange();
      if (!glyphs) {
        range.selectNodeContents(node);
        results.push(...[...range.getClientRects()].filter(r => r.width && r.height));
        continue;
      }
      inkContext.font = `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
      for (let i = 0; i < node.length; i++) {
        if (!node.textContent[i].trim()) continue;
        range.setStart(node, i); range.setEnd(node, i + 1);
        const r = range.getBoundingClientRect();
        const m = inkContext.measureText(node.textContent[i]);
        const ascent = m.fontBoundingBoxAscent || parseFloat(style.fontSize) * .9;
        const descent = m.fontBoundingBoxDescent || parseFloat(style.fontSize) * .2;
        const scale = r.height / (ascent + descent);
        const baseline = r.top + ascent * scale;
        results.push({left:r.left, right:r.right, top:baseline-m.actualBoundingBoxAscent*scale, bottom:baseline+m.actualBoundingBoxDescent*scale, line:r.top});
      }
    }
    if (glyphs && bounds.width && bounds.height) glyphCache.set(element, {content, rects:results.map(r => ({
      left:(r.left-bounds.left)/bounds.width, right:(r.right-bounds.left)/bounds.width,
      top:(r.top-bounds.top)/bounds.height, bottom:(r.bottom-bounds.top)/bounds.height, line:(r.line-bounds.top)/bounds.height
    }))});
    return results;
  }
  function shape(surface) {
    if (geometry.has(surface)) return geometry.get(surface);
    let result = null;
    if (surface.element.matches('.ttra-reveal-ready') &&
        (!surface.element.classList.contains('is-visible') || Number(getComputedStyle(surface.element).opacity) < .99)) {
      geometry.set(surface, null); return null;
    }
    if (surface.element.getClientRects().length) {
      const r = surface.element.getBoundingClientRect();
      if (r.width > 40 && r.height > 5) {
        if(surface.edge==='text') {
          if(parseFloat(getComputedStyle(surface.element).fontSize)>18) {geometry.set(surface,null);return null;}
          const ink=textRects(surface.element,true);
          const firstLine=Math.min(...ink.map(g=>g.line));
          const line=ink.filter(g=>Math.abs(g.line-firstLine)<3);
          if(line.length)result={left:Math.min(...line.map(g=>g.left)),right:Math.max(...line.map(g=>g.right)),top:Math.min(...line.map(g=>g.top)),radius:0};
        } else result = {left:r.left, right:r.right, top:surface.edge === 'bottom' ? r.bottom : r.top, radius:surface.edge === 'top' ? parseFloat(getComputedStyle(surface.element).borderTopLeftRadius)||0 : 0};
      }
    }
    geometry.set(surface, result);
    return result;
  }
  function point(surface, f) {
    if (!surface) return null;
    const s = shape(surface);
    if (!s || s.right-s.left < size.width*.8) return null;
    const margin = size.width*.43;
    const x = s.left+margin+(s.right-s.left-2*margin)*f;
    let y = s.top;
    const radius = Math.min(s.radius, (s.right-s.left)/2);
    const edge = Math.min(x-s.left, s.right-x);
    if (radius && edge < radius) y += radius-Math.sqrt(radius*radius-(radius-edge)**2);
    return {x, y:y-2, scale:surface.element.matches('.ttra-catalog-cta, .ttra-button') ? .5 : surface.edge==='text' ? .65 : 1};
  }
  function safe(p, entry = false) {
    if (!p || (!entry && (p.x < size.width*.55 || p.x > innerWidth-size.width*.55)) || (!entry && p.y > innerHeight-8)) return false;
    const scale=p.scale || 1;
    if (!entry && p.y-size.height*scale < ceiling()+4) return false;
    const left=p.x-size.width*.48*scale, right=p.x+size.width*.48*scale;
    const top=p.y-size.height*scale, bottom=p.y;
    return !obstacles.some(r=>left<r.right && right>r.left && top<r.bottom && bottom>r.top);
  }
  function refreshGeometry() {
    geometry = new Map();
    // Use glyph ink rather than line boxes: a cat may stand on a capital letter.
    obstacles = textElements.filter(el=>el.getClientRects().length).flatMap(el=>textRects(el,true));
  }
  function pose(value, now) { state=value; stateAt=now; cat.dataset.state=value; cat.dataset.gait=''; }
  function place(p, progress=0) {
    // Reveal the first peek by moving out from behind the edge, never by fading.
    const peekProgress=state==='peek'?Math.min(1,Math.max(0,(performance.now()-stateAt)/380)):1;
    const peekOffset=state==='peek'?(cat.dataset.entrySide==='bottom'?1:-1)*32*(1-peekProgress)**2:0;
    const top = p.y-size.height*.95+peekOffset;
    cat.style.transform=`translate3d(${(p.x-size.width*.5).toFixed(2)}px,${top.toFixed(2)}px,0)`;
    cat.style.clipPath = state==='peek' || state==='drop' ? `inset(${Math.max(0,ceiling()-top)}px -5px -5px -5px)` : '';
    cat.style.setProperty('--cat-tilt', `${state === 'jump' ? -10+20*progress : 0}deg`);
    cat.style.setProperty('--cat-scale',p.scale || 1);
    cat.dataset.anchor=current?.key || '';
    cat.classList.add('is-visible');
  }
  function updatePoop(now, clear = false) {
    if(!poop) return;
    const p=point(poop.surface,poop.fraction);
    if(clear || now-poop.at>=5000 || !p) {poop.node.remove();poop=null;return;}
    poop.node.style.transform=`translate(${p.x-15}px,${p.y-44}px)`;
  }
  function leaveBathroom(now, kind) {
    const s=shape(current);
    const facing=Number(cat.style.getPropertyValue('--cat-facing')) || 1;
    const usable=s.right-s.left-size.width*.86;
    const f=Math.max(0,Math.min(1,fraction-facing*size.width*.34/Math.max(1,usable)));
    const p=point(current,f);
    if(!safe(p)) return;
    const node=document.createElement('div');
    node.className=kind==='pee'?'ttra-cat-pee':'ttra-cat-poop';
    node.innerHTML=`<svg viewBox="0 0 40 60" aria-hidden="true" focusable="false">
      <g class="cat-steam" fill="none" stroke="#d6c8b6" stroke-width="1.8" stroke-linecap="round">
        <path d="M12 21C6 15 16 12 11 5"/><path d="M22 19C17 13 27 10 21 2"/><path d="M30 23C25 17 33 14 29 8"/>
      </g>
      <path d="M6 57C0 55 2 47 8 46C3 42 8 37 14 37C10 33 15 29 20 29C25 28 27 24 24 22C35 23 33 34 29 36C37 37 38 42 33 46C40 48 40 56 33 58Z" fill="#925834" stroke="#714027" stroke-width="1"/>
      <path d="M10 38Q20 42 29 36M8 47Q20 50 33 46" fill="none" stroke="#b47849" stroke-width="2" stroke-linecap="round"/>
      <ellipse cx="13" cy="46" rx="5" ry="6" fill="white"/><ellipse cx="27" cy="46" rx="5" ry="6" fill="white"/>
      <circle cx="14" cy="47" r="2.3" fill="#302016"/><circle cx="26" cy="47" r="2.3" fill="#302016"/>
      <path d="M14 53Q20 59 26 53Z" fill="white"/>
    </svg>`;
    if(kind==='pee') node.innerHTML=`<svg viewBox="0 0 40 60" aria-hidden="true" focusable="false">
      <ellipse cx="20" cy="55" rx="16" ry="4" fill="#e8bc48" opacity=".65"/>
      <ellipse cx="17" cy="54" rx="8" ry="1.5" fill="#fff2b4" opacity=".7"/>
      <path class="cat-pee-stream" d="M12 32Q24 38 20 53" fill="none" stroke="#e8bc48" stroke-width="2" stroke-linecap="round"/>
    </svg>`;
    poop?.node.remove();
    layer.prepend(node);
    poop={node,surface:current,fraction:f,at:now};
    updatePoop(now);
  }
  function updateClaws(now, clear = false) {
    updatePoop(now,clear);
    for (let i=clawMarks.length-1;i>=0;i--) {
      const mark=clawMarks[i];
      if(clear || now-mark.at>4000 || !mark.surface.element.getClientRects().length) {
        mark.node.remove();clawMarks.splice(i,1);continue;
      }
      const r=mark.surface.element.getBoundingClientRect();
      mark.node.style.transform=`translate(${r.left+mark.x*r.width}px,${r.top+mark.y*r.height}px)`;
    }
  }
  function leaveClaws(p, now) {
    if(now-lastClawAt<340 || motion.matches) return;
    const r=current.element.getBoundingClientRect();
    const x=p.x+(clawMarks.length%2 ? -size.width*.2 : size.width*.2)-8;
    const y=p.y-size.height*.52;
    if(x<r.left || x+18>r.right || y<r.top+2 || y+20>r.bottom) return;
    lastClawAt=now;
    const node=document.createElement('div');
    node.className='ttra-cat-claws';
    node.innerHTML='<svg viewBox="0 0 18 22" aria-hidden="true"><path d="M4 2L2 17M9 3L7 20M14 2L12 17"/></svg>';
    layer.prepend(node);
    clawMarks.push({node,surface:current,x:(x-r.left)/r.width,y:(y-r.top)/r.height,at:now});
    while(clawMarks.length>12)clawMarks.shift().node.remove();
    updateClaws(now);
  }
  function hide() { cat.classList.remove('is-visible'); current=target=null; }
  function arc(from,to,t,height) {
    return {x:from.x+(to.x-from.x)*t,y:from.y+(to.y-from.y)*t-4*height*t*(1-t),scale:(from.scale||1)+((to.scale||1)-(from.scale||1))*t};
  }
  function clearRoute(from,to,height,entry=false) {
    for (let i=0;i<=24;i++) if (!safe(arc(from,to,i/24,height),entry)) return false;
    return true;
  }
  function entryPoint(from,to,t,bend=null) {
    return {x:bend===null?from.x+(to.x-from.x)*t:(1-t)**2*from.x+2*(1-t)*t*bend+t*t*to.x,y:from.y+(to.y-from.y)*t-(cat.dataset.entrySide==='bottom'?48*t*(1-t):0),scale:(from.scale||1)+((to.scale||1)-(from.scale||1))*t};
  }
  function clearEntry(from,to,bend=null) {
    for(let i=0;i<=48;i++)if(!safe(entryPoint(from,to,i/48,bend),true))return false;
    return true;
  }
  function candidates() {
    return surfaces.flatMap(surface=>[.08,.24,.4,.56,.72,.92].map(f=>({surface,f,p:point(surface,f)}))).filter(v=>safe(v.p));
  }
  function rest(now) { pose('rest',now); nextAction=now+900; }
  function acquire(now) {
    const priority=s=>s.element.matches('.ttra-catalog-cta, .ttra-button')?(preferSmallCopy?1:0):s.edge==='text'?(preferSmallCopy?0:1):2;
    const options=candidates().sort((a,b)=>(a.surface.visits*3+priority(a.surface))-(b.surface.visits*3+priority(b.surface)));
    if (returning && !motion.matches) {
      // Choose the closest safe support to the edge the user just scrolled away from.
      cat.dataset.entrySide=entrySide;
      const entryY=v=>entrySide==='bottom'?innerHeight+size.height*v.p.scale*.48:ceiling()+24;
      options.sort((a,b)=>entrySide==='bottom'?b.p.y-a.p.y:a.p.y-b.p.y);
      const entries=options.flatMap(v=>[
        ...[v.p.x,innerWidth-size.width*.55-2,size.width*.55+2].map(x=>({...v,entry:{x,y:entryY(v),scale:v.p.scale},bend:null})),
        {...v,entry:{x:innerWidth-size.width*.55-2,y:entryY(v),scale:v.p.scale},bend:innerWidth+size.width*4},
        {...v,entry:{x:size.width*.55+2,y:entryY(v),scale:v.p.scale},bend:-size.width*4}
      ]);
      const option=entries.find(v=>clearEntry(v.entry,v.p,v.bend));
      if (!option) return;
      target=option.surface; targetFraction=option.f;
      returnStart=option.entry;returnBend=option.bend;
      cat.style.setProperty('--cat-ceiling', `${ceiling()}px`);
      pose('peek',now); place(returnStart);
      return;
    }
    const option=options[0];
    if (option) {current=option.surface; fraction=option.f; current.visits++; rest(now); place(option.p);}
  }
  function startBathroom(now) {
    // Skip missed slots after a hidden tab or a modal, without a burst of animations.
    nextBathroom+=Math.max(1,Math.floor((now-nextBathroom)/30000)+1)*30000;
    bathroomPlaced=false;
    pose(bathroomKind,now);
    bathroomKind=bathroomKind==='poop'?'pee':'poop';
  }
  function plan(now,from) {
    actions++;
    if(now>=nextBathroom) { startBathroom(now);return; }
    if (actions%5===0) {pose('scratch',now);return;}
    if (actions%7===0) {pose('look',now);return;}
    // Grip the face of the current card, then pull up over its actual top edge.
    if(actions%4===0 && current.edge==='top' && current.element.matches('.ttra-stage, .ttra-category, .ttra-about-photo')) {
      gripDepth=Math.min(48,size.height*.8);
      let clear=true;
      for(let i=0;i<=12;i++)if(!safe({x:from.x,y:from.y+gripDepth*i/12}))clear=false;
      if(clear){duration=2800;lastClawAt=0;pose('grip',now);return;}
    }
    // Walking is the default. Each step samples the same component's real edge.
    const walk=candidates().filter(v=>v.surface===current && Math.abs(v.p.x-from.x)>22)
      .sort((a,b)=>Math.abs(b.p.x-from.x)-Math.abs(a.p.x-from.x))
      .find(v=>Array.from({length:25},(_,i)=>point(current,fraction+(v.f-fraction)*i/24)).every(p=>safe(p)));
    if (walk && actions%3!==0) {
      target=current; targetFraction=walk.f;
      duration=Math.max(1500,Math.abs(walk.p.x-from.x)/38*1000);
      cat.style.setProperty('--cat-facing',walk.f>fraction?'1':'-1');
      pose('walk',now);return;
    }
    const options=candidates().filter(v=>v.surface!==current || Math.abs(v.p.x-from.x)>30).map(v=>{
      const distance=Math.hypot(v.p.x-from.x,v.p.y-from.y);
      return {...v,distance,height:Math.min(32,16+distance*.1)};
    }).filter(v=>v.distance< (innerWidth<700?105:140) && v.p.y-from.y>-65 && v.p.y-from.y<95)
      .sort((a,b)=>(a.surface.visits*180+a.distance+(a.surface===current?400:0))-(b.surface.visits*180+b.distance+(b.surface===current?400:0)));
    for (const next of options) {
      for (const h of [...Array.from({length:Math.ceil((next.height-4)/8)},(_,i)=>next.height-i*8),4]) {
        if (!clearRoute(from,next.p,h)) continue;
        target=next.surface;targetFraction=next.f;jumpHeight=h;duration=520+next.distance*1.4;
        cat.style.setProperty('--cat-facing',next.p.x>from.x?'1':'-1');
        cat.dataset.climbing=String(next.p.y<from.y-25);
        pose('crouch',now);return;
      }
    }
    pose('look',now);
  }
  function tick(now) {
    frame=0;
    if(blocked()){hide();updateClaws(now,true);return;}
    if(now-lastFrame<32){frame=requestAnimationFrame(tick);return;}
    lastFrame=now;
    refreshGeometry();
    updateClaws(now);
    if (!current && state!=='peek' && state!=='drop') {
      if(now-lastScroll>180 && now-startedAt>1000) acquire(now);
    }
    if(state==='peek' || state==='drop') {
      const to=point(target,targetFraction);
      if(!safe(to) || !clearEntry(returnStart,to,returnBend)){hide();pose('rest',now);}
      else if(state==='peek') {
        place(returnStart);
        if(now-stateAt>1000){duration=returnBend===null?950:1600;pose('drop',now);}
      } else {
        const t=Math.min(1,(now-stateAt)/duration);
        place(entryPoint(returnStart,to,cat.dataset.entrySide==='bottom'?1-(1-t)**2:t*t,returnBend));
        if(t===1){current=target;fraction=targetFraction;target=null;returning=false;pose('land',now);}
      }
    } else if(current) {
      const from=point(current,fraction);
      if(!safe(from)){returning=true;hide();pose('rest',now);}
      else if(state==='walk') {
        const t=Math.min(1,(now-stateAt)/duration);
        const position=fraction+(targetFraction-fraction)*t;
        const p=point(current,position);
        const ahead=point(current,Math.max(0,Math.min(1,position+Math.sign(targetFraction-fraction)*.045)));
        cat.dataset.gait=p && ahead && ahead.y<p.y-2 ? 'climb' : '';
        if(!safe(p)){hide();returning=true;pose('rest',now);}
        else {place(p);
          if(!motion.matches && now>=nextBathroom && now-lastScroll>300){fraction=position;target=null;startBathroom(now);}
          else if(t===1){fraction=targetFraction;target=null;rest(now);}
        }
      } else if(state==='poop' || state==='pee') {
        place(from);
        if(now-stateAt>=1900 && !bathroomPlaced){leaveBathroom(now,state);bathroomPlaced=true;}
        if(now-stateAt>=2600)rest(now);
      } else if(state==='grip') {
        const t=Math.min(1,(now-stateAt)/duration);
        const depth=t<.25 ? Math.sin(t/.25*Math.PI/2) : (1-(t-.25)/.75);
        const p={x:from.x,y:from.y+gripDepth*depth};
        if(!safe(p)){hide();pose('rest',now);}
        else {
          place(p);if(t>.15 && t<.85)leaveClaws(p,now);
          if(t===1)pose('land',now);
        }
      } else if(state==='crouch') {
        place(from);if(now-stateAt>220){const climbing=cat.dataset.climbing==='true';if(climbing)duration*=1.5;pose(climbing?'climb':'jump',now);}
      } else if(state==='jump' || state==='climb') {
        const to=point(target,targetFraction), t=Math.min(1,(now-stateAt)/duration);
        // A short hesitation and alternating pulls make an ascent feel earned.
        const travel=state==='climb' ? (t<.55 ? t/.55*.76 : .76+.24*((t-.55)/.45)**1.8) : t;
        const p=to && arc(from,to,travel,jumpHeight);
        if(!safe(p)||!safe(to)){returning=true;hide();pose('rest',now);}
        else {place(p,t);if(t===1){current=target;fraction=targetFraction;target=null;current.visits++;pose('land',now);}}
      } else {
        place(from);
        if(state==='rest' && !motion.matches && now>nextAction && now-lastScroll>300)plan(now,from);
        else if(state==='land' && now-stateAt>240)rest(now);
        else if((state==='scratch'||state==='look') && now-stateAt>(state==='scratch'?2200:1200))rest(now);
      }
    }
    if(!motion.matches)frame=requestAnimationFrame(tick);
  }
  function wake(){if(!frame)frame=requestAnimationFrame(tick);}
  function sync(){if(blocked()){cancelAnimationFrame(frame);frame=0;hide();updateClaws(performance.now(),true);pose('rest',performance.now());}else wake();}
  window.addEventListener('scroll',()=>{
    const delta=window.scrollY-lastScrollY;
    if(Math.abs(delta)>.5) entrySide=delta>0?'top':'bottom';
    lastScrollY=window.scrollY;
    lastScroll=performance.now();
    clearTimeout(settleTimer);settleTimer=setTimeout(wake,220);
    // Keep walking on a moving DOM edge. Re-enter only once the support leaves view.
    if(['jump','climb','crouch','peek','drop','grip','poop','pee'].includes(state)){returning=true;hide();pose('rest',lastScroll);}
    wake();
  },{passive:true});
  window.addEventListener('resize',()=>{returning=Boolean(current)||returning;glyphCache=new WeakMap();measure();hide();pose('rest',performance.now());wake();},{passive:true});
  document.addEventListener('visibilitychange',sync);
  motion.addEventListener('change',()=>{updateClaws(performance.now(),true);hide();pose('rest',performance.now());wake();});
  new MutationObserver(sync).observe(root,{attributes:true,attributeFilter:['class','data-modo']});
  new MutationObserver(sync).observe(document.body,{attributes:true,attributeFilter:['class']});
  document.fonts?.ready.then(()=>{glyphCache=new WeakMap();wake();});
  setTimeout(wake,1100);
  sync();
})();
