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
  const phone = new T.Group(); phone.scale.x = .96; scene.add(phone);
  const resources = new Set();
  const own = value => { resources.add(value); return value; };
  const mat = (color, metalness = 0, roughness = .4, extra = {}) => own(new T.MeshStandardMaterial({color, metalness, roughness, ...extra}));
  const titanium = mat(0xbcc1c8, .92, .24);
  const burgundy = mat(0x350b14, .72, .34);
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
    const canvas = document.createElement('canvas'); canvas.width=768; canvas.height=kind === 'back' ? 1075 : 1536;
    const c = canvas.getContext('2d');
    c.fillStyle = kind === 'screen' ? '#09090c' : kind === 'battery' ? '#202126' : '#350b14'; c.fillRect(0,0,768,1536);
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
      c.fillStyle='#92969d';
      c.font='29px Arial';['BATERÍA DE IONES DE LITIO', '', '3,87 V · 19,35 Wh', '5000 mAh'].forEach((line,i)=>c.fillText(line,72,290+i*68));
      c.font='110px Arial';c.fillText('+',65,1370);c.fillText('−',580,1370);
      c.fillStyle='#71747a';for(let i=0;i<70;i++){if(i%3)c.fillRect(72+i*8,1050,3,120);}
    } else {
      // Same vector mark as /logos/apple.svg, drawn without a network dependency.
      c.clearRect(0,0,canvas.width,canvas.height);
      c.save(); c.translate(canvas.width/2-110,canvas.height/2-110); c.scale(220/24,220/24);
      c.fillStyle='#17070c';
      c.fill(new Path2D("M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701"));
      c.restore();
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
  slab(back,1.72,3.48,.09,burgundy);
  // iPhone 17 Pro Max: full-width plateau, left-side lenses, right-side sensors.
  // Positive local X is the viewer's left when looking at the rear (-Z).
  slab(back,1.60,1.01,.09,burgundy,0,1.16,-.10,.18);
  const rearCameras = [[.48,1.39],[.055,1.16],[.48,.93]];
  for(const [x,y] of rearCameras) {
    cylinder(back,.218,.055,burgundy,x,y,-.176);
    cylinder(back,.188,.06,black,x,y,-.197);
    cylinder(back,.154,.065,glass,x,y,-.21);
    cylinder(back,.070,.07,lens,x,y,-.225);
    cylinder(back,.025,.072,glass,x,y,-.23);
  }
  cylinder(back,.081,.035,titanium,-.56,1.40,-.16);
  cylinder(back,.068,.04,white,-.56,1.40,-.18);
  cylinder(back,.075,.04,black,-.56,.93,-.18);
  cylinder(back,.012,.04,darkMetal,-.56,1.16,-.18);
  // Separate lower glass inset, with the centered Apple mark.
  const rearGlass = mat(0x300b12,.65,.42);
  slab(back,1.50,2.10,.015,rearGlass,0,-.52,-.058,.15);
  const rearLogo = face(back,1.40,1.96,-.084,texture('back'),true);
  rearLogo.position.y = -.52;
  rearLogo.material.transparent = true;
  rearLogo.material.metalness = .65;
  rearLogo.material.roughness = .6;
  const frame=part(0,[0,0,0]);
  // Hollow chassis: narrow rails leave the internal components visible.
  slab(frame,.055,3.20,.19,burgundy,-.85,0,0,.025);slab(frame,.055,3.20,.19,burgundy,.85,0,0,.025);
  slab(frame,1.61,.07,.19,burgundy,0,1.70,0,.03);slab(frame,1.61,.07,.19,burgundy,0,-1.70,0,.03);
  slab(frame,.07,.34,.065,burgundy,.895,.48,0,.025);
  slab(frame,.07,.23,.065,burgundy,-.895,.62,0,.025);slab(frame,.07,.23,.065,burgundy,-.895,.24,0,.025);
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
  const poweredDisplay = face(screen,1.54,3.26,.043,texture('screen'));
  const shutdownFlash = new T.Mesh(own(new T.PlaneGeometry(1.54,.012)),
    own(new T.MeshBasicMaterial({color:0xd5e7ff,transparent:true,opacity:0,depthWrite:false})));
  shutdownFlash.position.z = .05;
  screen.add(shutdownFlash);
  slab(screen,.46,.10,.011,black,0,1.50,.055,.05);
  cylinder(screen,.028,.012,lens,.13,1.5,.071);
  // Tiny connector sparks: one short pulse as the display and board detach.
  const sparkCanvas = document.createElement('canvas');
  sparkCanvas.width = sparkCanvas.height = 64;
  const sparkContext = sparkCanvas.getContext('2d');
  const sparkGlow = sparkContext.createRadialGradient(32,32,0,32,32,30);
  sparkGlow.addColorStop(0,'rgba(255,255,245,1)');
  sparkGlow.addColorStop(.15,'rgba(255,228,173,.8)');
  sparkGlow.addColorStop(.5,'rgba(255,180,105,.15)');
  sparkGlow.addColorStop(1,'rgba(255,180,105,0)');
  sparkContext.fillStyle = sparkGlow; sparkContext.fillRect(0,0,64,64);
  sparkContext.strokeStyle = 'rgba(255,246,216,.85)'; sparkContext.lineWidth = 1.5;
  sparkContext.beginPath(); sparkContext.moveTo(22,32); sparkContext.lineTo(42,32);
  sparkContext.moveTo(32,22); sparkContext.lineTo(32,42); sparkContext.stroke();
  const sparkTexture = own(new T.CanvasTexture(sparkCanvas));
  const sparks = [[battery,.3,.85,.09],[board,-.35,1.0,.09],[panel,.55,.15,.07]].map(([parent,x,y,z],index) => {
    const material = own(new T.SpriteMaterial({map:sparkTexture,transparent:true,opacity:0,depthWrite:false,blending:T.AdditiveBlending}));
    const sprite = new T.Sprite(material); sprite.position.set(x,y,z); sprite.scale.setScalar(.11); sprite.visible = false; parent.add(sprite);
    return {sprite,delay:index*.025};
  });
  // Camera assembly detaches independently, visible from both orbit directions.
  const cameras=part(-.24,[-1.45,1.4,-2.5]);
  for(const [x,y] of rearCameras){
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
  // Additional independent internals follow their assembled locations outward.
  // Small modules use low-detail geometry to keep the mobile render lightweight.
  const tinyBox = own(new T.BoxGeometry(1,1,1));
  function detail(parent,w,h,d,material,x=0,y=0,z=0) {
    const mesh = new T.Mesh(tinyBox,material);
    mesh.scale.set(w,h,d); mesh.position.set(x,y,z); parent.add(mesh); return mesh;
  }
  // Shield cans lift away from the logic board, exposing the chips below them.
  for (let i=0;i<4;i++) {
    const x=-.48+i*.32;
    const shield=part(.10,[x*1.8,.9+(i%2)*.3,1.0+i*.18]);
    detail(shield,.26,.26,.018,titanium,x,1.17,.035);
    detail(shield,.20,.018,.012,darkMetal,x,1.17,.05);
  }
  // Memory, power-management and radio modules remain small and staggered.
  for (let i=0;i<8;i++) {
    const x=-.56+(i%4)*.36, y=.90+Math.floor(i/4)*.49;
    const module=part(.075,[x*2.1, i<4?.5:1.35, (i%2?1:-1)*(.65+i*.065)]);
    detail(module,.14,.11,.024,black,x,y,.04);
    for(let pin=0;pin<3;pin++) {
      detail(module,.018,.025,.012,gold,x-.045+pin*.045,y-.065,.04);
      detail(module,.018,.025,.012,gold,x-.045+pin*.045,y+.065,.04);
    }
  }
  // Flex connectors and antenna strips peel off along the chassis edges.
  for(let i=0;i<6;i++) {
    const side=i%2?1:-1, y=.72-Math.floor(i/2)*.65;
    const connector=part(.085,[side*(1.1+i*.045),y*.65,.45+(i%3)*.34]);
    detail(connector,.13,.24,.025,black,side*.66,y,0);
    detail(connector,.07,.14,.012,gold,side*.66,y,.02);
  }
  for(let i=0;i<4;i++) {
    const side=i%2?1:-1, y=i<2?.68:-.70;
    const antenna=part(-.025,[side*1.5,y*.6,-.7-(i%2)*.25]);
    detail(antenna,.04,.52,.018,darkMetal,side*.79,y,0);
    detail(antenna,.016,.30,.006,gold,side*.79,y,.014);
  }
  // Optical rings and sensor filters separate from each rear camera module.
  const opticalRing = own(new T.TorusGeometry(.17,.015,6,24));
  rearCameras.forEach(([x,y],i) => {
    const gasket=part(-.27,[-1.25+i*.4,.8+i*.3,-1.6-i*.23]);
    const ring=new T.Mesh(opticalRing,black);ring.position.set(x,y,0);gasket.add(ring);
    const filter=part(-.28,[.7+i*.25,.65+i*.25,-1.35-i*.25]);
    detail(filter,.14,.14,.012,lens,x,y,0);
  });
  for(let i=0;i<4;i++) {
    const side=i%2?1:-1, y=i<2?1.55:-1.55;
    const bracket=part(.03,[side*1.35,y*.35,i%2?.55:-.55]);
    detail(bracket,.18,.055,.018,titanium,side*.58,y,0);
    detail(bracket,.025,.11,.018,titanium,side*.66,y-.03,0);
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
  light(0xffffff,5,-3,5,5);light(0x91b5ff,3,4,1,-4);light(0xffc6b5,.8,-4,-2,-2);light(0xffffff,2,1,-3,6);
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
      for (const {sprite,delay} of sparks) {
        const pulse = (t - 5.08 - delay) / .24;
        sprite.visible = pulse > 0 && pulse < 1;
        sprite.material.opacity = sprite.visible ? .8 * Math.sin(Math.PI*pulse) * (1-pulse) : 0;
        sprite.scale.setScalar(.08 + .05 * T.MathUtils.clamp(pulse,0,1));
      }
      // Losing contact: a brief flicker, vertical collapse, then the last line dies.
      // The glass remains in place and completely dark for the entire orbit.
      const shutdown = T.MathUtils.clamp((t-5.12)/.65,0,1);
      const collapse = ease((shutdown-.20)/.55);
      poweredDisplay.scale.y = Math.max(.003,1-collapse);
      const flicker = shutdown > 0 && shutdown < .22 ? .35+.65*Math.abs(Math.cos(shutdown*48)) : 1;
      poweredDisplay.material.color.setScalar(flicker*(1-ease((shutdown-.65)/.23)));
      poweredDisplay.visible = shutdown < .88;
      shutdownFlash.visible = shutdown > .45 && shutdown < 1;
      shutdownFlash.material.opacity = ease((shutdown-.45)/.2)*(1-ease((shutdown-.78)/.22));
      shutdownFlash.scale.x = 1-ease((shutdown-.78)/.22);
      // Hero hold, acceleration to centrifuge speed, then an abrupt time freeze.
      const spinTime = T.MathUtils.clamp(t-1.3,0,4.2);
      const turns = spinTime < 1.1 ? spinTime*spinTime/2.2 : spinTime-.55;
      phone.rotation.set(.10+.06*explosion, -.45+turns*(Math.PI*6/3.65), -.12);
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
