// Reduce una malla soldada a la cantidad de triángulos pedida (lo usa scripts/exportar_gato.py).
//   node scripts/simplificar_malla.mjs <carpeta con pos.f32 e idx.u32> <triángulos>
// Escribe low_pos.f32 y low_idx.u32 en la misma carpeta. Necesita: npm i meshoptimizer
import {MeshoptSimplifier as S} from 'meshoptimizer';
import fs from 'node:fs';

const [dir, target] = process.argv.slice(2);
await S.ready;
const read = (file, Type) => { const b = fs.readFileSync(`${dir}/${file}`); return new Type(b.buffer, b.byteOffset, b.byteLength / Type.BYTES_PER_ELEMENT); };
const pos = read('pos.f32', Float32Array), idx = read('idx.u32', Uint32Array);
const [out, error] = S.simplify(idx, pos, 3, target * 3, .03, ['Prune']);
const [remap, count] = S.compactMesh(out);
const low = new Float32Array(count * 3);
for (let i = 0; i < remap.length; i++) if (remap[i] !== 0xffffffff) low.set(pos.subarray(i * 3, i * 3 + 3), remap[i] * 3);
fs.writeFileSync(`${dir}/low_pos.f32`, Buffer.from(low.buffer));
fs.writeFileSync(`${dir}/low_idx.u32`, Buffer.from(out.buffer, out.byteOffset, out.byteLength));
console.log(`${idx.length / 3} → ${out.length / 3} triángulos, ${count} vértices, error ${error.toFixed(4)}`);
