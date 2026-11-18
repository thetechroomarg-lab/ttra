// Personaje de la bienvenida: malla real del avatar con esqueleto (scripts/exportar_avatar.py),
// animada en tiempo real con pasos plantados e IK de dos huesos. Sin clips pregrabados.
import * as T from './vendor/three/three.module.min.js';

const clamp01 = v => Math.min(1, Math.max(0, v));
const smooth = v => { v = clamp01(v); return v * v * (3 - 2 * v); };
const lerp = (a, b, t) => a + (b - a) * t;
const V = (x = 0, y = 0, z = 0) => new T.Vector3(x, y, z);
const UP = V(0, 1, 0), X = V(1, 0, 0), Z = V(0, 0, 1);

const STEP = .56, STEP_TIME = .52, HIP_Y = .95, ANKLE_Y = .09;

// Malla con esqueleto en el formato de scripts/exportar_avatar.py: cabecera JSON + buffers.
export function readRig(buf) {
  const headLength = new DataView(buf).getUint32(0, true);
  const head = JSON.parse(new TextDecoder().decode(new Uint8Array(buf, 4, headLength)));
  const view = (name, Type) => new Type(buf, 4 + headLength + head.layout[name][0], head.layout[name][1]);
  const geometry = new T.BufferGeometry();
  geometry.setAttribute('position', new T.BufferAttribute(view('position', Float32Array), 3));
  geometry.setAttribute('normal', new T.BufferAttribute(view('normal', Int8Array), 3, true));
  geometry.setAttribute('uv', new T.BufferAttribute(view('uv', Float32Array), 2));
  geometry.setAttribute('skinIndex', new T.BufferAttribute(new Uint16Array(view('skinIndex', Uint8Array)), 4));
  geometry.setAttribute('skinWeight', new T.BufferAttribute(view('skinWeight', Uint8Array), 4, true));
  geometry.setIndex(new T.BufferAttribute(view('index', head.index32 ? Uint32Array : Uint16Array), 1)); // las mallas HD pasan los 65.535 vértices
  return {geometry, joints: head.joints};
}
export function buildRig(geometry, joints, material) {
  const bone = {}, rest = {};
  const bones = joints.map(j => {
    const b = new T.Bone(); b.name = j.name; bone[j.name] = b; rest[j.name] = V(...j.pos);
    if (j.parent < 0) b.position.copy(rest[j.name]);
    else { const parent = joints[j.parent]; b.position.copy(rest[j.name]).sub(rest[parent.name]); bone[parent.name].add(b); }
    return b;
  });
  const object = new T.Group(); object.add(bones[0]); object.updateMatrixWorld(true);
  const mesh = new T.SkinnedMesh(geometry, material);
  mesh.castShadow = true; mesh.receiveShadow = true; mesh.frustumCulled = false;
  object.add(mesh); mesh.bind(new T.Skeleton(bones));
  return {object, mesh, bone, rest};
}

// ---------- IK de dos huesos con vector polo (codo / rodilla) ----------
const tmp = {a: V(), to: V(), dir: V(), perp: V(), d1: V(), d2: V(), q: new T.Quaternion(), qi: new T.Quaternion()};
export function solve(upper, lower, end, parentQ, target, pole, soft = 0) {
  const {a, to, dir, perp, d1, d2, q, qi} = tmp;
  a.setFromMatrixPosition(upper.matrixWorld);
  const l1 = lower.position.length(), l2 = end.position.length();
  to.subVectors(target, a);
  let reach = to.length();
  // Extensión suave: cerca del largo total la pierna frena de a poco en vez de trabarse recta de golpe.
  const full = (l1 + l2) * .999, knee = full * (1 - soft);
  if (soft && reach > knee) reach = knee + (full - knee) * (1 - Math.exp(-(reach - knee) / (full - knee)));
  const dist = T.MathUtils.clamp(reach, Math.abs(l1 - l2) + .01, full);
  dir.copy(to).normalize();
  const angle = Math.acos(T.MathUtils.clamp((l1 * l1 + dist * dist - l2 * l2) / (2 * l1 * dist), -1, 1));
  perp.copy(pole).addScaledVector(dir, -pole.dot(dir)).normalize();
  d1.copy(dir).multiplyScalar(Math.cos(angle)).addScaledVector(perp, Math.sin(angle));
  d2.copy(dir).multiplyScalar(dist).addScaledVector(d1, -l1).normalize();
  upper.quaternion.setFromUnitVectors(lower.position.clone().normalize(), d1.clone().applyQuaternion(qi.copy(parentQ).invert()));
  q.copy(parentQ).multiply(upper.quaternion);
  lower.quaternion.setFromUnitVectors(end.position.clone().normalize(), d2.applyQuaternion(qi.copy(q).invert()));
  return q.multiply(lower.quaternion).clone(); // orientación global del hueso inferior
}

export async function loadCharacter(base = '/welcome/', {hd = false} = {}) {
  const loader = new T.TextureLoader(), file = hd ? 'avatar-hd.bin' : 'avatar.bin'; // HD: misma malla subdividida y curvada
  const [buf, map, normalMap, roughnessMap] = await Promise.all([
    fetch(base + file).then(r => { if (!r.ok) throw new Error(file + ' ' + r.status); return r.arrayBuffer(); }),
    loader.loadAsync(base + 'avatar-color.webp'), loader.loadAsync(base + 'avatar-normal.webp'), loader.loadAsync(base + 'avatar-roughness.webp'),
  ]);
  const {geometry, joints} = readRig(buf);
  map.colorSpace = T.SRGBColorSpace; map.anisotropy = 16;
  // HD: piel y ropa con un velo suave a contraluz (sheen) en vez del brillo plástico parejo.
  const material = hd
    ? new T.MeshPhysicalMaterial({map, normalMap, roughnessMap, roughness: 1, metalness: 0, envMapIntensity: .7,
        sheen: .35, sheenRoughness: .6, sheenColor: new T.Color(0x6e5a50), specularIntensity: .55})
    : new T.MeshStandardMaterial({map, normalMap, roughnessMap, roughness: 1, metalness: 0, envMapIntensity: .7});

  // Sonrisa: la malla no trae expresiones, así que se arma un morph que sube y abre las comisuras
  // y levanta apenas las mejillas (la textura de la cara acompaña a los vértices).
  const P = geometry.attributes.position, smileDelta = new Float32Array(P.count * 3);
  const gauss = (dx, dy, sigma) => Math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma));
  for (let i = 0; i < P.count; i++) {
    const x = P.getX(i), y = P.getY(i), z = P.getZ(i);
    if (z < .015 || y < 1.47 || y > 1.63 || Math.abs(x) > .09) continue;
    const side = Math.sign(x) || 1, ax = Math.abs(x);
    const corner = gauss(ax - .031, y - 1.527, .015), cheek = gauss(ax - .046, y - 1.565, .022), lip = gauss(x, y - 1.522, .012);
    smileDelta[i * 3] = side * (.006 * corner + .0015 * cheek);
    smileDelta[i * 3 + 1] = .0115 * corner + .004 * cheek - .002 * lip;
    smileDelta[i * 3 + 2] = -.002 * corner + .002 * cheek;
  }
  geometry.morphAttributes.position = [new T.BufferAttribute(smileDelta, 3)];
  geometry.morphTargetsRelative = true;

  const {object, mesh, bone} = buildRig(geometry, joints, material);
  mesh.updateMorphTargets();
  const setSmile = v => { mesh.morphTargetInfluences[0] = v; };

  // ---------- Coreografía: se arma una vez que la escena dice dónde está el logo ----------
  // Cada paso ocupa un período; el pie vuela del 10% al 90% y el resto es apoyo doble.
  // La cadera sigue su propia trayectoria continua (no el promedio de los pies), así avanza
  // a velocidad pareja y se balancea sobre el pie de apoyo.
  let plan = null;
  function setStage({corner, wrist, arriveAt}) {
    const yawEnd = .2, yawWalk = Math.PI / 2;
    const center = V(corner.x - .45, 0, corner.z + .06);
    const leftOf = yaw => V(Math.cos(yaw), 0, -Math.sin(yaw));
    const count = 12;
    const walkZ = side => center.z - side * .085; // caminando hacia +X, la izquierda del personaje es -Z
    const plantOf = i => {
      const side = (count - i) % 2 === 0 ? 1 : -1; // el anteúltimo paso es del pie izquierdo (+1), el último del derecho
      if (i === count - 2) return {side, pos: center.clone().addScaledVector(leftOf(yawEnd), .115), yaw: yawEnd + .12};
      if (i === count - 1) return {side, pos: center.clone().addScaledVector(leftOf(yawEnd), -.115).add(V(0, 0, .03)), yaw: yawEnd - .1};
      // Los últimos pasos se acortan: frena antes de girar hacia el logo.
      const back = count - 3 - i, shorten = back === 0 ? .14 : back === 1 ? .06 : 0;
      return {side, pos: V(center.x - .32 - back * STEP + shorten, 0, walkZ(side)), yaw: yawWalk};
    };
    const period = i => STEP_TIME * (i >= count - 2 ? 1.2 : i >= count - 4 ? 1.08 : 1);
    let t = arriveAt; for (let i = 0; i < count; i++) t -= period(i);
    const last = {}, steps = [], starts = [];
    for (const i of [0, 1]) { const plant = plantOf(i); last[plant.side] = {pos: plant.pos.clone().add(V(-2 * STEP, 0, 0)), yaw: yawWalk}; }
    for (let i = 0; i < count; i++) {
      const plant = plantOf(i), P = period(i);
      steps.push({side: plant.side, from: last[plant.side], to: plant, stance: last[-plant.side], T: t, P, t0: t + .1 * P, t1: t + .9 * P});
      starts.push(t); last[plant.side] = plant; t += P;
    }
    starts.push(t);
    // Claves de la cadera: a mitad del vuelo está sobre el pie de apoyo, algo cargada hacia él.
    const keys = steps.map(s => {
      const mid = s.from.pos.clone().add(s.to.pos).multiplyScalar(.5).add(s.stance.pos).multiplyScalar(.5);
      return {t: (s.t0 + s.t1) / 2, p: mid.lerp(s.stance.pos, .28)};
    });
    keys.push({t: arriveAt + .12, p: center.clone()});
    plan = {steps, starts, keys, yawEnd, yawWalk, arriveAt, turnFrom: steps[count - 2].T, wrist: wrist.clone(), leftOf};
  }

  function hipsLinear(t, out) {
    const k = plan.keys;
    let i = 0; while (i < k.length - 2 && t > k[i + 1].t) i++;
    const u = (t - k[i].t) / (k[i + 1].t - k[i].t);
    return out.copy(k[i].p).lerp(k[i + 1].p, t > k[k.length - 1].t ? 1 : u); // antes de la primera clave extrapola; después de la última se queda
  }
  const hipsTmp = V();
  function hipsAt(t, out) { // promedio móvil: quita los quiebres entre tramos
    out.set(0, 0, 0);
    for (const dt of [-.1, -.05, 0, .05, .1]) out.add(hipsLinear(t + dt, hipsTmp));
    return out.multiplyScalar(.2);
  }

  const reachOf = s => Math.min(1, s.from.pos.distanceTo(s.to.pos) / (2 * STEP));
  // El pie rota sobre la punta al despegar: el tobillo sube y avanza.
  function withPitch(base, yaw, heelOff, pitch, lift) {
    const fwd = .13 - .13 * Math.cos(heelOff) + .09 * Math.sin(heelOff), up = .13 * Math.sin(heelOff) + .09 * Math.cos(heelOff) - .09;
    return {pos: base.clone().add(V(Math.sin(yaw) * fwd, 0, Math.cos(yaw) * fwd)), yaw, pitch, lift: lift + up};
  }
  function footAt(side, t) {
    const list = plan.steps.filter(s => s.side === side);
    for (let k = 0; k < list.length; k++) {
      const s = list[k], prev = list[k - 1];
      if (t < s.t0) { // apoyado: aplana tras el taloneo y despega el talón antes de volar
        const strike = prev ? (1 - smooth((t - prev.t1) / (.26 * prev.P))) * reachOf(prev) : 0;
        const heelOff = .7 * reachOf(s) * smooth((t - (s.t0 - .42 * s.P)) / (.42 * s.P));
        return withPitch(s.from.pos, s.from.yaw, heelOff, heelOff - .22 * strike, 0);
      }
      if (t < s.t1) {
        const w = (t - s.t0) / (s.t1 - s.t0), reach = reachOf(s);
        // El pie sale con el talón arriba (rodilla flexionada), acelera y frena de forma pareja y llega de talón.
        const heelOff = reach * (.7 + .12 * smooth(w / .15)) * (1 - smooth((w - .12) / .5));
        const pos = s.from.pos.clone().lerp(s.to.pos, .5 - .5 * Math.cos(Math.PI * w));
        return withPitch(pos, lerp(s.from.yaw, s.to.yaw, smooth(w)), heelOff, heelOff - .22 * reach * smooth((w - .55) / .45), lerp(.03, .065, reach) * Math.sin(Math.PI * w ** .85) ** 1.2);
      }
    }
    const end = list[list.length - 1];
    return withPitch(end.to.pos, end.to.yaw, 0, -.22 * (1 - smooth((t - end.t1) / (.26 * end.P))) * reachOf(end), 0);
  }
  // Fase continua de la marcha: +1 con el pie derecho adelante, -1 con el izquierdo.
  function gaitAt(t) {
    const {starts, steps} = plan;
    if (t < starts[0] || t >= starts[starts.length - 1]) return {swing: 0, frac: 0, side: 0};
    let i = 0; while (t >= starts[i + 1]) i++;
    const frac = (t - starts[i]) / (starts[i + 1] - starts[i]);
    return {swing: steps[i].side * Math.cos(Math.PI * frac), frac, side: steps[i].side};
  }

  const q = {hips: new T.Quaternion(), chest: new T.Quaternion(), a: new T.Quaternion(), b: new T.Quaternion(), yaw: new T.Quaternion()};
  const e3 = new T.Euler();
  const setEuler = (b, x, y, z) => b.quaternion.setFromEuler(e3.set(x, y, z, 'YXZ'));

  function update(t, times, camera) {
    if (!plan) return;
    const {yawEnd, yawWalk, arriveAt, wrist, leftOf} = plan;
    const fL = footAt(1, t), fR = footAt(-1, t);
    const walking = 1 - smooth((t - arriveAt + .35) / .55);
    const gait = gaitAt(t);
    const swing = gait.swing * walking, armSwing = gaitAt(t - .09).swing * walking; // los brazos llegan un instante después
    const stride = Math.sin(Math.PI * gait.frac) * walking;
    const lean = smooth((t - times.lean) / 1.1);
    const yaw = lerp(yawWalk, yawEnd, smooth((t - plan.turnFrom) / (arriveAt - plan.turnFrom)));
    const forward = V(Math.sin(yaw), 0, Math.cos(yaw));

    // Cadera: trayectoria continua, sube en el apoyo simple y baja en el doble; se recuesta hacia el logo al final.
    hipsAt(t, bone.Hips.position).addScaledVector(forward, .02 * walking).addScaledVector(leftOf(yawEnd), .055 * lean);
    bone.Hips.position.y = HIP_Y - lerp(.014, .062, walking) + .026 * (.5 - .5 * Math.cos(2 * Math.PI * gait.frac)) * walking - .008 * lean;
    // La pelvis acompaña a la pierna que avanza y cae un poco del lado del pie en el aire; el torso compensa.
    // Saludo: el antebrazo va y viene de lado a lado desde el codo; la mano llega un instante después.
    const wave = smooth((t - times.wave) / .6) * (1 - smooth((t - times.waveEnd) / .65));
    const waveEnv = smooth((t - times.wave - .3) / .4) * (1 - smooth((t - times.waveEnd + .3) / .4));
    const wavePhase = (t - times.wave - .3) * Math.PI * 2 * 1.55;
    const sway = Math.sin(wavePhase) * waveEnv, swayLate = Math.sin(wavePhase - .6) * waveEnv;
    setEuler(bone.Hips, .035 * walking, yaw + swing * .1, -gait.side * .04 * stride - .04 * lean);
    setEuler(bone.Spine, .025 * walking, -swing * .09, gait.side * .028 * stride - .09 * lean + .012 * sway * wave);
    setEuler(bone.Chest, .015 * walking + .012 * Math.cos(4 * Math.PI * gait.frac) * walking, -armSwing * .11, gait.side * .014 * stride - .07 * lean + .016 * sway * wave - .02 * wave);
    const steady = (swing * .01 + armSwing * .1) * .8; // la cabeza no gira con los hombros
    // La cabeza mira al frente al caminar y gira hacia la cámara al saludar.
    const look = smooth((t - times.look) / .6);
    setSmile(smooth((t - times.look - .25) / .8)); // sonríe al mirar a cámara y la mantiene hasta el fundido
    const toCamera = Math.atan2(camera.position.x - bone.Hips.position.x, camera.position.z - bone.Hips.position.z);
    const headYaw = T.MathUtils.clamp(toCamera - yaw, -.9, .9) * look;
    const nod = Math.sin((t - times.wave) * 4) * .018 * wave;
    setEuler(bone.Neck, .02 * look + nod - .02 * walking, headYaw * .4 + steady * .5, .07 * lean);
    setEuler(bone.Head, -.03 * look + nod - .02 * walking, headYaw * .6 + steady * .5, .07 * lean);
    object.updateMatrixWorld(true);
    q.hips.copy(bone.Hips.quaternion);
    q.chest.copy(q.hips).multiply(bone.Spine.quaternion).multiply(bone.Chest.quaternion);
    q.yaw.setFromAxisAngle(UP, yaw);

    // Piernas: tobillo al punto plantado (por eso el pie no patina) y rodilla hacia adelante.
    for (const [side, f, up, low, foot] of [[1, fL, bone.LUpLeg, bone.LLeg, bone.LFoot], [-1, fR, bone.RUpLeg, bone.RLeg, bone.RFoot]]) {
      const target = f.pos.clone(); target.y = ANKLE_Y + f.lift;
      const shin = solve(up, low, foot, q.hips, target, V(Math.sin(f.yaw), 0, Math.cos(f.yaw)), .05);
      q.a.setFromAxisAngle(UP, f.yaw).multiply(q.b.setFromAxisAngle(X, f.pitch));
      foot.quaternion.copy(shin.invert()).multiply(q.a);
    }

    // Brazos: péndulo opuesto a las piernas; el izquierdo termina apoyado sobre el logo y el derecho saluda.
    const shoulder = V(), target = V(), pole = V();
    // El brazo cuelga y se flexiona más cuando va hacia adelante que cuando va hacia atrás.
    const hang = (side, angle, out) => target.set(side * out, -Math.cos(angle), Math.sin(angle)).normalize().multiplyScalar(.437 - walking * (.014 + .05 * Math.max(0, angle))).applyQuaternion(q.yaw).add(shoulder);
    // Izquierdo
    shoulder.setFromMatrixPosition(bone.LArm.matrixWorld);
    hang(1, armSwing * .33 + .06, .07);
    target.lerp(wrist, lean).y += .13 * Math.sin(Math.PI * lean);
    pole.set(lerp(.25, 1, lean), lerp(0, .25, lean), lerp(-1, -.2, lean)).applyQuaternion(q.yaw); // apoyado: el codo sale hacia el logo
    solve(bone.LArm, bone.LFore, bone.LHand, q.chest, target, pole);
    setEuler(bone.LHand, .25 * lean, 0, 0);
    // Derecho
    shoulder.setFromMatrixPosition(bone.RArm.matrixWorld);
    hang(-1, -armSwing * .33 + .06, .07);
    // Codo quieto a la altura del pecho y abierto hacia afuera; la muñeca describe un arco alrededor de él.
    const tilt = .1 + .52 * sway;
    const waveTarget = V(-.17 - .2 * Math.sin(tilt), -.13 + .2 * Math.cos(tilt), .14).applyQuaternion(q.yaw).add(shoulder);
    target.lerp(waveTarget, wave).y += .05 * Math.sin(Math.PI * wave);
    pole.set(lerp(-.25, -.6, wave), lerp(0, -1, wave), lerp(-1, .1, wave)).applyQuaternion(q.yaw);
    solve(bone.RArm, bone.RFore, bone.RHand, q.chest, target, pole);
    setEuler(bone.RHand, 0, 0, -.42 * swayLate * wave);
  }

  return {object, bone, setStage, setSmile, update};
}
