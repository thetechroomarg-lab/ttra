"""Convierte un gato de Meshy (FBX estático de millones de triángulos, sin esqueleto) en una malla liviana
con esqueleto y pesos para la bienvenida 3D.

    python3 scripts/exportar_gato.py gato  <carpeta con el .fbx y sus .png> web/static/welcome
    python3 scripts/exportar_gato.py fendi <carpeta con el .fbx y sus .png> web/static/welcome

Pasos: suelda vértices, reduce la malla (scripts/simplificar_malla.mjs), arma UV nuevas y hornea ahí el
color original, alinea al gato (mira a +Z, parado en y=0) y calcula esqueleto y pesos.
Escribe <nombre>.bin (mismo formato que avatar.bin) y <nombre>-color.webp; si el gato tiene ojos
marcados, también <nombre>-dormida.webp, la misma textura con los ojos cerrados.

Necesita numpy, scipy, xatlas y Pillow, y node con el paquete meshoptimizer (npm i meshoptimizer).
"""
import sys, glob, json, struct, zlib, array, subprocess, tempfile, os
import numpy as np, xatlas
from PIL import Image
from scipy.spatial import cKDTree
from scipy import ndimage
Image.MAX_IMAGE_PIXELS = None

# Cada gato: cómo alinearlo y su esqueleto, medidos sobre su malla.
# Izquierda del gato = +X, mira a +Z. Las patas van de hombro/cadera a codo/rodilla, muñeca/garrón y dedos.
GATOS = {
    'gato': {  # blanco y naranja; alto = rodilla del avatar
        'yaw': -1.194, 'escala': .30, 'dx': .04, 'alto': .48,
        'joints': [
            ('Hips', -1, (0, .255, -.13)), ('Spine', 0, (0, .265, -.01)), ('Chest', 1, (0, .255, .10)),
            ('Neck', 2, (.008, .31, .15)), ('Head', 3, (.035, .36, .18)),
            ('Tail1', 0, (-.008, .26, -.19)), ('Tail2', 5, (-.012, .31, -.255)), ('Tail3', 6, (-.016, .37, -.29)), ('Tail4', 7, (-.024, .425, -.285)),
            ('FLUp', 2, (.045, .215, .10)), ('FLLow', 9, (.043, .125, .096)), ('FLPaw', 10, (.04, .04, .078)),
            ('FRUp', 2, (-.035, .215, .135)), ('FRLow', 12, (-.036, .125, .126)), ('FRPaw', 13, (-.037, .04, .115)),
            ('HLUp', 0, (.065, .24, -.165)), ('HLLow', 15, (.065, .15, -.155)), ('HLPaw', 16, (.063, .06, -.185)),
            ('HRUp', 0, (-.055, .24, -.115)), ('HRLow', 18, (-.064, .15, -.065)), ('HRPaw', 19, (-.057, .06, -.115)),
        ],
        'cuerpo': [((0, .245, -.18), (0, .26, -.07)), ((0, .26, -.07), (0, .255, .04)), ((0, .25, .04), (0, .255, .13)), .09],
        'cuello': ((.008, .30, .145), (.03, .345, .175), .06),
        'cabeza': [((.035, .365, .185), (.085, .36, .225), .07), ((.0, .40, .16), (-.02, .46, .15), .045), ((.07, .40, .14), (.09, .46, .13), .045)],
        'cola': ((-.03, .455, -.245), .045),
        'dedos': {'FL': (.045, .012, .10), 'FR': (-.037, .012, .15), 'HL': (.065, .012, -.16), 'HR': (-.065, .012, -.085)},
        'patas_r': (.042, .034),
    },
    'fendi': {  # carey de pelo largo; la cabeza viene girada 66° a su derecha y la cola colgando
        'yaw': .9983, 'alto': .46, 'dx': -.035,
        'joints': [
            ('Hips', -1, (0, .24, -.12)), ('Spine', 0, (0, .25, -.01)), ('Chest', 1, (0, .245, .10)),
            ('Neck', 2, (-.01, .29, .155)), ('Head', 3, (-.035, .35, .21)),
            ('Tail1', 0, (-.02, .30, -.205)), ('Tail2', 5, (-.03, .22, -.235)), ('Tail3', 6, (-.04, .14, -.24)), ('Tail4', 7, (-.05, .07, -.25)),
            ('FLUp', 2, (.045, .21, .13)), ('FLLow', 9, (.03, .12, .14)), ('FLPaw', 10, (.035, .04, .165)),
            ('FRUp', 2, (-.045, .21, .11)), ('FRLow', 12, (-.03, .12, .12)), ('FRPaw', 13, (-.04, .04, .13)),
            ('HLUp', 0, (.06, .23, -.16)), ('HLLow', 15, (.07, .13, -.105)), ('HLPaw', 16, (.06, .055, -.14)),
            ('HRUp', 0, (-.055, .23, -.14)), ('HRLow', 18, (-.06, .13, -.095)), ('HRPaw', 19, (-.055, .055, -.125)),
        ],
        'cuerpo': [((0, .24, -.21), (0, .25, -.07)), ((0, .25, -.07), (0, .25, .04)), ((0, .245, .04), (0, .25, .14)), .11],
        'cuello': ((-.01, .29, .155), (-.035, .35, .21), .065),
        'cabeza': [((-.04, .36, .215), (-.11, .335, .245), .065), ((-.05, .41, .262), (-.045, .46, .27), .035), ((-.08, .41, .195), (-.085, .46, .19), .035)],
        'cola': ((-.06, .0, -.26), .06),
        'dedos': {'FL': (.041, .01, .195), 'FR': (-.046, .01, .16), 'HL': (.058, .01, -.11), 'HR': (-.055, .01, -.09)},
        'patas_r': (.045, .036),
        # Ojos (izquierdo, derecho) y hacia dónde mira la cabeza en reposo: para pintar los ojos cerrados.
        'ojos': ((-.0809, .3684, .266), (-.1029, .3649, .2169)),
    },
}

nombre, src, out = sys.argv[1], sys.argv[2], sys.argv[3]
G = GATOS[nombre]
TRIANGULOS = 12000

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
color = color[iy, ix]
save = (lambda img, file: Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(f'{out}/{file}', quality=86, method=6))
save(color, f'{nombre}-color.webp')

# ---- 4. Alineación: mira a +Z, izquierda del gato = +X, parado en y=0 ----
y_min, y_rango = pos[:, 1].min(), np.ptp(pos[:, 1])
escala = G.get('escala') or G['alto'] / y_rango
cs, sn = np.cos(-G['yaw']), np.sin(-G['yaw'])
def alinear(Q):
    Q = Q.reshape(-1, 3).astype(np.float64)
    R = np.stack([Q[:, 0] * cs + Q[:, 2] * sn, Q[:, 1] - y_min, -Q[:, 0] * sn + Q[:, 2] * cs], 1) * escala
    R[:, 0] += G['dx']
    return R
A = alinear(pos)
assert abs(A[:, 1].max() - G['alto']) < .01, A[:, 1].max()

# ---- 5. Ojos cerrados: se pinta párpado (pelo de alrededor) y la línea del ojo cerrado ----
if 'ojos' in G:
    L, R = (np.array(o) for o in G['ojos'])
    u = (L - R) / np.linalg.norm(L - R)                    # a lo ancho de la cara
    f = np.cross(u, (0, 1, 0)); f /= np.linalg.norm(f)     # hacia adonde mira
    v = np.cross(f, u)                                     # hacia arriba de la cara
    P3 = alinear(where).reshape(H, W, 3)
    dormida = color.copy()
    for c in (L, R):
        rel = P3 - c
        a, b, h = rel @ u, rel @ v, rel @ f
        RX, RY = .0125, .0095
        r = np.sqrt((a / RX) ** 2 + (b / RY) ** 2) + 9 * (np.abs(h) > .014)
        ring = (r > 1.25) & (r < 1.8)
        fur = np.median(color[ring], axis=0)
        cover = np.clip((1.15 - r) / .25, 0, 1)[..., None]            # párpado con borde suave
        lid = fur * (.88 + .12 * np.clip(b / RY, -1, 1))[..., None]   # un poco más oscuro abajo, como sombra
        dormida = dormida * (1 - cover) + lid * cover
        line = np.exp(-((b - (-.0016 + .0042 * (a / RX) ** 2)) / .0009) ** 2) * (np.abs(a) < RX * .95) * cover[..., 0]
        dormida = dormida * (1 - .85 * line[..., None]) + np.array([22, 16, 13]) * .85 * line[..., None]
    save(dormida, f'{nombre}-dormida.webp')

tri = tri.astype(np.int64)
fn = np.cross(A[tri[:, 1]] - A[tri[:, 0]], A[tri[:, 2]] - A[tri[:, 0]])   # normales suaves por posición soldada
Nw = np.zeros((vmap.max() + 1, 3))
for c in range(3): np.add.at(Nw, vmap[tri[:, c]], fn)
N = Nw[vmap]; N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12

# ---- 6. Esqueleto y pesos: cada hueso influye según la distancia a sus segmentos, en radios del hueso ----
J = G['joints']
B = {n: i for i, (n, _, _) in enumerate(J)}
jp = lambda n: np.array(J[B[n]][2], float)
*tramos, r_cuerpo = G['cuerpo']
cola_fin, r_cola = G['cola']
SEG = {
    'Hips': [(*tramos[0], r_cuerpo)], 'Spine': [(*tramos[1], r_cuerpo)], 'Chest': [(*tramos[2], r_cuerpo)],
    'Neck': [G['cuello']], 'Head': G['cabeza'],
    'Tail1': [(jp('Tail1'), jp('Tail2'), r_cola)], 'Tail2': [(jp('Tail2'), jp('Tail3'), r_cola)], 'Tail3': [(jp('Tail3'), jp('Tail4'), r_cola)], 'Tail4': [(jp('Tail4'), cola_fin, r_cola)],
}
r_muslo, r_pata = G['patas_r']
for leg, toe in G['dedos'].items():
    up, lo, paw = jp(leg + 'Up'), jp(leg + 'Low'), jp(leg + 'Paw')
    SEG[leg + 'Up'] = [(up + (lo - up) * .3, lo, r_muslo)]; SEG[leg + 'Low'] = [(lo, paw, r_pata)]; SEG[leg + 'Paw'] = [(paw, toe, r_pata)]
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
open(f'{out}/{nombre}.bin', 'wb').write(struct.pack('<I', len(head)) + head + b''.join(buffers))
print(nombre, 'vértices', len(A), 'triángulos', len(tri), 'islas de UV', atlas.chart_count)
