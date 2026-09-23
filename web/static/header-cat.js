import {createState,advance,toggleState,celebrate,interact,dismissIntroduction,clamp} from './header-cat-state.mjs';
import {catArtwork} from './header-cat-art.js';
import {persistentNavigation} from './cat-navigation.js';

const KEY='ttra_header_cat_state_v1',PREF='ttra_header_cat_enabled';
const motion=matchMedia('(prefers-reduced-motion: reduce)');
let state=createState();
try {
  const saved=JSON.parse(sessionStorage.getItem(KEY)||'null');
  if(saved?.version===1 && typeof saved.active==='boolean' && Number.isFinite(saved.epoch) && Number.isFinite(saved.seed) && Number.isFinite(saved.x) && saved.phase && ['off','enter','return','walk','idle','scratch','lick','jump','pee','poop','sleep','belly','attack','bury-walk','bury','introduce'].includes(saved.phase.kind) && [saved.phase.start,saved.phase.duration,saved.phase.from,saved.phase.to].every(Number.isFinite) && Array.isArray(saved.waste))state=saved;
  else if(localStorage.getItem(PREF)==='1')toggleState(state,Date.now());
} catch {}
const styles=new WeakMap(),mounted=new WeakMap();
function style(doc) {
  if(styles.has(doc))return styles.get(doc);
  const promise=new Promise(resolve=>{
    const link=doc.createElement('link');link.rel='stylesheet';link.href='/header-cat.css';link.onload=resolve;link.onerror=resolve;doc.head.append(link);
  });styles.set(doc,promise);return promise;
}
await style(document);
const portal=document.createElement('div');portal.id='ttra-header-cat-portal';
const cat=document.createElement('div');cat.id='ttra-header-cat';cat.setAttribute('role','button');cat.tabIndex=0;cat.setAttribute('aria-label','Acariciar al gatito');cat.innerHTML=catArtwork+'<span class="ttra-cat-zzz"><span>Z</span><span>Z</span><span>Z</span></span>';
cat.style.setProperty('--cat-clock',`${-(Date.now()-state.epoch)/1000}s`);
let pointerKind='mouse';
cat.addEventListener('pointerdown',event=>{pointerKind=event.pointerType;});
cat.addEventListener('click',event=>{event.stopPropagation();caress(event.pointerType||pointerKind,event.detail);});
cat.addEventListener('keydown',event=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();if(!event.repeat)caress();}});
portal.append(cat);document.body.append(portal);
const bubble=document.createElement('div');bubble.id='ttra-cat-introduction';bubble.hidden=true;
bubble.innerHTML='<a href="/vaiven">Mirá, este soy yo</a><button type="button" aria-label="Cerrar el globo">×</button>';
document.body.append(bubble);
const dismiss=()=>{dismissIntroduction(state,Date.now());persist();render();start();};
bubble.querySelector('button').addEventListener('click',()=>{dismiss();cat.focus({preventScroll:true});});
const albumLink=bubble.querySelector('a');
let albumLinkReady=false,albumLinkPending=false;
albumLink.addEventListener('click',async event=>{
  if(albumLinkReady){albumLinkReady=false;dismiss();return;}
  event.preventDefault();event.stopImmediatePropagation();
  if(albumLinkPending)return;
  albumLinkPending=true;albumLink.setAttribute('aria-busy','true');
  const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),5000);
  try {
    const response=await fetch('/vaiven/acceso',{method:'POST',signal:controller.signal});
    if(!response.ok)throw new Error('album-access');
    const {access}=await response.json();
    if(typeof access!=='string'||!access)throw new Error('album-access');
    if(state.phase.kind!=='introduce')return;
    albumLink.href=`/vaiven?access=${encodeURIComponent(access)}`;
    albumLink.textContent='Mirá, este soy yo';albumLinkReady=true;albumLink.click();
  } catch { albumLink.textContent='No pude abrirlo. Tocá para reintentar.'; }
  finally {clearTimeout(timeout);albumLinkPending=false;albumLink.removeAttribute('aria-busy');}
});
let current=null,geometry=null,resize=null,observer=null,raf=0,lastSave=0,lastPose='',lastSerial=-1;
const wasteNodes=new Map();
const persist=()=>{try{sessionStorage.setItem(KEY,JSON.stringify(state));}catch{}};
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
  geometry={top:h.top,height:h.height,left,right,size,travel:Math.max(0,right-left-size),floor:h.height-6,doorX:b.right-size*.65,mobile};
  Object.assign(portal.style,{top:`${h.top}px`,height:`${h.height}px`});
  Object.assign(cat.style,{width:`${size}px`,height:`${size*5/6}px`});
  Object.assign(button.style,{left:`${b.left-h.left}px`,top:`${b.top-h.top}px`,width:`${b.width}px`,height:`${b.height}px`});
  Object.assign(house.style,{left:`${b.left-h.left}px`,top:`${b.top-h.top}px`,width:`${b.width}px`,height:`${b.height}px`});
}
function toggle() {
  advance(state,Date.now(),geometry||{});toggleState(state,Date.now(),geometry?.travel||0);
  try{localStorage.setItem(PREF,state.active?'1':'0');}catch{}
  persist();lastPose='';render();start();
}
function caress(pointer='keyboard',detail=1) {
  const now=Date.now();advance(state,now,geometry||{});interact(state,now,pointer,detail);persist();render();start();
  if(state.phase.kind==='introduce')bubble.querySelector('a').focus({preventScroll:true});
}
function reward() { celebrate(state,Date.now());persist();start(); }
async function attach(doc) {
  if(doc!==document && !navigation.accepts(doc))return;
  if(doc.querySelector('body.vaiven-page #vaiven-album')){
    resize?.disconnect();observer?.disconnect();current=null;geometry=null;
    cancelAnimationFrame(raf);raf=0;portal.hidden=true;bubble.hidden=true;
    dismissIntroduction(state,Date.now());persist();return;
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
    brand.classList.add('ttra-cat-door');header.append(house,button);
    binding={doc,header,brand,button,house};mounted.set(doc,binding);
    doc.defaultView.addEventListener('ttra:cart-added',reward);
    doc.addEventListener('keydown',event=>{if(event.key==='Escape'&&state.phase.kind==='introduce'){dismiss();cat.focus({preventScroll:true});}});
    doc.addEventListener('pointerdown',event=>{if(state.phase.kind==='introduce'&&!cat.contains(event.target)&&!bubble.contains(event.target))dismiss();});
    doc.defaultView.addEventListener('scroll',measure,{passive:true});
    doc.defaultView.addEventListener('resize',measure,{passive:true});
  }
  current=binding;resize?.disconnect();observer?.disconnect();
  resize=new ResizeObserver(measure);resize.observe(header);
  const account=header.querySelector('.ttra-header-account');if(account)resize.observe(account);
  observer=new MutationObserver(()=>{syncTheme();measure();render();start();});
  observer.observe(doc.documentElement,{attributes:true,attributeFilter:['data-classic-theme','class']});
  syncTheme();measure();render();start();
  if(pageDoc.location.pathname==='/' && pageDoc.defaultView.__TTRA_VAIVEN_RETURN){
    pageDoc.defaultView.__TTRA_VAIVEN_RETURN=null;
    if(state.active)toggle();
    if(state.phase.kind==='return'){
      state.phase.duration=Math.min(state.phase.duration,2200);
      state.phase.running=true;
      persist();render();start();
    }
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
function render() {
  if(!geometry||!current)return;
  const now=Date.now();const g=geometry;
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
  current.brand.style.transform=angle?`perspective(650px) rotateY(${-angle}deg)`:'';
  if(pose.kind==='jump'&&!motion.matches)y-=Math.sin(p*Math.PI)*12;
  if(pose.kind==='joy'&&!motion.matches)y-=Math.sin(pose.joyProgress*Math.PI)*18;
  if(motion.matches && !['enter','return'].includes(kind))x=g.left;
  const facing=kind==='return'?-1:state.phase.direction||(kind==='poop'&&state.x>.5?-1:state.phase.to<state.phase.from?-1:1);
  cat.style.setProperty('--cat-facing',String(facing));
  const visual=['enter','return','bury-walk'].includes(pose.kind)?'walk':pose.kind;
  if(lastPose!==visual||lastSerial!==state.phase.serial){
    cat.dataset.state=visual;cat.dataset.behavior=kind;
    cat.style.setProperty('--cat-phase',`${-(now-state.phase.start)/1000}s`);
    lastPose=visual;lastSerial=state.phase.serial;
  }
  cat.style.transform=`translate3d(${x.toFixed(2)}px,${y.toFixed(2)}px,0)`;
  cat.dataset.sequence=String(state.serial);
  if(!bubble.hidden){
    const width=bubble.getBoundingClientRect().width;
    const left=clamp(x+g.size/2-width/2,12,innerWidth-width-12);
    bubble.style.left=`${left}px`;bubble.style.top=`${g.top+g.height+8}px`;
    bubble.style.setProperty('--bubble-pointer',`${clamp(x+g.size/2-left,18,width-18)}px`);
  }
  for(const w of state.waste){
    let node=wasteNodes.get(w.id);
    if(!node){node=document.createElement('span');node.className='ttra-header-cat-waste';node.dataset.kind=w.kind;if(w.kind==='poop'){
      const emoji=document.createElement('span');emoji.className='cat-poop-emoji';emoji.textContent='💩';
      const earth=document.createElement('span');earth.className='cat-earth-mound';
      const particles=document.createElement('span');particles.className='cat-earth-particles';
      for(let i=0;i<5;i++){const grain=document.createElement('i');grain.style.setProperty('--grain',i);particles.append(grain);}
      node.append(emoji,earth,particles);
    }portal.prepend(node);wasteNodes.set(w.id,node);}
    node.style.left=`${clamp(g.left+w.x*g.travel+g.size*(w.offset??.18)-9,g.left+5,Math.max(g.left+5,g.right-26))}px`;
    node.style.opacity=String(clamp(((w.expires??w.created+5000)-now)/1000));
    node.style.setProperty('--earth-cover',String(w.buryAt?clamp((now-w.buryAt)/2400):0));
    node.style.setProperty('--earth-direction',String(w.offset>.5?-1:1));
    node.dataset.burying=String(pose.kind==='bury'&&state.phase.wasteId===w.id);
    node.dataset.covered=String(Boolean(w.buryAt&&now-w.buryAt>1800));
  }
  for(const [id,node]of wasteNodes)if(!state.waste.some(w=>w.id===id)){node.remove();wasteNodes.delete(id);}
  if(now-lastSave>1000){lastSave=now;persist();}
}
function tick(){raf=0;render();if(state.phase.kind!=='off')raf=requestAnimationFrame(tick);}
function start(){if(!raf&&state.phase.kind!=='off')raf=requestAnimationFrame(tick);}
window.addEventListener('pagehide',persist);
window.addEventListener('pageshow',()=>{measure();render();start();});
document.addEventListener('visibilitychange',()=>{if(!document.hidden){render();start();}else persist();});
motion.addEventListener('change',()=>{render();start();});
function resetAfterWelcome() {
  window.__TTRA_CAT_RESET_AFTER_WELCOME=false;
  cancelAnimationFrame(raf);raf=0;
  state=createState();lastPose='';lastSerial=-1;
  for(const node of wasteNodes.values())node.remove();
  wasteNodes.clear();portal.hidden=true;bubble.hidden=true;
  try{localStorage.removeItem(PREF);}catch{}
  persist();render();
}
window.addEventListener('ttra:welcome-entered',resetAfterWelcome);
// The intro may finish before this dynamically imported module has loaded.
if(window.__TTRA_CAT_RESET_AFTER_WELCOME)resetAfterWelcome();
await attach(document);
