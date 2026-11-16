"""Traza el logo (PNG) a contornos vectoriales: python trace_logo.py <png> <out.json> <check.png>"""
import sys, json, math
from PIL import Image, ImageDraw, ImageChops
src, out, check = sys.argv[1:4]
S = 2
im0 = Image.open(src).convert('RGB')
W0, H0 = im0.size
im = im0.resize((W0*S, H0*S), Image.LANCZOS)
W, H = im.size
r, g, b = im.split()
white = ImageChops.darker(ImageChops.darker(r, g), b).point(lambda v: 255 if v > 127 else 0)
px = white.load()
Y0, Y1 = 0, H
def inside(x, y): return 0 <= x < W and Y0 <= y < Y1 and px[x, y] > 0
# red dot
rp, gp = r.load(), g.load()
sx = sy = n = 0
for y in range(H):
    for x in range(W):
        if rp[x, y] > 140 and gp[x, y] < 90: sx += x; sy += y; n += 1
dot = ((sx/n+.5)/S, (sy/n+.5)/S, math.sqrt(n/math.pi)/S)
rows_sum = [sum(1 for x in range(0, W, 2) if px[x, y]) for y in range(H)]
cuts = []
for guess in (405, 612, 828):
    lo, hi = (guess-25)*S, (guess+25)*S
    m = min(rows_sum[lo:hi]); ys = [y for y in range(lo, hi) if rows_sum[y] == m]
    cuts.append(ys[len(ys)//2])
print('cuts', [c/S for c in cuts], [rows_sum[c] for c in cuts])
bands = list(zip([0]+cuts, cuts+[H]))
def trace():
    global nxt
    # crack-following: directed edges with the filled pixel on the left
    nxt = {}
    for y in range(Y0, Y1):
        for x in range(W):
            if px[x, y] == 0: continue
            if not inside(x, y-1): nxt.setdefault((x+1, y), []).append((x, y))      # top edge, going left
            if not inside(x, y+1): nxt.setdefault((x, y+1), []).append((x+1, y+1))  # bottom, going right
            if not inside(x-1, y): nxt.setdefault((x, y), []).append((x, y+1))      # left, going down
            if not inside(x+1, y): nxt.setdefault((x+1, y+1), []).append((x+1, y))  # right, going up
    loops = []
    while nxt:
        start = next(iter(nxt)); p = start; prev = None; loop = []
        while True:
            outs = nxt[p]
            if len(outs) == 1 or prev is None: q = outs.pop(0)
            else:
                # at a diagonal touch choose the turn that keeps components separate (turn left relative to heading)
                dx, dy = p[0]-prev[0], p[1]-prev[1]
                best = max(outs, key=lambda o: (dx*(o[1]-p[1]) - dy*(o[0]-p[0])))
                outs.remove(best); q = best
            if not outs: del nxt[p]
            loop.append(p); prev = p; p = q
            if p == start: break
        loops.append(loop)
    def area(l): return sum(l[i][0]*l[(i+1)%len(l)][1]-l[(i+1)%len(l)][0]*l[i][1] for i in range(len(l)))/2
    def rdp(pts, eps):
        keep = [False]*len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts)-1)]
        while stack:
            a, b_ = stack.pop()
            if b_ <= a+1: continue
            ax, ay = pts[a]; bx, by = pts[b_]; dx, dy = bx-ax, by-ay; L = math.hypot(dx, dy) or 1
            m, mi = 0, -1
            for i in range(a+1, b_):
                d = abs((pts[i][0]-ax)*dy-(pts[i][1]-ay)*dx)/L
                if d > m: m, mi = d, i
            if m > eps: keep[mi] = True; stack += [(a, mi), (mi, b_)]
        return [p for p, k in zip(pts, keep) if k]
    def simplify(l, eps):
        # split the closed loop at its two farthest-apart-ish anchors so RDP has fixed ends
        i0 = min(range(len(l)), key=lambda i: (l[i][0]+l[i][1])); i1 = max(range(len(l)), key=lambda i: (l[i][0]+l[i][1]))
        if i0 > i1: i0, i1 = i1, i0
        a = rdp(l[i0:i1+1], eps); b_ = rdp(l[i1:]+l[:i0+1], eps)
        return a[:-1]+b_[:-1]
    polys = []
    for l in loops:
        A = area(l)
        if abs(A) < 60*S*S: continue
        s = simplify(l, 1.1)
        polys.append({'a': A, 'pts': [(x/S, y/S) for x, y in s]})
    def pip(pt, poly):
        x, y = pt; c = False
        for i in range(len(poly)):
            x1, y1 = poly[i]; x2, y2 = poly[i-1]
            if (y1 > y) != (y2 > y) and x < (x2-x1)*(y-y1)/(y2-y1)+x1: c = not c
        return c
    sign = 1 if max(polys, key=lambda p: abs(p['a']))['a'] > 0 else -1
    outers = [p for p in polys if p['a']*sign > 0]; holes = [p for p in polys if p['a']*sign < 0]
    shapes = [{'o': o['pts'], 'h': []} for o in outers]
    for h in holes:
        cands = [s for s in shapes if pip(h['pts'][0], s['o'])]
        min(cands, key=lambda s: abs(area(s['o'])))['h'].append(h['pts'])
    shapes.sort(key=lambda s: (min(p[1] for p in s['o'])//40, min(p[0] for p in s['o'])))
    return shapes
rows = []
for Y0, Y1 in bands:
    rows.append(trace())
shapes = [s_ for r_ in rows for s_ in r_]
rnd = lambda pts: [[round(x, 2), round(y, 2)] for x, y in pts]
data = {'w': W0, 'h': H0, 'dot': [round(v, 2) for v in dot], 'rows': [[{'o': rnd(s['o']), 'h': [rnd(h) for h in s['h']]} for s in r_] for r_ in rows]}
data['shapes'] = [s_ for r_ in data['rows'] for s_ in r_]
allshapes = data.pop('shapes'); json.dump(data, open(out, 'w'), separators=(',', ':')); data['shapes'] = allshapes
# check render
chk = Image.new('L', (W0*4, H0*4), 0); d = ImageDraw.Draw(chk)
for s in data['shapes']:
    d.polygon([(x*4, y*4) for x, y in s['o']], fill=255)
    for h in s['h']: d.polygon([(x*4, y*4) for x, y in h], fill=0)
chk = chk.resize((W0, H0), Image.LANCZOS)
ref = ImageChops.darker(ImageChops.darker(*im0.split()[:2]), im0.split()[2])
diff = ImageChops.difference(chk, ref).point(lambda v: 255 if v > 110 else 0)
bad = sum(1 for v in diff.getdata() if v); tot = sum(1 for v in ref.getdata() if v > 127)
vis = Image.merge('RGB', (chk, ref, ref)); vis.save(check)
print('size', W0, H0, 'dot', data['dot'], 'shapes', len(shapes), 'pts', sum(len(s['o'])+sum(len(h) for h in s['h']) for s in shapes), 'mismatch px', bad, 'of', tot)
for s in data['shapes']:
    xs = [p[0] for p in s['o']]; ys = [p[1] for p in s['o']]
    pass; print(' bbox', min(xs), min(ys), max(xs), max(ys), 'holes', len(s['h']), 'n', len(s['o']))
