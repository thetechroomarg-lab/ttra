import {createState,advance,toggleState,setPhase,celebrate,pet,interact,dismissIntroduction,clamp} from './header-cat-state.mjs';
import {catArtwork} from './header-cat-art.js';
import {fendiArtwork} from './header-cat-art-fendi.js';
import {bituArtwork} from './header-cat-art-bitu.js';
import {createDoor} from './header-cat-door.js';
import {persistentNavigation} from './cat-navigation.js';

const KEY='ttra_header_cat_state_v1',PREF='ttra_header_cat_enabled';
const KEY_FENDI='ttra_header_cat_fendi_state_v1';
const KEY_BITU='ttra_header_cat_bitu_state_v1';
const motion=matchMedia('(prefers-reduced-motion: reduce)');
let state=createState();
let fendiState=createState();
let bituState=createState();
try {
  const saved=JSON.parse(sessionStorage.getItem(KEY)||'null');
  if(saved?.version===1 && typeof saved.active==='boolean' && Number.isFinite(saved.epoch) && Number.isFinite(saved.seed) && Number.isFinite(saved.x) && saved.phase && ['off','enter','return','walk','idle','scratch','lick','jump','pee','poop','sleep','belly','attack','bury-walk','bury','introduce'].includes(saved.phase.kind) && [saved.phase.start,saved.phase.duration,saved.phase.from,saved.phase.to].every(Number.isFinite) && Array.isArray(saved.waste))state=saved;
  else if(localStorage.getItem(PREF)==='1')toggleState(state,Date.now());
} catch {}
// Fendi y Bitu son más simples -nunca hacen scratch/lick/belly/attack/
// introduce- pero comparten el mismo formato de estado genérico, así que la
// validación de guardado es la misma sin el chequeo de PREF (nunca quedan
// "recordadas afuera" solas: siempre salen por la puerta después de Vaiven,
// ver toggle()).
function restoreCompanion(key) {
  try {
    const saved=JSON.parse(sessionStorage.getItem(key)||'null');
    if(saved?.version===1 && typeof saved.active==='boolean' && Number.isFinite(saved.epoch) && Number.isFinite(saved.seed) && Number.isFinite(saved.x) && saved.phase && ['off','enter','return','walk','idle','jump','sniff','funny','sleep','pee','poop','bury-walk','bury','introduce'].includes(saved.phase.kind) && [saved.phase.start,saved.phase.duration,saved.phase.from,saved.phase.to].every(Number.isFinite) && Array.isArray(saved.waste))return saved;
  } catch {}
  return null;
}
fendiState=restoreCompanion(KEY_FENDI)||fendiState;
bituState=restoreCompanion(KEY_BITU)||bituState;
const styles=new WeakMap(),mounted=new WeakMap();
function style(doc) {
  if(styles.has(doc))return styles.get(doc);
  const promise=new Promise(resolve=>{
    const link=doc.createElement('link');link.rel='stylesheet';link.href='/header-cat.css';link.onload=resolve;link.onerror=resolve;doc.head.append(link);
  });styles.set(doc,promise);return promise;
}
await style(document);
// El globito de "10 clicks -> álbum de fotos" es solo para clientes logueados;
// invitados siguen viendo el resto de las reacciones (joy, ataque a los 3 clicks).
let ttraLoggedIn=false;
fetch('/api/me').then(r=>{ttraLoggedIn=r.ok;}).catch(()=>{});
const portal=document.createElement('div');portal.id='ttra-header-cat-portal';
const cat=document.createElement('div');cat.id='ttra-header-cat';cat.setAttribute('role','button');cat.tabIndex=0;cat.setAttribute('aria-label','Acariciar al gatito');cat.innerHTML=catArtwork+'<span class="ttra-cat-zzz"><span>Z</span><span>Z</span><span>Z</span></span>';
cat.style.setProperty('--cat-clock',`${-(Date.now()-state.epoch)/1000}s`);
let pointerKind='mouse';
cat.addEventListener('pointerdown',event=>{pointerKind=event.pointerType;});
cat.addEventListener('click',event=>{event.stopPropagation();caress(event.pointerType||pointerKind,event.detail);});
cat.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();if(!event.repeat)caress();}});
// Fendi y Bitu se acarician igual que Vaiven (mismo pet(): salto de
// alegría, o ataque juguetón a los 3 clicks seguidos). Las tres escalan a
// "introduce" (el globito con el link al álbum) a los 10 clicks/taps
// seguidos, pero SOLO si hay un cliente logueado (ttraLoggedIn) -un
// invitado sigue viendo el resto de las reacciones, nunca el globito-.
function makeCompanion(id, artwork, label, s, persistFn, useInteract, getBubble) {
  const el=document.createElement('div');el.id=id;el.setAttribute('role','button');el.tabIndex=0;
  el.setAttribute('aria-label',label);el.innerHTML=artwork+'<span class="ttra-cat-zzz"><span>Z</span><span>Z</span><span>Z</span></span>';
  let pointerKindLocal='mouse';
  el.addEventListener('pointerdown',event=>{pointerKindLocal=event.pointerType;});
  function react(pointer='keyboard',detail=1) {
    const now=Date.now();
    if(useInteract && ttraLoggedIn)interact(s,now,pointer,detail);else pet(s,now);
    persistFn();render();renderFendi();renderBitu();start();
    if(useInteract && s.phase.kind==='introduce')getBubble().querySelector('a').focus({preventScroll:true});
  }
  el.addEventListener('click',event=>{event.stopPropagation();react(event.pointerType||pointerKindLocal,event.detail);});
  el.addEventListener('keydown',event=>{if((event.key==='Enter'||event.key===' ')&&!event.repeat){event.preventDefault();react();}});
  return el;
}
const catFendi=makeCompanion('ttra-header-cat-fendi',fendiArtwork,'Acariciar a Fendi',fendiState,()=>persistFendi(),true,()=>bubbleFendi);
const catBitu=makeCompanion('ttra-header-cat-bitu',bituArtwork,'Acariciar a Bitu',bituState,()=>persistBitu(),true,()=>bubbleBitu);
portal.append(cat,catFendi,catBitu);document.body.append(portal);
const door3d=createDoor();
// Globito de "encontraste mi álbum secreto" a los 10 clicks/taps seguidos
// (ver interact() en header-cat-state.mjs). Fábrica reusada por Vaiven y
// Bitu -Fendi todavía no tiene esta escalada, a propósito-.
function makeIntroBubble(id,s,persistFn,renderFn,focusEl,albumPath,accessPath) {
  const el=document.createElement('div');el.id=id;el.className='ttra-cat-introduction';el.hidden=true;
  el.innerHTML='<a href="'+albumPath+'">Mirá, este soy yo</a><button type="button" aria-label="Cerrar el globo">×</button>';
  document.body.append(el);
  const dismiss=()=>{dismissIntroduction(s,Date.now());persistFn();renderFn();start();};
  el.querySelector('button').addEventListener('click',()=>{dismiss();focusEl.focus({preventScroll:true});});
  const albumLink=el.querySelector('a');
  let albumLinkReady=false,albumLinkPending=false;
  albumLink.addEventListener('click',async event=>{
    if(albumLinkReady){albumLinkReady=false;dismiss();return;}
    event.preventDefault();event.stopImmediatePropagation();
    if(albumLinkPending)return;
    albumLinkPending=true;albumLink.setAttribute('aria-busy','true');
    const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),5000);
    try {
      const response=await fetch(accessPath,{method:'POST',signal:controller.signal});
      if(!response.ok)throw new Error('album-access');
      const {access}=await response.json();
      if(typeof access!=='string'||!access)throw new Error('album-access');
      if(s.phase.kind!=='introduce')return;
      albumLink.href=`${albumPath}?access=${encodeURIComponent(access)}`;
      albumLink.textContent='Mirá, este soy yo';albumLinkReady=true;albumLink.click();
    } catch { albumLink.textContent='No pude abrirlo. Tocá para reintentar.'; }
    finally {clearTimeout(timeout);albumLinkPending=false;albumLink.removeAttribute('aria-busy');}
  });
  return el;
}
const bubble=makeIntroBubble('ttra-cat-introduction',state,()=>persist(),()=>render(),cat,'/vaiven','/vaiven/acceso');
const bubbleBitu=makeIntroBubble('ttra-cat-introduction-bitu',bituState,()=>persistBitu(),()=>renderBitu(),catBitu,'/bitu','/bitu/acceso');
const bubbleFendi=makeIntroBubble('ttra-cat-introduction-fendi',fendiState,()=>persistFendi(),()=>renderFendi(),catFendi,'/fendi','/fendi/acceso');
let current=null,geometry=null,resize=null,observer=null,raf=0,lastSave=0,lastPose='',lastSerial=-1;
let lastPoseFendi='',lastSerialFendi=-1;
let lastPoseBitu='',lastSerialBitu=-1;
const wasteNodes=new Map();
const wasteNodesFendi=new Map();
const wasteNodesBitu=new Map();
const persist=()=>{try{sessionStorage.setItem(KEY,JSON.stringify(state));}catch{}};
const persistFendi=()=>{try{sessionStorage.setItem(KEY_FENDI,JSON.stringify(fendiState));}catch{}};
const persistBitu=()=>{try{sessionStorage.setItem(KEY_BITU,JSON.stringify(bituState));}catch{}};
function measure() {
  if(!current?.header.isConnected)return;
  const {doc,header,brand,button,house}=current;
  const transform=brand.style.transform;brand.style.transform='none';
  const h=header.getBoundingClientRect(),b=brand.getBoundingClientRect();
  brand.style.transform=transform;
  if(!h.height)return;
  const controls=header.querySelector('.ttra-header-account');
  const right=Math.min(h.right-12,controls?.getBoundingClientRect().left-10||h.right-12);
  const left=b.right+10;
  const mobile=doc.defaultView.innerWidth<=700;
  const size=Math.min(mobile?72:92,Math.max(28,right-left));
  // Sin el margen que había antes (h.height-6): las tres deben pisar
  // justo el borde inferior del header, no flotar unos px arriba.
  geometry={top:h.top,height:h.height,left,right,size,travel:Math.max(0,right-left-size),floor:h.height,doorX:b.right-size*.65,mobile,headerLeft:h.left,headerWidth:h.width};
  Object.assign(portal.style,{top:`${h.top}px`,height:`${h.height}px`});
  Object.assign(cat.style,{width:`${size}px`,height:`${size*5/6}px`});
  const sizeFendi=size*.9;
  Object.assign(catFendi.style,{width:`${sizeFendi}px`,height:`${sizeFendi*5/6}px`});
  Object.assign(catBitu.style,{width:`${sizeFendi}px`,height:`${sizeFendi*5/6}px`});
  Object.assign(button.style,{left:`${b.left-h.left}px`,top:`${b.top-h.top}px`,width:`${b.width}px`,height:`${b.height}px`});
  Object.assign(house.style,{left:`${b.left-h.left}px`,top:`${b.top-h.top}px`,width:`${b.width}px`,height:`${b.height}px`});
  Object.assign(door3d.canvas.style,{left:`${b.left-h.left}px`,top:`${b.top-h.top}px`});
  door3d.setSize(b.width,b.height);
}
const companions=[
  {s:()=>state,activateOnly:false},
  {s:()=>fendiState,activateOnly:true},
  {s:()=>bituState,activateOnly:true},
];
// Manda a casa a la(s) que estén afuera en este momento -no asume que están
// todas afuera (ver __TTRA_FENDI_RETURN: se puede volver de su álbum
// habiendo salido solo ella y Vaiven, sin Bitu)-.
function sendAllHome(now) {
  for(const c of companions){
    if(c.s().active){advance(c.s(),now,geometry||{});toggleState(c.s(),now,geometry?.travel||0);}
  }
  duet=null;
}
function toggle() {
  // La puerta es un ciclo de 4 toques: 1) sale Vaiven, 2) sale Fendi, 3)
  // sale Bitu, 4) las tres vuelven adentro juntas. Ninguna vuelve a entrar
  // sola mientras otra sigue afuera -no tendría sentido dejarla "sola en
  // la calle"-, así que el último toque las manda a las tres.
  // Mientras cualquiera está entrando o volviendo, la puerta no responde
  // -tocarla ahí reiniciaba a la que ya estaba "afuera según el estado" de
  // vuelta a 'enter' desde x=0, aunque en pantalla todavía estuviera a
  // mitad de camino del 'return', y el salto se veía como que el gato
  // desaparecía-. Vuelve a responder recién cuando las tres terminaron de
  // entrar/volver del todo.
  if([state,fendiState,bituState].some(s=>['enter','return'].includes(s.phase.kind)))return;
  const now=Date.now();
  const next=companions.find(c=>!c.s().active);
  if(next) {
    advance(next.s(),now,geometry||{});toggleState(next.s(),now,geometry?.travel||0);
  } else {
    sendAllHome(now);
  }
  try{localStorage.setItem(PREF,state.active?'1':'0');}catch{}
  persist();persistFendi();persistBitu();lastPose='';lastPoseFendi='';lastPoseBitu='';render();renderFendi();renderBitu();start();
}
function caress(pointer='keyboard',detail=1) {
  const now=Date.now();advance(state,now,geometry||{});if(ttraLoggedIn)interact(state,now,pointer,detail);else pet(state,now);persist();render();start();
  if(state.phase.kind==='introduce')bubble.querySelector('a').focus({preventScroll:true});
}
function reward() { celebrate(state,Date.now());persist();start(); }
async function attach(doc) {
  if(doc!==document && !navigation.accepts(doc))return;
  if(doc.querySelector('body.vaiven-page #vaiven-album, body.bitu-page #bitu-album, body.fendi-page #fendi-album')){
    resize?.disconnect();observer?.disconnect();current=null;geometry=null;
    cancelAnimationFrame(raf);raf=0;portal.hidden=true;bubble.hidden=true;bubbleBitu.hidden=true;bubbleFendi.hidden=true;
    dismissIntroduction(state,Date.now());dismissIntroduction(bituState,Date.now());dismissIntroduction(fendiState,Date.now());
    persist();persistBitu();persistFendi();return;
  }
  const pageDoc=doc;
  if(doc!==document){
    if(!mounted.has(doc)){
      doc.defaultView.addEventListener('ttra:cart-added',reward);
      mounted.set(doc,{delegated:true});
    }
    doc=document;
  }
  await style(doc);
  const header=doc.querySelector('body > header.ttra-site-header');
  const brand=header?.querySelector('.rc-logo, .ttra-page-brand');
  if(!header||!brand)return;
  let binding=mounted.get(doc);
  if(!binding){
    const button=doc.createElement('button');button.type='button';button.className='ttra-cat-logo-toggle';
    button.addEventListener('click',event=>{event.preventDefault();event.stopPropagation();toggle();});
    const house=doc.createElement('div');house.className='ttra-cat-house';house.hidden=true;house.setAttribute('aria-hidden','true');
    if(brand.matches('a')){brand.removeAttribute('href');brand.removeAttribute('aria-label');}
    brand.classList.add('ttra-cat-door');header.append(house,door3d.canvas,button);
    binding={doc,header,brand,button,house};mounted.set(doc,binding);
    doc.defaultView.addEventListener('ttra:cart-added',reward);
    doc.addEventListener('keydown',event=>{
      if(event.key!=='Escape')return;
      if(state.phase.kind==='introduce'){dismissIntroduction(state,Date.now());persist();render();cat.focus({preventScroll:true});}
      if(bituState.phase.kind==='introduce'){dismissIntroduction(bituState,Date.now());persistBitu();renderBitu();catBitu.focus({preventScroll:true});}
      if(fendiState.phase.kind==='introduce'){dismissIntroduction(fendiState,Date.now());persistFendi();renderFendi();catFendi.focus({preventScroll:true});}
    });
    doc.addEventListener('pointerdown',event=>{
      if(state.phase.kind==='introduce'&&!cat.contains(event.target)&&!bubble.contains(event.target)){dismissIntroduction(state,Date.now());persist();render();}
      if(bituState.phase.kind==='introduce'&&!catBitu.contains(event.target)&&!bubbleBitu.contains(event.target)){dismissIntroduction(bituState,Date.now());persistBitu();renderBitu();}
      if(fendiState.phase.kind==='introduce'&&!catFendi.contains(event.target)&&!bubbleFendi.contains(event.target)){dismissIntroduction(fendiState,Date.now());persistFendi();renderFendi();}
    });
    doc.defaultView.addEventListener('scroll',measure,{passive:true});
    doc.defaultView.addEventListener('resize',measure,{passive:true});
  }
  current=binding;resize?.disconnect();observer?.disconnect();
  resize=new ResizeObserver(measure);resize.observe(header);
  const account=header.querySelector('.ttra-header-account');if(account)resize.observe(account);
  observer=new MutationObserver(()=>{syncTheme();measure();render();renderFendi();renderBitu();start();});
  observer.observe(doc.documentElement,{attributes:true,attributeFilter:['data-classic-theme','class']});
  syncTheme();measure();render();renderFendi();renderBitu();start();
  if(pageDoc.location.pathname==='/' && pageDoc.defaultView.__TTRA_VAIVEN_RETURN){
    pageDoc.defaultView.__TTRA_VAIVEN_RETURN=null;
    // toggle() asume el orden secuencial de la puerta (activaría a la
    // siguiente inactiva en vez de mandar a Vaiven a casa si él salió
    // solo); sendAllHome() manda a casa solo a quien esté afuera de verdad.
    if(state.active)sendAllHome(Date.now());
    for(const s of [state,fendiState,bituState]) {
      if(s.phase.kind==='return') {
        s.phase.duration=Math.min(s.phase.duration,2200);
        s.phase.running=true;
      }
    }
    persist();persistFendi();persistBitu();render();renderFendi();renderBitu();start();
  }
  if(pageDoc.location.pathname==='/' && pageDoc.defaultView.__TTRA_BITU_RETURN){
    pageDoc.defaultView.__TTRA_BITU_RETURN=null;
    if(bituState.active)sendAllHome(Date.now());
    for(const s of [state,fendiState,bituState]) {
      if(s.phase.kind==='return') {
        s.phase.duration=Math.min(s.phase.duration,2200);
        s.phase.running=true;
      }
    }
    persist();persistFendi();persistBitu();render();renderFendi();renderBitu();start();
  }
  if(pageDoc.location.pathname==='/' && pageDoc.defaultView.__TTRA_FENDI_RETURN){
    pageDoc.defaultView.__TTRA_FENDI_RETURN=null;
    // Fendi puede estar afuera sin que Bitu lo esté (el ciclo de la puerta
    // es secuencial, Bitu es la última en salir), así que acá manda a casa
    // a quien esté afuera en vez de asumir que están las tres.
    if(fendiState.active)sendAllHome(Date.now());
    for(const s of [state,fendiState,bituState]) {
      if(s.phase.kind==='return') {
        s.phase.duration=Math.min(s.phase.duration,2200);
        s.phase.running=true;
      }
    }
    persist();persistFendi();persistBitu();render();renderFendi();renderBitu();start();
  }
}
function syncTheme(){
  if(!current)return;
  const color=current.doc.defaultView.getComputedStyle(current.doc.documentElement).getPropertyValue('--rc-green');
  portal.style.setProperty('--rc-green',color);
}
const navigation=persistentNavigation({attach,portal});
// Frames delegate to this host rather than creating a mascot or behavior engine.
window.TTRAHeaderCat={ready:doc=>navigation.ready(doc),attach:doc=>{if(navigation.accepts(doc)&&doc.readyState==='complete')attach(doc);}};
const ease=t=>{t=clamp(t);return t*t*(3-2*t);};
// Dúo Vaiven+Fendi: cuando las dos están afuera y libres (no enter/return/
// jump/sniff/funny), cada tanto se dispara UN gesto guionado -perseguirse
// (Fendi corre, Vaiven salta hacia donde va) o el gag de olerle la cola-
// en vez de dejarlas 100% al azar. setPhase pisa lo que advance() hubiera
// elegido random para esa transición puntual; el resto del tiempo siguen
// deambulando solas con la máquina de estados de siempre.
let duet=null,nextDuetCheck=0,lastVaivenX=0,lastFendiX=0,lastBituX=0,angleVaiven=0,angleFendi=0,angleBitu=0;
function stepDuet(now,g) {
  if(!state.active||!fendiState.active||!bituState.active){duet=null;return;}
  const free=['idle','walk'];
  if(duet) {
    if(duet.kind==='sniff') {
      // Oler la cola: Vaiven+Fendi nada más -Bitu sigue a lo suyo-.
      if(duet.stage==='approach' && now>=duet.until) {
        setPhase(state,'sniff',now,900,state.x);
        duet={kind:'sniff',stage:'sniff',until:now+900};
      } else if(duet.stage==='sniff' && now>=duet.until) {
        setPhase(state,'funny',now,1100,state.x);
        duet={kind:'sniff',stage:'funny',until:now+1100};
      } else if(duet.stage==='funny' && now>=duet.until) {
        setPhase(state,'idle',now,1400,state.x);
        duet=null;
      }
    } else if(duet.kind==='chase') {
      // Vaiven+Bitu se persiguen a las corridas -Bitu nunca es la que
      // "juega" con Fendi, siempre es con Vaiven- mientras Fendi se va
      // caminando (no deslizando dormida) hasta el rincón y ahí sí duerme.
      if(duet.fendiStage==='walk' && now>=duet.fendiUntil) {
        setPhase(fendiState,'sleep',now,3600,fendiState.x);
        duet.fendiStage='sleep';
      }
      if(now>=duet.until) {
        duet.leg=(duet.leg||0)+1;
        if(duet.leg>3) {
          setPhase(state,'idle',now,1000,state.x);
          setPhase(bituState,'idle',now,1000,bituState.x);
          if(fendiState.phase.kind==='sleep')setPhase(fendiState,'idle',now,1200,fendiState.x);
          duet=null;
        } else {
          const target=clamp(Math.random());
          const dur=700+Math.random()*450;
          setPhase(bituState,'walk',now,dur,target);
          const gapFrac=g.travel?(g.size*.9*.55)/g.travel:0;
          setPhase(state,duet.leg%2===0?'jump':'walk',now,dur,clamp(target+(target<state.x?gapFrac:-gapFrac)));
          duet.until=now+dur;
        }
      }
    }
    return;
  }
  if(now<nextDuetCheck)return;
  nextDuetCheck=now+4500+Math.random()*3500;
  if(!free.includes(state.phase.kind)||!free.includes(fendiState.phase.kind)||!free.includes(bituState.phase.kind))return;
  const r=Math.random();
  if(r<.35) {
    // Vaiven+Bitu se ponen a jugar: Fendi se retira caminando al rincón
    // más cercano y recién ahí se duerme, mientras corren de acá para allá.
    const corner=fendiState.x<.5?0:1;
    // Sin tope, si Fendi estaba lejos del rincón (todo el ancho del piso)
    // tardaba varios segundos en llegar y recién ahí se dormía -acá se
    // apura un poco, no tiene que caminar a paso normal para esto-.
    const walkDur=Math.min(2200,Math.max(500,Math.abs(corner-fendiState.x)*g.travel/(g.mobile?20:42)*1000));
    setPhase(fendiState,'walk',now,walkDur,corner);
    duet={kind:'chase',leg:0,until:now,fendiStage:'walk',fendiUntil:now+walkDur};
  } else if(r<.55) {
    // Oler la cola: Vaiven camina hasta quedar justo detrás de Fendi.
    const facingFendi=fendiState.phase.to<fendiState.phase.from?-1:1;
    const gapFrac=g.travel?(g.size*.9*.32)/g.travel:0;
    setPhase(state,'walk',now,1100,clamp(fendiState.x-facingFendi*gapFrac));
    duet={kind:'sniff',stage:'approach',until:now+1100};
  }
}
// Compartido por Vaiven y Fendi -misma frecuencia de pis/caca, mapa de
// nodos DOM aparte para cada una porque los ids de waste son por gato.
// Mientras están quietas/caminando (nunca durante una pose ya armada a
// propósito: dormir, oler, cara graciosa, etc.) giran apenas la cabeza
// hacia la puntita de la línea roja de scroll y la siguen a medida que
// avanza -window.__ttraScrollPct lo actualiza site-header.js en cada frame-.
function applyScrollLook(el,x,kind,facing,g) {
  if(motion.matches || (kind!=='idle'&&kind!=='walk') || typeof window.__ttraScrollPct!=='number' || !g.headerWidth) {
    el.style.setProperty('--cat-look','0deg');
    return;
  }
  const tipX=g.headerLeft+(window.__ttraScrollPct/100)*g.headerWidth;
  const dx=tipX-x;
  const look=Math.max(-9,Math.min(9,dx/50))*facing;
  el.style.setProperty('--cat-look',`${look.toFixed(1)}deg`);
}
function renderWaste(s,nodes,pose,g,now) {
  for(const w of s.waste){
    let node=nodes.get(w.id);
    if(!node){node=document.createElement('span');node.className='ttra-header-cat-waste';node.dataset.kind=w.kind;if(w.kind==='poop'){
      const emoji=document.createElement('span');emoji.className='cat-poop-emoji';emoji.textContent='💩';
      const earth=document.createElement('span');earth.className='cat-earth-mound';
      const particles=document.createElement('span');particles.className='cat-earth-particles';
      for(let i=0;i<5;i++){const grain=document.createElement('i');grain.style.setProperty('--grain',i);particles.append(grain);}
      node.append(emoji,earth,particles);
    }portal.prepend(node);nodes.set(w.id,node);}
    node.style.left=`${clamp(g.left+w.x*g.travel+g.size*(w.offset??.18)-9,g.left+5,Math.max(g.left+5,g.right-26))}px`;
    node.style.opacity=String(clamp(((w.expires??w.created+5000)-now)/1000));
    node.style.setProperty('--earth-cover',String(w.buryAt?clamp((now-w.buryAt)/2400):0));
    node.style.setProperty('--earth-direction',String(w.offset>.5?-1:1));
    node.dataset.burying=String(pose.kind==='bury'&&s.phase.wasteId===w.id);
    node.dataset.covered=String(Boolean(w.buryAt&&now-w.buryAt>1800));
  }
  for(const [id,node]of nodes)if(!s.waste.some(w=>w.id===id)){node.remove();nodes.delete(id);}
}
function render() {
  if(!geometry||!current)return;
  const now=Date.now();const g=geometry;
  stepDuet(now,g);
  const pose=advance(state,now,g),p=pose.progress,kind=state.phase.kind;
  const visible=kind!=='off' && !current.doc.documentElement.classList.contains('ttra-welcome-pending');
  portal.hidden=!visible;
  bubble.hidden=!visible||kind!=='introduce';
  cat.setAttribute('aria-expanded',String(!bubble.hidden));
  cat.setAttribute('aria-controls',bubble.id);
  cat.dataset.running=String(kind==='return'&&Boolean(state.phase.running));
  current.button.setAttribute('aria-label',state.active?'Volver a guardar el gatito':'Dejar salir al gatito');
  current.button.setAttribute('aria-pressed',String(state.active));
  current.house.hidden=kind!=='enter'&&kind!=='return';
  let x=g.left+pose.x*g.travel,y=g.floor-g.size*5/6*.92,angle=0;
  if(kind==='enter') {
    angle=p<.25?ease(p/.25)*105:p<.7?105:(1-ease((p-.7)/.3))*105;
    x=g.doorX+(g.left-g.doorX)*ease((p-.2)/.5);
    cat.hidden=p<.19;
  } else if(kind==='return') {
    angle=p<.3?0:p<.5?ease((p-.3)/.2)*105:p<.8?105:(1-ease((p-.8)/.2))*105;
    x=p<.65?g.left+state.phase.from*g.travel*(1-ease(p/.65)):g.left+(g.doorX-g.left)*ease((p-.65)/.22);
    cat.hidden=p>.88;
  } else cat.hidden=false;
  angleVaiven=angle;
  if(pose.kind==='jump'&&!motion.matches)y-=Math.sin(p*Math.PI)*12;
  if(pose.kind==='joy'&&!motion.matches)y-=Math.sin(pose.joyProgress*Math.PI)*18;
  if(motion.matches && !['enter','return'].includes(kind))x=g.left;
  const facing=kind==='return'?-1:state.phase.direction||(kind==='poop'&&state.x>.5?-1:state.phase.to<state.phase.from?-1:1);
  cat.style.setProperty('--cat-facing',String(facing));
  applyScrollLook(cat,x,kind,facing,g);
  const visual=['enter','return','bury-walk'].includes(pose.kind)?'walk':pose.kind;
  if(lastPose!==visual||lastSerial!==state.phase.serial){
    cat.dataset.state=visual;cat.dataset.behavior=kind;
    cat.style.setProperty('--cat-phase',`${-(now-state.phase.start)/1000}s`);
    lastPose=visual;lastSerial=state.phase.serial;
  }
  lastVaivenX=x;
  cat.style.transform=`translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0)`;
  cat.dataset.sequence=String(state.serial);
  if(!bubble.hidden){
    const width=bubble.getBoundingClientRect().width;
    const left=clamp(x+g.size/2-width/2,12,innerWidth-width-12);
    bubble.style.left=`${left}px`;bubble.style.top=`${g.top+g.height+8}px`;
    bubble.style.setProperty('--bubble-pointer',`${clamp(x+g.size/2-left,18,width-18)}px`);
  }
  renderWaste(state,wasteNodes,pose,g,now);
  if(now-lastSave>1000){lastSave=now;persist();}
}
function renderFendi() {
  if(!geometry||!current)return;
  const now=Date.now();const g=geometry,size=g.size*.9;
  const pose=advance(fendiState,now,g),p=pose.progress,kind=fendiState.phase.kind;
  const visible=kind!=='off' && !current.doc.documentElement.classList.contains('ttra-welcome-pending');
  catFendi.hidden=!visible;
  bubbleFendi.hidden=!visible||kind!=='introduce';
  catFendi.setAttribute('aria-expanded',String(!bubbleFendi.hidden));
  catFendi.setAttribute('aria-controls',bubbleFendi.id);
  if(!visible){angleFendi=0;if(now-lastSave>1000)persistFendi();door3d.setAngle(Math.max(angleVaiven,angleFendi,angleBitu));door3d.render();return;}
  let x=g.left+pose.x*g.travel,y=g.floor-size*5/6*.92;
  angleFendi=0;
  if(kind==='enter') {
    angleFendi=p<.25?ease(p/.25)*105:p<.7?105:(1-ease((p-.7)/.3))*105;
    x=g.doorX+(g.left-g.doorX)*ease((p-.2)/.5);
    catFendi.hidden=p<.19;
  } else if(kind==='return') {
    angleFendi=p<.3?0:p<.5?ease((p-.3)/.2)*105:p<.8?105:(1-ease((p-.8)/.2))*105;
    x=p<.65?g.left+fendiState.phase.from*g.travel*(1-ease(p/.65)):g.left+(g.doorX-g.left)*ease((p-.65)/.22);
    catFendi.hidden=p>.88;
  }
  if(pose.kind==='jump'&&!motion.matches)y-=Math.sin(p*Math.PI)*10;
  if(motion.matches && !['enter','return'].includes(kind))x=g.left;
  // Separación mínima para que no se apilen los sprites (glitch visual)
  // -salvo durante el gag armado a propósito, donde el acercamiento es la gracia-.
  if(!duet && kind!=='enter' && kind!=='return') {
    for(const otherX of [lastVaivenX,lastBituX]) {
      const minGap=(g.size+size)*.34;
      const dx=otherX-x;
      if(Math.abs(dx)<minGap)x-=(minGap-Math.abs(dx))/2*(dx>=0?1:-1);
    }
    // El empujón de separación no puede mandarla más allá de la puerta -sin
    // esto, con otro gato pegado al borde izquierdo, el empujón la podía
    // dejar caminando encima del logo-.
    x=Math.max(g.left,Math.min(g.left+g.travel,x));
  }
  const facing=kind==='return'?-1:(kind==='poop'&&fendiState.x>.5?-1:(fendiState.phase.to<fendiState.phase.from?-1:1));
  catFendi.style.setProperty('--cat-facing',String(facing));
  applyScrollLook(catFendi,x,kind,facing,g);
  const visual=['enter','return','bury-walk'].includes(pose.kind)?'walk':pose.kind;
  if(lastPoseFendi!==visual||lastSerialFendi!==fendiState.phase.serial){
    catFendi.dataset.state=visual;
    catFendi.style.setProperty('--cat-phase',`${-(now-fendiState.phase.start)/1000}s`);
    lastPoseFendi=visual;lastSerialFendi=fendiState.phase.serial;
  }
  lastFendiX=x;
  catFendi.style.transform=`translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0)`;
  if(!bubbleFendi.hidden){
    const width=bubbleFendi.getBoundingClientRect().width;
    const left=clamp(x+size/2-width/2,12,innerWidth-width-12);
    bubbleFendi.style.left=`${left}px`;bubbleFendi.style.top=`${g.top+g.height+8}px`;
    bubbleFendi.style.setProperty('--bubble-pointer',`${clamp(x+size/2-left,18,width-18)}px`);
  }
  renderWaste(fendiState,wasteNodesFendi,pose,g,now);
  if(now-lastSave>1000)persistFendi();
  door3d.setAngle(Math.max(angleVaiven,angleFendi,angleBitu));
  door3d.render();
}
function renderBitu() {
  if(!geometry||!current)return;
  const now=Date.now();const g=geometry,size=g.size*.9;
  const pose=advance(bituState,now,g),p=pose.progress,kind=bituState.phase.kind;
  const visible=kind!=='off' && !current.doc.documentElement.classList.contains('ttra-welcome-pending');
  catBitu.hidden=!visible;
  bubbleBitu.hidden=!visible||kind!=='introduce';
  catBitu.setAttribute('aria-expanded',String(!bubbleBitu.hidden));
  catBitu.setAttribute('aria-controls',bubbleBitu.id);
  if(!visible){angleBitu=0;if(now-lastSave>1000)persistBitu();door3d.setAngle(Math.max(angleVaiven,angleFendi,angleBitu));door3d.render();return;}
  let x=g.left+pose.x*g.travel,y=g.floor-size*5/6*.92;
  angleBitu=0;
  if(kind==='enter') {
    angleBitu=p<.25?ease(p/.25)*105:p<.7?105:(1-ease((p-.7)/.3))*105;
    x=g.doorX+(g.left-g.doorX)*ease((p-.2)/.5);
    catBitu.hidden=p<.19;
  } else if(kind==='return') {
    angleBitu=p<.3?0:p<.5?ease((p-.3)/.2)*105:p<.8?105:(1-ease((p-.8)/.2))*105;
    x=p<.65?g.left+bituState.phase.from*g.travel*(1-ease(p/.65)):g.left+(g.doorX-g.left)*ease((p-.65)/.22);
    catBitu.hidden=p>.88;
  }
  if(pose.kind==='jump'&&!motion.matches)y-=Math.sin(p*Math.PI)*10;
  if(motion.matches && !['enter','return'].includes(kind))x=g.left;
  if(!duet && kind!=='enter' && kind!=='return') {
    for(const otherX of [lastVaivenX,lastFendiX]) {
      const minGap=(g.size+size)*.34;
      const dx=otherX-x;
      if(Math.abs(dx)<minGap)x-=(minGap-Math.abs(dx))/2*(dx>=0?1:-1);
    }
    x=Math.max(g.left,Math.min(g.left+g.travel,x));
  }
  const facing=kind==='return'?-1:(kind==='poop'&&bituState.x>.5?-1:(bituState.phase.to<bituState.phase.from?-1:1));
  catBitu.style.setProperty('--cat-facing',String(facing));
  applyScrollLook(catBitu,x,kind,facing,g);
  const visual=['enter','return','bury-walk'].includes(pose.kind)?'walk':pose.kind;
  if(lastPoseBitu!==visual||lastSerialBitu!==bituState.phase.serial){
    catBitu.dataset.state=visual;
    catBitu.style.setProperty('--cat-phase',`${-(now-bituState.phase.start)/1000}s`);
    lastPoseBitu=visual;lastSerialBitu=bituState.phase.serial;
  }
  lastBituX=x;
  catBitu.style.transform=`translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0)`;
  if(!bubbleBitu.hidden){
    const width=bubbleBitu.getBoundingClientRect().width;
    const left=clamp(x+size/2-width/2,12,innerWidth-width-12);
    bubbleBitu.style.left=`${left}px`;bubbleBitu.style.top=`${g.top+g.height+8}px`;
    bubbleBitu.style.setProperty('--bubble-pointer',`${clamp(x+size/2-left,18,width-18)}px`);
  }
  renderWaste(bituState,wasteNodesBitu,pose,g,now);
  if(now-lastSave>1000)persistBitu();
  door3d.setAngle(Math.max(angleVaiven,angleFendi,angleBitu));
  door3d.render();
}
function tick(){raf=0;render();renderFendi();renderBitu();if(state.phase.kind!=='off')raf=requestAnimationFrame(tick);}
function start(){if(!raf&&state.phase.kind!=='off')raf=requestAnimationFrame(tick);}
window.addEventListener('pagehide',()=>{persist();persistFendi();persistBitu();});
window.addEventListener('pageshow',()=>{measure();render();renderFendi();renderBitu();start();});
document.addEventListener('visibilitychange',()=>{if(!document.hidden){render();renderFendi();renderBitu();start();}else{persist();persistFendi();persistBitu();}});
motion.addEventListener('change',()=>{render();renderFendi();renderBitu();start();});
function resetAfterWelcome() {
  window.__TTRA_CAT_RESET_AFTER_WELCOME=false;
  cancelAnimationFrame(raf);raf=0;
  state=createState();lastPose='';lastSerial=-1;
  fendiState=createState();lastPoseFendi='';lastSerialFendi=-1;duet=null;
  bituState=createState();lastPoseBitu='';lastSerialBitu=-1;
  for(const node of wasteNodes.values())node.remove();
  for(const node of wasteNodesFendi.values())node.remove();
  for(const node of wasteNodesBitu.values())node.remove();
  wasteNodes.clear();wasteNodesFendi.clear();wasteNodesBitu.clear();
  portal.hidden=true;bubble.hidden=true;bubbleBitu.hidden=true;bubbleFendi.hidden=true;catFendi.hidden=true;catBitu.hidden=true;
  try{localStorage.removeItem(PREF);}catch{}
  persist();persistFendi();persistBitu();render();renderFendi();renderBitu();
}
window.addEventListener('ttra:welcome-entered',resetAfterWelcome);
// The intro may finish before this dynamically imported module has loaded.
if(window.__TTRA_CAT_RESET_AFTER_WELCOME)resetAfterWelcome();
await attach(document);
