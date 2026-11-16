"""Convierte el gato (FBX estático de varios millones de triángulos, sin esqueleto) en una malla liviana
con esqueleto y pesos para la bienvenida 3D.

    python3 scripts/exportar_gato.py <carpeta con el .fbx y sus .png> web/static/welcome

Pasos: suelda vértices, reduce la malla (scripts/simplificar_malla.mjs), arma UV nuevas y hornea ahí el
color original, alinea al gato (mira a +Z, parado en y=0, alto = rodilla del avatar) y calcula esqueleto
y pesos. Escribe gato.bin (mismo formato que avatar.bin) y gato-color.webp.

Necesita numpy, scipy, xatlas y Pillow, y node con el paquete meshoptimizer (npm i meshoptimizer).
"""
import sys, glob, json, struct, zlib, array, subprocess, tempfile, os
import numpy as np, xatlas
from PIL import Image
from scipy.spatial import cKDTree
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None

src, out = sys.argv[1], sys.argv[2]
TRIANGULOS = 12000
ALTO = .48                         # altura total: la rodilla del avatar
YAW, ESCALA, DX = -1.194, .30, .04  # el modelo viene en diagonal y corrido del eje

# ---- 1. Malla original ----
d = open(glob.glob(src + '/*.fbx')[0], 'rb').read()
def fbx_array(tag, after=0):
    o = d.index(bytes([len(tag)]) + tag, after) + 1 + len(tag)
    t = chr(d[o]); n, enc, size = struct.unpack_from('<III', d, o + 1)
    raw = d[o + 13:o + 13 + size]
    a = array.array({'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i'}[t]); a.frombytes(zlib.decompress(raw) if enc else raw)
    assert len(a) == n, tag
    return np.array(a), o + 13 + size
V, p = fbx_array(b'Vertices'); V = V.reshape(-1, 3)
pidx, p = fbx_array(b'PolygonVertexIndex', p)
UV, p = fbx_array(b'UV', d.index(b'LayerElementUV')); UV = UV.reshape(-1, 2)
uvidx, _ = fbx_array(b'UVIndex', p)
assert (pidx[2::3] < 0).all(), 'se esperaba una malla triangulada'
pidx = np.where(pidx < 0, -pidx - 1, pidx)
P = np.stack([V[:, 0], V[:, 2], -V[:, 1]], 1)            # a Y arriba
_, first = np.unique(pidx.astype(np.int64) * (len(UV) + 1) + uvidx, return_index=True)
hi_pos, hi_uv = P[pidx[first]].astype('<f4'), UV[uvidx[first]].astype('<f4')   # un vértice por (posición, uv)

# ---- 2. Reducción sobre la malla soldada (sin costuras de UV que la traben) ----
_, wfirst, winv = np.unique(np.round(P * 1e5).astype(np.int64), axis=0, return_index=True, return_inverse=True)
with tempfile.TemporaryDirectory() as tmp:
    P[wfirst].astype('<f4').tofile(tmp + '/pos.f32'); winv.reshape(-1)[pidx].astype('<u4').tofile(tmp + '/idx.u32')
    subprocess.run(['node', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'simplificar_malla.mjs'), tmp, str(TRIANGULOS)], check=True)
    low = np.fromfile(tmp + '/low_pos.f32', '<f4').reshape(-1, 3); tri = np.fromfile(tmp + '/low_idx.u32', '<u4').reshape(-1, 3)

# ---- 3. UV nuevas y color horneado desde la textura original ----
atlas = xatlas.Atlas(); atlas.add_mesh(low, tri)
chart = xatlas.ChartOptions(); chart.max_iterations = 2
pack = xatlas.PackOptions(); pack.resolution = 1024; pack.padding = 4; pack.bilinear = True
atlas.generate(chart, pack)
vmap, tri, uv = atlas[0]
pos = low[vmap].astype(np.float64)
W, H = atlas.width, atlas.height
where = np.zeros((H, W, 3), np.float32); mask = np.zeros((H, W), bool)
X, Y = uv[:, 0] * W, (1 - uv[:, 1]) * H
for t in tri:                                             # posición 3D de cada texel del atlas
    x, y = X[t], Y[t]
    x0, x1 = max(int(x.min()) - 1, 0), min(int(x.max()) + 1, W - 1); y0, y1 = max(int(y.min()) - 1, 0), min(int(y.max()) + 1, H - 1)
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + .5, np.arange(y0, y1 + 1) + .5)
    den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
    if abs(den) < 1e-12: continue
    w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
    w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
    w2 = 1 - w0 - w1
    e = -.6 / max(np.sqrt(abs(den)), 1)                   # medio texel de margen alrededor del triángulo
    m = (w0 >= e) & (w1 >= e) & (w2 >= e) & ~mask[y0:y1 + 1, x0:x1 + 1]
    if not m.any(): continue
    q = w0[..., None] * pos[t[0]] + w1[..., None] * pos[t[1]] + w2[..., None] * pos[t[2]]
    where[y0:y1 + 1, x0:x1 + 1][m] = q[m]; mask[y0:y1 + 1, x0:x1 + 1][m] = True
tex = np.asarray(Image.open(next(f for f in glob.glob(src + '/*.png') if f.endswith('texture.png'))).convert('RGB'))
th, tw = tex.shape[:2]
hi_col = tex[np.clip(((1 - hi_uv[:, 1]) * th).astype(int), 0, th - 1), np.clip((hi_uv[:, 0] * tw).astype(int), 0, tw - 1)].astype(np.float32)
dist, near = cKDTree(hi_pos).query(where[mask], k=4, workers=-1)
w = 1 / (dist + 1e-5)
color = np.zeros((H, W, 3), np.float32); color[mask] = (hi_col[near] * w[..., None]).sum(1) / w.sum(1, keepdims=True)
_, (iy, ix) = ndimage.distance_transform_edt(~mask, return_indices=True)   # rellena alrededor de cada isla
Image.fromarray(np.clip(color[iy, ix], 0, 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(out + '/gato-color.webp', quality=86, method=6)

# ---- 4. Alineación: mira a +Z, izquierda del gato = +X, parado en y=0 ----
cs, sn = np.cos(-YAW), np.sin(-YAW)
A = np.stack([pos[:, 0] * cs + pos[:, 2] * sn, pos[:, 1] - pos[:, 1].min(), -pos[:, 0] * sn + pos[:, 2] * cs], 1) * ESCALA
A[:, 0] += DX
assert abs(A[:, 1].max() - ALTO) < .01, A[:, 1].max()
tri = tri.astype(np.int64)
fn = np.cross(A[tri[:, 1]] - A[tri[:, 0]], A[tri[:, 2]] - A[tri[:, 0]])   # normales suaves por posición soldada
Nw = np.zeros((vmap.max() + 1, 3))
for c in range(3): np.add.at(Nw, vmap[tri[:, c]], fn)
N = Nw[vmap]; N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12

# ---- 5. Esqueleto (medido sobre la malla; la pose de reposo es el gato parado con la cabeza girada) ----
J = [  # nombre, padre, posición
    ('Hips', -1, (0, .255, -.13)), ('Spine', 0, (0, .265, -.01)), ('Chest', 1, (0, .255, .10)),
    ('Neck', 2, (.008, .31, .15)), ('Head', 3, (.035, .36, .18)),
    ('Tail1', 0, (-.008, .26, -.19)), ('Tail2', 5, (-.012, .31, -.255)), ('Tail3', 6, (-.016, .37, -.29)), ('Tail4', 7, (-.024, .425, -.285)),
    ('FLUp', 2, (.045, .215, .10)), ('FLLow', 9, (.043, .125, .096)), ('FLPaw', 10, (.04, .04, .078)),
    ('FRUp', 2, (-.035, .215, .135)), ('FRLow', 12, (-.036, .125, .126)), ('FRPaw', 13, (-.037, .04, .115)),
    ('HLUp', 0, (.065, .24, -.165)), ('HLLow', 15, (.065, .15, -.155)), ('HLPaw', 16, (.063, .06, -.185)),
    ('HRUp', 0, (-.055, .24, -.115)), ('HRLow', 18, (-.064, .15, -.065)), ('HRPaw', 19, (-.057, .06, -.115)),
]
B = {n: i for i, (n, _, _) in enumerate(J)}
jp = lambda n: np.array(J[B[n]][2], float)
# Cada hueso influye según la distancia a sus segmentos, medida en radios del hueso (cuerpo grueso, patas finas).
SEG = {
    'Hips': [((0, .245, -.18), (0, .26, -.07), .09)], 'Spine': [((0, .26, -.07), (0, .255, .04), .09)], 'Chest': [((0, .25, .04), (0, .255, .13), .09)],
    'Neck': [((.008, .30, .145), (.03, .345, .175), .06)],
    'Head': [((.035, .365, .185), (.085, .36, .225), .07), ((.0, .40, .16), (-.02, .46, .15), .045), ((.07, .40, .14), (.09, .46, .13), .045)],  # cráneo y orejas
    'Tail1': [(jp('Tail1'), jp('Tail2'), .045)], 'Tail2': [(jp('Tail2'), jp('Tail3'), .045)], 'Tail3': [(jp('Tail3'), jp('Tail4'), .045)], 'Tail4': [(jp('Tail4'), (-.03, .455, -.245), .045)],
}
for leg, toe in (('FL', (.045, .012, .10)), ('FR', (-.037, .012, .15)), ('HL', (.065, .012, -.16)), ('HR', (-.065, .012, -.085))):
    up, lo, paw = jp(leg + 'Up'), jp(leg + 'Low'), jp(leg + 'Paw')
    SEG[leg + 'Up'] = [(up + (lo - up) * .3, lo, .042)]; SEG[leg + 'Low'] = [(lo, paw, .034)]; SEG[leg + 'Paw'] = [(paw, toe, .034)]
def seg_dist(Q, a, b):
    a, b = np.array(a, float), np.array(b, float); ab = b - a
    t = np.clip(((Q - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(Q - (a + t[:, None] * ab), axis=1)
D = np.full((len(A), len(J)), 1e9)
for n, segs in SEG.items():
    for a, b, r in segs: D[:, B[n]] = np.minimum(D[:, B[n]], seg_dist(A, a, b) / r)
Wt = np.exp(-(D - D.min(1, keepdims=True)) / .16)
order = np.argsort(-Wt, axis=1)[:, :4]
w4 = np.take_along_axis(Wt, order, 1); w4[w4 < .03] = 0; w4 /= w4.sum(1, keepdims=True)
w8 = np.round(w4 * 255).astype(np.int32); w8[:, 0] += 255 - w8.sum(1)

assert len(A) < 65536
buffers, layout, off = [], {}, 0
for name, arr in (('position', A.astype('<f4')), ('normal', np.round(N * 127).astype('i1')), ('uv', uv.astype('<f4')),
                  ('skinIndex', order.astype('u1')), ('skinWeight', w8.astype('u1')), ('index', tri.reshape(-1).astype('<u2'))):
    raw = arr.tobytes(); raw += b'\0' * (-len(raw) % 4)
    layout[name] = [off, arr.size]; buffers.append(raw); off += len(raw)
head = json.dumps({'vertices': len(A), 'layout': layout, 'joints': [{'name': n, 'parent': p, 'pos': list(q)} for n, p, q in J]}).encode()
head += b' ' * (-len(head) % 4)
open(out + '/gato.bin', 'wb').write(struct.pack('<I', len(head)) + head + b''.join(buffers))
print('vértices', len(A), 'triángulos', len(tri), 'islas de UV', atlas.chart_count)
