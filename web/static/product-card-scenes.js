import * as T from './vendor/three/three.module.min.js';

// One GPU context renders into the card canvases, avoiding five WebGL contexts.
export function createProductCardScenes(entries) {
  const renderer = new T.WebGLRenderer({antialias:true, alpha:true, powerPreference:'low-power'});
  renderer.setPixelRatio(1);
  renderer.setClearColor(0x000000,0);
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  const resources = new Set();
  const own = object => { resources.add(object); return object; };
  const material = (color, metalness=.2, roughness=.35, extra={}) => own(new T.MeshStandardMaterial({color,metalness,roughness,...extra}));
  const black=material(0x17191d,.55,.32), rubber=material(0x090b0e,.05,.75);
  const silver=material(0xc4c8ce,.85,.24), edge=material(0x41464e,.8,.25);
  const glass=material(0x03060d,.55,.12), lens=material(0x091f39,.8,.12);
  const blue=material(0x1766bf,.35,.32), green=material(0x5dff62,.2,.3,{emissive:0x31cf48,emissiveIntensity:.6});
  const unitBox=own(new T.BoxGeometry(1,1,1));
  function mesh(parent,geometry,mat,x=0,y=0,z=0) {const m=new T.Mesh(geometry,mat);m.position.set(x,y,z);parent.add(m);return m;}
  function box(parent,w,h,d,mat,x=0,y=0,z=0){const m=mesh(parent,unitBox,mat,x,y,z);m.scale.set(w,h,d);return m;}
  function roundedGeometry(w,h,d,r=.12) {
    r=Math.min(r,w/2,h/2);const x=-w/2,y=-h/2,s=new T.Shape();
    s.moveTo(x+r,y);s.lineTo(x+w-r,y);s.quadraticCurveTo(x+w,y,x+w,y+r);s.lineTo(x+w,y+h-r);s.quadraticCurveTo(x+w,y+h,x+w-r,y+h);s.lineTo(x+r,y+h);s.quadraticCurveTo(x,y+h,x,y+h-r);s.lineTo(x,y+r);s.quadraticCurveTo(x,y,x+r,y);
    const g=own(new T.ExtrudeGeometry(s,{depth:d,bevelEnabled:true,bevelThickness:.012,bevelSize:.012,bevelSegments:2,curveSegments:10,steps:1}));g.translate(0,0,-d/2);return g;
  }
  const slab=(p,w,h,d,m,x=0,y=0,z=0,r=.12)=>mesh(p,roundedGeometry(w,h,d,r),m,x,y,z);
  function disc(p,r,d,m,x,y,z){const o=mesh(p,own(new T.CylinderGeometry(r,r,d,24)),m,x,y,z);o.rotation.x=Math.PI/2;return o;}
  function texture(draw,w=512,h=512){const c=document.createElement('canvas');c.width=w;c.height=h;draw(c.getContext('2d'),w,h);const t=own(new T.CanvasTexture(c));t.colorSpace=T.SRGBColorSpace;return t;}
  function decal(p,w,h,x,y,z,map,back=false){const m=own(new T.MeshBasicMaterial({map,transparent:true,depthWrite:false}));const o=mesh(p,own(new T.PlaneGeometry(w,h)),m,x,y,z);if(back)o.rotation.y=Math.PI;return o;}
  const apple=texture(c=>{c.fillStyle='#555960';c.save();c.translate(160,125);c.scale(8,8);c.fill(new Path2D('M12.152 6.896c-.948 0-2.415-1.078-3.96-1.04-2.04.027-3.91 1.183-4.961 3.014-2.117 3.675-.546 9.103 1.519 12.09 1.013 1.454 2.208 3.09 3.792 3.039 1.52-.065 2.09-.987 3.935-.987 1.831 0 2.35.987 3.96.948 1.637-.026 2.676-1.48 3.676-2.948 1.156-1.688 1.636-3.325 1.662-3.415-.039-.013-3.182-1.221-3.22-4.857-.026-3.04 2.48-4.494 2.597-4.559-1.429-2.09-3.623-2.324-4.39-2.376-2-.156-3.675 1.09-4.61 1.09zM15.53 3.83c.843-1.012 1.4-2.427 1.245-3.83-1.207.052-2.662.805-3.532 1.818-.78.896-1.454 2.338-1.273 3.714 1.338.104 2.715-.688 3.559-1.701'));c.restore();});
  const alien=texture(c=>{c.fillStyle='#65ff6e';c.beginPath();c.moveTo(256,68);c.bezierCurveTo(55,52,65,270,256,445);c.bezierCurveTo(447,270,457,52,256,68);c.fill();c.fillStyle='#101711';for(const side of [-1,1]){c.save();c.translate(256+side*75,245);c.rotate(-side*.45);c.beginPath();c.ellipse(0,0,34,67,0,0,Math.PI*2);c.fill();c.restore();}});
  function screenTexture(w,h) {
    return texture((c)=>{
      const background=c.createRadialGradient(w*.5,h*.42,0,w*.5,h*.5,Math.max(w,h)*.7);
      background.addColorStop(0,'#202622');background.addColorStop(1,'#060908');
      c.fillStyle=background;c.fillRect(0,0,w,h);
      // Match the header wordmark: heavy Arial, tight tracking and the red final dot.
      const size=Math.min(w*.25,h*.19),tracking=-size*.065,lineHeight=size*.88;
      c.font=`800 ${size}px Arial, Helvetica, sans-serif`;c.textBaseline='alphabetic';
      const measure=text=>[...text].reduce((width,char)=>width+c.measureText(char).width+tracking,0)-tracking;
      const lines=['THE','TECH','ROOM','ARG.'];
      const left=(w-Math.max(...lines.map(measure)))/2;
      const top=(h-lineHeight*3-size*.73)/2+size*.73;
      lines.forEach((line,row)=>{let x=left;for(const char of line){c.fillStyle=char==='.'?'#d52f27':'#f4f3ea';c.fillText(char,x,top+row*lineHeight);x+=c.measureText(char).width+tracking;}});
    },w,h);
  }
  // Texture aspect ratios match each display so the logo is never stretched.
  const phoneScreen=screenTexture(615,1340),tabletScreen=screenTexture(1260,890),laptopScreen=screenTexture(1300,705);

  function phone(){
    const p=new T.Group();slab(p,1.38,2.90,.12,edge,0,0,0,.13);slab(p,1.34,2.86,.035,black,0,0,-.077,.12);
    slab(p,1.32,2.82,.012,glass,0,0,.072,.12);decal(p,1.23,2.68,0,0,.101,phoneScreen);
    disc(p,.025,.008,black,0,1.29,.092);
    // Three lenses share the pill-shaped island; auxiliary sensor sits beside it.
    slab(p,.41,1.34,.065,black,.43,.65,-.13,.19);
    for(const y of [1.06,.65,.24]){disc(p,.173,.06,edge,.43,y,-.18);disc(p,.14,.063,glass,.43,y,-.195);disc(p,.081,.065,lens,.43,y,-.209);disc(p,.03,.068,glass,.43,y,-.215);}
    disc(p,.104,.04,black,-.05,.69,-.118);disc(p,.072,.045,lens,-.05,.69,-.14);disc(p,.043,.02,silver,-.05,1.06,-.11);
    const logo=texture(c=>{c.fillStyle='#93989e';c.font='500 44px Arial';c.textAlign='center';c.fillText('SAMSUNG',256,285);});decal(p,.73,.25,0,-1.03,-.099,logo,true);
    slab(p,.033,.37,.045,edge,.705,.48,0,.012);slab(p,.033,.19,.045,edge,.705,.01,0,.012);
    box(p,.22,.018,.04,black,0,-1.46,0);for(let i=0;i<5;i++)box(p,.022,.015,.035,rubber,-.43+i*.052,-1.46,0);
    return {model:p,radius:1.65,halfHeight:1.55,yaw:Math.PI+.35,tilt:-.07};
  }
  function tablet(){
    const p=new T.Group();slab(p,2.75,2.02,.075,silver,0,0,0,.12);slab(p,2.69,1.96,.008,glass,0,0,.047,.1);decal(p,2.52,1.78,0,0,.076,tabletScreen);disc(p,.022,.006,black,0,.945,.06);
    slab(p,.4,.43,.045,black,1.09,.7,-.06,.095);disc(p,.12,.045,edge,1.09,.73,-.10);disc(p,.095,.047,lens,1.09,.73,-.124);disc(p,.028,.012,silver,.99,.57,-.095);
    decal(p,.92,.92,0,0,-.05,apple,true);for(let i=0;i<3;i++)disc(p,.019,.005,edge,-.075+i*.075,-.8,-.05);
    for(let side of [-1,1])for(let i=0;i<8;i++)box(p,.012,.035,.02,black,side*1.39,.4-i*.07,0);
    slab(p,.18,.024,.04,silver,-.98,1.03,0,.01);
    return {model:p,radius:1.83,halfHeight:1.12,yaw:Math.PI+.38,tilt:.04};
  }
  function laptop(){
    const p=new T.Group();const base=slab(p,2.9,1.92,.12,black,0,-.60,.12,.09);base.rotation.x=-Math.PI/2;
    const deck=new T.Group();deck.position.set(0,-.524,.12);deck.rotation.x=-Math.PI/2;p.add(deck);
    for(let row=0;row<5;row++)for(let col=0;col<13;col++)box(deck,.16,.12,.015,rubber,-1.20+col*.2,.40-row*.18,.012);
    slab(deck,.8,.42,.005,edge,0,-.53,.012,.035);box(deck,.75,.025,.01,green,0,-.73,.019);
    for(let i=0;i<15;i++)box(deck,.115,.025,.009,edge,-1.25+i*.18,.73,.01);
    const lid=new T.Group();lid.position.set(0,-.53,-.81);lid.rotation.x=-.19;p.add(lid);
    slab(lid,2.91,1.78,.1,black,0,.9,0,.07);slab(lid,2.72,1.52,.015,glass,0,.92,.06,.025);decal(lid,2.60,1.41,0,.92,.09,laptopScreen);
    decal(lid,.48,.55,0,.95,-.064,alien,true);disc(lid,.014,.006,edge,0,1.73,.065);
    for(let side of [-1,1]){for(let i=0;i<9;i++)box(p,.026,.025,.09,rubber,side*1.465,-.60,-.55+i*.065);box(p,.03,.044,.17,silver,side*1.465,-.59,.4);}
    box(p,2.3,.015,.025,green,0,-.64,-.865);
    return {model:p,radius:1.94,halfHeight:1.4,yaw:Math.PI-.5,tilt:.13};
  }
  function controller(){
    const p=new T.Group();const shape=new T.Shape();
    // Sculpted shoulders and tapered grips, with a separate rear shell and seam.
    shape.moveTo(-1.08,.62);shape.bezierCurveTo(-1.38,.61,-1.46,.30,-1.50,-.10);
    shape.bezierCurveTo(-1.54,-.48,-1.63,-.91,-1.36,-.98);
    shape.bezierCurveTo(-1.13,-1.06,-.98,-.68,-.80,-.41);
    shape.bezierCurveTo(-.62,-.17,-.45,-.26,0,-.28);
    shape.bezierCurveTo(.45,-.26,.62,-.17,.80,-.41);
    shape.bezierCurveTo(.98,-.68,1.13,-1.06,1.36,-.98);
    shape.bezierCurveTo(1.63,-.91,1.54,-.48,1.50,-.10);
    shape.bezierCurveTo(1.46,.30,1.38,.61,1.08,.62);
    shape.bezierCurveTo(.73,.71,.49,.58,0,.58);
    shape.bezierCurveTo(-.49,.58,-.73,.71,-1.08,.62);shape.closePath();
    const shell=(depth,bevel)=>{const g=own(new T.ExtrudeGeometry(shape,{depth,bevelEnabled:true,bevelThickness:bevel,bevelSize:.065,bevelSegments:6,curveSegments:24,steps:1}));g.translate(0,0,-depth/2);return g;};
    mesh(p,shell(.10,.085),black,0,0,-.13);
    mesh(p,shell(.11,.10),blue,0,0,.105);
    const core=new T.Shape();core.moveTo(-.66,.62);core.lineTo(.66,.62);core.lineTo(.53,.12);core.bezierCurveTo(.9,-.18,.75,-.45,.43,-.47);core.lineTo(-.43,-.47);core.bezierCurveTo(-.75,-.45,-.9,-.18,-.53,.12);core.closePath();const cg=own(new T.ExtrudeGeometry(core,{depth:.015,bevelEnabled:false,curveSegments:14}));mesh(p,cg,rubber,0,0,.26);
    slab(p,1.02,.45,.024,black,0,.39,.29,.08);
    const glow=material(0x61bbff,.3,.3,{emissive:0x298cfa,emissiveIntensity:1});box(p,.027,.38,.012,glow,-.53,.36,.29);box(p,.027,.38,.012,glow,.53,.36,.29);
    for(let side of [-1,1]){disc(p,.215,.08,black,side*.44,-.22,.31);disc(p,.15,.1,rubber,side*.44,-.22,.38);mesh(p,own(new T.TorusGeometry(.155,.013,6,32)),edge,side*.44,-.22,.44);slab(p,.53,.20,.22,rubber,side*.96,.72,-.08,.07);slab(p,.43,.16,.15,black,side*.97,.63,-.25,.065);}
    // Four separated directional buttons and concave-looking rubber thumb caps.
    for(const [dx,dy] of [[0,.115],[0,-.115],[-.115,0],[.115,0]])slab(p,.105,.105,.055,black,-1+dx,.28+dy,.30,.025);
    for(const side of [-1,1]){
      disc(p,.12,.008,rubber,side*.44,-.22,.435);
      slab(p,.045,.12,.028,edge,side*.64,.42,.29,.018);
      for(let i=0;i<16;i++){const angle=i*Math.PI/8;disc(p,.007,.004,edge,side*.44+Math.cos(angle)*.138,-.22+Math.sin(angle)*.138,.444);}
    }
    for(const [x,y,symbol,color] of [[1,.47,'△','#7cdfc4'],[1.2,.27,'○','#ed94a6'],[1,.07,'×','#a7bcf8'],[.8,.27,'□','#d3a8ed']]){
      disc(p,.089,.045,black,x,y,.29);const t=texture(c=>{c.font='280px Arial';c.fillStyle=color;c.textAlign='center';c.textBaseline='middle';c.fillText(symbol,256,260);});decal(p,.13,.13,x,y,.316,t);
    }
    for(let i=0;i<5;i++)disc(p,.012,.012,edge,-.1+i*.05,.07,.285);disc(p,.045,.025,edge,0,-.20,.3);box(p,.13,.033,.012,edge,0,-.37,.27);
    box(p,.18,.035,.012,glass,0,.565,-.22);slab(p,.9,.55,.012,black,0,.0,-.274,.1);
    p.scale.setScalar(.82);
    return {model:p,radius:1.83,halfHeight:1.23,yaw:-.25,tilt:.14};
  }
  function headphones(){
    const p=new T.Group();
    // Two stainless rails support the breathable canopy and telescoping stems.
    const arc=[];for(let i=0;i<=36;i++){const a=Math.PI*i/36;arc.push(new T.Vector3(Math.cos(a)*.92,.35+Math.sin(a)*1.25,0));}
    for(const z of [-.15,.15]){const points=arc.map(v=>new T.Vector3(v.x,v.y,z));mesh(p,own(new T.TubeGeometry(new T.CatmullRomCurve3(points),40,.038,8,false)),edge);}
    const band=new T.Shape();band.absellipse(0,.35,.9,1.25,0,Math.PI,false,0);band.absellipse(0,.35,.79,1.12,Math.PI,0,true,0);band.closePath();const bg=own(new T.ExtrudeGeometry(band,{depth:.28,bevelEnabled:false,curveSegments:30}));bg.translate(0,0,-.14);mesh(p,bg,rubber);
    const canopy=material(0x272a30,.12,.85);for(let i=1;i<20;i++){const a=Math.PI*i/20;const rib=box(p,.028,.03,.29,canopy,Math.cos(a)*.846,.35+Math.sin(a)*1.185,0);rib.rotation.z=a-Math.PI/2;}
    for(const side of [-1,1]){
      const cup=new T.Group();cup.position.set(side*.93,-.29,0);cup.rotation.z=side*.12;p.add(cup);
      cup.rotation.y=side*.16;
      // Round spun-metal ear cups, a softly domed back and padded circular cushions.
      const dome=mesh(cup,own(new T.SphereGeometry(.49,40,24)),black,0,0,-.045);dome.scale.z=.40;
      disc(cup,.474,.13,edge,0,0,.015);
      disc(cup,.459,.13,black,0,0,.04);
      const cushion=mesh(cup,own(new T.TorusGeometry(.362,.103,16,48)),rubber,0,0,.17);cushion.scale.z=.86;
      disc(cup,.279,.028,rubber,0,0,.155);
      const weave=texture((c,w,h)=>{c.fillStyle='#101216';c.fillRect(0,0,w,h);c.strokeStyle='#32353a';c.lineWidth=2;for(let i=0;i<w;i+=12){c.beginPath();c.moveTo(i,0);c.lineTo(i,h);c.stroke();c.beginPath();c.moveTo(0,i);c.lineTo(w,i);c.stroke();}});
      const grille=own(new T.MeshStandardMaterial({map:weave,roughness:.95,metalness:0}));
      mesh(cup,own(new T.CircleGeometry(.266,48)),grille,0,0,.175);
      mesh(cup,own(new T.TorusGeometry(.465,.009,8,48)),edge,0,0,-.08);
      box(p,.055,.55,.065,silver,side*.92,.42,0);
      slab(cup,.13,.25,.11,edge,0,.42,-.01,.06);
      disc(cup,.022,.014,rubber,side*.22,-.34,-.18);
      if(side===1){const crown=mesh(cup,own(new T.CylinderGeometry(.055,.055,.045,32)),edge,.19,.445,0);crown.rotation.z=-.35;slab(cup,.12,.025,.065,edge,-.12,.478,0,.012);}

    }
    p.position.y=-.30;
    return {model:p,radius:1.5,halfHeight:1.40,yaw:-.35,tilt:-.04};
  }
  const makers={phone,tablet,laptop,controller,headphones};
  // Neutral studio reflections keep dark finishes legible through the full turn.
  const studio=new T.Scene();studio.background=new T.Color(0x646970);
  const studioMaterial=new T.MeshBasicMaterial({color:0xffffff});const studioGeometry=new T.PlaneGeometry(4,7);
  for(const [x,y,z] of [[-4,2,2],[4,3,0],[0,3,-5]]){const m=new T.Mesh(studioGeometry,studioMaterial);m.position.set(x,y,z);m.lookAt(0,0,0);studio.add(m);}
  const pmrem=new T.PMREMGenerator(renderer);const environment=pmrem.fromScene(studio,.08);pmrem.dispose();studioMaterial.dispose();studioGeometry.dispose();
  const views=entries.map(entry=>{
    const scene=new T.Scene();scene.environment=environment.texture;
    scene.add(new T.HemisphereLight(0xffffff,0x55534c,2.5));
    for(const [x,y,z,power] of [[-3,4,5,4],[4,1,-3,3],[0,-2,4,1]]){const l=new T.DirectionalLight(0xffffff,power);l.position.set(x,y,z);scene.add(l);}
    const product=makers[entry.kind]();scene.add(product.model);
    return {...entry,...product,scene,camera:new T.PerspectiveCamera(32,1,.1,50),context:entry.canvas.getContext('2d')};
  });
  function render(view,time=0) {
    const width=view.canvas.clientWidth,height=view.canvas.clientHeight;if(!width||!height)return;
    const dpr=Math.min(devicePixelRatio,1.4);const w=Math.round(width*dpr),h=Math.round(height*dpr);
    if(view.canvas.width!==w||view.canvas.height!==h){view.canvas.width=w;view.canvas.height=h;}
    renderer.setSize(w,h,false);view.camera.aspect=width/height;
    const halfFov=T.MathUtils.degToRad(16);
    const distance=Math.max(view.halfHeight,view.radius/view.camera.aspect)/Math.tan(halfFov)*1.14+.18;
    view.camera.position.set(0,.18,distance);view.camera.lookAt(0,.05,0);view.camera.updateProjectionMatrix();
    view.model.rotation.set(view.tilt,view.yaw+time*.34,view.kind==='phone'?-.10:0);
    renderer.render(view.scene,view.camera);view.context.clearRect(0,0,w,h);view.context.drawImage(renderer.domElement,0,0);
    view.card.classList.add('ttra-3d-ready');
  }
  return {views,render,contextCanvas:renderer.domElement,dispose(){resources.forEach(r=>r.dispose());environment.dispose();renderer.dispose();renderer.forceContextLoss();}};
}
