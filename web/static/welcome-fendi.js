// Fendi en la bienvenida: malla real con esqueleto (scripts/exportar_gato.py fendi), animada en tiempo real.
// Duerme sobre el teclado; cuando paso se despierta, se levanta, baja de un salto, me sigue al trote y
// se frota contra mi pierna izquierda. Igual que el gato: las patas pisan marcas fijas (IK, sin patinar)
// y el cuerpo se arma encima de los apoyos; los pasos salen de la velocidad sobre un recorrido.
import * as T from './vendor/three/three.module.min.js';
import {readRig, buildRig, solve} from './welcome-character.js';
import {curve, track} from './welcome-cat.js';

const clamp01 = v => Math.min(1, Math.max(0, v));
const smooth = v => { v = clamp01(v); return v * v * (3 - 2 * v); };
const lerp = (a, b, t) => a + (b - a) * t;
const V = (x = 0, y = 0, z = 0) => new T.Vector3(x, y, z);
const UP = V(0, 1, 0), X = V(1, 0, 0), Z = V(0, 0, 1);
const TAU = Math.PI * 2;
const wrap = a => a - TAU * Math.round(a / TAU);
const pulse = (t, a, b, fadeIn = .15, fadeOut = .15) => smooth((t - a) / fadeIn) * (1 - smooth((t - b + fadeOut) / fadeOut));

const FEET = ['FL', 'FR', 'HL', 'HR'];
const HEAD_REST_YAW = -1.15; // la malla trae la cabeza girada a su derecha
// Momentos (segundos de la escena). Paso frente a su punta del escritorio a los 1,45 y me apoyo en el logo a los 4,7.
const WAKE = .75, RISE = 1.35, DESK_WALK = 1.8, JUMP = 2.2, TROT = 2.5, RUB = 4.85, STOP = 7.55;

// Recorrido suave por puntos (Catmull-Rom en planta) con la velocidad dada por claves [t, v]:
// se reescala para llegar justo al final del recorrido en el último instante.
function route(points, speedKeys) {
  const P = points.map(p => new T.Vector2(p.x, p.z)), n = P.length, pts = [];
  for (let i = 0; i < n - 1; i++) {
    const p0 = P[Math.max(0, i - 1)], p1 = P[i], p2 = P[i + 1], p3 = P[Math.min(n - 1, i + 2)];
    for (let k = 0; k < 40; k++) {
      const u = k / 40, u2 = u * u, u3 = u2 * u;
      const f = (a, b, c, d) => .5 * (2 * b + (-a + c) * u + (2 * a - 5 * b + 4 * c - d) * u2 + (-a + 3 * b - 3 * c + d) * u3);
      pts.push(new T.Vector2(f(p0.x, p1.x, p2.x, p3.x), f(p0.y, p1.y, p2.y, p3.y)));
    }
  }
  pts.push(P[n - 1].clone());
  const len = [0]; for (let i = 1; i < pts.length; i++) len.push(len[i - 1] + pts[i].distanceTo(pts[i - 1]));
  const L = len[len.length - 1], speed = curve(speedKeys), t0 = speedKeys[0][0], t1 = speedKeys[speedKeys.length - 1][0];
  const dt = 1 / 240, S = [0];
  for (let t = t0; t < t1; t += dt) S.push(S[S.length - 1] + Math.max(0, speed(t)) * dt);
  const scale = L / S[S.length - 1];
  const distAt = t => { const f = (Math.min(Math.max(t, t0), t1) - t0) / dt, i = Math.min(Math.floor(f), S.length - 2); return lerp(S[i], S[i + 1], f - i) * scale; };
  const pointAt = (s, out) => {
    let lo = 0, hi = len.length - 1; while (hi - lo > 1) { const m = (lo + hi) >> 1; if (len[m] <= s) lo = m; else hi = m; }
    const u = (s - len[lo]) / (len[hi] - len[lo] || 1), a = pts[lo], b = pts[hi];
    out.o = V(lerp(a.x, b.x, u), 0, lerp(a.y, b.y, u)); out.yaw = Math.atan2(b.x - a.x, b.y - a.y);
    return out;
  };
  const atS = (d, out = {}) => pointAt(Math.min(Math.max(d, 0), L - 1e-4), out);
  return {t0, t1, length: L, s: distAt, atS, at: (t, out = {}) => atS(distAt(t), out), speed: t => speed(t) * scale};
}

export async function loadFendi(base = '/welcome/') {
  const loader = new T.TextureLoader();
  const [buf, awake, asleep] = await Promise.all([
    fetch(base + 'fendi.bin').then(r => { if (!r.ok) throw new Error('fendi.bin ' + r.status); return r.arrayBuffer(); }),
    loader.loadAsync(base + 'fendi-color.webp'), loader.loadAsync(base + 'fendi-dormida.webp'),
  ]);
  for (const map of [awake, asleep]) { map.colorSpace = T.SRGBColorSpace; map.anisotropy = 8; }
  const {geometry, joints} = readRig(buf);
  const material = new T.MeshStandardMaterial({map: asleep, roughness: .9, metalness: 0, envMapIntensity: .6});
  const {object, bone, rest} = buildRig(geometry, joints, material);

  // Medidas del esqueleto en reposo.
  const PELVIS_Z = rest.Hips.z, CHEST_Z = rest.Chest.z;
  const linkA = rest.Spine.clone().sub(rest.Hips), linkB = rest.Chest.clone().sub(rest.Spine);
  const LA = linkA.length(), LB = linkB.length();
  const REST1 = Math.atan2(linkA.y, linkA.z), REST2 = Math.atan2(linkB.y, linkB.z);
  const PAW_Y = Object.fromEntries(FEET.map(f => [f, rest[f + 'Paw'].y]));
  // Dónde apoya cada pata respecto del cuerpo: echada, parada, al andar, agazapada y al caer.
  const LIE = {FL: V(.05, 0, .25), FR: V(-.05, 0, .27), HL: V(.085, 0, -.07), HR: V(-.085, 0, -.06)};
  const GAIT = {FL: V(.045, 0, .15), FR: V(-.045, 0, .15), HL: V(.055, 0, -.135), HR: V(-.055, 0, -.135)};
  const CROUCH = {FL: V(.045, 0, .14), FR: V(-.045, 0, .14), HL: V(.06, 0, -.09), HR: V(-.06, 0, -.09)};
  const LANDED = {FL: V(.045, 0, .16), FR: V(-.045, 0, .16), HL: V(.055, 0, -.07), HR: V(-.055, 0, -.07)};

  const fwdOf = (yaw, out = V()) => out.set(Math.sin(yaw), 0, Math.cos(yaw));
  const leftOf = (yaw, out = V()) => out.set(Math.cos(yaw), 0, -Math.sin(yaw));
  const place = (o, yaw, home) => o.clone().addScaledVector(leftOf(yaw), home.x).addScaledVector(fwdOf(yaw), home.z);

  // ---------- Coreografía ----------
  let plan = null;
  function setStage({bed, deskWalk, landing, leg, watch}) {
    const edge = deskWalk[deskWalk.length - 1];
    const plants = {FL: [], FR: [], HL: [], HR: []};
    // Una marca nueva cierra la anterior si quedó abierta: la pata despega `swing` antes de volver a pisar.
    const plant = (foot, t0, t1, o, yaw, home, extra = {}, swing = .2) => {
      const list = plants[foot], prev = list[list.length - 1];
      if (prev && prev.t1 === Infinity) prev.t1 = Math.max(prev.t0 + .02, Math.min(t0 - .06, t0 - swing));
      list.push({t0, t1, pos: place(o, yaw, home).setY(o.y), yaw, o: o.clone(), ...extra});
    };
    // Pasos sobre un recorrido: la cadencia sale de la velocidad (frena y arranca sin patinar).
    // Si arranca quieta, las patas que recién tendrían que estar volando esperan su paso siguiente.
    const gaitSteps = (path, from, to, {offset, duty, stride}, fromRest = true) => {
      const dt = 1 / 240, samples = [];
      let phase = 0, prev = path.at(from);
      for (let t = from; t <= to + 1e-9; t += dt) {
        const p = path.at(t), v = p.o.distanceTo(prev.o) / dt;
        phase += v / stride(v) * dt; samples.push({t, phase, o: p.o, yaw: p.yaw}); prev = p;
      }
      const end = samples[samples.length - 1], timeAt = ph => { let i = 0; while (i < samples.length - 1 && samples[i + 1].phase < ph) i++; return samples[i]; };
      for (const foot of FEET) {
        for (let k = 0; k + offset[foot] < end.phase; k++) {
          const down = k + offset[foot];
          if (fromRest && down < (1 - duty) * .7) continue;
          const sDown = timeAt(down), mid = timeAt(down + duty / 2), up = down + duty < end.phase ? timeAt(down + duty).t : Infinity;
          plant(foot, sDown.t, up, (up === Infinity ? end : mid).o.clone().setY(path.y), (up === Infinity ? end : mid).yaw, GAIT[foot], {}, timeAt(down - (1 - duty)).t > from ? sDown.t - timeAt(down - (1 - duty)).t : .15);
        }
      }
      return end;
    };
    // Al llegar, cada pata termina debajo de su lugar aunque el último paso haya quedado a mitad.
    const settle = (end, y, at) => FEET.forEach((foot, i) => {
      const last = plants[foot][plants[foot].length - 1], want = place(end.o, end.yaw, GAIT[foot]);
      if (last.t1 !== Infinity || last.pos.distanceTo(want.setY(y)) > .03) plant(foot, at + i * .07, Infinity, end.o.clone().setY(y), end.yaw, GAIT[foot], {}, .16);
    });

    // 1. Echada sobre el escritorio, mirando hacia donde voy a pasar.
    const bedYaw = Math.PI / 2;
    FEET.forEach(f => plant(f, -1, Infinity, bed, bedYaw, LIE[f], {key: true}));
    // 2. Se levanta: primero las manos vuelven debajo de los hombros, después las patas.
    [['FL', .0], ['FR', .07], ['HL', .26], ['HR', .33]].forEach(([f, d]) => plant(f, RISE + d + .12, Infinity, bed, bedYaw, GAIT[f], {lift: .03, key: true}, .12));
    // 3. Camina hasta el borde del escritorio girando hacia donde va a saltar.
    const jumpYaw = Math.atan2(landing.x - edge.x, landing.z - edge.z);
    const deskPath = route([bed, ...deskWalk],
      [[DESK_WALK, 0], [DESK_WALK + .12, .5], [JUMP - .3, .5], [JUMP - .12, 0]]);
    deskPath.y = bed.y;
    const deskEnd = gaitSteps(deskPath, DESK_WALK, JUMP - .12, {offset: {HR: .02, FR: .27, HL: .52, FL: .77}, duty: .6, stride: v => .16 + .2 * v});
    // Se agazapa al borde: junta las patas traseras.
    const K = {key: true};
    plant('HL', JUMP - .1, Infinity, edge, jumpYaw, CROUCH.HL, K, .12); plant('HR', JUMP - .05, Infinity, edge, jumpYaw, CROUCH.HR, K, .12);
    plant('FL', JUMP - .08, Infinity, edge, jumpYaw, CROUCH.FL, K, .1); plant('FR', JUMP - .03, Infinity, edge, jumpYaw, CROUCH.FR, K, .1);
    // 4. Salta al piso: despegan las manos, empujan las patas; caen primero las manos.
    const LIFT_F = JUMP + .1, LIFT_H = JUMP + .16, LAND_F = JUMP + .4, LAND_H = JUMP + .47;
    plant('FL', LAND_F, Infinity, landing, jumpYaw, LANDED.FL, K, LAND_F - LIFT_F); plant('FR', LAND_F + .03, Infinity, landing, jumpYaw, LANDED.FR, K, LAND_F + .03 - LIFT_F - .02);
    plant('HL', LAND_H, Infinity, landing, jumpYaw, LANDED.HL, K, LAND_H - LIFT_H); plant('HR', LAND_H + .03, Infinity, landing, jumpYaw, LANDED.HR, K, LAND_H + .03 - LIFT_H - .02);

    // 5. Me sigue al trote por detrás y entra por mi izquierda, entre la pierna y el logo.
    //    Pasa rozándome con el flanco, da la vuelta adelante y vuelve a frotarse con la cabeza.
    const at = (dx, dz) => V(leg.x + dx, 0, leg.z + dz);
    const finalYaw = -1.95, bunt = at(.12, .13).addScaledVector(fwdOf(finalYaw), -.2); // la cabeza queda adelante y afuera de la canilla
    const floorPath = route([landing, landing.clone().addScaledVector(fwdOf(jumpYaw), .35).setY(0), V(-.9, 0, -1.05), V(-.1, 0, -.78), at(.12, -.62), at(.17, -.36), at(.15, 0), at(.16, .26),
      at(.25, .55), at(.48, .63), at(.68, .53), at(.7, .42), at(.6, .32), bunt], // vuelta amplia adelante del logo y llega derecha
      [[TROT, 0], [TROT + .25, 1.4], [RUB - .4, 1.35], [RUB, .42], [RUB + 1.3, .38], [RUB + 1.6, .5], [STOP - .6, .45], [STOP, 0]]);
    floorPath.y = 0;
    gaitSteps(floorPath, TROT, RUB - .15, {offset: {HL: .02, FR: .04, HR: .52, FL: .54}, duty: .45, stride: v => .2 + .3 * v});
    const end = gaitSteps(floorPath, RUB - .15, STOP, {offset: {HR: .02, FR: .27, HL: .52, FL: .77}, duty: .62, stride: v => .2 + .25 * v}, false);
    settle(end, 0, STOP);
    // Mientras se frota en el lugar, amasa un poco con las manos.
    [8.1, 8.6, 9.1].forEach((t, i) => plant(i % 2 ? 'FR' : 'FL', t, Infinity, end.o, end.yaw, GAIT[i % 2 ? 'FR' : 'FL'], {lift: .03}, .14));

    // Cintura escapular y pelvis: cada una pasa por encima de sus apoyos.
    const girdle = feet => {
      const keys = [];
      for (const foot of feet) for (const s of plants[foot].filter(s => s.key)) {
        const key = t => keys.push({t, x: s.o.x, z: s.o.z, yaw: s.yaw});
        if (s.t1 - s.t0 < .2) key((s.t0 + s.t1) / 2); else { key(Math.max(s.t0, 0) + .06); if (isFinite(s.t1)) key(s.t1 - .06); }
      }
      return keys;
    };
    const chestKeys = girdle(['FL', 'FR']), pelvisKeys = girdle(['HL', 'HR']);
    // Sobre un recorrido el cuerpo sigue la curva, no los apoyos (que van a saltos): el pecho va adelante
    // y la pelvis lo sigue por la misma huella, así dobla como un gato y no como una tabla.
    const along = (path, from, to) => {
      for (let t = from; t < to; t += .04) {
        const d = path.s(t), p = path.atS(d), b = path.atS(d + PELVIS_Z); // pelvis sobre la huella, a un largo de cuerpo
        const o = b.o.clone().addScaledVector(fwdOf(b.yaw), -PELVIS_Z);
        chestKeys.push({t, x: p.o.x, z: p.o.z, yaw: p.yaw});
        pelvisKeys.push({t, x: o.x, z: o.z, yaw: b.yaw});
      }
    };
    along(deskPath, DESK_WALK + .04, JUMP - .12); along(floorPath, TROT + .04, STOP + .3);
    const unwrap = keys => { keys.sort((a, b) => a.t - b.t); keys.reduce((p, k) => { k.yaw = p.yaw + wrap(k.yaw - p.yaw); return k; }); return keys; };

    const D = bed.y, k = list => curve(list);
    plan = {
      plants, watch, leg: leg.clone(), bedY: D,
      chest: track(unwrap(chestKeys)), pelvis: track(unwrap(pelvisKeys)),
      // Alturas: echada, se sienta en dos tiempos, camina, se agazapa, salta y amortigua, trota.
      chestY: k([[0, D + .125], [RISE, D + .125], [RISE + .2, D + .215], [RISE + .45, D + .235], [JUMP - .15, D + .23], [JUMP, D + .17], [LIFT_F, D + .22],
        [JUMP + .2, D + .2], [JUMP + .3, D + .02], [LAND_F, .19], [LAND_F + .12, .2], [TROT + .3, .225], [RUB, .23], [STOP, .232]]),
      pelvisY: k([[0, D + .115], [RISE + .2, D + .118], [RISE + .5, D + .232], [JUMP - .15, D + .23], [JUMP, D + .15], [LIFT_H, D + .27], [JUMP + .24, D + .23],
        [JUMP + .33, D + .08], [JUMP + .41, .48], [LAND_H, .2], [LAND_H + .12, .2], [TROT + .3, .222], [RUB, .232], [STOP, .236]]),
      breathe: t => (1 - smooth((t - RISE) / .3)) * .005 * Math.sin(t * TAU * .32),
      trot: t => smooth((t - TROT - .1) / .2) * (1 - smooth((t - RUB + .3) / .3)),
      // Inclinación hacia mi pierna mientras se frota (positivo: hacia su derecha).
      roll: t => .16 * pulse(t, RUB + .15, RUB + 1.5, .35, .4) + .12 * smooth((t - STOP + .3) / .4),
      awake: t => smooth((t - WAKE) / .45),
      // Pestañeos: abre a los 1,35, parpadea dormida, y al final me mira con un pestañeo lento.
      eyesClosed: t => t < WAKE || (t > WAKE + .28 && t < WAKE + .38) || (t > 8.2 && t < 8.55),
      // Cabeza: dormida apoyada; despierta me mira, mira el piso antes de saltar, mira adelante al trotar.
      lookMan: t => smooth((t - WAKE) / .4) * (1 - smooth((t - DESK_WALK - .1) / .3)) + .5 * pulse(t, TROT + .6, RUB - .3, .3, .3) + pulse(t, 8.0, 9.6, .3, .1),
      lookLeg: t => pulse(t, RUB, 8.1, .3, .3),
      lookDown: t => pulse(t, JUMP - .3, JUMP + .15, .2, .15),
      tail: t => ({ // ángulos de la cola: levantada al andar, de contrapeso en el salto, enroscada dormida
        sleep: 1 - smooth((t - RISE - .1) / .5), jump: pulse(t, JUMP - .05, LAND_H + .15, .15, .25),
        quiver: pulse(t, RUB + .4, 9.6, .4, .1),
      }),
    };
  }

  // Dónde está una pata: apoyada en su marca o volando hacia la siguiente.
  const footOut = FEET.map(() => ({pos: V(), yaw: 0, pitch: 0}));
  function footAt(index, t) {
    const foot = FEET[index], list = plan.plants[foot], out = footOut[index];
    let i = 0; while (i < list.length - 1 && t >= list[i + 1].t0) i++;
    const a = list[i], b = list[i + 1];
    if (!b || t <= a.t1) { out.pos.copy(a.pos); out.yaw = a.yaw; out.pitch = 0; return out; }
    const w = (t - a.t1) / (b.t0 - a.t1), drop = a.pos.y - b.pos.y > .3;
    // Al bajar del escritorio la pata sale hacia adelante y recién después cae.
    const wh = drop ? smooth(w / .55) : .5 - .5 * Math.cos(Math.PI * w), wv = drop ? smooth((w - .2) / .8) : wh;
    const reach = Math.hypot(b.pos.x - a.pos.x, b.pos.z - a.pos.z), arch = Math.sin(Math.PI * w);
    out.pos.copy(a.pos).lerp(b.pos, wh);
    out.pos.y = lerp(a.pos.y, b.pos.y, wv) + (b.lift ?? .02 + .1 * Math.min(reach, .4)) * arch;
    out.yaw = a.yaw + wrap(b.yaw - a.yaw) * smooth(w);
    out.pitch = (foot[0] === 'F' ? .9 : .5) * arch * (drop ? .3 : 1);
    return out;
  }

  const q = {yaw: new T.Quaternion(), hips: new T.Quaternion(), spine: new T.Quaternion(), chest: new T.Quaternion(), a: new T.Quaternion(), b: new T.Quaternion(),
    head: new T.Quaternion(), neck: new T.Quaternion(), inv: new T.Quaternion(), tail: new T.Quaternion(), prev: new T.Quaternion()};
  const c = {}, pv = {}, pelvis = V(), chest = V(), delta = V(), tmpA = V(), tmpB = V(), pole = V(), target = V(), headPos = V(), look = V(), dir = V();
  const LEGS = [['FL', 'chest', -1], ['FR', 'chest', -1], ['HL', 'hips', 1], ['HR', 'hips', 1]];
  const ident = new T.Quaternion();

  // Hacia dónde mira la cabeza, como yaw y pitch relativos al pecho (positivo: a su izquierda y arriba).
  function aim(point, out) {
    dir.subVectors(point, headPos).applyQuaternion(q.inv.copy(q.chest).invert());
    out.yaw = Math.atan2(dir.x, dir.z); out.pitch = Math.atan2(dir.y, Math.hypot(dir.x, dir.z));
    return out;
  }
  const lookA = {}, lookB = {};

  function update(t) {
    if (!plan) return;
    material.map = plan.eyesClosed(t) ? asleep : awake;
    plan.chest(t, c); plan.pelvis(t, pv);
    const trot = plan.trot(t), roll = plan.roll(t), stride = t * TAU / .42;
    pelvis.set(pv.x, 0, pv.z).addScaledVector(fwdOf(pv.yaw, tmpA), PELVIS_Z);
    pelvis.y = plan.pelvisY(t) + .012 * Math.sin(stride + 2) * trot;
    chest.set(c.x, 0, c.z).addScaledVector(fwdOf(c.yaw, tmpA), CHEST_Z);
    chest.y = plan.chestY(t) + .012 * Math.sin(stride - .6) * trot + plan.breathe(t);

    // Columna: dos tramos entre pelvis y pecho; si se acercan, el lomo se arquea hacia arriba.
    delta.subVectors(chest, pelvis);
    const flat = Math.hypot(delta.x, delta.z), yawBody = flat > 1e-4 ? Math.atan2(delta.x, delta.z) : pv.yaw;
    const dist = T.MathUtils.clamp(delta.length(), (LA + LB) * .55, (LA + LB) * .999), rise = Math.atan2(delta.y, flat);
    const up1 = rise + Math.acos(T.MathUtils.clamp((LA * LA + dist * dist - LB * LB) / (2 * LA * dist), -1, 1));
    const up2 = rise - Math.acos(T.MathUtils.clamp((LB * LB + dist * dist - LA * LA) / (2 * LB * dist), -1, 1));
    q.yaw.setFromAxisAngle(UP, yawBody);
    bone.Hips.position.copy(pelvis);
    q.hips.copy(q.yaw).multiply(q.a.setFromAxisAngle(X, REST1 - up1)).multiply(q.b.setFromAxisAngle(Z, roll * .7));
    bone.Hips.quaternion.copy(q.hips);
    q.spine.copy(q.yaw).multiply(q.a.setFromAxisAngle(X, REST2 - up2)).multiply(q.b.setFromAxisAngle(Z, roll));
    bone.Spine.quaternion.copy(q.hips).invert().multiply(q.spine);
    const bend = T.MathUtils.clamp(wrap(c.yaw - yawBody), -.8, .8) * .7;
    q.chest.setFromAxisAngle(UP, yawBody + bend).multiply(q.a.setFromAxisAngle(X, REST2 - up2)).multiply(q.b.setFromAxisAngle(Z, roll * 1.2));
    bone.Chest.quaternion.copy(q.spine).invert().multiply(q.chest);
    object.updateMatrixWorld(true);

    // Cabeza: dormida apoyada sobre las manos, girada hacia la cámara; despierta busca un punto y lo sigue.
    headPos.setFromMatrixPosition(bone.Neck.matrixWorld);
    const awakeW = plan.awake(t);
    let yaw = lerp(-.8, 0, awakeW), pitch = lerp(-.8, 0, awakeW), headRoll = lerp(.35, 0, awakeW);
    const blendTo = (w, a) => { if (w <= 0) return; yaw = lerp(yaw, T.MathUtils.clamp(a.yaw, -1.3, 1.3), w); pitch = lerp(pitch, T.MathUtils.clamp(a.pitch, -.9, .7), w); };
    if (plan.watch) blendTo(Math.min(1, plan.lookMan(t)), aim(look.setFromMatrixPosition(plan.watch.matrixWorld), lookA));
    // Frotándose: la mejilla contra la canilla, con empujoncitos.
    const rub = plan.lookLeg(t), nudge = Math.sin((t - RUB) * TAU * 1.3);
    // Apunta a la superficie de la canilla del lado de ella, no al centro de la pierna.
    look.set(headPos.x - plan.leg.x, 0, headPos.z - plan.leg.z).setLength(.07).add(plan.leg).setY(.3 + .03 * nudge);
    blendTo(rub, aim(look, lookB));
    headRoll += rub * (-Math.sign(lookB.yaw || 1) * .3 + .12 * nudge); // inclina la mejilla del lado de la pierna
    pitch = lerp(pitch, -.85, plan.lookDown(t));
    // Total: girar desde la pose de la malla a la deseada; el cuello hace casi la mitad.
    q.head.setFromAxisAngle(UP, yaw).multiply(q.a.setFromAxisAngle(X, -pitch)).multiply(q.b.setFromAxisAngle(Z, headRoll)).multiply(q.tail.setFromAxisAngle(UP, -HEAD_REST_YAW));
    q.neck.slerpQuaternions(ident, q.head, .45);
    bone.Neck.quaternion.copy(q.neck);
    bone.Head.quaternion.copy(q.neck).invert().multiply(q.head);

    // Cola, con ángulos absolutos respecto de la cadera (0 = colgando, π/2 = atrás, ~2,8 = parada).
    const tl = plan.tail(t), sway = Math.sin(t * 2.3), quiver = tl.quiver * Math.sin(t * TAU * 9) * .06;
    const awakeUp = 1 - tl.sleep;
    const pitchs = [0, 0, 0, 0].map((_, i) => lerp([.3, .85, 1.35, 1.45][i], [2.55, 2.75, 2.95 + quiver, 3.4 + quiver * 1.5][i], awakeUp));
    const yaws = [0, 0, 0, 0].map((_, i) => lerp([.2, .8, 1.5, 2.1][i], (.06 + .03 * i) * sway, awakeUp));
    for (let i = 0; i < 4; i++) { pitchs[i] = lerp(pitchs[i], [1.45, 1.6, 1.7, 1.75][i], tl.jump); pitchs[i] += .06 * Math.sin(stride + i * .7) * trot; }
    q.prev.identity();
    for (let i = 0; i < 4; i++) {
      q.tail.setFromAxisAngle(UP, yaws[i]).multiply(q.a.setFromAxisAngle(X, pitchs[i]));
      bone['Tail' + (i + 1)].quaternion.copy(q.prev).invert().multiply(q.tail);
      q.prev.copy(q.tail);
    }
    object.updateMatrixWorld(true);

    // Patas: muñeca o garrón a su marca; el codo dobla hacia atrás y la rodilla hacia adelante.
    LEGS.forEach(([foot, parent, bendTo], i) => {
      const f = footAt(i, t), parentQ = q[parent];
      target.copy(f.pos); target.y += PAW_Y[foot];
      pole.set(0, -.25, bendTo).applyQuaternion(parentQ);
      const lower = solve(bone[foot + 'Up'], bone[foot + 'Low'], bone[foot + 'Paw'], parentQ, target, pole, .06);
      q.a.setFromAxisAngle(UP, f.yaw).multiply(q.b.setFromAxisAngle(X, f.pitch));
      bone[foot + 'Paw'].quaternion.copy(lower.invert()).multiply(q.a);
    });
  }

  return {object, bone, setStage, update, maps: [awake, asleep]};
}
