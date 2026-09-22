import * as T from './vendor/three/three.module.min.js';

const ease = (v) => { v = T.MathUtils.clamp(v, 0, 1); return v*v*(3-2*v); };

export function createScene(host) {
  const renderer = new T.WebGLRenderer({antialias: true, alpha: false, powerPreference: 'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.7));
  renderer.setClearColor(0x000000);
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.35;
  host.appendChild(renderer.domElement);
  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(35, 1, .1, 100);
  const phone = new T.Group(); scene.add(phone);
  const resources = new Set();
  const own = value => { resources.add(value); return value; };
  const mat = (color, metalness = 0, roughness = .4, extra = {}) => own(new T.MeshStandardMaterial({color, metalness, roughness, ...extra}));
  const titanium = mat(0xbcc1c8, .92, .24);
  const orange = mat(0xe66f32, .72, .3);
  const darkMetal = mat(0x292c32, .8, .28);
  const glass = mat(0x050810, .55, .16);
  const gold = mat(0xd6ad69, .8, .25);
  const black = mat(0x111217, .4, .38);
  const pcb = mat(0x13332e, .45, .4);
  const lens = mat(0x141c46, .85, .09, {emissive: 0x14205a, emissiveIntensity: .25});
  const white = mat(0xe4e6e9, .55, .27);
  function rounded(w, h, d, radius = .13) {
    const x = -w/2, y = -h/2, r = Math.min(radius, w/2, h/2);
    const s = new T.Shape();
    s.moveTo(x+r, y); s.lineTo(x+w-r,y); s.quadraticCurveTo(x+w,y,x+w,y+r);
    s.lineTo(x+w,y+h-r); s.quadraticCurveTo(x+w,y+h,x+w-r,y+h);
    s.lineTo(x+r,y+h); s.quadraticCurveTo(x,y+h,x,y+h-r);
    s.lineTo(x,y+r); s.quadraticCurveTo(x,y,x+r,y);
    const g = own(new T.ExtrudeGeometry(s,{depth:d, bevelEnabled:true, bevelSegments:3, steps:1, bevelSize:.015, bevelThickness:.015, curveSegments:12}));
    g.translate(0,0,-d/2); return g;
  }
  function slab(parent,w,h,d,material,x=0,y=0,z=0,r=.13) {
    const mesh = new T.Mesh(rounded(w,h,d,r), material); mesh.position.set(x,y,z); parent.add(mesh); return mesh;
  }
  function cylinder(parent,r,d,material,x,y,z) {
    const mesh = new T.Mesh(own(new T.CylinderGeometry(r,r,d,40)),material);
    mesh.rotation.x = Math.PI/2; mesh.position.set(x,y,z); parent.add(mesh); return mesh;
  }
  function texture(kind) {
    const canvas = document.createElement('canvas'); canvas.width=768; canvas.height=1536;
    const c = canvas.getContext('2d');
    c.fillStyle = kind === 'screen' ? '#09090c' : kind === 'battery' ? '#202126' : '#e87940'; c.fillRect(0,0,768,1536);
    if (kind === 'screen') {
      const glow=c.createRadialGradient(500,870,10,430,850,680);
      glow.addColorStop(0,'#ff8061');glow.addColorStop(.3,'#d52d24');glow.addColorStop(.65,'#441319');glow.addColorStop(1,'#09090c');
      c.fillStyle=glow;c.fillRect(0,0,768,1536);
      for(let i=0;i<5;i++){c.beginPath();c.ellipse(440,880,180+i*58,380+i*64,-.45,0,Math.PI*2);c.strokeStyle=`rgba(255,180,150,${.35-i*.055})`;c.lineWidth=2;c.stroke();}
      c.fillStyle='#fff';c.font='bold 27px Arial';c.fillText('09:41',55,80);
      c.fillRect(639,57,55,22);c.fillRect(698,64,5,9);
      c.font='bold 105px Arial';c.fillText('THE',65,430);c.fillText('TECH',65,545);c.fillText('ROOM',65,660);c.fillText('ARG.',65,775);
      c.font='21px Arial';c.fillStyle='#ffffffbb';c.fillText('HECHO PARA TU MUNDO.',65,1370);
      c.fillStyle='#fff';c.fillRect(255,1485,258,8);
    } else if(kind === 'battery') {
      c.fillStyle='#92969d';c.font='bold 70px Arial';c.fillText('TTRA',72,200);
      c.font='29px Arial';['ENERGÍA PARA','LO QUE VIENE.','', 'BATERÍA DE IONES DE LITIO', '3,87 V · 19,35 Wh', '5000 mAh'].forEach((line,i)=>c.fillText(line,72,290+i*68));
      c.font='110px Arial';c.fillText('+',65,1370);c.fillText('−',580,1370);
      c.fillStyle='#71747a';for(let i=0;i<70;i++){if(i%3)c.fillRect(72+i*8,1050,3,120);}
    } else {
      c.fillStyle='#63321e';c.textAlign='center';c.font='bold 83px Arial';['THE','TECH','ROOM','ARG.'].forEach((line,i)=>c.fillText(line,384,680+i*92));
      c.font='17px Arial';c.fillText('DISEÑADO PARA TU MUNDO',384,1400);
    }
    const t=own(new T.CanvasTexture(canvas));t.colorSpace=T.SRGBColorSpace;t.anisotropy=Math.min(4,renderer.capabilities.getMaxAnisotropy());return t;
  }
  function face(parent,w,h,z,map,flip=false) {
    const material=own(new T.MeshStandardMaterial({map,roughness:.3,metalness:.15,side:T.DoubleSide}));
    const mesh=new T.Mesh(own(new T.PlaneGeometry(w,h)),material);mesh.position.z=z;
    if(flip)mesh.rotation.y=Math.PI;
    parent.add(mesh);return mesh;
  }
  const parts=[];
  function part(z, target) {
    const group=new T.Group();group.position.z=z;phone.add(group);parts.push({group,start:new T.Vector3(0,0,z),target:new T.Vector3(...target)});return group;
  }
  const back=part(-.16,[-.7,.3,-1.85]);
  slab(back,1.72,3.48,.09,orange);face(back,1.57,3.28,-.065,texture('back'),true);
  slab(back,.83,.89,.08,orange,-.37,.99,-.10,.17);
  for(const [x,y] of [[-.58,1.23],[-.19,1.03],[-.58,.79]]) {
    cylinder(back,.168,.08,orange,x,y,-.18);cylinder(back,.125,.085,glass,x,y,-.22);cylinder(back,.074,.09,lens,x,y,-.23);
  }
  cylinder(back,.055,.09,white,-.16,1.32,-.17);
  const frame=part(0,[0,0,0]);
  // Hollow chassis: narrow rails leave the internal components visible.
  slab(frame,.055,3.20,.19,orange,-.85,0,0,.025);slab(frame,.055,3.20,.19,orange,.85,0,0,.025);
  slab(frame,1.61,.07,.19,orange,0,1.70,0,.03);slab(frame,1.61,.07,.19,orange,0,-1.70,0,.03);
  slab(frame,.07,.34,.065,orange,.895,.48,0,.025);
  slab(frame,.07,.23,.065,orange,-.895,.62,0,.025);slab(frame,.07,.23,.065,orange,-.895,.24,0,.025);
  slab(frame,.31,.03,.095,black,0,-1.742,0,.01);
  for(let i=0;i<6;i++)slab(frame,.028,.03,.035,black,.35+i*.065,-1.743,0,.01);
  const battery=part(.035,[-.8,-.65,.85]);
  slab(battery,1.32,2.12,.095,black,0,-.30,0,.07);
  const batteryFace=face(battery,1.26,2.04,.064,texture('battery'));batteryFace.position.y=-.30;
  slab(battery,.17,.3,.015,gold,.3,.85,.02,.02);
  const board=part(.055,[.75,1.0,-.8]);
  slab(board,1.4,.70,.055,pcb,0,1.15,0,.045);
  for(let i=0;i<4;i++) {
    slab(board,.24,.24,.035,i%2?darkMetal:titanium,-.48+i*.32,1.17,.055,.015);
    for(let j=0;j<5;j++)slab(board,.017,.048,.015,gold,-.56+i*.32+j*.035,.999,.04,.001);
  }
  for(let i=0;i<12;i++)slab(board,.04,.025,.016,gold,-.59+i*.108,1.43,.04,.003);
  const panel=part(.12,[.65,.15,1.65]);
  slab(panel,1.67,3.43,.045,darkMetal);slab(panel,1.48,3.22,.015,black,0,0,.04);
  const screen=part(.20,[1.4,.40,2.65]);
  slab(screen,1.68,3.44,.05,glass);
  face(screen,1.54,3.26,.043,texture('screen'));
  slab(screen,.46,.10,.011,black,0,1.50,.055,.05);
  cylinder(screen,.028,.012,lens,.13,1.5,.071);
  // Camera assembly detaches independently, visible from both orbit directions.
  const cameras=part(-.24,[-1.45,1.4,-2.5]);
  for(const [x,y] of [[-.48,1.2],[-.13,1],[-.48,.78]]){
    cylinder(cameras,.148,.12,darkMetal,x,y,0);cylinder(cameras,.105,.13,lens,x,y,.02);cylinder(cameras,.065,.14,glass,x,y,.03);
  }
  const speaker=part(.06,[.35,-1.4,-1]);
  slab(speaker,1.28,.20,.08,darkMetal,0,-1.41,0,.04);
  for(let i=0;i<10;i++)slab(speaker,.045,.12,.015,black,-.47+i*.103,-1.41,.055,.015);
  // Independent internals remain inside the assembled body until the burst.
  const coil = part(-.07, [-1.1, -.25, -1.05]);
  for (let i = 0; i < 10; i++) {
    const ring = new T.Mesh(own(new T.TorusGeometry(.34+i*.023, .009, 5, 56)), gold);
    ring.position.y = -.25; coil.add(ring);
  }
  slab(coil,.10,.44,.015,gold,.18,-.96,0,.01);
  const thermal = part(-.10, [.50,-.28,-1.45]);
  slab(thermal,1.35,2.8,.018,mat(0x9b6540,.8,.3),0,0,0,.12);
  for(let i=0;i<6;i++) slab(thermal,.035,2.3,.008,gold,-.5+i*.2,0,.02,.01);
  const haptic = part(.025, [-1.2,-.8,.4]);
  slab(haptic,.70,.22,.09,titanium,-.24,-1.35,0,.03);
  for(let i=0;i<5;i++) slab(haptic,.025,.14,.012,darkMetal,-.47+i*.11,-1.35,.06,.005);
  const port = part(.035, [.8,-1.1,.7]);
  slab(port,.50,.25,.04,pcb,0,-1.40,0,.015);
  slab(port,.29,.11,.10,titanium,0,-1.51,.025,.03);
  slab(port,.22,.065,.015,black,0,-1.53,.09,.02);
  for(let i=0;i<3;i++) {
    const chip = part(.08, [i*.65-.65,1.55+i*.18,.6+i*.38]);
    slab(chip,.27,.24,.04,darkMetal,-.45+i*.43,1.12,0,.018);
    slab(chip,.18,.15,.006,titanium,-.45+i*.43,1.12,.033,.006);
    const flex = part(.07,[i*.65-.65,-.4,1.0+i*.35]);
    slab(flex,.09,.95,.008,gold,-.5+i*.48,-.15,0,.012);
    slab(flex,.25,.08,.016,black,-.5+i*.48,.34,0,.008);
  }
  for(let i=0;i<8;i++) {
    const x = i%2 ? .76 : -.76, y = 1.45-Math.floor(i/2)*.96;
    const screw = part(.045,[x*1.7,(y>0?.65:-.65),i%2?.9:-.85]);
    cylinder(screw,.033,.08,titanium,x,y,0);
    slab(screw,.04,.009,.005,black,x,y,.047,.001);
  }
  // Compress both the local geometry and assembled layer spacing by 60%.
  // Explosion offsets stay independent of physical thickness.
  parts.forEach(({group,start,target}) => {
    group.scale.z = .4;
    start.z *= .4;
    target.multiplyScalar(.72);
    group.position.copy(start);
  });
  const ambient=new T.HemisphereLight(0xbfd5ff,0x51443d,2);scene.add(ambient);
  function light(color,intensity,x,y,z){const l=new T.DirectionalLight(color,intensity);l.position.set(x,y,z);scene.add(l);}
  light(0xffffff,5,-3,5,5);light(0x91b5ff,3,4,1,-4);light(0xff513b,3,-4,-2,-2);light(0xffffff,2,1,-3,6);
  // Large luminous studio panels provide real metal reflections.
  const studio=new T.Scene();studio.background=new T.Color(0x292c33);
  for(const [x,y,z,w,h] of [[-4,2,0,3,8],[4,3,1,2,7],[0,5,0,8,3],[0,0,5,5,8]]){
    const m=new T.Mesh(new T.PlaneGeometry(w,h),new T.MeshBasicMaterial({color:0xffffff,side:T.DoubleSide}));m.position.set(x,y,z);m.lookAt(0,0,0);studio.add(m);
  }
  const pmrem=new T.PMREMGenerator(renderer);const env=pmrem.fromScene(studio,.05);scene.environment=env.texture;
  studio.traverse(o=>{o.geometry?.dispose();o.material?.dispose();});pmrem.dispose();
  function resize(){const w=host.clientWidth,h=host.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();}
  const observer=new ResizeObserver(resize);observer.observe(host);resize();
  return {
    render(t){
      const explosion=ease((t-4.95)/.55);const orbit=ease((t-5.5)/4.7);
      parts.forEach(({group,start,target})=>group.position.lerpVectors(start,target,explosion));
      // Hero hold, acceleration to centrifuge speed, then an abrupt time freeze.
      const spinTime = T.MathUtils.clamp(t-1.3,0,4.2);
      const turns = spinTime < 1.1 ? spinTime*spinTime/2.2 : spinTime-.55;
      phone.rotation.set(.10+.06*explosion, -.45+turns*(Math.PI*16/3.65), -.12);
      // At 5.5s all components and phone rotation freeze; only the camera moves.
      const angle=orbit*1.7;
      const distance=T.MathUtils.lerp(Math.max(8.2,5/camera.aspect),Math.max(10.8,11.8/camera.aspect),explosion);
      camera.position.set(Math.sin(angle)*distance, .25+orbit*1.6, Math.cos(angle)*distance);
      camera.lookAt(0,0,0);
      renderer.render(scene,camera);
    },
    dispose(){observer.disconnect();resources.forEach(r=>r.dispose());env.dispose();renderer.dispose();renderer.forceContextLoss();renderer.domElement.remove();}
  };
}
