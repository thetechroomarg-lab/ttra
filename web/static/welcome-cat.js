// Gato de la bienvenida: malla real con esqueleto (scripts/exportar_gato.py), animada en tiempo real.
// Todo sale de dónde y cuándo pisa cada pata: el cuerpo se arma encima de los apoyos y las patas
// se resuelven con IK, así ninguna patina. Sin clips pregrabados.
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
const RUN_SPEED = 3, STRIDE_TIME = .28, BRAKE_TIME = .42; // galope corto: ~3,5 trancos por segundo
const RUN_Y = .215, HEAD_REST_YAW = .85; // la malla trae la cabeza girada hacia su izquierda

// Curva suave por claves [t, valor] (Hermite con tangentes por diferencias; plana en los extremos).
export function curve(keys) {
  const n = keys.length;
  const m = keys.map((k, i) => i === 0 || i === n - 1 ? 0 : (keys[i + 1][1] - keys[i - 1][1]) / (keys[i + 1][0] - keys[i - 1][0]));
  return t => {
    if (t <= keys[0][0]) return keys[0][1];
    if (t >= keys[n - 1][0]) return keys[n - 1][1];
    let i = 0; while (t > keys[i + 1][0]) i++;
    const [t0, v0] = keys[i], [t1, v1] = keys[i + 1], h = t1 - t0, u = (t - t0) / h, u2 = u * u, u3 = u2 * u;
    return (2 * u3 - 3 * u2 + 1) * v0 + (u3 - 2 * u2 + u) * h * m[i] + (3 * u2 - 2 * u3) * v1 + (u3 - u2) * h * m[i + 1];
  };
}
// Trayectoria en planta por claves {t, x, z, yaw}: lineal entre claves y promediada para quitar quiebres.
export function track(keys) {
  keys.sort((a, b) => a.t - b.t);
  const lin = (t, out) => {
    const last = keys.length - 1;
    if (t <= keys[0].t) return Object.assign(out, keys[0]);
    if (t >= keys[last].t) return Object.assign(out, keys[last]);
    let i = 0; while (t > keys[i + 1].t) i++;
    const a = keys[i], b = keys[i + 1], u = b.t === a.t ? 1 : (t - a.t) / (b.t - a.t);
    out.x = lerp(a.x, b.x, u); out.z = lerp(a.z, b.z, u); out.yaw = lerp(a.yaw, b.yaw, u);
    return out;
  };
  const s = {};
  return (t, out) => {
    out.x = out.z = out.yaw = 0;
    for (const dt of [-.06, -.03, 0, .03, .06]) { lin(t + dt, s); out.x += s.x * .2; out.z += s.z * .2; out.yaw += s.yaw * .2; }
    return out;
  };
}

export async function loadCat(base = '/welcome/', {hd = false} = {}) {
  const mesh = hd ? 'gato-hd.bin' : 'gato.bin'; // HD: misma malla subdividida y curvada
  const [buf, map] = await Promise.all([
    fetch(base + mesh).then(r => { if (!r.ok) throw new Error(mesh + ' ' + r.status); return r.arrayBuffer(); }),
    new T.TextureLoader().loadAsync(base + 'gato-color.webp'),
  ]);
  const {geometry, joints} = readRig(buf);
  map.colorSpace = T.SRGBColorSpace; map.anisotropy = 8;
  // Pelo: sin brillo plástico y con un velo suave a contraluz (sheen) en la versión HD.
  const material = new T.MeshPhysicalMaterial({map, roughness: .86, metalness: 0, envMapIntensity: .6,
    sheen: hd ? .35 : 0, sheenRoughness: .75, sheenColor: new T.Color(0xd9cbb8)});
  const {object, bone, rest} = buildRig(geometry, joints, material);
  object.visible = false;

  // Medidas del esqueleto en reposo.
  const PELVIS_Z = rest.Hips.z, CHEST_Z = rest.Chest.z;
  const linkA = rest.Spine.clone().sub(rest.Hips), linkB = rest.Chest.clone().sub(rest.Spine);
  const LA = linkA.length(), LB = linkB.length(), SPINE = rest.Chest.distanceTo(rest.Hips);
  const REST1 = Math.atan2(linkA.y, linkA.z), REST2 = Math.atan2(linkB.y, linkB.z);
  const PAW_Y = {FL: rest.FLPaw.y, FR: rest.FRPaw.y, HL: rest.HLPaw.y, HR: rest.HRPaw.y};
  // Dónde cae cada pata respecto del cuerpo: parado tal cual la malla, al andar y agazapado.
  const STAND = Object.fromEntries(FEET.map(f => [f, V(rest[f + 'Paw'].x, 0, rest[f + 'Paw'].z)]));
  const GAIT = {FL: V(.04, 0, .095), FR: V(-.04, 0, .095), HL: V(.06, 0, -.15), HR: V(-.06, 0, -.15)};
  const CROUCH = {FL: V(.04, 0, .1), FR: V(-.04, 0, .1), HL: V(.065, 0, -.1), HR: V(-.065, 0, -.1)};
  const LANDED = {FL: V(.04, 0, .095), FR: V(-.04, 0, .095), HL: V(.06, 0, -.045), HR: V(-.06, 0, -.045)};

  const fwdOf = (yaw, out = V()) => out.set(Math.sin(yaw), 0, Math.cos(yaw));
  const leftOf = (yaw, out = V()) => out.set(Math.cos(yaw), 0, -Math.sin(yaw));
  const place = (o, yaw, home) => o.clone().addScaledVector(leftOf(yaw), home.x).addScaledVector(fwdOf(yaw), home.z);

  // ---------- Coreografía: se arma una vez que la escena dice dónde está el logo ----------
  let plan = null;
  function setStage({origin, u, n, top, laneZ, spawnX, arriveAt}) {
    const at = (s, d = 0, y = 0) => origin.clone().addScaledVector(u, s).addScaledVector(n, d).setY(y);
    const yawU = Math.atan2(u.x, u.z), yawEnd = yawU - Math.PI; // termina mirando hacia quien llega
    // Tiempos (seg. desde que frena): se agacha, despegan las manos, empujan las patas, cae arriba y gira.
    const t0 = arriveAt - 2.1;
    const LIFT_F = .41, LIFT_H = .52, LAND_F = 1.1, LAND_H = 1.18, TURN = 1.33;
    // Salta en diagonal desde adelante de la punta izquierda: el hombre pasa por detrás sin pisarlo.
    const ground = at(-.75, .5), landing = at(.55, 0, top), final = at(.42, 0, top);
    const yawJump = Math.atan2(landing.x - ground.x, landing.z - ground.z);

    // Carrera: viene de atrás por el lado de la cámara, pasa al hombre y frena frente al logo.
    const tBrake = t0 - BRAKE_TIME, brakeDist = RUN_SPEED * BRAKE_TIME / 2;
    const left = t => t >= t0 ? 0 : t >= tBrake ? brakeDist * ((t0 - t) / BRAKE_TIME) ** 2 : brakeDist + RUN_SPEED * (tBrake - t); // metros que faltan
    const pathAt = (t, out) => {
      const r = left(t), laneAt = d => lerp(ground.z, laneZ + .55, smooth((d - .3) / 2));
      out.o = V(ground.x - r, 0, laneAt(r));
      out.yaw = lerp(Math.atan2(.05, laneAt(r) - laneAt(r + .05)), yawJump, 1 - smooth(r / .7));
      return out;
    };
    const tStart = tBrake - (Math.max(1, ground.x - spawnX) - brakeDist) / RUN_SPEED;

    const plants = {FL: [], FR: [], HL: [], HR: []};
    const plant = (foot, tDown, tUp, o, yaw, home, extra) => plants[foot].push({t0: tDown, t1: tUp, pos: place(o, yaw, home), yaw, o: o.clone(), ...extra});
    // Galope: empujan las dos patas, vuela, caen las dos manos, vuelve a volar.
    const phase = {HL: 0, HR: .09, FR: .47, FL: .57}, stance = .34 * STRIDE_TIME, p = {};
    const stop = {HL: t0 - .1, HR: t0 - .05, FL: t0 - .02, FR: t0 + .03};
    for (const foot of FEET) {
      for (let k = Math.ceil((tStart - t0) / STRIDE_TIME) - 1; ; k++) {
        const down = t0 + (k + phase[foot]) * STRIDE_TIME;
        if (down + stance > stop[foot] - .12) break;
        pathAt(down + stance / 2, p);
        plant(foot, down, down + stance, p.o, p.yaw, GAIT[foot]);
      }
      // Frena y queda plantado para agacharse.
      const hind = foot[0] === 'H';
      plant(foot, stop[foot], t0 + (hind ? LIFT_H : LIFT_F) + (foot[1] === 'L' ? .03 : 0), ground, yawJump, CROUCH[foot]);
      // Cae arriba del logo: primero las manos, enseguida las patas, recogidas debajo del cuerpo.
      plant(foot, t0 + (hind ? LAND_H : LAND_F) + (foot[1] === 'L' ? .03 : 0), t0 + TURN + {FR: 0, FL: .05, HR: .12, HL: .34}[foot], landing, yawU, LANDED[foot],
        hind ? {o: at(.58, 0, top), lift: .1} : {lift: .12});
      // Media vuelta sobre las patas: las manos giran por el lado de la cámara y las patas se acomodan.
      plant(foot, t0 + TURN + {FR: .38, FL: .43, HR: .3, HL: .52}[foot], Infinity, final, yawEnd, STAND[foot],
        hind ? {lift: .03} : {lift: .11, arc: n.clone().multiplyScalar(foot === 'FL' ? .15 : .13)});
    }

    // Cintura escapular y pelvis: cada una pasa por encima de sus apoyos.
    const girdle = feet => {
      const keys = [];
      for (const foot of feet) for (const s of plants[foot]) {
        const key = t => keys.push({t, x: s.o.x, z: s.o.z, yaw: s.yaw});
        if (s.t1 - s.t0 < .2) key((s.t0 + s.t1) / 2); else { key(s.t0 + .08); if (isFinite(s.t1)) key(s.t1 - .08); }
      }
      return keys;
    };
    const chestKeys = girdle(['FL', 'FR']), pelvisKeys = girdle(['HL', 'HR']);
    // En la media vuelta el pecho rodea a la pelvis por el frente del logo.
    const mid = at(.52, .03); chestKeys.push({t: t0 + TURN + .22, x: mid.x, z: mid.z, yaw: yawU - Math.PI / 2});
    const hold = at(.56); pelvisKeys.push({t: t0 + TURN + .2, x: hold.x, z: hold.z, yaw: yawU - .5});

    const k = (list, base = 0) => curve(list.map(([t, v]) => [t0 + t, v + base]));
    plan = {
      plants, tStart, t0, yawEnd, stride: t => (t - t0) / STRIDE_TIME,
      running: t => 1 - smooth((t - t0 + .2) / .2),
      chest: track(chestKeys), pelvis: track(pelvisKeys),
      // Alturas del pecho y de la pelvis: carrera baja, agazapado, impulso, parábola y amortiguación al caer.
      chestY: k([[-.15, RUN_Y], [0, .22], [.22, .165], [.33, .175], [LIFT_F, .3], [.47, .4], [LIFT_H, .5], [.65, 1.03], [.77, 1.37], [.9, 1.55], [1, 1.58],
        [LAND_F, 1.5], [1.2, 1.4], [TURN, 1.43], [TURN + .2, 1.5], [TURN + .45, 1.45], [TURN + .65, top + rest.Chest.y]]),
      pelvisY: k([[-.15, RUN_Y], [0, .21], [.22, .13], [.42, .135], [LIFT_H, .31], [.65, .82], [.77, 1.19], [.9, 1.43], [1.02, 1.55], [1.13, 1.53],
        [LAND_H, 1.47], [1.28, 1.37], [1.4, 1.4], [TURN + .22, 1.41], [TURN + .55, top + rest.Hips.y]]),
      back: k([[-.05, 0], [.22, -.035], [.36, -.03], [.5, 0]]), // agazapado, el peso va hacia atrás
      wiggle: t => .012 * Math.sin((t - t0) * TAU * 7) * smooth((t - t0 - .16) / .1) * (1 - smooth((t - t0 - .4) / .06)),
      // Cabeza: mira arriba antes de saltar, acompaña el giro, mira a quien llega y después a la cámara.
      headYaw: k([[1.2, 0], [TURN + .05, -.5], [TURN + .3, -.3], [TURN + .55, .2], [2.25, .25], [2.9, HEAD_REST_YAW]]),
      headPitch: k([[-.1, 0], [.2, .6], [.45, .65], [.7, .3], [1, -.12], [1.25, 0]]),
      // Cola (cuánto baja hacia atrás): tendida en la carrera y al acechar, de contrapeso en el salto y arriba al final.
      tail: k([[-.1, 1], [.2, 1.1], [.45, 1], [.56, .3], [.8, .7], [1.1, .45], [1.25, .1], [1.5, .35], [TURN + .65, 0]]),
      twitch: t => smooth((t - t0 - .05) / .15) * (1 - smooth((t - t0 - .4) / .1)),
      settled: t => smooth((t - t0 - TURN - .6) / .5),
    };
  }

  // Dónde está una pata: apoyada en su marca o volando hacia la siguiente.
  const footOut = FEET.map(() => ({pos: V(), yaw: 0, pitch: 0}));
  function footAt(index, t) {
    const foot = FEET[index], list = plan.plants[foot], out = footOut[index];
    let i = 0; while (i < list.length - 1 && t >= list[i + 1].t0) i++;
    const a = list[i], b = list[i + 1];
    if (!b || t <= a.t1) { out.pos.copy(a.pos); out.yaw = a.yaw; out.pitch = 0; return out; }
    const w = (t - a.t1) / (b.t0 - a.t1), rise = b.pos.y - a.pos.y, climbing = Math.abs(rise) > .3;
    // Al subir, la pata gana altura antes de avanzar (pasa por encima del borde del logo).
    const wh = climbing ? smooth((w - .12) / .88) : .5 - .5 * Math.cos(Math.PI * w), wv = climbing ? smooth(w / .72) : wh;
    const reach = Math.hypot(b.pos.x - a.pos.x, b.pos.z - a.pos.z), arch = Math.sin(Math.PI * w);
    out.pos.copy(a.pos).lerp(b.pos, wh);
    out.pos.y = lerp(a.pos.y, b.pos.y, wv) + (b.lift ?? .025 + .1 * Math.min(reach, .5)) * arch;
    if (b.arc) out.pos.addScaledVector(b.arc, arch);
    out.yaw = lerp(a.yaw, b.yaw, smooth(w));
    out.pitch = (foot[0] === 'F' ? .9 : .5) * arch; // la mano se dobla al levantarse
    return out;
  }

  const q = {yaw: new T.Quaternion(), hips: new T.Quaternion(), spine: new T.Quaternion(), chest: new T.Quaternion(), a: new T.Quaternion(), b: new T.Quaternion()};
  const e3 = new T.Euler(), c = {}, pv = {}, pelvis = V(), chest = V(), delta = V(), tmpA = V(), tmpB = V(), pole = V(), target = V();
  const setEuler = (b, x, y, z, order = 'XYZ') => b.quaternion.setFromEuler(e3.set(x, y, z, order));
  const LEGS = [['FL', 'chest', -1], ['FR', 'chest', -1], ['HL', 'hips', 1], ['HR', 'hips', 1]];

  function update(t) {
    if (!plan) return;
    object.visible = t >= plan.tStart;
    if (!object.visible) return;
    const running = plan.running(t), stride = plan.stride(t) * TAU, settled = plan.settled(t);
    plan.chest(t, c); plan.pelvis(t, pv);
    const back = plan.back(t);
    // Pelvis y pecho en el mundo; el galope los hace subir y bajar a contratiempo.
    pelvis.set(pv.x, 0, pv.z).addScaledVector(fwdOf(pv.yaw, tmpA), PELVIS_Z + back).addScaledVector(leftOf(pv.yaw, tmpB), plan.wiggle(t));
    pelvis.y = plan.pelvisY(t) + .016 * Math.sin(stride + 2.2) * running;
    chest.set(c.x, 0, c.z).addScaledVector(fwdOf(c.yaw, tmpA), CHEST_Z + back * .6);
    chest.y = plan.chestY(t) + .016 * Math.sin(stride - .6) * running + .002 * Math.sin(t * 2.1) * settled;

    // Columna: dos tramos entre pelvis y pecho; si se acercan, el lomo se arquea hacia arriba.
    delta.subVectors(chest, pelvis);
    const flat = Math.hypot(delta.x, delta.z), yawBody = flat > 1e-4 ? Math.atan2(delta.x, delta.z) : pv.yaw;
    const dist = T.MathUtils.clamp(delta.length(), (LA + LB) * .55, (LA + LB) * .999), rise = Math.atan2(delta.y, flat);
    const up1 = rise + Math.acos(T.MathUtils.clamp((LA * LA + dist * dist - LB * LB) / (2 * LA * dist), -1, 1));
    const up2 = rise - Math.acos(T.MathUtils.clamp((LB * LB + dist * dist - LA * LA) / (2 * LB * dist), -1, 1));
    q.yaw.setFromAxisAngle(UP, yawBody);
    bone.Hips.position.copy(pelvis);
    q.hips.copy(q.yaw).multiply(q.a.setFromAxisAngle(X, REST1 - up1)).multiply(q.b.setFromAxisAngle(Z, plan.wiggle(t) * 6));
    bone.Hips.quaternion.copy(q.hips);
    q.spine.copy(q.yaw).multiply(q.a.setFromAxisAngle(X, REST2 - up2));
    bone.Spine.quaternion.copy(q.hips).invert().multiply(q.spine);
    // El pecho apunta hacia donde van las manos: en los giros el cuerpo se curva.
    const bend = T.MathUtils.clamp(wrap(c.yaw - yawBody), -.7, .7) * .6;
    q.chest.setFromAxisAngle(UP, yawBody + bend).multiply(q.a.setFromAxisAngle(X, REST2 - up2));
    bone.Chest.quaternion.copy(q.spine).invert().multiply(q.chest);

    // Cabeza: compensa la inclinación del pecho para mantener la mirada.
    const yawHead = plan.headYaw(t) + .04 * Math.sin(t * 1.3) * settled - HEAD_REST_YAW - bend * .5;
    const pitchHead = T.MathUtils.clamp(plan.headPitch(t) - (up2 - REST2) * .8, -.9, .9);
    setEuler(bone.Neck, -pitchHead * .5, yawHead * .45, 0);
    setEuler(bone.Head, -pitchHead * .5, yawHead * .55, 0);

    // Cola: acompaña el tranco, se agita la punta al acechar y se mece despacio al final.
    const tail = plan.tail(t), twitch = plan.twitch(t), flick = (t - plan.t0) * TAU * 5, sway = t * 1.9;
    setEuler(bone.Tail1, -tail * .85 + .1 * Math.sin(stride + 1) * running, 0, .07 * Math.sin(sway) * settled);
    setEuler(bone.Tail2, -tail * .3 + .08 * Math.sin(stride + .2) * running, .15 * Math.sin(flick) * twitch, .09 * Math.sin(sway - .6) * settled);
    setEuler(bone.Tail3, -tail * .4, .35 * Math.sin(flick - .7) * twitch, .11 * Math.sin(sway - 1.2) * settled);
    setEuler(bone.Tail4, -tail * .45, .45 * Math.sin(flick - 1.4) * twitch, .13 * Math.sin(sway - 1.8) * settled);
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

  return {object, bone, setStage, update};
}
