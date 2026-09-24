// El logo-puerta en 3D real (mismo Three.js vendorizado que las cards de la
// home, ver product-card-scenes.js): un panel con la marca grabada al
// frente, picaporte, y una bisagra en el borde izquierdo -gira sobre ese
// eje en vez del rotateY plano en CSS que usaba antes- para que la entrada
// y salida de Vaiven/Fendi se sienta como una puerta real abriéndose.
import * as T from './vendor/three/three.module.min.js';

export function createDoor() {
  const renderer = new T.WebGLRenderer({antialias:true, alpha:true, powerPreference:'low-power'});
  renderer.setPixelRatio(1);
  renderer.setClearColor(0x000000,0);
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.1;

  const scene = new T.Scene();
  scene.add(new T.HemisphereLight(0xffffff,0x2a2f2b,2.2));
  const key = new T.DirectionalLight(0xffffff,2.4); key.position.set(-2,3,4); scene.add(key);
  const fill = new T.DirectionalLight(0xffffff,.8); fill.position.set(3,1,2); scene.add(fill);
  const camera = new T.PerspectiveCamera(26,1,.1,50);

  // Textura del frente: mismo lenguaje tipográfico que el wordmark real del
  // header (Arial 800, tracking negativo, punto final en rojo) para que el
  // panel 3D no desentone con el resto del sitio cuando está cerrado/plano.
  function wordmarkTexture(w,h) {
    const c = document.createElement('canvas'); c.width=w; c.height=h;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#181410'; ctx.fillRect(0,0,w,h);
    const size = h*.2, tracking = -size*.07, lineHeight = size*.86;
    ctx.font = `800 ${size}px Arial, Helvetica, sans-serif`; ctx.textBaseline='alphabetic';
    const measure = text => [...text].reduce((width,char)=>width+ctx.measureText(char).width+tracking,0)-tracking;
    const lines = ['THE','TECH','ROOM','ARG.'];
    const left = (w-Math.max(...lines.map(measure)))/2;
    const top = (h-lineHeight*3-size*.73)/2+size*.73;
    lines.forEach((line,row)=>{
      let x=left;
      for(const char of line){
        ctx.fillStyle = char==='.' ? '#d52f27' : '#f4f3ea';
        ctx.fillText(char,x,top+row*lineHeight);
        x += ctx.measureText(char).width+tracking;
      }
    });
    const t = new T.CanvasTexture(c); t.colorSpace = T.SRGBColorSpace; return t;
  }

  const hinge = new T.Group();
  let panel=null, panelWidth=1, panelHeight=1, wordmark=null;
  function buildPanel(aspect) {
    if(panel){hinge.remove(panel);panel.geometry.dispose();for(const m of [].concat(panel.material))m.dispose();}
    if(wordmark)wordmark.dispose();
    panelHeight = 1.6; panelWidth = panelHeight*Math.max(.55,Math.min(3,aspect));
    wordmark = wordmarkTexture(512, Math.round(512/Math.max(aspect,.01)));
    const depth = .05;
    // emissiveMap con la misma textura: el panel gira bastante rápido y con
    // solo luz direccional se apagaba a negro apenas empezaba a girar -acá
    // se lee el wordmark todo el trayecto, sin perder el volumen 3D que dan
    // las luces sobre el resto del panel-. Sin picaporte a propósito: es una
    // "puerta oculta", el logo no debe leerse como una puerta de verdad
    // hasta que gira.
    const front = new T.MeshStandardMaterial({map:wordmark,emissiveMap:wordmark,emissive:0xffffff,emissiveIntensity:.55,roughness:.55,metalness:.05});
    const edge = new T.MeshStandardMaterial({color:0x2a221a,roughness:.7,metalness:.1});
    const materials = [edge,edge,edge,edge,front,edge];
    panel = new T.Mesh(new T.BoxGeometry(panelWidth,panelHeight,depth),materials);
    // El pivote de la bisagra queda en el borde izquierdo: se corre la malla
    // +width/2 así el origen del grupo (donde rota) coincide con ese borde.
    panel.position.set(panelWidth/2,0,0);
    hinge.add(panel);
  }
  buildPanel(1);
  scene.add(hinge);

  let lastW=0,lastH=0;
  const canvas = document.createElement('canvas');
  canvas.className = 'ttra-cat-door-3d';
  const ctx2d = canvas.getContext('2d');

  function setSize(cssWidth,cssHeight) {
    if(!cssWidth||!cssHeight)return;
    canvas.style.width=`${cssWidth}px`;canvas.style.height=`${cssHeight}px`;
    const dpr=Math.min(devicePixelRatio,1.6);
    const w=Math.round(cssWidth*dpr),h=Math.round(cssHeight*dpr);
    if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
    renderer.setSize(w,h,false);
    camera.aspect=cssWidth/cssHeight;
    const aspect=cssWidth/cssHeight;
    if(Math.abs(aspect-lastW/lastH||0)>.01){buildPanel(aspect);}
    lastW=cssWidth;lastH=cssHeight;
    const halfFov=T.MathUtils.degToRad(13);
    const distance=(panelHeight/2)/Math.tan(halfFov)*1.06;
    camera.position.set(panelWidth/2,0,distance);
    camera.lookAt(panelWidth/2,0,0);
    camera.updateProjectionMatrix();
  }

  function setAngle(deg) { hinge.rotation.y = -T.MathUtils.degToRad(deg); }

  function render() {
    if(!canvas.width||!canvas.height)return;
    renderer.render(scene,camera);
    ctx2d.clearRect(0,0,canvas.width,canvas.height);
    ctx2d.drawImage(renderer.domElement,0,0);
  }

  return {canvas,setSize,setAngle,render,dispose(){renderer.dispose();renderer.forceContextLoss();}};
}
