"""Suaviza una malla con esqueleto de la bienvenida (formato de avatar.bin / gato.bin) para la versión HD.

    python3 scripts/suavizar_malla.py web/static/welcome/avatar.bin web/static/welcome/avatar-hd.bin

Para cuando no está el modelo original: subdivide cada triángulo en cuatro y curva los vértices nuevos
según las normales (teselado de Phong), así la silueta queda redonda en vez de facetada. Los vértices
originales no se mueven, el esqueleto es el mismo y los pesos de los vértices nuevos salen de los de su
arista, así la animación no cambia. Las UV siguen siendo las mismas, así que valen las mismas texturas.
Necesita numpy.
"""
import sys, json, struct
import os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from normales_seguras import normales_seguras

ALFA = .75  # cuánto se curva cada vértice nuevo hacia las normales (0 = plano, 1 = Phong pleno)

src, out = sys.argv[1], sys.argv[2]
b = open(src, 'rb').read()
hl = struct.unpack_from('<I', b)[0]; head = json.loads(b[4:4 + hl]); base = 4 + hl
get = lambda n, dt: np.frombuffer(b, dt, head['layout'][n][1], base + head['layout'][n][0])
pos = get('position', '<f4').reshape(-1, 3).astype(np.float64)
uv = get('uv', '<f4').reshape(-1, 2).astype(np.float64)
sidx = get('skinIndex', 'u1').reshape(-1, 4).astype(np.int64)
swt = get('skinWeight', 'u1').reshape(-1, 4).astype(np.float64) / 255
tri = get('index', '<u4' if head.get('index32') else '<u2').reshape(-1, 3).astype(np.int64)
n, J = len(pos), len(head['joints'])

# Normales suaves por posición (soldando las costuras de UV): los dos lados de una costura curvan igual.
_, weld = np.unique(np.round(pos * 1e6).astype(np.int64), axis=0, return_inverse=True)
weld = weld.reshape(-1)
fn = np.cross(pos[tri[:, 1]] - pos[tri[:, 0]], pos[tri[:, 2]] - pos[tri[:, 0]])
Nw = np.zeros((weld.max() + 1, 3))
for c in range(3): np.add.at(Nw, weld[tri[:, c]], fn)
Nw /= np.linalg.norm(Nw, axis=1, keepdims=True) + 1e-12

# Un vértice nuevo por arista (por par de vértices, así cada lado de una costura conserva su UV).
edges = np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]])
key = np.sort(edges, 1)
uniq, inv = np.unique(key[:, 0] * n + key[:, 1], return_inverse=True)
a, c = uniq // n, uniq % n
pa, pc, na, nc = pos[a], pos[c], Nw[weld[a]], Nw[weld[c]]
m = (pa + pc) / 2
proj = lambda q, p, nn: q - ((q - p) * nn).sum(1, keepdims=True) * nn
mid = (1 - ALFA) * m + ALFA * (proj(m, pa, na) + proj(m, pc, nc)) / 2

# Pesos de los vértices nuevos: mezcla de los dos extremos, quedan los cuatro huesos más pesados.
Wd = np.zeros((len(uniq), J))
for k in range(4):
    np.add.at(Wd, (np.arange(len(uniq)), sidx[a, k]), swt[a, k] / 2)
    np.add.at(Wd, (np.arange(len(uniq)), sidx[c, k]), swt[c, k] / 2)
order = np.argsort(-Wd, 1)[:, :4]; w4 = np.take_along_axis(Wd, order, 1); w4 /= w4.sum(1, keepdims=True)

P2 = np.concatenate([pos, mid]); UV2 = np.concatenate([uv, (uv[a] + uv[c]) / 2])
SI = np.concatenate([sidx, order]); SW = np.concatenate([swt, w4])
e = inv.reshape(3, -1) + n                                   # vértice nuevo de cada arista de cada triángulo
t0, t1, t2 = tri.T; m01, m12, m20 = e
T2 = np.concatenate([np.stack([t0, m01, m20], 1), np.stack([m01, t1, m12], 1), np.stack([m20, m12, t2], 1), np.stack([m01, m12, m20], 1)])

# Normales finales suaves por posición.
_, weld2 = np.unique(np.round(P2 * 1e6).astype(np.int64), axis=0, return_inverse=True)
weld2 = weld2.reshape(-1)
fn = np.cross(P2[T2[:, 1]] - P2[T2[:, 0]], P2[T2[:, 2]] - P2[T2[:, 0]])
N2 = np.zeros((weld2.max() + 1, 3))
for k in range(3): np.add.at(N2, weld2[T2[:, k]], fn)
N2 = normales_seguras(P2, T2, N2[weld2])

w8 = np.round(SW * 255).astype(np.int32); w8[:, 0] += 255 - w8.sum(1)
big = len(P2) >= 65536
buffers, layout, off = [], {}, 0
for name, arr in (('position', P2.astype('<f4')), ('normal', np.round(N2 * 127).astype('i1')), ('uv', UV2.astype('<f4')),
                  ('skinIndex', SI.astype('u1')), ('skinWeight', w8.astype('u1')), ('index', T2.reshape(-1).astype('<u4' if big else '<u2'))):
    raw = arr.tobytes(); raw += b'\0' * (-len(raw) % 4)
    layout[name] = [off, arr.size]; buffers.append(raw); off += len(raw)
h2 = json.dumps({'vertices': len(P2), 'index32': big, 'layout': layout, 'joints': head['joints']}).encode()
h2 += b' ' * (-len(h2) % 4)
open(out, 'wb').write(struct.pack('<I', len(h2)) + h2 + b''.join(buffers))
print(src, '→', out, f'{len(tri)} → {len(T2)} triángulos, {n} → {len(P2)} vértices,',
      'desplazamiento máx. de los nuevos', f'{np.linalg.norm(mid - m, axis=1).max() * 1000:.1f} mm')
