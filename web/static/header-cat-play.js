// Juegos de los gatitos que reaccionan a lo que pasa en la página.
// Regla de oro (aprendida a la fuerza): los gatos NUNCA salen de su piso -el
// borde inferior del header-. Si algo de la página entra en el juego, es ese
// algo el que viene al piso, no el gato el que camina por bordes de la UI.
//
// - Punto rojo: el "." de "Lo tenés." salta del título al piso y los gatos lo
//   persiguen como a un láser, hasta que uno lo manda de vuelta a su lugar.
//   Arranca solo una vez por visita, o tocando el punto.
// - Susto: un scroll muy rápido los hace saltar con la cola inflada.
// - Caza: el mouse sobre el header es una presa: de cerca le tiran un
//   zarpazo, de un poco más lejos se agazapan y saltan hacia él.
//
// Todo es decorativo: no toca clicks, foco ni contenido. El punto original
// solo se oculta con una clase en <html> mientras su copia anda suelta.
import {setPhase,clamp} from './header-cat-state.mjs';

const FREE=['idle','walk','loaf','stretch','yawn','scratch','lick','spin'];
const AUTO_KEY='ttra_cat_dot_auto_v1';
const AWAY='ttra-cat-dot-away';
// Velocidad de corrida en px/s: más rápido se ven deslizándose, no corriendo.
const RUN=160;
const ease=t=>{t=clamp(t);return t*t*(3-2*t);};
const easeOut=t=>1-(1-clamp(t))**3;

export function createPlay({motion,summon}) {
  const dot=document.createElement('span');
  dot.id='ttra-cat-dot';dot.hidden=true;dot.setAttribute('aria-hidden','true');
  document.body.append(dot);
  // Tocar el punto deja un pedido vigente unos segundos: si no hay gatos
  // afuera se llama a uno (summon) y el juego arranca apenas llega.
  let page=null,game=null,requestedUntil=0,eligibleSince=0;
  let lastPct=null,lastPctAt=0,startleAt=0,pointer=null;
  const cooldown=new WeakMap();
  const clicks=new WeakSet();

  addEventListener('pointermove',event=>{
    if(event.pointerType==='mouse')pointer={x:event.clientX,y:event.clientY,at:performance.now()};
  },{passive:true});
  document.documentElement.addEventListener('mouseleave',()=>{pointer=null;});

  function attachPage(doc) {
    if(page&&page!==doc)finish(true);
    page=doc;eligibleSince=0;
    if(clicks.has(doc))return;clicks.add(doc);
    doc.addEventListener('click',event=>{
      if(!event.target.closest?.('#ttra-hero-title .ttra-accent'))return;
      requestedUntil=Date.now()+6000;summon?.();
    });
    if(!doc.getElementById('ttra-cat-dot-style')){
      const style=doc.createElement('style');style.id='ttra-cat-dot-style';
      style.textContent=`html.${AWAY} #ttra-hero-title .ttra-accent{visibility:hidden}`;
      doc.head.append(style);
    }
  }

  // Dónde está el punto rojo del título en coordenadas de la ventana de
  // arriba (la home puede estar adentro del iframe del shell persistente).
  function anchor() {
    try {
      if(!page?.documentElement||page.documentElement.dataset.modo!=='classic')return null;
      if(page.getElementById('ttra-hero-title')?.classList.contains('ttra-text-rolling'))return null;
      const el=page.querySelector('#ttra-hero-title .ttra-accent');
      if(!el)return null;
      const r=el.getBoundingClientRect();if(!r.width||!r.height)return null;
      let ox=0,oy=0;const frame=page.defaultView.frameElement;
      if(frame){const f=frame.getBoundingClientRect();ox=f.left;oy=f.top;}
      // El punto redondo es el ::after del acento (ver classic-editorial.css):
      // la copia que juega en el piso sale con su mismo tamaño, lugar y color.
      const dotCss=page.defaultView.getComputedStyle(el,'::after');
      const d=parseFloat(dotCss.width);
      if(!d)return null;
      return {x:ox+r.left+(parseFloat(dotCss.left)||0)+d/2,y:oy+r.bottom-(parseFloat(dotCss.bottom)||0)-d/2,d,color:dotCss.backgroundColor};
    } catch {return null;}
  }
  const onScreen=(a,g)=>a&&a.y>g.top+g.height+a.d&&a.y<innerHeight-a.d;
  const free=c=>c.s.active&&FREE.includes(c.s.phase.kind);
  const paw=(c,dir)=>c.x+c.size*(dir>0?.8:.2);
  const toNorm=(px,g)=>g.travel>0?clamp((px-g.left)/g.travel):0;

  function place(x,y,squash=1) {
    dot.style.transform=`translate3d(${(x-game.d/2).toFixed(1)}px,${(y-game.d/2).toFixed(1)}px,0) scale(${squash.toFixed(2)},${(1/squash).toFixed(2)})`;
  }
  function face(c,x){c.s.phase.direction=x>c.x+c.size/2?1:-1;}
  // Sale corriendo hasta dejar la pata sobre px; tarda según la distancia.
  function run(c,px,now,g) {
    const dir=px>c.x+c.size/2?1:-1,left=px-(dir>0?.8:.2)*c.size;
    setPhase(c.s,'chase',now,Math.max(450,Math.abs(left-c.x)/RUN*1000),toNorm(left,g));
    c.s.phase.direction=dir;
  }

  // Con un toque explícito también juegan las que duermen (en el celular se
  // duermen al minuto y sin esto el punto nunca respondía); el juego
  // automático no las despierta.
  function start(now,g,cats,wake=false) {
    const players=cats.filter(c=>free(c)||wake&&c.s.active&&c.s.phase.kind==='sleep');
    const a=anchor();
    if(!players.length||!onScreen(a,g))return false;
    const floorY=g.top+g.floor;
    const minX=g.left+g.size*.3,maxX=g.left+g.travel+g.size*.7;
    if(maxX-minX<60)return false;
    // El punto vuela directo a la pata de uno de los gatos, al azar.
    const target=players[Math.floor(Math.random()*players.length)];
    for(const c of players){setPhase(c.s,'watch',now,60000,c.s.x);face(c,a.x);}
    const x=clamp(paw(target,target.s.phase.direction),minX,maxX),y=floorY-a.d/2-1;
    const flight=clamp(Math.hypot(x-a.x,y-a.y)/1.1,450,900);
    game={stage:'escape',at:now,until:now+flight,players,target,turn:players.indexOf(target)+1,dashes:0,
      total:3+Math.floor(Math.random()*3),d:a.d,floorY,minX,maxX,x,y,from:a,deadline:now+60000};
    Object.assign(dot.style,{width:`${game.d}px`,height:`${game.d}px`,background:a.color});
    dot.hidden=false;place(a.x,a.y);
    page.documentElement.classList.add(AWAY);
    return true;
  }

  function finish(aborted,now=Date.now()) {
    if(!game)return;
    if(page?.documentElement)page.documentElement.classList.remove(AWAY);
    dot.hidden=true;
    for(const c of game.players){
      if(c.s.active&&['watch','chase','pounce','swat'].includes(c.s.phase.kind))setPhase(c.s,'idle',now,aborted?800:1600,c.s.x);
    }
    game=null;
  }

  // Un tramo de "láser": el punto se escapa a otro lugar del piso y el gato
  // de turno sale corriendo atrás, con un poco de retraso.
  function dash(now,g) {
    const chaser=game.players[game.turn%game.players.length];
    const span=game.maxX-game.minX;
    // Escapadas cortas (entre un cuarto y la mitad del piso): a paso de
    // corrida, cruzarlo entero dejaba al punto varios segundos esperando.
    const jump=span*(.25+Math.random()*.25);
    let dir=Math.random()<.5?-1:1;
    if(game.x+dir*jump>game.maxX||game.x+dir*jump<game.minX)dir=-dir;
    const to=clamp(game.x+dir*jump,game.minX,game.maxX);
    const dur=260+Math.random()*180;
    Object.assign(game,{stage:'dash',at:now,until:now+dur,fromX:game.x,toX:to,chaser});
    run(chaser,to,now,g);
    for(const c of game.players)if(c!==chaser&&c.s.phase.kind!=='pounce')setPhase(c.s,'watch',now,30000,c.s.x);
  }

  function stepGame(now,g,cats) {
    const live=game.players.every(c=>cats.some(o=>o.s===c.s));
    if(!live||now>game.deadline||game.players.some(c=>!c.s.active)||document.documentElement.classList.contains('ttra-scroll-locked')){finish(true,now);return;}
    // Los objetos de cats se recrean en cada frame: se refresca la posición.
    // Y si a alguno se le terminó la fase del juego, la máquina de estados le
    // habría elegido otra al azar (irse caminando): vuelve a mirar el punto.
    for(const c of game.players){
      const fresh=cats.find(o=>o.s===c.s);c.x=fresh.x;c.size=fresh.size;
      if(!['watch','chase','pounce','swat'].includes(c.s.phase.kind))setPhase(c.s,'watch',now,30000,c.s.x);
    }
    const p=clamp((now-game.at)/Math.max(1,game.until-game.at));
    if(game.stage==='escape') {
      const a=anchor()||game.from;
      // Tiro directo, con apenas una comba (antes subía en vertical y
      // después se iba sola hacia los gatos).
      const x=a.x+(game.x-a.x)*ease(p),y=a.y+(game.y-a.y)*ease(p)-Math.sin(p*Math.PI)*30;
      place(x,y);
      for(const c of game.players)if(c!==game.target)face(c,x);
      if(p>=1){
        // Lo recibe de un zarpazo y el punto sale disparado: arranca la persecución.
        place(game.x,game.y,.7);
        setPhase(game.target.s,'swat',now,700,game.target.s.x);face(game.target,game.x);
        Object.assign(game,{stage:'pause',at:now,until:now,chaser:game.target,dashAt:now+260});
      }
      return;
    }
    if(game.stage==='dash') {
      game.x=game.fromX+(game.toX-game.fromX)*easeOut(p);
      place(game.x,game.y-Math.sin(p*Math.PI)*6,1+.6*Math.sin(p*Math.PI));
      for(const c of game.players)if(c.s.phase.kind==='watch')face(c,game.x);
      if(p>=1){game.dashes++;game.turn++;Object.assign(game,{stage:'pause',at:now,until:now+650+Math.random()*450});}
      return;
    }
    if(game.stage==='pause') {
      place(game.x,game.y);
      const chaser=game.chaser||game.players[0];
      if(game.dashAt){if(now>=game.dashAt){game.dashAt=0;dash(now,g);}return;}
      // Espera a que el gato llegue corriendo.
      if(chaser.s.phase.kind==='chase')return;
      if(now<game.until)return;
      const dir=game.x>chaser.x+chaser.size/2?1:-1;
      if(game.dashes<game.total) {
        // Salta... y el punto se escapa justo antes de que caiga.
        setPhase(chaser.s,'pounce',now,600,toNorm(game.x-(dir>0?.8:.2)*chaser.size,g));
        chaser.s.phase.direction=dir;game.dashAt=now+330;
        return;
      }
      if(Math.abs(paw(chaser,dir)-game.x)>chaser.size*.5&&!game.approached) {
        game.approached=true;run(chaser,game.x,now,g);
        return;
      }
      // El último manotazo es el bueno: el punto vuelve volando a su lugar.
      setPhase(chaser.s,'swat',now,700,chaser.s.x);chaser.s.phase.direction=dir;
      Object.assign(game,{stage:'wind',at:now,until:now+260});
      return;
    }
    if(game.stage==='wind') {
      place(game.x,game.y,1-.3*p);
      if(p>=1)Object.assign(game,{stage:'home',at:now,until:now+800,fromX:game.x});
      return;
    }
    if(game.stage==='home') {
      const a=anchor();
      if(!a||!onScreen(a,g)){dot.style.opacity=String(1-p);if(p>=1){dot.style.opacity='';finish(false,now);}return;}
      const x=game.fromX+(a.x-game.fromX)*ease(p);
      const y=game.y+(a.y-game.y)*ease(p)-Math.sin(p*Math.PI)*110;
      place(x,y,p>.92?1.35:1);
      for(const c of game.players)face(c,x);
      if(p>=1)finish(false,now);
    }
  }

  // Scroll muy rápido = susto. Lee el mismo porcentaje que ya publica
  // site-header.js en cada frame, sea cual sea el documento que scrollea.
  function stepStartle(now,cats) {
    const pct=window.__ttraScrollPct;
    if(typeof pct!=='number'){lastPct=null;return;}
    const dt=now-lastPctAt;
    if(lastPct!==null&&dt>0&&dt<200&&Math.abs(pct-lastPct)/dt*1000>140&&now-startleAt>5000) {
      startleAt=now;
      for(const c of cats)if(c.s.active&&[...FREE,'sleep'].includes(c.s.phase.kind))setPhase(c.s,'startle',now+Math.random()*120,750,c.s.x);
    }
    lastPct=pct;lastPctAt=now;
  }

  // El cursor sobre el header es una presa.
  function stepHunt(now,g,cats) {
    if(!pointer||performance.now()-pointer.at>2500)return;
    if(pointer.y<g.top||pointer.y>g.top+g.height+12)return;
    for(const c of cats) {
      if(!c.s.active||!['idle','loaf','walk'].includes(c.s.phase.kind))continue;
      if(now<(cooldown.get(c.s)||0))continue;
      const dx=pointer.x-(c.x+c.size/2),dir=dx>0?1:-1;
      if(Math.abs(dx)<c.size*.75){
        setPhase(c.s,'swat',now,700,c.s.x);c.s.phase.direction=dir;cooldown.set(c.s,now+2600);
      } else if(Math.abs(dx)<c.size*2.6&&c.s.phase.kind!=='walk'){
        setPhase(c.s,'crouch',now,1100,c.s.x);c.s.phase.direction=dir;cooldown.set(c.s,now+4200);
      }
    }
  }

  // cats: [{s, x, size}] con x = borde izquierdo ya dibujado de cada gato.
  function step(now,g,cats) {
    if(motion.matches||!g){if(game)finish(true,now);requestedUntil=0;return false;}
    if(game){stepGame(now,g,cats);return Boolean(game);}
    stepStartle(now,cats);
    stepHunt(now,g,cats);
    let auto=false;
    if(cats.some(free)&&onScreen(anchor(),g)){
      eligibleSince||=now;
      try{auto=now-eligibleSince>7000&&!sessionStorage.getItem(AUTO_KEY);}catch{}
    } else eligibleSince=0;
    const requested=requestedUntil>now;
    if((requested||auto)&&start(now,g,cats,requested)){
      try{sessionStorage.setItem(AUTO_KEY,'1');}catch{}
      requestedUntil=0;return true;
    }
    return false;
  }

  addEventListener('pagehide',()=>finish(true));
  return {attachPage,step,finish,get busy(){return Boolean(game);}};
}
