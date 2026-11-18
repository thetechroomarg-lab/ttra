// Bienvenida 3D: oficina, logo extruido desde sus contornos reales y cámara cinematográfica.
// Todo es geometría en tiempo real; no hay video, sprites ni audio.
import * as T from './vendor/three/three.module.min.js';
import LOGO from './welcome-logo.js';
import {loadCharacter} from './welcome-character.js';
import {loadCat} from './welcome-cat.js';
import {loadFendi} from './welcome-fendi.js';
import {drawEditor, drawStore, drawMovie, POSTERS} from './welcome-decor.js';
import {RoundedBoxGeometry} from './vendor/three/addons/geometries/RoundedBoxGeometry.js';

const clamp01 = v => Math.min(1, Math.max(0, v));
const smooth = v => { v = clamp01(v); return v * v * (3 - 2 * v); };
const outCubic = v => 1 - Math.pow(1 - clamp01(v), 3);
const lerp = (a, b, t) => a + (b - a) * t;

const LOGO_HEIGHT = 1.2, LOGO_DEPTH = .26, LOGO_X = 1.3, LOGO_YAW = -.12;

// Con personaje corre la secuencia completa; si el avatar no carga, la versión corta sin él.
const makeTimeline = character => character
  ? {logoStart: 2.5, stagger: .22, rise: 1.2, dot: 4.3, arrive: 4.75, lean: 4.7, look: 5.5, wave: 5.8, waveEnd: 7.75, fadeStart: 8.3, fadeDuration: 1.2, end: 9.5,
     phase: t => t < 1 ? 'office' : t < 2.5 ? 'enter' : t < 4.7 ? 'logo' : t < 5.8 ? 'lean' : t < 7.85 ? 'wave' : t < 8.3 ? 'hold' : 'fade'}
  : {logoStart: 1.1, stagger: .28, rise: 1.25, dot: 3.1, fadeStart: 4.7, fadeDuration: 1.2, end: 5.9,
     phase: t => t < 1.1 ? 'office' : t < 3.5 ? 'logo' : t < 4.7 ? 'hold' : 'fade'};

// Equipos potentes reciben la versión HD (mallas y texturas de alta resolución, sombras finas y posproceso);
// celulares y equipos modestos, la liviana. ?hd=1 / ?hd=0 la fuerza para probar.
function qualityTier() {
  const small = Math.min(innerWidth, innerHeight) < 600;
  const weak = (navigator.hardwareConcurrency || 4) <= 4 || (navigator.deviceMemory || 8) <= 4;
  const forced = new URLSearchParams(location.search).get('hd');
  const hd = forced ? forced === '1' : !(small || weak);
  return hd ? {hd, dpr: 2, shadow: 4096} : {hd, dpr: 1.5, shadow: small || weak ? 1024 : 2048};
}

// ---------- Texturas procedurales ----------
function canvasTexture(w, h, draw, repeat) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new T.CanvasTexture(c); t.colorSpace = T.SRGBColorSpace; t.anisotropy = 8;
  if (repeat) { t.wrapS = t.wrapT = T.RepeatWrapping; t.repeat.set(...repeat); }
  return t;
}
function rng(seed) { return () => (seed = (seed * 16807) % 2147483647) / 2147483647; }

function concreteTexture(size = 1024) {
  const r = rng(7), k = size / 1024;
  return canvasTexture(size, size, (g, w, h) => {
    g.scale(k, k); w /= k; h /= k;
    g.fillStyle = '#56585b'; g.fillRect(0, 0, w, h); // piso gris oscuro: contraste con el logo blanco
    for (let i = 0; i < 260; i++) { // manchas suaves del alisado
      const x = r() * w, y = r() * h, rad = 30 + r() * 150, c = r() < .5 ? 255 : 120;
      const grad = g.createRadialGradient(x, y, 0, x, y, rad);
      grad.addColorStop(0, `rgba(${c},${c},${c},${.01 + r() * .014})`); grad.addColorStop(1, `rgba(${c},${c},${c},0)`);
      g.fillStyle = grad; g.fillRect(x - rad, y - rad, rad * 2, rad * 2);
    }
    for (let i = 0; i < 5000; i++) { g.fillStyle = `rgba(${r() < .5 ? 90 : 240},${r() < .5 ? 90 : 240},${r() < .5 ? 90 : 240},.05)`; g.fillRect(r() * w, r() * h, 1.5, 1.5); }
    g.fillStyle = 'rgba(30,31,33,.6)'; g.fillRect(0, 0, w, 2); g.fillRect(0, 0, 2, h); // juntas de dilatación
  }, [1, 1]);
}

// HD: relieve y brillo del cemento alisado. Un campo de alturas (ondulaciones del llaneado, grano y poros)
// del que salen el normal map y un mapa de rugosidad: el reflejo de las luces se quiebra como en un piso real.
function concreteDetail(size = 2048) {
  const r = rng(19), c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d');
  g.fillStyle = '#808080'; g.fillRect(0, 0, size, size);
  for (let i = 0; i < 420; i++) { // ondulaciones suaves, repetidas en los bordes para que el mosaico no tenga costura
    const x = r() * size, y = r() * size, rad = size * (.02 + r() * .12), v = r() < .5 ? 255 : 0, a = .02 + r() * .05;
    for (const dx of [-size, 0, size]) for (const dy of [-size, 0, size]) {
      if (x + dx + rad < 0 || x + dx - rad > size || y + dy + rad < 0 || y + dy - rad > size) continue;
      const grad = g.createRadialGradient(x + dx, y + dy, 0, x + dx, y + dy, rad);
      grad.addColorStop(0, `rgba(${v},${v},${v},${a})`); grad.addColorStop(1, `rgba(${v},${v},${v},0)`);
      g.fillStyle = grad; g.fillRect(x + dx - rad, y + dy - rad, rad * 2, rad * 2);
    }
  }
  const img = g.getImageData(0, 0, size, size), d = img.data, H = new Float32Array(size * size), R = new Float32Array(size * size);
  for (let i = 0; i < size * size; i++) {
    const low = d[i * 4] / 255, pore = r() < .0016 ? -.6 : 0;
    H[i] = low * 2.2 + (r() - .5) * .35 + pore; // grano fino y algún poro
    R[i] = .2 + (1 - low) * .16 + (r() - .5) * .04; // donde el llaneado dejó la superficie más lisa, refleja más
  }
  const at = (x, y) => H[((y + size) % size) * size + (x + size) % size];
  const nrm = new ImageData(size, size), rough = new ImageData(size, size), n = nrm.data, ro = rough.data;
  for (let y = 0; y < size; y++) for (let x = 0; x < size; x++) {
    const i = y * size + x, gx = at(x + 1, y) - at(x - 1, y), gy = at(x, y + 1) - at(x, y - 1);
    const nx = -gx * .5, ny = gy * .5, len = Math.hypot(nx, ny, 1); // la imagen va hacia abajo y la v de la textura hacia arriba
    n[i * 4] = (nx / len * .5 + .5) * 255; n[i * 4 + 1] = (ny / len * .5 + .5) * 255; n[i * 4 + 2] = (1 / len * .5 + .5) * 255; n[i * 4 + 3] = 255;
    ro[i * 4] = ro[i * 4 + 1] = ro[i * 4 + 2] = Math.min(255, Math.max(0, R[i] * 255)); ro[i * 4 + 3] = 255;
  }
  const tex = data => {
    const cv = document.createElement('canvas'); cv.width = cv.height = size; cv.getContext('2d').putImageData(data, 0, 0);
    const t = new T.CanvasTexture(cv); t.wrapS = t.wrapT = T.RepeatWrapping; t.anisotropy = 8; return t;
  };
  return {normalMap: tex(nrm), roughnessMap: tex(rough)};
}

function screenTexture(kind) {
  return canvasTexture(640, 360, (g, w, h) => {
    const r = rng(kind * 31 + 5);
    g.fillStyle = '#12161c'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#0c0f14'; g.fillRect(0, 0, w, 22);
    ['#e0605a', '#e0b44e', '#5cba6a'].forEach((c, i) => { g.fillStyle = c; g.beginPath(); g.arc(14 + i * 15, 11, 4, 0, 7); g.fill(); });
    const bar = (x, y, bw, c, bh = 5) => { g.fillStyle = c; g.beginPath(); g.roundRect(x, y, bw, bh, 2.5); g.fill(); };
    if (kind % 2 === 0) { // editor: árbol de archivos + líneas de código abstractas
      g.fillStyle = '#171c24'; g.fillRect(0, 22, 120, h);
      for (let i = 0; i < 16; i++) bar(12 + (i % 4 ? 12 : 0), 38 + i * 18, 44 + r() * 46, i === 5 ? '#6ea8ff' : '#3a4452');
      const pal = ['#7fb4ff', '#c7a5f5', '#8fd3a4', '#e7c57c', '#5b6675', '#d98a8a'];
      let indent = 0;
      for (let i = 0; i < 17; i++) {
        const y = 38 + i * 18; bar(132, y, 10, '#2c3440');
        if (r() < .12) continue;
        indent = Math.max(0, Math.min(3, indent + (r() < .3 ? 1 : r() < .45 ? -1 : 0)));
        let x = 156 + indent * 20;
        for (let k = 0, n = 1 + Math.floor(r() * 4); k < n && x < w - 90; k++) { const bw = 18 + r() * 70; bar(x, y, bw, pal[Math.floor(r() * pal.length)]); x += bw + 8; }
      }
    } else { // panel: gráfico de líneas + métricas
      for (let i = 0; i < 3; i++) { g.fillStyle = '#19202a'; g.beginPath(); g.roundRect(18 + i * 204, 38, 192, 70, 6); g.fill(); bar(32 + i * 204, 54, 60, '#4a5666'); bar(32 + i * 204, 74, 100, ['#7fb4ff', '#8fd3a4', '#e7c57c'][i], 12); }
      g.fillStyle = '#19202a'; g.beginPath(); g.roundRect(18, 122, 604, 220, 6); g.fill();
      for (let i = 1; i < 5; i++) { g.fillStyle = '#232c38'; g.fillRect(34, 122 + i * 42, 572, 1); }
      ['#7fb4ff', '#8fd3a4'].forEach((c, s) => {
        g.strokeStyle = c; g.lineWidth = 2.5; g.beginPath();
        let y = 250 - s * 40;
        for (let i = 0; i <= 24; i++) { y = Math.max(150, Math.min(320, y + (r() - .55) * 26)); i ? g.lineTo(34 + i * 23.8, y) : g.moveTo(34, y); }
        g.stroke();
      });
    }
  });
}

export async function createScene(host) {
  const tier = qualityTier();
  const renderer = new T.WebGLRenderer({antialias: true, alpha: false, powerPreference: 'high-performance'});
  let dpr = Math.min(devicePixelRatio || 1, tier.dpr);
  renderer.setPixelRatio(dpr);
  renderer.setClearColor(0x000000);
  renderer.toneMapping = T.ACESFilmicToneMapping;
  renderer.toneMappingExposure = .86;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = T.PCFSoftShadowMap;
  host.appendChild(renderer.domElement);

  const scene = new T.Scene();
  scene.background = new T.Color(0x0b0a09);
  // HD: posproceso cargado aparte (solo lo baja quien lo usa). Si falla, se renderiza directo como siempre.
  const postModules = tier.hd ? Promise.all(['EffectComposer', 'RenderPass', 'GTAOPass', 'UnrealBloomPass', 'OutputPass']
    .map(name => import(`./vendor/three/addons/postprocessing/${name}.js`))).catch(error => { console.warn('[bienvenida] sin posproceso:', error.message); return null; }) : null;
  const camera = new T.PerspectiveCamera(32, 1, .1, 60);
  const unitBox = new T.BoxGeometry(1, 1, 1), unitCyl = new T.CylinderGeometry(1, 1, 1, 28), unitPlane = new T.PlaneGeometry(1, 1);
  const std = (color, roughness = .7, metalness = 0, extra = {}) => new T.MeshStandardMaterial({color, roughness, metalness, ...extra});
  const lit = (color, strength) => new T.MeshBasicMaterial({color: new T.Color(color).multiplyScalar(strength), toneMapped: true});
  // HD: las cajas chicas y medianas (muebles, monitores, libros, marcos) llevan el canto redondeado, que
  // atrapa la luz como un mueble real; las paredes y los listones finísimos siguen siendo cajas simples.
  const rounded = new Map();
  function box(parent, m, w, h, d, x, y, z, shadow = true) {
    const small = Math.min(w, h, d), bevel = tier.hd && small >= .012 && Math.max(w, h, d) < 3;
    const key = bevel && [w, h, d].map(v => v.toFixed(4)).join();
    if (bevel && !rounded.has(key)) rounded.set(key, new RoundedBoxGeometry(w, h, d, 3, Math.min(.009, small * .28)));
    const o = new T.Mesh(bevel ? rounded.get(key) : unitBox, m); if (!bevel) o.scale.set(w, h, d); o.position.set(x, y, z);
    o.castShadow = shadow; o.receiveShadow = true; parent.add(o); return o;
  }
  function cyl(parent, m, r, h, x, y, z, shadow = true) {
    const o = new T.Mesh(unitCyl, m); o.scale.set(r, h, r); o.position.set(x, y, z);
    o.castShadow = shadow; o.receiveShadow = true; parent.add(o); return o;
  }

  // ---------- Entorno de reflejos (HDR procedural: ventana cálida + techo) ----------
  const pmrem = new T.PMREMGenerator(renderer);
  const envScene = new T.Scene();
  envScene.add(new T.Mesh(new T.BoxGeometry(14, 6, 14), new T.MeshBasicMaterial({color: 0x3c3d40, side: T.BackSide})));
  const envPanel = (c, s, w, h, x, y, z, ry, rx = 0) => { const p = new T.Mesh(unitPlane, lit(c, s)); p.scale.set(w, h, 1); p.position.set(x, y, z); p.rotation.set(rx, ry, 0); envScene.add(p); };
  envPanel(0xfff1dc, 9, 6, 3, -6.9, .6, 0, Math.PI / 2);
  envPanel(0xfff6ea, 4, 8, 3, 0, 2.9, 0, 0, Math.PI / 2);
  envPanel(0xdfe8f5, 1.6, 6, 3, 0, .4, 6.9, Math.PI);
  const envTarget = pmrem.fromScene(envScene, .03);
  scene.environment = envTarget.texture; scene.environmentIntensity = .38;
  envScene.traverse(o => { o.geometry?.dispose(); o.material?.dispose(); });
  pmrem.dispose();

  // ---------- Materiales ----------
  const oakMap = concreteTexture(tier.hd ? 2048 : 1024), floorDetail = tier.hd ? concreteDetail() : null;
  const floorMat = floorDetail
    ? std(0xffffff, 1, 0, {map: oakMap, normalMap: floorDetail.normalMap, normalScale: new T.Vector2(.35, .35), roughnessMap: floorDetail.roughnessMap, envMapIntensity: 1.15})
    : std(0xffffff, .34, 0, {map: oakMap, envMapIntensity: 1.1});
  const plaster = std(0x45474a, .9); // paredes gris oscuro
  const accent = std(0x3f4144, .9); // pared de acento detrás del logo: fondo calmo y oscuro para la tipografía blanca
  const ceilingMat = std(0x5a5c5f, .95);
  const oak = std(0xcfa877, .55);
  const oakDark = std(0x8a6744, .6);
  const blackMetal = std(0x17181a, .42, .85);
  const aluminium = std(0xb9bcc0, .32, .9);
  const plastic = std(0x1c1d20, .55, .1);
  const fabric = std(0x2b2e33, .95);
  const glass = new T.MeshPhysicalMaterial({color: 0xdfeaf0, roughness: .04, metalness: 0, transparent: true, opacity: .16, envMapIntensity: 1.6, side: T.DoubleSide, depthWrite: false});
  const ceramic = std(0xe9e6df, .35);
  const leaf = std(0x3d5a37, .62, 0, {side: T.DoubleSide});

  // ---------- Arquitectura ----------
  const room = new T.Group(); scene.add(room);
  const BACK = -4.4, LEFT = -6.2, RIGHT = 6.6, TOP = 3.05;
  const floor = new T.Mesh(unitPlane, floorMat); floor.scale.set(RIGHT - LEFT, 18, 1); floor.rotation.x = -Math.PI / 2; floor.position.set((LEFT + RIGHT) / 2, 0, BACK + 9); floor.receiveShadow = true; room.add(floor);
  oakMap.repeat.set((RIGHT - LEFT) / 2.4, 18 / 2.4);
  if (floorDetail) for (const t of Object.values(floorDetail)) t.repeat.set((RIGHT - LEFT) / 1.6, 18 / 1.6); // otro período: no se repite junto con las manchas
  box(room, plaster, RIGHT - LEFT, TOP, .12, (LEFT + RIGHT) / 2, TOP / 2, BACK - .06, false);
  box(room, ceilingMat, RIGHT - LEFT, .1, 18, (LEFT + RIGHT) / 2, TOP + .05, BACK + 9, false);
  box(room, plaster, .12, TOP, 18, RIGHT + .06, TOP / 2, BACK + 9, false);
  box(room, std(0x2c2d30, .7), RIGHT - LEFT, .09, .02, (LEFT + RIGHT) / 2, .045, BACK + .01, false); // zócalo
  // Pared izquierda con ventanal: antepecho, dintel y vidrio muy iluminado detrás de la carpintería.
  box(room, plaster, .12, .55, 18, LEFT - .06, .275, BACK + 9, false);
  box(room, plaster, .12, .35, 18, LEFT - .06, TOP - .175, BACK + 9, false);
  const sky = new T.Mesh(unitPlane, lit(0xfff3e2, 3.2)); sky.scale.set(18, 2.3, 1); sky.rotation.y = Math.PI / 2; sky.position.set(LEFT - .1, 1.62, BACK + 9); room.add(sky);
  for (let z = BACK; z <= 6; z += 1.5) box(room, blackMetal, .07, 2.2, .05, LEFT - .02, 1.62, z, false);
  box(room, blackMetal, .07, .04, 18, LEFT - .02, 1.75, BACK + 9, false);

  box(room, accent, RIGHT - .1, TOP, .02, (RIGHT + .1) / 2, TOP / 2, BACK + .012, false);
  // Estante flotante con libros, cajas y una planta chica.
  box(room, oakDark, 1.9, .035, .26, 4.9, 1.72, BACK + .14);
  box(room, oakDark, 1.9, .035, .26, 4.9, 2.12, BACK + .14);
  const bookTones = [0x2c3a4a, 0x8c5a3c, 0xd9d2c4, 0x4d5b4a, 0x1e1e20, 0xb08a4f, 0x6b7785];
  const br = rng(11);
  for (let x = 4.05, i = 0; x < 5; i++) { const w = .028 + br() * .03, h = .19 + br() * .09; box(room, std(bookTones[i % bookTones.length], .8), w, h, .17, x + w / 2, 1.7375 + h / 2, BACK + .14); x += w + .003; }
  box(room, std(0xe7e2d8, .7), .3, .16, .2, 5.45, 1.8175, BACK + .14);
  box(room, std(0x2a2c30, .5), .22, .1, .18, 5.45, 1.9475, BACK + .14);
  for (let x = 4.1, i = 3; x < 4.6; i++) { const w = .03 + br() * .03, h = .2 + br() * .08; box(room, std(bookTones[i % bookTones.length], .8), w, h, .17, x + w / 2, 2.1375 + h / 2, BACK + .14); x += w + .003; }
  cyl(room, ceramic, .075, .13, 5.25, 2.2025, BACK + .14);

  // Sala técnica vidriada al fondo a la izquierda: rack con equipos y LEDs discretos.
  const techX = -5.25;
  box(room, blackMetal, .05, TOP, .05, -4.75, TOP / 2, BACK + 1.5, false);
  box(room, blackMetal, 1.45, .05, .05, (LEFT - 4.75) / 2, 2.2, BACK + 1.5, false);
  const pane = new T.Mesh(unitPlane, glass); pane.scale.set(1.45, TOP, 1); pane.position.set((LEFT - 4.75) / 2, TOP / 2, BACK + 1.5); room.add(pane);
  box(room, plastic, .62, 1.95, .7, techX, .975, BACK + .55);
  for (let i = 0; i < 9; i++) {
    box(room, std(0x2a2c31, .4, .7), .56, .085, .02, techX, .3 + i * .19, BACK + .91, false);
    for (let k = 0; k < 4; k++) box(room, lit(k === 3 && i % 3 === 0 ? 0xffb84d : 0x6fe09a, 1.6), .012, .012, .004, techX - .22 + k * .035, .3 + i * .19, BACK + .922, false);
  }

  // ---------- Luminarias ----------
  const tube = lit(0xfff2df, 5);
  for (const z of [-2.4, .6, 3.6]) for (const x of [-3.2, 1.2]) { box(room, blackMetal, 2.5, .05, .09, x, TOP - .2, z, false); box(room, tube, 2.42, .012, .06, x, TOP - .229, z, false); }
  const pendantMat = std(0x18181a, .5, .6);
  const pendants = [-2.15, -.95].map(x => {
    cyl(room, blackMetal, .004, .95, x, TOP - .475, -2.55, false);
    const shade = new T.Mesh(new T.CylinderGeometry(.05, .17, .16, 32, 1, true), pendantMat); shade.material.side = T.DoubleSide; shade.position.set(x, 2.02, -2.55); room.add(shade);
    const bulb = new T.Mesh(new T.SphereGeometry(.045, 16, 12), lit(0xffd9a6, 7)); bulb.position.set(x, 1.99, -2.55); room.add(bulb);
    return shade;
  });

  // ---------- Puestos de trabajo ----------
  // Monitores: Visual Studio Code a la izquierda, panel al centro y la tienda a la derecha; la MacBook lleva otro editor.
  const screens = [canvasTexture(640, 360, drawEditor), screenTexture(1), screenTexture(2), canvasTexture(640, 360, (g, w, h) => drawStore(g, w, h, LOGO))];
  const screenMats = screens.map(map => new T.MeshBasicMaterial({map, color: new T.Color(1.25, 1.25, 1.25)}));
  function monitor(parent, x, z, ry, mat, w = .62) {
    const g = new T.Group(); g.position.set(x, .755, z); g.rotation.y = ry; parent.add(g);
    const h = w * 9 / 16;
    box(g, aluminium, .24, .012, .19, 0, .006, 0);
    box(g, aluminium, .045, .32, .02, 0, .16, -.04);
    box(g, plastic, w + .016, h + .016, .022, 0, .2 + h / 2, 0);
    const s = new T.Mesh(unitPlane, mat); s.scale.set(w, h, 1); s.position.set(0, .2 + h / 2, .0115); g.add(s);
  }
  function chair(parent, x, z, ry) {
    const g = new T.Group(); g.position.set(x, 0, z); g.rotation.y = ry; parent.add(g);
    for (let i = 0; i < 5; i++) { const a = new T.Group(); a.rotation.y = i * Math.PI * .4; g.add(a); box(a, aluminium, .03, .025, .3, 0, .07, .15); cyl(a, plastic, .028, .03, 0, .028, .29).rotation.z = Math.PI / 2; }
    cyl(g, blackMetal, .025, .34, 0, .25, 0);
    box(g, fabric, .48, .07, .46, 0, .47, 0);
    box(g, plastic, .05, .34, .04, 0, .66, -.24);
    const back = box(g, fabric, .46, .52, .05, 0, .86, -.26); back.rotation.x = -.1;
    for (const s of [-1, 1]) { box(g, plastic, .03, .2, .03, s * .26, .58, -.02); box(g, plastic, .055, .025, .26, s * .26, .685, 0); }
  }
  // Único puesto: escritorio amplio con tres monitores en arco y una MacBook abierta.
  const desk = new T.Group(); desk.position.set(-1.55, 0, -2.5); room.add(desk);
  box(desk, oak, 2.4, .032, .82, 0, .739, 0);
  for (const s of [-1, 1]) { box(desk, blackMetal, .045, .72, .045, s * 1.12, .36, -.34); box(desk, blackMetal, .045, .72, .045, s * 1.12, .36, .34); box(desk, blackMetal, .045, .045, .72, s * 1.12, .7, 0); box(desk, blackMetal, .06, .02, .74, s * 1.12, .01, 0); }
  box(desk, blackMetal, 2.1, .08, .12, 0, .64, -.32); // bandeja pasacables
  monitor(desk, -.66, -.12, .34, screenMats[0]);
  monitor(desk, 0, -.22, 0, screenMats[1]);
  monitor(desk, .66, -.12, -.34, screenMats[3]);
  box(desk, aluminium, .43, .014, .125, 0, .762, .16);
  box(desk, plastic, .41, .004, .105, 0, .771, .16, false);
  box(desk, plastic, .06, .028, .1, .34, .769, .18);
  box(desk, std(0x25272b, .9), .3, .003, .24, .36, .7565, .17, false); // mouse pad
  cyl(desk, ceramic, .04, .09, -.5, .8, .24);
  const macbook = new T.Group(); macbook.position.set(.92, .755, .2); macbook.rotation.y = -.5; desk.add(macbook);
  box(macbook, aluminium, .31, .012, .215, 0, .006, 0);
  box(macbook, plastic, .27, .002, .1, 0, .0125, -.04, false); // teclado
  box(macbook, std(0x9a9da2, .3, .9), .1, .001, .06, 0, .0125, .065, false); // trackpad
  const lid = new T.Group(); lid.position.set(0, .012, -.105); lid.rotation.x = -.32; macbook.add(lid);
  box(lid, aluminium, .31, .2, .007, 0, .1, 0);
  const macScreen = new T.Mesh(unitPlane, screenMats[2]); macScreen.scale.set(.292, .182, 1); macScreen.position.set(0, .1, .004); lid.add(macScreen);
  chair(desk, -.1, .95, Math.PI + .5);

  // Planta de piso (ficus) junto al ventanal y aparador bajo a la derecha.
  const plant = new T.Group(); plant.position.set(-5.2, 0, -.9); room.add(plant);
  cyl(plant, ceramic, .2, .42, 0, .21, 0); cyl(plant, std(0x3a2c20, 1), .185, .02, 0, .425, 0, false);
  cyl(plant, std(0x5a4632, .9), .016, 1.1, 0, .97, 0);
  const leafShape = new T.Shape(); leafShape.moveTo(0, 0); leafShape.bezierCurveTo(.1, .06, .11, .22, 0, .34); leafShape.bezierCurveTo(-.11, .22, -.1, .06, 0, 0);
  const leafGeo = new T.ShapeGeometry(leafShape, 8);
  const pr = rng(23);
  for (let i = 0; i < 22; i++) {
    const l = new T.Mesh(leafGeo, leaf), a = i * 2.4, y = .75 + pr() * .85;
    l.position.set(Math.cos(a) * .03, y, Math.sin(a) * .03); l.rotation.set(0, -a + Math.PI / 2, 0); l.rotateX(.9 + pr() * .5); l.scale.setScalar(.8 + pr() * .5);
    l.castShadow = true; plant.add(l);
  }
  const credenza = new T.Group(); credenza.position.set(3.95, 0, BACK + .32); room.add(credenza);
  box(credenza, oak, 2.2, .62, .48, 0, .43, 0);
  for (const s of [-1, 1]) box(credenza, blackMetal, .04, .12, .4, s * 1, .06, 0);
  for (let i = 1; i < 4; i++) box(credenza, std(0xb99468, .6), .006, .58, .006, -1.1 + i * .55, .43, .241, false);
  // Televisor con una película de acción (canvas animado) y una consola blanca al lado.
  const TV_W = 1.2, TV_H = TV_W * 9 / 16, tvX = -.12;
  box(credenza, blackMetal, .5, .012, .22, tvX, .746, 0); box(credenza, blackMetal, .06, .07, .04, tvX, .785, -.02);
  box(credenza, plastic, TV_W + .02, TV_H + .02, .03, tvX, .82 + TV_H / 2, 0);
  const movieCanvas = document.createElement('canvas'); movieCanvas.width = 384; movieCanvas.height = 216;
  const movieCtx = movieCanvas.getContext('2d');
  const movie = new T.CanvasTexture(movieCanvas); movie.colorSpace = T.SRGBColorSpace;
  const tvScreen = new T.Mesh(unitPlane, new T.MeshBasicMaterial({map: movie, color: new T.Color(1.5, 1.5, 1.5)}));
  tvScreen.scale.set(TV_W, TV_H, 1); tvScreen.position.set(tvX, .82 + TV_H / 2, .016); credenza.add(tvScreen);
  const tvGlow = new T.PointLight(0xffa25c, 0, 3, 1.6); tvGlow.position.set(tvX, 1.1, .5); credenza.add(tvGlow);
  let movieAt = -1;
  function playMovie(t) {
    if (Math.abs(t - movieAt) < 1 / 30) return;
    movieAt = t; drawMovie(movieCtx, 384, 216, t); movie.needsUpdate = true;
    const boom = Math.floor(t / 1.7) % 3 === 1; // la explosión tiñe la pared
    tvGlow.intensity = boom ? 2.4 : .7; tvGlow.color.set(boom ? 0xff8a3c : 0x7fa8ff);
  }
  const consoleWhite = std(0xf2f2f0, .45);
  for (const s of [-1, 1]) box(credenza, consoleWhite, .022, .39, .26, .8 + s * .042, .935, .02).rotation.z = s * -.03;
  box(credenza, plastic, .062, .36, .24, .8, .92, .02);
  box(credenza, lit(0x4da3ff, 2.2), .004, .2, .004, .767, .95, .151, false);
  box(credenza, consoleWhite, .15, .03, .1, .5, .757, .15).rotation.y = .4; // mando

  // Cuadros en la pared del fondo: se alternan ilustraciones de anime y afiches de rock.
  const posterMaps = POSTERS.map(p => canvasTexture(256, p.square ? 256 : 356, p.draw));
  const posterX = [-3.6, -2.75, -1.9, -1.05, .55, 1.4, 2.25, 3.1];
  POSTERS.forEach((p, i) => {
    const w = p.square ? .62 : .56, h = p.square ? .62 : .78, y = 2.2 + (i % 2 ? .07 : -.05), z = BACK + (posterX[i] > .1 ? .022 : 0);
    box(room, blackMetal, w + .05, h + .05, .03, posterX[i], y, z + .016);
    const art = new T.Mesh(unitPlane, new T.MeshStandardMaterial({map: posterMaps[i], roughness: .55, emissive: 0xffffff, emissiveMap: posterMaps[i], emissiveIntensity: .22}));
    art.scale.set(w, h, 1); art.position.set(posterX[i], y, z + .032); room.add(art);
  });

  // ---------- Logo: escultura tipográfica extruida desde los contornos oficiales ----------
  const baselinePx = Math.max(...LOGO.rows.flat().flatMap(s => s.o.map(p => p[1])));
  const topPx = Math.min(...LOGO.rows.flat().flatMap(s => s.o.map(p => p[1])));
  const xs = LOGO.rows.flat().flatMap(s => s.o.map(p => p[0]));
  const centerPx = (Math.min(...xs) + Math.max(...xs)) / 2;
  const K = LOGO_HEIGHT / (baselinePx - topPx);
  const toV = p => new T.Vector2((p[0] - centerPx) * K, (baselinePx - p[1]) * K);
  const logoMat = new T.MeshPhysicalMaterial({color: 0xf3f1ec, roughness: .5, metalness: 0, clearcoat: .25, clearcoatRoughness: .3, envMapIntensity: .9});
  const sideMat = std(0x3a3c3f, .6); // cantos gris oscuro
  const dotMat = new T.MeshPhysicalMaterial({color: 0xe2001a, roughness: .28, clearcoat: .6, clearcoatRoughness: .2});
  const logo = new T.Group(); logo.position.set(LOGO_X, 0, 0); logo.rotation.y = LOGO_YAW; scene.add(logo);
  const twists = [.55, -.42, .3, -.18];
  const rows = LOGO.rows.map((shapes, i) => {
    const geo = new T.ExtrudeGeometry(shapes.map(s => {
      const shape = new T.Shape(s.o.map(toV));
      shape.holes = s.h.map(h => new T.Path(h.map(toV)));
      return shape;
    }), {depth: LOGO_DEPTH, bevelEnabled: false, curveSegments: 1});
    geo.translate(0, 0, -LOGO_DEPTH / 2);
    geo.computeBoundingBox();
    const mesh = new T.Mesh(geo, [logoMat, sideMat]); mesh.castShadow = true; logo.add(mesh); // sin auto-sombra: evita vetas en los cantos curvos
    return {mesh, top: geo.boundingBox.max.y, twist: twists[i]};
  });
  const dotR = LOGO.dot[2] * K, dotY = (baselinePx - LOGO.dot[1]) * K;
  // Canto del punto en el mismo gris que las letras; rojo solo en las caras (grupos del cilindro: lado, tapa, tapa).
  const dot = new T.Mesh(new T.CylinderGeometry(dotR, dotR, LOGO_DEPTH, 48), [sideMat, dotMat, dotMat]);
  dot.rotation.x = Math.PI / 2; dot.position.set((LOGO.dot[0] - centerPx) * K, dotY, 0); dot.castShadow = dot.receiveShadow = true; logo.add(dot);

  // ---------- Iluminación ----------
  scene.add(new T.HemisphereLight(0xf4f5f7, 0x8d8e90, .5));
  const sun = new T.DirectionalLight(0xffe7c8, 2.3);
  sun.position.set(-6.5, 5, 6.5); sun.target.position.set(.4, 0, -.6); scene.add(sun, sun.target);
  sun.castShadow = true; sun.shadow.mapSize.setScalar(tier.shadow);
  Object.assign(sun.shadow.camera, {left: -7, right: 7, top: 6, bottom: -5, near: 1, far: 22});
  sun.shadow.bias = -.0008; sun.shadow.normalBias = .05; sun.shadow.radius = 5;
  const key = new T.SpotLight(0xfff1de, 30, 9, .42, .85, 1.6); key.position.set(LOGO_X + 1.1, 2.9, 3); key.target.position.set(LOGO_X, .6, 0); scene.add(key, key.target);
  for (const x of [-2.15, -.95]) { const p = new T.PointLight(0xffcf99, 5, 4.5, 1.8); p.position.set(x, 1.9, -2.5); scene.add(p); }

  // ---------- Personaje (opcional: si no carga, la bienvenida sigue sin él) ----------
  const logoHalfW = (Math.max(...xs) - Math.min(...xs)) * K / 2;
  // Los gatos acompañan al personaje: si la malla de alguno no carga, la secuencia corre igual sin él.
  let character = null, cat = null, fendi = null;
  try {
    const optional = (load, name) => load().catch(error => { console.warn(`[bienvenida] sin ${name}:`, error.message); return null; });
    [character, cat, fendi] = await Promise.race([Promise.all([loadCharacter('/welcome/', tier), optional(() => loadCat('/welcome/', tier), 'gato'), optional(() => loadFendi('/welcome/', tier), 'Fendi')]),
      new Promise((_, no) => setTimeout(() => no(new Error('avatar: tiempo agotado')), 7000))]);
    scene.add(character.object);
    character.object.traverse(o => { if (o.material) o.material.envMapIntensity = .6; });
    if (cat) scene.add(cat.object);
    if (fendi) { scene.add(fendi.object); fendi.maps.forEach(map => renderer.initTexture(map)); } // ojos abiertos y cerrados ya en la GPU
  } catch (error) { console.warn('[bienvenida] sin personaje:', error.message); }
  const timeline = makeTimeline(character);
  logo.updateMatrixWorld(true);
  const corner = logo.localToWorld(new T.Vector3(-logoHalfW, LOGO_HEIGHT, 0));
  character?.setStage({corner, wrist: logo.localToWorld(new T.Vector3(-logoHalfW + .01, LOGO_HEIGHT + .04, LOGO_DEPTH / 2 + .07)), arriveAt: timeline.arrive});
  // El gato corre por el costado del personaje, salta desde la punta izquierda del logo y queda parado arriba.
  cat?.setStage({origin: logo.localToWorld(new T.Vector3(-logoHalfW, 0, 0)), u: new T.Vector3(1, 0, 0).applyQuaternion(logo.quaternion), n: new T.Vector3(0, 0, 1).applyQuaternion(logo.quaternion),
    top: LOGO_HEIGHT, laneZ: corner.z + .06, spawnX: LEFT + .7, arriveAt: timeline.arrive});
  // Fendi duerme sobre el escritorio, baja de un salto y me sigue hasta frotarse con mi pierna izquierda,
  // que se mide poniendo al personaje en el instante en que ya está apoyado en el logo.
  if (fendi) {
    character.update(timeline.wave, timeline, camera);
    desk.updateWorldMatrix(true, false);
    const onDesk = (x, z) => desk.localToWorld(new T.Vector3(x, .755, z)); // punta izquierda del escritorio, a la vista (la silla tapa el centro)
    fendi.setStage({bed: onDesk(-1.02, .13), deskWalk: [onDesk(-.9, .135), onDesk(-.82, .18), onDesk(-.8, .24)],
      landing: desk.localToWorld(new T.Vector3(-.65, 0, .95)), leg: new T.Vector3().setFromMatrixPosition(character.bone.LFoot.matrixWorld).setY(0), watch: character.bone.Head,
      legR: Object.fromEntries([['hip', 'RUpLeg'], ['knee', 'RLeg'], ['ankle', 'RFoot']].map(([k, b]) => [k, new T.Vector3().setFromMatrixPosition(character.bone[b].matrixWorld)]))});
  }
  const HAS_CHARACTER = !!character;

  // ---------- Cámara: encuadre calculado según el aspecto, no un canvas achicado ----------
  const tanHalf = Math.tan(T.MathUtils.degToRad(camera.fov / 2));
  const logoHalf = (Math.max(...xs) - Math.min(...xs)) * K / 2;
  // Zona de los tres protagonistas al final (metros sobre el piso, en el plano del logo).
  const ZOOM_START = 6.0, CAST = {cx: .46, cy: .88, w: 2.4, h: 1.9};
  function frame(t) {
    const aspect = camera.aspect, portrait = aspect < 1;
    // Cuadro final: logo (y personaje a su izquierda) completo con aire alrededor.
    const left = HAS_CHARACTER ? corner.x - 1.05 : LOGO_X - logoHalf, right = LOGO_X + logoHalf;
    const end = portrait
      ? {cx: (left + right) / 2, cy: .5, w: (right - left) + .46, h: 1.9, eye: .95}
      : {cx: (left + right) / 2 - (HAS_CHARACTER ? .55 : .85), cy: .74, w: (right - left) + 2.3, h: 1.95, eye: 1};
    const start = portrait
      ? {cx: end.cx - 2.5, cy: 1, w: end.w + .9, h: 2.6, eye: 1.45}
      : {cx: end.cx - (HAS_CHARACTER ? .6 : 1.6), cy: 1.1, w: end.w + (HAS_CHARACTER ? 1.1 : 2.4), h: 2.7, eye: 1.45};
    // El encuadre llega antes de que el logo termine de emerger, así nunca queda cortado.
    const settle = timeline.logoStart + (portrait ? .5 : 1.5);
    const e = smooth(t / settle), drift = Math.max(0, t - settle) * .01;
    let cx = lerp(start.cx, end.cx, e), cy = lerp(start.cy, end.cy, e), w = lerp(start.w, end.w, e), h = lerp(start.h, end.h, e);
    // Celular vertical: al final se acerca hasta encuadrar justo a los tres (Fendi a mi derecha, yo y el gato arriba del logo).
    if (portrait && HAS_CHARACTER) {
      const z = smooth((t - ZOOM_START) / 1.3);
      cx = lerp(cx, CAST.cx, z); cy = lerp(cy, CAST.cy, z); w = lerp(w, CAST.w, z); h = lerp(h, CAST.h, z);
    }
    const dist = Math.max(h / (2 * tanHalf), w / (2 * tanHalf * aspect)) * (1 - drift);
    camera.position.set(cx + lerp(-.14, -.05, e) * dist, lerp(start.eye, end.eye, e), dist);
    camera.lookAt(cx, cy, 0);
  }

  function animateLogo(t) {
    rows.forEach((row, i) => {
      const e = outCubic((t - timeline.logoStart - i * timeline.stagger) / timeline.rise);
      // Cada fila emerge del piso (la primera es THE, la más alta) y gira hasta alinearse.
      row.mesh.position.y = -(row.top + .04) * (1 - e);
      row.mesh.rotation.y = row.twist * (1 - smooth((t - timeline.logoStart - i * timeline.stagger) / (timeline.rise * 1.05)));
    });
    const d = outCubic((t - timeline.dot) / .45);
    dot.position.y = lerp(-dotR - .02, dotY, d);
  }

  // ---------- Posproceso HD: oclusión ambiental (contacto entre objetos), brillo de las luces y antialias MSAA ----------
  let post = null;
  const modules = await postModules;
  if (modules) {
    const [{EffectComposer}, {RenderPass}, {GTAOPass}, {UnrealBloomPass}, {OutputPass}] = modules;
    // Antialias MSAA solo en pantallas comunes: en retina los píxeles ya son finos y cuesta casi la mitad del cuadro.
    const target = new T.WebGLRenderTarget(1, 1, {type: T.HalfFloatType, samples: dpr >= 1.75 ? 0 : 4});
    const composer = new EffectComposer(renderer, target);
    composer.addPass(new RenderPass(scene, camera));
    const ao = new GTAOPass(scene, camera, 1, 1);
    // La oclusión es una señal suave: calcularla a media resolución no se nota y cuesta la cuarta parte.
    const aoSize = ao.setSize.bind(ao); ao.setSize = (w, h) => aoSize(Math.ceil(w / 2), Math.ceil(h / 2));
    ao.updateGtaoMaterial({radius: .3, distanceExponent: 1.6, thickness: 1, scale: 1.15, samples: 12, distanceFallOff: 1});
    ao.updatePdMaterial({lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 4, rings: 2, samples: 12});
    ao.blendIntensity = .9;
    composer.addPass(ao);
    const bloom = new UnrealBloomPass(new T.Vector2(1, 1), .35, .45, 2.2); // solo lo muy brillante: tubos, lámparas, pantallas, la tele
    const bloomSize = bloom.setSize.bind(bloom); bloom.setSize = (w, h) => bloomSize(Math.ceil(w / 2), Math.ceil(h / 2)); // halo difuso: a media resolución alcanza
    composer.addPass(bloom);
    composer.addPass(new OutputPass());
    post = {composer, ao, bloom, target};
  }

  function resize() {
    const w = host.clientWidth || innerWidth, h = host.clientHeight || innerHeight;
    renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix();
    if (post) { post.composer.setPixelRatio(dpr); post.composer.setSize(w, h); }
  }
  const observer = new ResizeObserver(resize); observer.observe(host);
  addEventListener('orientationchange', resize);
  resize(); frame(0); animateLogo(0); playMovie(0);
  renderer.compile(scene, camera);

  // DPR adaptativo: si el equipo no sostiene el ritmo, baja resolución antes que perder fluidez.
  let lastNow = 0, slow = 0, frames = 0;
  const fixed = new URLSearchParams(location.search).has('fijo'); // para medir: resolución fija
  function adapt() {
    if (fixed) return;
    const now = performance.now();
    if (lastNow) { frames++; if (now - lastNow > 26) slow++; }
    lastNow = now;
    if (frames >= 40) {
      if (slow > 16 && dpr > 1.25) { dpr = Math.max(1.25, dpr - .25); renderer.setPixelRatio(dpr); resize(); }
      else if (slow > 16 && post?.ao.enabled) post.ao.enabled = false; // después, sin oclusión ambiental
      else if (slow > 16 && dpr > 1) { dpr = 1; renderer.setPixelRatio(dpr); resize(); }
      else if (slow > 16 && sun.castShadow) sun.castShadow = false; // último recurso: sin sombras dinámicas
      frames = slow = 0;
    }
  }

  return {
    timeline, post, renderer, // post y renderer: para medir rendimiento desde afuera
    render(t) { adapt(); frame(t); animateLogo(t); playMovie(t); character?.update(t, timeline, camera); cat?.update(t); fendi?.update(t); post ? post.composer.render() : renderer.render(scene, camera); },
    dispose() {
      observer.disconnect(); removeEventListener('orientationchange', resize);
      const seen = new Set();
      scene.traverse(o => {
        if (o.geometry && !seen.has(o.geometry)) { seen.add(o.geometry); o.geometry.dispose(); }
        for (const m of [].concat(o.material || [])) if (!seen.has(m)) { seen.add(m); m.map?.dispose(); m.normalMap?.dispose(); m.roughnessMap?.dispose(); m.dispose(); }
        o.shadow?.map?.dispose(); o.skeleton?.dispose();
      });
      screens.forEach(s => s.dispose()); posterMaps.forEach(s => s.dispose()); movie.dispose(); oakMap.dispose(); if (floorDetail) Object.values(floorDetail).forEach(t => t.dispose()); envTarget.dispose(); pendants.length = 0;
      if (post) { post.composer.passes.forEach(p => p.dispose?.()); post.composer.dispose(); post.target.dispose(); }
      renderer.renderLists.dispose(); renderer.dispose(); renderer.forceContextLoss(); renderer.domElement.remove();
    },
  };
}
