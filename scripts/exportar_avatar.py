"""Convierte el avatar (FBX estático en T-pose, sin esqueleto) en una malla con esqueleto y pesos
para la bienvenida 3D.

    python3 scripts/exportar_avatar.py <carpeta con el .fbx y sus .png> web/static/welcome              # malla (numpy)
    .venv/bin/python scripts/exportar_avatar.py <carpeta> web/static/welcome --texturas                  # texturas (Pillow)

Escribe avatar.bin (cabecera JSON + buffers) y las texturas .webp.
El esqueleto y los pesos se calculan acá a partir de las proporciones de la malla.
"""
import sys, glob, json, struct, zlib, array

def parse_fbx(path):
    d = open(path, 'rb').read()
    big = struct.unpack_from('<I', d, 23)[0] >= 7500
    def node(o):
        if big: end, n, _ = struct.unpack_from('<QQQ', d, o); o += 24
        else: end, n, _ = struct.unpack_from('<III', d, o); o += 12
        nl = d[o]; o += 1
        if end == 0: return None, o
        name = d[o:o+nl].decode('latin1'); o += nl
        props = []
        for _ in range(n):
            t = chr(d[o]); o += 1
            if t in 'YCIFDL':
                f, sz = {'Y': ('<h', 2), 'C': ('<b', 1), 'I': ('<i', 4), 'F': ('<f', 4), 'D': ('<d', 8), 'L': ('<q', 8)}[t]
                props.append(struct.unpack_from(f, d, o)[0]); o += sz
            elif t in 'fdlib':
                _, enc, cl = struct.unpack_from('<III', d, o); o += 12
                raw = d[o:o+cl]; o += cl
                a = array.array({'f': 'f', 'd': 'd', 'l': 'q', 'i': 'i', 'b': 'b'}[t]); a.frombytes(zlib.decompress(raw) if enc else raw); props.append(a)
            else:
                ln = struct.unpack_from('<I', d, o)[0]; o += 4
                props.append(d[o:o+ln]); o += ln
        kids = []
        while o < end:
            k, o2 = node(o)
            if k is None: break
            kids.append(k); o = o2
        return (name, props, kids), end
    o, top = 27, []
    while o < len(d) - 25:
        k, o = node(o)
        if k is None: break
        top.append(k)
    return top
child = lambda n, name: next(k for k in n[2] if k[0] == name)

src, out = sys.argv[1], sys.argv[2]
if '--texturas' in sys.argv:
    from PIL import Image
    tex = lambda suffix: Image.open(next(f for f in glob.glob(src + '/*.png') if f.endswith(suffix)))
    tex('tri.png').convert('RGB').save(out + '/avatar-color.webp', quality=88, method=6)
    tex('_normal.png').convert('RGB').resize((1024, 1024), Image.LANCZOS).save(out + '/avatar-normal.webp', quality=92, method=6)
    tex('_roughness.png').convert('L').resize((512, 512), Image.LANCZOS).convert('RGB').save(out + '/avatar-roughness.webp', quality=85, method=6)
    sys.exit()
import numpy as np
top = parse_fbx(glob.glob(src + '/*.fbx')[0])
geo = child(next(n for n in top if n[0] == 'Objects'), 'Geometry')
V = np.array(child(geo, 'Vertices')[1][0]).reshape(-1, 3)
P = np.stack([V[:, 0], V[:, 2], -V[:, 1]], 1)            # a Y arriba, mirando a +Z
pidx = np.array(child(geo, 'PolygonVertexIndex')[1][0])
assert (pidx[2::3] < 0).all(), 'se esperaba una malla triangulada'
pidx = np.where(pidx < 0, -pidx - 1, pidx)
uvn = child(geo, 'LayerElementUV')
UV = np.array(child(uvn, 'UV')[1][0]).reshape(-1, 2); uvidx = np.array(child(uvn, 'UVIndex')[1][0])

# Normales suaves por posición (las costuras de UV no cortan el sombreado).
tri = pidx.reshape(-1, 3)
fn = np.cross(P[tri[:, 1]] - P[tri[:, 0]], P[tri[:, 2]] - P[tri[:, 0]])
N = np.zeros_like(P)
for c in range(3): np.add.at(N, tri[:, c], fn)
N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12

# Un vértice por combinación (posición, uv).
keys, inv = np.unique(np.stack([pidx, uvidx], 1), axis=0, return_inverse=True)
pos, nor, uv, index = P[keys[:, 0]], N[keys[:, 0]], UV[keys[:, 1]], inv.reshape(-1).astype(np.uint16)

# ---- Esqueleto (medido sobre la malla en T-pose; izquierda del personaje = +X) ----
J = [  # nombre, padre, posición
    ('Hips', -1, (0, .95, -.035)), ('Spine', 0, (0, 1.08, -.035)), ('Chest', 1, (0, 1.24, -.045)),
    ('Neck', 2, (0, 1.455, -.04)), ('Head', 3, (0, 1.5, -.03)),
    ('LArm', 2, (.19, 1.395, -.08)), ('LFore', 5, (.44, 1.39, -.085)), ('LHand', 6, (.64, 1.395, -.09)),
    ('RArm', 2, (-.19, 1.395, -.08)), ('RFore', 8, (-.44, 1.39, -.085)), ('RHand', 9, (-.64, 1.395, -.09)),
    ('LUpLeg', 0, (.105, .86, -.045)), ('LLeg', 11, (.11, .47, -.05)), ('LFoot', 12, (.11, .09, -.055)),
    ('RUpLeg', 0, (-.105, .86, -.045)), ('RLeg', 14, (-.11, .47, -.05)), ('RFoot', 15, (-.11, .09, -.055)),
]
B = {n: i for i, (n, _, _) in enumerate(J)}
ss = lambda a, b, x: np.clip((x - a) / (b - a), 0, 1) ** 2 * (3 - 2 * np.clip((x - a) / (b - a), 0, 1))
x, y, z = pos[:, 0], pos[:, 1], pos[:, 2]
ax = np.abs(x)
W = np.zeros((len(pos), len(J)))
# Tronco y cabeza por altura.
# Cuello y cabeza solo en la columna central: la mandíbula y la boca van enteras con la cabeza.
central = 1 - ss(.1, .16, np.abs(pos[:, 0]))
hips_spine, spine_chest, chest_neck, neck_head = ss(.99, 1.13, y), ss(1.15, 1.3, y), ss(1.435, 1.475, y) * central, ss(1.465, 1.5, y) * central
W[:, B['Hips']] = 1 - hips_spine
W[:, B['Spine']] = hips_spine * (1 - spine_chest)
W[:, B['Chest']] = spine_chest * (1 - chest_neck)
W[:, B['Neck']] = chest_neck * (1 - neck_head)
W[:, B['Head']] = neck_head
# Brazos: máscara lateral, luego codo y muñeca a lo largo del eje X.
arm = ss(.17, .27, ax) * ss(1.16, 1.29, y)
fore, hand = ss(.39, .49, ax), ss(.61, .67, ax)
W *= (1 - arm)[:, None]
for side, sel in (('L', x > 0), ('R', x <= 0)):
    a = arm * sel
    W[:, B[side + 'Arm']] = a * (1 - fore); W[:, B[side + 'Fore']] = a * fore * (1 - hand); W[:, B[side + 'Hand']] = a * hand
# Piernas: debajo de la cadera, rodilla y tobillo por altura (el calzado entero va con el pie).
leg = 1 - ss(.76, .95, y)
knee = 1 - ss(.41, .53, y)
foot = np.maximum(1 - ss(.07, .14, y), (1 - ss(.12, .17, y)) * ss(.0, .05, z))
left = ss(-.035, .035, x)
W *= (1 - leg)[:, None]
for side, s in (('L', left), ('R', 1 - left)):
    l = leg * s
    W[:, B[side + 'UpLeg']] = l * (1 - knee); W[:, B[side + 'Leg']] = l * knee * (1 - foot); W[:, B[side + 'Foot']] = l * knee * foot
order = np.argsort(-W, axis=1)[:, :4]
w4 = np.take_along_axis(W, order, 1); w4 /= w4.sum(1, keepdims=True)
w8 = np.round(w4 * 255).astype(np.int32); w8[:, 0] += 255 - w8.sum(1)

buffers, layout, off = [], {}, 0
for name, arr in (('position', pos.astype('<f4')), ('normal', np.round(nor * 127).astype('i1')), ('uv', uv.astype('<f4')),
                  ('skinIndex', order.astype('u1')), ('skinWeight', w8.astype('u1')), ('index', index.astype('<u2'))):
    raw = arr.tobytes(); raw += b'\0' * (-len(raw) % 4)
    layout[name] = [off, arr.size]; buffers.append(raw); off += len(raw)
head = json.dumps({'vertices': len(pos), 'layout': layout, 'joints': [{'name': n, 'parent': p, 'pos': list(q)} for n, p, q in J]}).encode()
head += b' ' * (-len(head) % 4)
open(out + '/avatar.bin', 'wb').write(struct.pack('<I', len(head)) + head + b''.join(buffers))

print('vértices', len(pos), 'triángulos', len(index) // 3, 'pesos máx por hueso', {n: int((order[:, 0] == i).sum()) for n, i in B.items()})
