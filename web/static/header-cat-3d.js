// Vaiven y Fendi del header en 3D: las mismas mallas con esqueleto de la bienvenida
// (welcome-cat.js / welcome-fendi.js), pero manejadas por la máquina de estados del header
// (header-cat-state.mjs). Cada fase (caminar, dormir, rascarse, saltar...) se traduce a una
// pose del esqueleto; las patas siguen resolviéndose con IK y pisan según cuánto avanza el gato
// en pantalla, así que no patinan.
import * as T from './vendor/three/three.module.min.js';
import {readRig, buildRig, solve} from './welcome-character.js';

const clamp01 = v => Math.min(1, Math.max(0, v));
const smooth = v => { v = clamp01(v); return v * v * (3 - 2 * v); };
const lerp = (a, b, t) => a + (b - a) * t;
const V = (x = 0, y = 0, z = 0) => new T.Vector3(x, y, z);
const UP = V(0, 1, 0), X = V(1, 0, 0), Z = V(0, 0, 1);
const TAU = Math.PI * 2;
const wrap = a => a - TAU * Math.round(a / TAU);
const FEET = ['FL', 'FR', 'HL', 'HR'];
const LEGS = [['FL', 'chest', -1], ['FR', 'chest', -1], ['HL', 'hips', 1], ['HR', 'hips', 1]];
const BASE = '/welcome/';

// Qué malla/textura usa cada uno y cómo se apoyan sus patas en cada postura (medidas de la bienvenida).
const RIGS = {
  vaiven: {
    mesh: 'gato.bin', color: 'gato-color.webp', headRest: .85, sheen: 0xd9cbb8, rough: .86,
    gait: {FL: V(.04, 0, .095), FR: V(-.04, 0, .095), HL: V(.06, 0, -.15), HR: V(-.06, 0, -.15)},
    crouch: {FL: V(.04, 0, .1), FR: V(-.04, 0, .1), HL: V(.065, 0, -.1), HR: V(-.065, 0, -.1)},
    lie: {FL: V(.04, 0, .17), FR: V(-.04, 0, .17), HL: V(.07, 0, -.05), HR: V(-.07, 0, -.05)},
    tail: 'relative',
    // Vaiven no trae textura con ojos cerrados: se arma pintando el color del pelo sobre los ojos (texels medidos en el atlas).
    eyes: {r: 15, at: [[430, 161], [172, 282], [189, 751], [568, 305], [194, 956], [853, 122], [897, 928]]},
  },
  fendi: {
    mesh: 'fendi.bin', color: 'fendi-color.webp', closed: 'fendi-dormida.webp', headRest: -1.15, sheen: 0x7a5a3c, rough: .88,
    gait: {FL: V(.045, 0, .15), FR: V(-.045, 0, .15), HL: V(.055, 0, -.135), HR: V(-.055, 0, -.135)},
    crouch: {FL: V(.045, 0, .14), FR: V(-.045, 0, .14), HL: V(.06, 0, -.09), HR: V(-.06, 0, -.09)},
    lie: {FL: V(.05, 0, .25), FR: V(-.05, 0, .27), HL: V(.085, 0, -.07), HR: V(-.085, 0, -.06)},
    tail: 'absolute',
  },
};
const loads = {};
function loadAssets(kind) {
  const cfg = RIGS[kind];
  return loads[kind] ||= (async () => {
    const loader = new T.TextureLoader();
    let [buf, awake, asleep] = await Promise.all([
      fetch(BASE + cfg.mesh).then(r => { if (!r.ok) throw new Error(cfg.mesh + ' ' + r.status); return r.arrayBuffer(); }),
      loader.loadAsync(BASE + cfg.color), cfg.closed ? loader.loadAsync(BASE + cfg.closed) : null,
    ]);
    if (!asleep && cfg.eyes) asleep = new T.CanvasTexture(paintEyesShut(awake.image, cfg.eyes));
    for (const map of [awake, asleep]) if (map) { map.colorSpace = T.SRGBColorSpace; map.anisotropy = 4; }
    return {buf, awake, asleep};
  })();
}

// Copia de la textura con los ojos tapados: sobre cada marca de ojo se pinta el color medio del pelo de alrededor.
function paintEyesShut(image, {r, at}) {
  const c = document.createElement('canvas'); c.width = image.width; c.height = image.height;
  const g = c.getContext('2d', {willReadFrequently: true}); g.drawImage(image, 0, 0);
  for (const [x, y] of at) {
    const ring = g.getImageData(Math.max(0, x - r * 2), Math.max(0, y - r * 2), r * 4, r * 4).data;
    let R = 0, G = 0, B = 0, n = 0;
    for (let i = 0; i < ring.length; i += 4) { if (ring[i] + ring[i + 1] + ring[i + 2] > 560) { R += ring[i]; G += ring[i + 1]; B += ring[i + 2]; n++; } }
    n ||= 1;
    g.fillStyle = `rgb(${R / n | 0},${G / n | 0},${B / n | 0})`;
    g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill();
  }
  return c;
}

// Sombra blanda bajo el gato (el svg original traía una elipse).
function shadowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d'), grad = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grad.addColorStop(0, 'rgba(41,35,31,.5)'); grad.addColorStop(1, 'rgba(41,35,31,0)');
  g.fillStyle = grad; g.fillRect(0, 0, 64, 64);
  return new T.CanvasTexture(c);
}

// Medio de ancho de la vista en metros: el gato de pie mide ~0,55 m de largo con la cola.
const VIEW_W = 1.1, ASPECT = 6 / 5, VIEW_H = VIEW_W / ASPECT, FLOOR_FRAC = .08;

export function createCat3D(kind) {
  const cfg = RIGS[kind];
  const canvas = document.createElement('canvas');
  canvas.className = 'ttra-cat-3d';
  const renderer = new T.WebGLRenderer({canvas, antialias: true, alpha: true, powerPreference: 'low-power'});
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = T.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  renderer.outputColorSpace = T.SRGBColorSpace;
  const scene = new T.Scene();
  scene.add(new T.HemisphereLight(0xffffff, 0x6d6459, 1.9));
  const key = new T.DirectionalLight(0xffffff, 2.2); key.position.set(-1.5, 3, 3); scene.add(key);
  const fill = new T.DirectionalLight(0xfff1e0, .7); fill.position.set(2, 1, 2); scene.add(fill);
  const camera = new T.OrthographicCamera(-VIEW_W / 2, VIEW_W / 2, VIEW_H * (1 - FLOOR_FRAC), -VIEW_H * FLOOR_FRAC, .1, 20);
  camera.position.set(0, 0, 5);
  const shadow = new T.Mesh(new T.PlaneGeometry(1, 1), new T.MeshBasicMaterial({map: shadowTexture(), transparent: true, depthWrite: false}));
  shadow.rotation.x = -Math.PI / 2; shadow.position.y = .002; scene.add(shadow);

  let rig = null, size = {w: 0, h: 0}, mpp = VIEW_W / 92;
  const api = {canvas, ready: false, setSize, update, draw};

  function setSize(w, h) {
    w = Math.max(1, Math.round(w)); h = Math.max(1, Math.round(h));
    if (size.w === w && size.h === h) return;
    size = {w, h}; mpp = VIEW_W / w;
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.setSize(w, h, false);
  }

  loadAssets(kind).then(({buf, awake, asleep}) => {
    const {geometry, joints} = readRig(buf.slice(0));
    const material = new T.MeshPhysicalMaterial({map: awake, roughness: cfg.rough, metalness: 0, envMapIntensity: .6,
      sheen: .3, sheenRoughness: .75, sheenColor: new T.Color(cfg.sheen)});
    const built = buildRig(geometry, joints, material);
    built.mesh.castShadow = built.mesh.receiveShadow = false;
    scene.add(built.object);
    rig = prepare(built, material, awake, asleep);
    api.ready = true;
  }).catch(() => {});

  // ---------- Medidas del esqueleto y pose ----------
  function prepare({object, bone, rest}, material, awake, asleep) {
    const linkA = rest.Spine.clone().sub(rest.Hips), linkB = rest.Chest.clone().sub(rest.Spine);
    const r = {
      object, bone, material, awake, asleep, rest,
      PZ: rest.Hips.z, CZ: rest.Chest.z, HY: rest.Hips.y, CY: rest.Chest.y,
      LA: linkA.length(), LB: linkB.length(),
      REST1: Math.atan2(linkA.y, linkA.z), REST2: Math.atan2(linkB.y, linkB.z),
      PAW_Y: Object.fromEntries(FEET.map(f => [f, rest[f + 'Paw'].y])),
      STAND: Object.fromEntries(FEET.map(f => [f, V(rest[f + 'Paw'].x, 0, rest[f + 'Paw'].z)])),
    };
    return r;
  }

  const fwdOf = (yaw, out = V()) => out.set(Math.sin(yaw), 0, Math.cos(yaw));
  const leftOf = (yaw, out = V()) => out.set(Math.cos(yaw), 0, -Math.sin(yaw));
  const q = {yaw: new T.Quaternion(), hips: new T.Quaternion(), spine: new T.Quaternion(), chest: new T.Quaternion(), a: new T.Quaternion(), b: new T.Quaternion(),
    head: new T.Quaternion(), neck: new T.Quaternion(), tail: new T.Quaternion(), prev: new T.Quaternion()};
  const ident = new T.Quaternion();
  const pelvis = V(), chest = V(), delta = V(), tmpA = V(), tmpB = V(), pole = V(), target = V(), footPos = V();
  const e3 = new T.Euler();

  // Pose pedida: alturas, cabeza, cola y dónde apoya (o vuela) cada pata, en el marco del cuerpo.
  const S = {feet: Object.fromEntries(FEET.map(f => [f, {x: 0, y: 0, z: 0, pitch: 0}]))};
  function resetPose() {
    const {HY, CY, STAND} = rig;
    Object.assign(S, {pelvisY: HY, chestY: CY, pelvisZ: 0, chestZ: 0, roll: 0, yawAdd: 0, headYaw: 0, headPitch: 0, headRoll: 0,
      tail: 0, curl: 0, sway: 1, tailSpeed: 1, closed: false, bounce: 0, bend: 0});
    for (const f of FEET) Object.assign(S.feet[f], {x: STAND[f].x, y: 0, z: STAND[f].z, pitch: 0});
  }
  const setFoot = (f, x, y, z, pitch = 0) => Object.assign(S.feet[f], {x, y, z, pitch});
  const setHome = (homes, dy = 0) => { for (const f of FEET) setFoot(f, homes[f].x, dy, homes[f].z); };

  // Zancada en el lugar: la fase avanza con la distancia recorrida, así las patas pisan sin patinar.
  const gaitState = {phase: 0};
  // Longitud de zancada (m) por velocidad. Al correr el barrido de cada pata se limita a lo que la pierna alcanza.
  const strideFor = (speed, running) => running ? (.2 + .04 * speed) / .55 : .2 + .25 * speed;
  const OFFSET_WALK = {HR: .02, FR: .27, HL: .52, FL: .77}, OFFSET_RUN = {HL: .02, FR: .04, HR: .52, FL: .54};
  function gait(speed, running, mv) {
    const g = cfg.gait, duty = running ? .55 : .62, stride = strideFor(speed, running);
    const offset = running ? OFFSET_RUN : OFFSET_WALK;
    const sweep = stride * duty;
    for (const f of FEET) {
      const u = ((gaitState.phase + offset[f]) % 1 + 1) % 1;
      let z, y;
      // Mientras la pata está apoyada el cuerpo avanza duty*zancada: ese es el barrido real de la pata
      // (más que eso la pierna no llega al piso y el gato "camina en el aire").
      if (u < duty) { z = g[f].z + sweep * (.5 - u / duty); y = 0; }
      else { const w = (u - duty) / (1 - duty); z = g[f].z - sweep * .5 + sweep * smooth(w); y = (.025 + .1 * Math.min(sweep, .4)) * Math.sin(Math.PI * w); }
      const s = S.feet[f];
      s.x = lerp(s.x, g[f].x, mv); s.z = lerp(s.z, z, mv); s.y = lerp(s.y, y, mv);
      const arch = u < duty ? 0 : Math.sin(Math.PI * (u - duty) / (1 - duty));
      s.pitch = lerp(s.pitch, (f[0] === 'F' ? .9 : .5) * arch, mv);
    }
    const stridePhase = gaitState.phase * TAU;
    S.bounce = (running ? .016 : .007) * mv;
    // Con las patas abiertas la pierna no llega al piso a menos que el cuerpo baje: se agacha en proporción al barrido.
    S.pelvisY += S.bounce * Math.sin(stridePhase * 2 + 2.2) - .2 * sweep * mv;
    S.chestY += S.bounce * Math.sin(stridePhase * 2 - .6) - .2 * sweep * mv;
    S.tail = lerp(S.tail, running ? 1 : .35, mv);
    // Balanceo: el cuerpo se inclina al apoyar cada lado y la cabeza compensa, como un andar de gato.
    S.roll += (running ? .03 : .045) * Math.sin(stridePhase) * mv;
    S.headYaw += -.07 * Math.sin(stridePhase) * mv;
    S.headPitch += (running ? .05 : .035) * Math.sin(stridePhase * 2 + 1) * mv;
    S.chestZ += (running ? .02 : .008) * Math.sin(stridePhase * 2 + .4) * mv;
  }

  // Traduce la fase del header a la pose. t: segundos desde que empezó la fase; p: progreso 0-1.
  function layout(k, t, p, c) {
    const {HY, CY} = rig, g = cfg.gait;
    const breathe = Math.sin(c.time * TAU * .35);
    const sit = (amount = 1) => { // sentada: la cadera baja y el pecho sube, patas delanteras derechas
      S.pelvisY = lerp(HY, HY * .5, amount); S.chestY = lerp(CY, CY * 1.22, amount); S.pelvisZ = -.05 * amount;
      setFoot('HL', .09, 0, -.07); setFoot('HR', -.09, 0, -.07);
    };
    const lie = (amount = 1) => { // echada: panza al piso
      S.pelvisY = lerp(HY, HY * .5, amount); S.chestY = lerp(CY, CY * .5, amount);
      for (const f of FEET) { const h = cfg.lie[f]; S.feet[f].x = lerp(S.feet[f].x, h.x, amount); S.feet[f].z = lerp(S.feet[f].z, h.z, amount); }
    };
    switch (k) {
      case 'sleep': {
        lie(smooth(t / .6)); S.closed = true; S.headPitch = -.65; S.headYaw = -.5; S.headRoll = .3;
        S.chestY += .006 * breathe; S.tail = .4; S.curl = 1; S.sway = 0; break;
      }
      case 'loaf': {
        lie(smooth(t / .5)); S.headPitch = .1; S.tail = .3; S.curl = .4; S.chestY += .004 * breathe; break;
      }
      case 'scratch': {
        sit(smooth(t / .3)); S.closed = true; S.headPitch = -.1; S.headRoll = -.2;
        const k2 = Math.sin(t * TAU * 5.5);
        setFoot('HL', .09, .02 + .1 + .02 * k2, CY * .35, -.4); S.feet.HL.x = .12; S.feet.HL.z = rig.CZ - .02 + .03 * k2; S.feet.HL.y = .17 + .03 * k2;
        S.headRoll = -.3 - .05 * k2; break;
      }
      case 'lick': {
        sit(smooth(t / .3)); S.closed = true; S.headPitch = -.7; S.headYaw = .5;
        const lick = Math.sin(t * TAU * 2);
        setFoot('FL', .06, .18 + .02 * lick, rig.CZ + .1, -.8); S.headPitch -= .08 * lick; break;
      }
      case 'pee': {
        S.pelvisY = HY * .72; S.chestY = CY * .95; setFoot('HL', .09, 0, -.12); setFoot('HR', -.09, 0, -.12);
        S.tail = 0; S.sway = 0; S.headPitch = .05; break;
      }
      case 'poop': {
        S.pelvisY = HY * .55; S.chestY = CY * .85; S.pelvisZ = -.03; setFoot('HL', .08, 0, -.14); setFoot('HR', -.08, 0, -.14);
        S.tail = 0; S.sway = 0; S.headPitch = -.1; S.pelvisY += .004 * Math.sin(t * TAU * 6); break;
      }
      case 'belly': {
        // Se tira de espaldas y mueve las patitas en el aire.
        const down = smooth(t / .45);
        S.roll = Math.PI * down; S.pelvisY = lerp(HY, HY * .85, down); S.chestY = lerp(CY, CY * .85, down);
        const wig = Math.sin(t * TAU * 2.2) * down;
        setFoot('FL', .07, lerp(0, .27, down) + .03 * wig, rig.CZ + .06, 0.2); setFoot('FR', -.07, lerp(0, .25, down) - .03 * wig, rig.CZ + .04, .2);
        setFoot('HL', .08, lerp(0, .26, down) - .03 * wig, -.04); setFoot('HR', -.08, lerp(0, .27, down) + .03 * wig, -.06);
        S.headRoll = -Math.PI * down * .4; S.closed = down > .6; S.tail = .5; S.sway = 0; break;
      }
      case 'attack': case 'swat': {
        // Zarpazo con una manito (alterna izquierda y derecha según la fase); el cuerpo se queda en el piso.
        const left = c.serial % 2 === 0, f = left ? 'FL' : 'FR', side = left ? .045 : -.045;
        S.headPitch = -.15; S.tail = .15; S.tailSpeed = 3; S.chestY = CY * .9;
        const hit = k === 'swat' ? Math.sin(clamp01(p) * Math.PI) : Math.max(0, Math.sin(t * TAU * 1.7));
        S.chestZ = .03 * hit;
        setFoot(f, side, .13 + .1 * hit, rig.CZ + .08 + .13 * hit, -.5 * hit);
        S.headYaw = .12 * hit * (left ? 1 : -1); break;
      }
      case 'bury': {
        S.headPitch = -.4; S.chestY = CY * .92;
        const kick = Math.sin(t * TAU * 2.2);
        setFoot('HL', .07, .06 * Math.max(0, kick), -.18 - .12 * Math.max(0, kick));
        setFoot('HR', -.07, .06 * Math.max(0, -kick), -.18 - .12 * Math.max(0, -kick));
        S.pelvisY = HY * .92; break;
      }
      case 'stretch': {
        // Reverencia: pecho abajo, cola al cielo, manos hacia adelante.
        const a = smooth(Math.min(p / .25, (1 - p) / .25));
        S.chestY = lerp(CY, CY * .62, a); S.pelvisY = lerp(HY, HY * 1.05, a);
        setFoot('FL', .045, 0, g.FL.z + .09 * a); setFoot('FR', -.045, 0, g.FR.z + .09 * a);
        S.headPitch = .2 * a; S.tail = lerp(0, 0, a); S.closed = a > .6; break;
      }
      case 'yawn': {
        const a = smooth(Math.min(p / .3, (1 - p) / .3));
        S.headPitch = .85 * a; S.closed = a > .3; S.chestY = CY * (1 + .05 * a); break;
      }
      case 'crouch': {
        const a = smooth(t / .45);
        S.chestY = lerp(CY, CY * .64, a); S.pelvisY = lerp(HY, HY * .82, a); setHome(cfg.crouch);
        S.tail = .8; S.tailSpeed = 2.5; S.headPitch = -.1; S.roll = .012 * Math.sin(t * TAU * 6) * a; break;
      }
      case 'jump': case 'pounce': case 'startle': case 'joy': {
        const a = Math.sin(clamp01(c.air) * Math.PI);
        S.chestY = CY + .03 * a; S.pelvisY = HY + .015 * a;
        setFoot('FL', .045, .1 * a, cfg.gait.FL.z + .02 * a, .8 * a); setFoot('FR', -.045, .1 * a, cfg.gait.FR.z + .02 * a, .8 * a);
        setFoot('HL', .06, .1 * a, -.1 * a - .02 + cfg.gait.HL.z * (1 - a)); setFoot('HR', -.06, .1 * a, -.1 * a - .02 + cfg.gait.HR.z * (1 - a));
        S.headPitch = .2 * a; S.tail = k === 'startle' ? 0 : .5 * a;
        if (k === 'joy') S.closed = true; if (k === 'startle') S.tailSpeed = 4; break;
      }
      case 'spin': {
        S.yawAdd = TAU * smooth(p); c.speed = Math.max(c.speed, .35); c.walkFeet = true; S.tail = .4; break;
      }
      case 'sniff': S.headPitch = -.55; S.headYaw = .1 * Math.sin(t * TAU * 2); S.chestY += .003 * breathe; break;
      case 'funny': S.headRoll = .45 * Math.sin(p * Math.PI) ; S.headPitch = .15; S.closed = false; break;
      case 'introduce': S.headPitch = .08; S.chestY += .003 * breathe; break;
      default: { // idle, watch y compañía: parada, respirando, con la cabeza siguiendo la línea roja
        S.chestY += .004 * breathe; S.pelvisY += .002 * breathe;
        S.headPitch = c.look; if (k === 'watch') S.headPitch += .15;
      }
    }
  }

  let lastTime = 0, yawCur = null, closedNow = false, speedSm = 0, floatErr = 0, calibrated = false, blinkAt = 0, blinkUntil = 0, posed = false;
  const P = {feet: Object.fromEntries(FEET.map(f => [f, {x: 0, y: 0, z: 0, pitch: 0}]))}; // pose ya suavizada
  // Acerca la pose pedida a la mostrada con un filtro de primer orden: sin saltos entre una fase y la siguiente.
  function smoothPose(dt, tauBody, tauFeet) {
    const ab = posed ? 1 - Math.exp(-dt / tauBody) : 1, af = posed ? 1 - Math.exp(-dt / tauFeet) : 1;
    for (const k in S) if (typeof S[k] === 'number') P[k] = posed ? P[k] + (S[k] - P[k]) * ab : S[k];
    for (const f of FEET) for (const k of ['x', 'y', 'z', 'pitch']) P.feet[f][k] = posed ? P.feet[f][k] + (S.feet[f][k] - P.feet[f][k]) * af : S.feet[f][k];
    P.closed = S.closed; posed = true;
  }
  function update(ctx) {
    if (!rig) return false;
    if (!calibrated && size.w) { calibrated = true; calibrate(); }
    const time = ctx.still ? 0 : ctx.now / 1000, rawDt = lastTime ? Math.max(0, time - lastTime) : 0, dt = Math.min(.1, rawDt);
    lastTime = time;
    const {kind: k, visual} = ctx;
    resetPose();
    // Velocidad = lo que se movió en pantalla / tiempo real transcurrido (si el cuadro tardó mucho, no es confiable: se mantiene la anterior).
    const c = {time, serial: ctx.serial || 0, look: ctx.look, air: ctx.air, speed: rawDt > .25 ? speedSm : Math.min(2.6, ctx.dx * mpp / Math.max(rawDt, 1 / 120)), walkFeet: false};
    if (!dt) c.speed = 0;
    layout(k, ctx.t, ctx.p, c);
    const walks = visual === 'walk' || c.walkFeet;
    // La velocidad medida en pantalla viene a saltos (easing, empujones de separación): se alisa.
    speedSm += (c.speed - speedSm) * (dt ? 1 - Math.exp(-dt / .12) : 1);
    const mvTarget = walks ? smooth(speedSm / .08) : 0;
    const moving = walks && mvTarget > 0;
    if (moving) {
      const running = ctx.running || speedSm > 1.1;
      gaitState.phase += speedSm / strideFor(speedSm, running) * dt;
      gait(speedSm, running, mvTarget);
    }
    smoothPose(dt, .1, moving ? .012 : .09);
    // Parpadeo: cada 2,5-6 s los ojos se cierran ~0,14 s (solo si hay animación).
    if (!ctx.still) {
      if (!blinkAt) blinkAt = time + 1 + Math.random() * 3;
      if (time >= blinkAt) { blinkUntil = time + .14; blinkAt = time + 2.5 + Math.random() * 3.5; }
    }
    c.blink = time < blinkUntil;
    drive(ctx, c, dt);
    return true;
  }

  // El piso se mide en pantalla, no en el esqueleto: se dibuja el gato parado, se busca la fila más baja
  // con pelo o patas y se sube o baja el modelo hasta que esa fila quede justo en la línea del piso.
  // Así ningún modelo (ni su pelaje) queda flotando ni hundido, sea cual sea la malla.
  function calibrate() {
    try {
      const gl = renderer.getContext(), W = gl.drawingBufferWidth, H = gl.drawingBufferHeight;
      shadow.visible = false; rig.object.position.y = 0;
      resetPose(); posed = false; yawCur = null; floatErr = 0;
      const ctx = {facing: 1, running: false}, c = {time: 0, blink: false};
      smoothPose(0, .1, .09); drive(ctx, c, 0);
      renderer.render(scene, camera);
      const px = new Uint8Array(W * H * 4); gl.readPixels(0, 0, W, H, gl.RGBA, gl.UNSIGNED_BYTE, px);
      let low = -1;
      for (let y = 0; y < H && low < 0; y++) for (let x = 0; x < W; x++) if (px[(y * W + x) * 4 + 3] > 60) { low = y; break; }
      if (low >= 0) {
        const metersPerRow = VIEW_H / H, shift = (low - FLOOR_FRAC * H) * metersPerRow; // > 0: el modelo quedó por encima del piso
        rig.baseY = Math.max(-.08, Math.min(.08, -shift)); rig.object.position.y = rig.baseY;
      }
    } catch {}
    shadow.visible = true; posed = false; yawCur = null; floatErr = 0;
  }

  function drive(ctx, c, dt) {
    const {bone, rest, HY, CY, PZ, CZ, LA, LB, REST1, REST2, PAW_Y} = rig;
    const targetYaw = ctx.facing * (Math.PI / 2 - .3);
    yawCur = yawCur === null ? targetYaw : yawCur + Math.max(-dt * 7, Math.min(dt * 7, wrap(targetYaw - yawCur)));
    const yaw = yawCur + P.yawAdd * ctx.facing;
    pelvis.set(0, 0, 0).addScaledVector(fwdOf(yaw, tmpA), PZ + P.pelvisZ); pelvis.y = P.pelvisY - floatErr;
    chest.set(0, 0, 0).addScaledVector(fwdOf(yaw, tmpA), CZ + P.chestZ); chest.y = P.chestY - floatErr;
    delta.subVectors(chest, pelvis);
    const flat = Math.hypot(delta.x, delta.z), yawBody = flat > 1e-4 ? Math.atan2(delta.x, delta.z) : yaw;
    const dist = T.MathUtils.clamp(delta.length(), (LA + LB) * .55, (LA + LB) * .999), rise = Math.atan2(delta.y, flat);
    const up1 = rise + Math.acos(T.MathUtils.clamp((LA * LA + dist * dist - LB * LB) / (2 * LA * dist), -1, 1));
    const up2 = rise - Math.acos(T.MathUtils.clamp((LB * LB + dist * dist - LA * LA) / (2 * LB * dist), -1, 1));
    q.yaw.setFromAxisAngle(UP, yawBody);
    bone.Hips.position.copy(pelvis);
    q.hips.copy(q.yaw).multiply(q.a.setFromAxisAngle(X, REST1 - up1)).multiply(q.b.setFromAxisAngle(Z, P.roll * .7));
    bone.Hips.quaternion.copy(q.hips);
    q.spine.copy(q.yaw).multiply(q.a.setFromAxisAngle(X, REST2 - up2)).multiply(q.b.setFromAxisAngle(Z, P.roll));
    bone.Spine.quaternion.copy(q.hips).invert().multiply(q.spine);
    q.chest.setFromAxisAngle(UP, yawBody).multiply(q.a.setFromAxisAngle(X, REST2 - up2)).multiply(q.b.setFromAxisAngle(Z, P.roll * 1.2));
    bone.Chest.quaternion.copy(q.spine).invert().multiply(q.chest);

    // Cabeza: respecto del pecho. headRest compensa la rotación con que viene exportada la malla.
    const pitch = T.MathUtils.clamp(P.headPitch, -1.1, 1.1);
    q.head.setFromAxisAngle(UP, P.headYaw).multiply(q.a.setFromAxisAngle(X, -pitch)).multiply(q.b.setFromAxisAngle(Z, P.headRoll)).multiply(q.tail.setFromAxisAngle(UP, -cfg.headRest));
    q.neck.slerpQuaternions(ident, q.head, .45);
    bone.Neck.quaternion.copy(q.neck);
    bone.Head.quaternion.copy(q.neck).invert().multiply(q.head);

    tailPose(c.time, ctx.running);
    rig.object.updateMatrixWorld(true);

    // Patas: muñeca o garrón a su marca; el codo dobla hacia atrás y la rodilla hacia adelante.
    LEGS.forEach(([foot, parent, bendTo]) => {
      const f = P.feet[foot], parentQ = q[parent];
      footPos.set(0, 0, 0).addScaledVector(leftOf(yawBody, tmpA), f.x).addScaledVector(fwdOf(yawBody, tmpB), f.z); footPos.y = f.y;
      target.copy(footPos); target.y += PAW_Y[foot];
      pole.set(0, -.25, bendTo).applyQuaternion(parentQ);
      const lower = solve(bone[foot + 'Up'], bone[foot + 'Low'], bone[foot + 'Paw'], parentQ, target, pole, .06);
      q.a.setFromAxisAngle(UP, yawBody).multiply(q.b.setFromAxisAngle(X, f.pitch));
      bone[foot + 'Paw'].quaternion.copy(lower.invert()).multiply(q.a);
    });

    // Contacto con el piso: si una pata apoyada quedó en el aire (la pierna no llegó), se baja el cuerpo
    // en el cuadro siguiente. Nunca debe verse un gato flotando sobre la línea.
    rig.object.updateMatrixWorld(true);
    let worst = 0, lowest = Infinity;
    for (const foot of FEET) {
      if (P.feet[foot].y > .014) continue;
      const gap = tmpA.setFromMatrixPosition(bone[foot + 'Paw'].matrixWorld).y - rig.object.position.y - PAW_Y[foot];
      worst = Math.max(worst, gap); lowest = Math.min(lowest, gap);
    }
    // Garantía final: la pata apoyada más baja toca el piso en este mismo cuadro (se sube o baja todo el modelo).
    rig.object.position.y = (rig.baseY || 0) - (lowest === Infinity ? 0 : Math.max(-.05, Math.min(.05, lowest)));

    // Ojos cerrados (Fendi trae textura dormida; Vaiven no tiene).
    const shut = P.closed || c.blink;
    if (rig.asleep) {
      if (shut !== closedNow) { closedNow = shut; rig.material.map = shut ? rig.asleep : rig.awake; rig.material.needsUpdate = true; }
    }

    shadow.scale.set(.62, .26, 1);
    shadow.rotation.set(-Math.PI / 2, 0, yaw - Math.PI / 2, 'XYZ');
  }

  function tailPose(time, running) {
    const {bone} = rig, sway = Math.sin(time * 2.3 * P.tailSpeed);
    if (cfg.tail === 'absolute') {
      // Ángulos absolutos respecto de la cadera (0 = colgando, π/2 = atrás, ~2,8 = parada).
      const up = 1 - P.curl, quiver = 0;
      const pitchs = [0, 1, 2, 3].map(i => lerp(lerp([2.55, 2.75, 2.95, 3.4][i], [1.45, 1.6, 1.7, 1.75][i], P.tail), [.3, .85, 1.35, 1.45][i], P.curl));
      const yaws = [0, 1, 2, 3].map(i => lerp((.06 + .03 * i) * sway * P.sway, [.2, .8, 1.5, 2.1][i], P.curl));
      q.prev.identity();
      for (let i = 0; i < 4; i++) {
        q.tail.setFromAxisAngle(UP, yaws[i]).multiply(q.a.setFromAxisAngle(X, pitchs[i]));
        bone['Tail' + (i + 1)].quaternion.copy(q.prev).invert().multiply(q.tail);
        q.prev.copy(q.tail);
      }
    } else {
      // Relativo a la malla: 0 = parada, 1 = tendida hacia atrás.
      const t = P.tail, sw = sway * P.sway, set = (b, x, y, z) => b.quaternion.setFromEuler(e3.set(x, y, z, 'XYZ'));
      set(bone.Tail1, -t * .85 + P.curl * -.2, P.curl * .35, .07 * sw);
      set(bone.Tail2, -t * .3, P.curl * .55 + .06 * sw, .09 * sw);
      set(bone.Tail3, -t * .4, P.curl * .55 + .1 * sw, .11 * sw);
      set(bone.Tail4, -t * .45, P.curl * .55 + .14 * sw, .13 * sw);
    }
  }

  // El que llama maneja el reloj; draw() solo pinta.
  function draw() { if (rig && size.w) renderer.render(scene, camera); }
  // Para centrar al gato en el cuadro: la cola cuelga hacia atrás.
  api.debug = () => ({floatErr, speedSm, feet: Object.fromEntries(FEET.map(f => [f, P.feet[f].y.toFixed(3)]))});
  api.groundShift = () => rig ? rig.baseY : null; // metros que se corrigió el modelo para apoyar en el piso
  api.setFacing = f => { camera.position.x = -f * .06; };
  return api;
}
