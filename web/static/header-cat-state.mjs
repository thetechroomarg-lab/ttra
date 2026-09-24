// Serializable clock-driven behavior. Navigation never creates a second clock.
export const clamp = (n, a=0, b=1) => Math.max(a, Math.min(b, n));
const mix = (a,b,t) => a+(b-a)*t;
function random(s) { s.seed=(Math.imul(s.seed,1664525)+1013904223)>>>0; return s.seed/4294967296; }
export function createState(now=Date.now(), seed=(Math.random()*4294967295)>>>0) {
  return {version:1,active:false,epoch:now,seed,x:0,serial:0,phase:{kind:'off',start:now,duration:0,from:0,to:0},nextBathroom:now+18000,bathroom:'pee',sleepAt:now+70000,waste:[],joyAt:0};
}
export function setPhase(s,kind,now,duration,to=s.x) {
  s.phase={kind,start:now,duration,from:s.x,to,serial:++s.serial};
}
export function toggleState(s,now,travel=500) {
  s.active=!s.active;s.petTimes=[];s.interactionCount=0;
  if(s.active) {
    s.epoch=now;s.x=0;s.nextBathroom=now+18000;s.bathroom='pee';s.sleepAt=now+70000;
    setPhase(s,'enter',now,1800,0);
  } else setPhase(s,'return',now,Math.min(5000,1800+s.x*travel/100*1000),0);
}
export function celebrate(s,now) { if(s.active && s.phase.kind!=='enter')s.joyAt=now; }
export function pet(s,now) {
  if(!s.active || ['enter','return','off','attack','introduce'].includes(s.phase.kind))return;
  s.joyAt=0;
  s.petTimes=(Array.isArray(s.petTimes)?s.petTimes:[]).filter(t=>Number.isFinite(t)&&now-t>=0&&now-t<=1500);
  s.petTimes.push(now);
  if(s.petTimes.length>=3){s.petTimes=[];setPhase(s,'attack',now,2400,s.x);}
  else s.joyAt=now;
}
export function interact(s,now,pointer='mouse',detail=1) {
  if(!s.active||['enter','return','off','introduce'].includes(s.phase.kind))return;
  if(pointer==='touch'||pointer==='mouse'||pointer==='pen') {
    s.interactionCount=now-(s.lastInteraction??-Infinity)<=1500?(s.interactionCount||0)+1:1;
    s.lastInteraction=now;
  }
  if(s.interactionCount>=10) {
    s.joyAt=0;s.interactionCount=0;s.petTimes=[];setPhase(s,'introduce',now,3600000,s.x);return;
  }
  pet(s,now);
}
export function dismissIntroduction(s,now) {
  if(s.phase.kind==='introduce')setPhase(s,'idle',now,1600,s.x);
}
function next(s,now,mobile,travel) {
  if(!s.active){setPhase(s,'off',now,0);return;}
  if(s.phase.kind==='poop') {
    const waste=s.waste.find(w=>w.id===s.phase.serial);
    if(waste){
      const direction=s.x<=.5?1:-1;
      const to=clamp(s.x+direction*Math.min(1,(mobile?24:40)/Math.max(1,travel)));
      setPhase(s,'bury-walk',now,1000,travel>0?to:s.x);
      s.phase.wasteId=waste.id;s.phase.direction=direction;return;
    }
  }
  if(s.phase.kind==='bury-walk') {
    const {wasteId,direction}=s.phase,waste=s.waste.find(w=>w.id===wasteId);
    if(waste){
      waste.buryAt=now;waste.expires=now+3800;
      setPhase(s,'bury',now,2800);s.phase.wasteId=wasteId;s.phase.direction=direction;return;
    }
  }
  if(mobile && now>=s.sleepAt){setPhase(s,'sleep',now,3600000);return;}
  if(now>=s.nextBathroom){const kind=s.bathroom;s.bathroom=kind==='pee'?'poop':'pee';s.nextBathroom=now+28000;setPhase(s,kind,now,2800);return;}
  const r=random(s);
  if(r<.5 && travel>2) {
    const step=Math.min(1,(mobile?24:130)/travel);
    let to=clamp(s.x+(random(s)>.5?1:-1)*step*(.4+random(s)*.6));
    if(Math.abs(to-s.x)<.02)to=clamp(s.x+(s.x<.5?step:-step));
    setPhase(s,'walk',now,Math.max(900,Math.abs(to-s.x)*travel/(mobile?20:42)*1000),to);
  } else if(!mobile && r>.90) {
    setPhase(s,'jump',now,850,clamp(s.x+(s.x<.5?1:-1)*Math.min(.12,28/Math.max(1,travel))));
  } else setPhase(s,r<.66?'idle':r<.8?'scratch':'lick',now,2400+random(s)*2200);
}
function deposit(s,p) {
  if(!['pee','poop'].includes(p.kind)||p.dropped)return;
  p.dropped=true;
  const created=p.start+p.duration*.58;
  s.waste.push({id:p.serial,kind:p.kind,x:p.to,created,
    offset:p.kind==='poop'&&p.to>.5?.82:.18,
    expires:p.kind==='poop'?p.start+p.duration+4800:created+5000});
}
export function advance(s,now,{mobile=false,travel=500}={}) {
  let p=s.phase;
  // Catch up the same seeded sequence after background tabs and ordinary reloads.
  for(let i=0;p.kind!=='off' && now>=p.start+p.duration && i<256;i++) {
    deposit(s,p);s.x=p.to;
    if((p.kind==='introduce'||p.kind==='sleep'&&mobile) && s.active){p.start=now;p.duration=3600000;break;}
    next(s,p.start+p.duration,mobile,travel);p=s.phase;
  }
  const progress=p.duration?clamp((now-p.start)/p.duration):0;
  s.x=mix(p.from,p.to,progress);
  if(progress>.58)deposit(s,p);
  s.waste=s.waste.filter(w=>now<(w.expires??w.created+5000));
  const joy=s.active && s.joyAt>0 && now-s.joyAt<1150;
  return {kind:joy?'joy':p.kind,progress,joyProgress:joy?clamp((now-s.joyAt)/1150):0,x:s.x};
}
