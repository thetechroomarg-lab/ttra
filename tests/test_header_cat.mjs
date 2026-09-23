import test from 'node:test';
import assert from 'node:assert/strict';
import {createState,toggleState,advance,celebrate} from '../web/static/header-cat-state.mjs';
test('serialized behavior resumes the same clock and random sequence',()=>{
 const s=createState(1000,123);toggleState(s,1000);advance(s,20000);
 const restored=JSON.parse(JSON.stringify(s));
 assert.deepEqual(advance(s,31000),advance(restored,31000));assert.deepEqual(s,restored);
});
test('mobile uses both bathroom actions before sleeping, without ordinary jumps',()=>{
 const s=createState(1000,42);toggleState(s,1000);const seen=new Set();
 for(let t=1000;t<100000;t+=100){const p=advance(s,t,{mobile:true,travel:80});seen.add(p.kind);assert.ok(p.x>=0&&p.x<=1);}
 for(const kind of ['walk','pee','poop','sleep'])assert.ok(seen.has(kind),kind);
 assert.ok(!seen.has('jump'));assert.equal(s.phase.kind,'sleep');
});
test('desktop keeps all movement bounded and has varied behavior',()=>{
 const s=createState(1000,42);toggleState(s,1000);const seen=new Set();
 for(let t=1000;t<400000;t+=100){const p=advance(s,t,{mobile:false,travel:950});seen.add(p.kind);assert.ok(p.x>=0&&p.x<=1);}
 for(const kind of ['walk','jump','scratch','lick','pee','poop'])assert.ok(seen.has(kind),kind);
});
test('cart joy is temporary, and returning home actually disables the cat',()=>{
 const s=createState(1000,42);toggleState(s,1000);advance(s,10000);celebrate(s,10000);
 assert.equal(advance(s,10500).kind,'joy');assert.notEqual(advance(s,12000).kind,'joy');
 toggleState(s,13000);assert.equal(s.active,false);assert.equal(s.phase.kind,'return');
 advance(s,20000);assert.equal(s.phase.kind,'off');celebrate(s,21000);assert.equal(advance(s,21000).kind,'off');
});
test('pee still disappears five seconds after it was deposited',()=>{
 const s=createState(1000,42);toggleState(s,1000);
 for(let t=1000;t<23000;t+=100)advance(s,t,{mobile:true,travel:80});
 assert.ok(s.waste.length);advance(s,29000,{mobile:true,travel:80});assert.equal(s.waste.length,0);
});
test('petting stops travel, persists across navigation and resumes after three seconds',async()=>{
 const {pet}=await import('../web/static/header-cat-state.mjs');
 const s=createState(1000,42);toggleState(s,1000);advance(s,10000);
 const x=s.x;pet(s,10000);
 assert.equal(advance(s,11000).kind,'belly');assert.equal(s.x,x);
 const restored=JSON.parse(JSON.stringify(s));
 assert.equal(advance(restored,12999).kind,'belly');assert.equal(restored.x,x);
 assert.notEqual(advance(restored,13000).kind,'belly');
 pet(restored,14000);assert.equal(advance(restored,16999).kind,'belly');
 assert.notEqual(advance(restored,17000).kind,'belly');
 toggleState(s,12000);pet(s,12100);assert.equal(s.phase.kind,'return');
});
test('three rapid pets trigger claws, cannot prolong attack, then calm down',async()=>{
 const {pet}=await import('../web/static/header-cat-state.mjs');
 const s=createState(1000,42);toggleState(s,1000);advance(s,10000);const x=s.x;
 pet(s,10000);pet(s,10400);assert.equal(s.phase.kind,'belly');
 const restored=JSON.parse(JSON.stringify(s));pet(restored,10800);
 assert.equal(advance(restored,11000).kind,'attack');assert.equal(restored.x,x);
 const end=restored.phase.start+restored.phase.duration;
 pet(restored,12000);assert.equal(restored.phase.start+restored.phase.duration,end);
 assert.notEqual(advance(restored,end+100).kind,'attack');
 pet(restored,end+200);assert.equal(restored.phase.kind,'belly');
});
test('spaced pets stay gentle and closing the door cancels an attack',async()=>{
 const {pet}=await import('../web/static/header-cat-state.mjs');
 const s=createState(1000,42);toggleState(s,1000);advance(s,10000);
 for(const t of [10000,12000,14000]){pet(s,t);assert.equal(s.phase.kind,'belly');}
 pet(s,14200);pet(s,14400);assert.equal(s.phase.kind,'attack');
 toggleState(s,14500);pet(s,14600);assert.equal(s.phase.kind,'return');
});
test('poop is followed by a bounded walk, burial and a shared fade, even after navigation',async()=>{
 const {setPhase}=await import('../web/static/header-cat-state.mjs');
 for(const [x,travel] of [[0,500],[1,80],[.5,0]]){
  const s=createState(1000,42);s.active=true;s.x=x;s.nextBathroom=99999;setPhase(s,'poop',1000,2800);
  advance(s,2700,{mobile:true,travel});assert.equal(s.waste.length,1);
  advance(s,3800,{mobile:true,travel});assert.equal(s.phase.kind,'bury-walk');
  const restored=JSON.parse(JSON.stringify(s));
  advance(restored,4800,{mobile:true,travel});assert.equal(restored.phase.kind,'bury');
  assert.ok(restored.x>=0&&restored.x<=1);
  assert.ok(Math.abs(restored.x-x)*travel<=40);
  assert.equal(restored.waste[0].buryAt,4800);
  advance(restored,7600,{mobile:true,travel});assert.equal(restored.waste.length,1);
  advance(restored,8600,{mobile:true,travel});assert.equal(restored.waste.length,0);
 }
});
test('ten mouse clicks or touch taps open a stationary introduction',async()=>{
 const {interact,dismissIntroduction}=await import('../web/static/header-cat-state.mjs');
 for(const pointer of ['mouse','touch']){
  const s=createState(1000,42);toggleState(s,1000);advance(s,10000);const x=s.x;
  const count=10;
  for(let i=1;i<=count;i++){interact(s,10000+i*100,pointer,i);if(i<10)assert.notEqual(s.phase.kind,'introduce');}
  assert.equal(s.phase.kind,'introduce');assert.equal(advance(s,20000).x,x);
  const restored=JSON.parse(JSON.stringify(s));assert.equal(advance(restored,40000).kind,'introduce');
  dismissIntroduction(restored,41000);assert.notEqual(restored.phase.kind,'introduce');
 }
});
test('separated touch taps do not accumulate toward the secret album',async()=>{
 const {interact}=await import('../web/static/header-cat-state.mjs');
 const s=createState(1000,42);toggleState(s,1000);advance(s,10000);
 for(let i=0;i<12;i++){advance(s,10000+i*2000);interact(s,10000+i*2000,'touch',1);}
 assert.notEqual(s.phase.kind,'introduce');
});
