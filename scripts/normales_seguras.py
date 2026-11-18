"""Normales sin ceros para las mallas de la bienvenida.

En el pelo de los gatos hay mechones finos de dos caras: al promediar las normales por posición, las
caras opuestas se anulan y queda una normal nula. Normalizar un vector nulo en la GPU da NaN, que se ve
como un punto negro (y en el posproceso, el brillo lo esparce en manchas). Acá, donde el promedio por
posición se anula, se usa el del propio vértice y, si también se anula, la normal de su cara más grande.

    python3 scripts/normales_seguras.py web/static/welcome/gato.bin [más archivos]   # arregla en el lugar
"""
import sys, json, struct
import numpy as np


def normales_seguras(P, tri, N_soldadas):
    """N_soldadas: normales sin normalizar promediadas por posición, una por vértice. Devuelve normales unitarias."""
    fn = np.cross(P[tri[:, 1]] - P[tri[:, 0]], P[tri[:, 2]] - P[tri[:, 0]])
    escala = np.zeros(len(P)); propia = np.zeros_like(P); mayor = np.zeros_like(P); area = np.zeros(len(P))
    largo = np.linalg.norm(fn, axis=1)
    for c in range(3):
        np.add.at(escala, tri[:, c], largo); np.add.at(propia, tri[:, c], fn)
    orden = np.argsort(largo)                                  # la cara más grande queda escrita al final
    for c in range(3):
        v = tri[orden, c]; mayor[v] = fn[orden]
    N = N_soldadas.copy()
    floja = np.linalg.norm(N, axis=1) < .2 * escala + 1e-15
    N[floja] = propia[floja]
    floja &= np.linalg.norm(propia, axis=1) < .2 * escala + 1e-15
    N[floja] = mayor[floja]
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-15
    return N


if __name__ == '__main__':
    for path in sys.argv[1:]:
        b = bytearray(open(path, 'rb').read())
        hl = struct.unpack_from('<I', b)[0]; head = json.loads(bytes(b[4:4 + hl])); base = 4 + hl
        off = lambda n: base + head['layout'][n][0]
        get = lambda n, dt: np.frombuffer(bytes(b), dt, head['layout'][n][1], off(n))
        P = get('position', '<f4').reshape(-1, 3).astype(np.float64)
        tri = get('index', '<u4' if head.get('index32') else '<u2').reshape(-1, 3).astype(np.int64)
        _, weld = np.unique(np.round(P * 1e6).astype(np.int64), axis=0, return_inverse=True); weld = weld.reshape(-1)
        fn = np.cross(P[tri[:, 1]] - P[tri[:, 0]], P[tri[:, 2]] - P[tri[:, 0]])
        Nw = np.zeros((weld.max() + 1, 3))
        for c in range(3): np.add.at(Nw, weld[tri[:, c]], fn)
        antes = (np.linalg.norm(get('normal', 'i1').reshape(-1, 3).astype(float), axis=1) < 20).sum()
        N = normales_seguras(P, tri, Nw[weld])
        q = np.round(N * 127).astype('i1')
        b[off('normal'):off('normal') + q.nbytes] = q.tobytes()
        open(path, 'wb').write(bytes(b))
        print(path, 'normales nulas', antes, '→', int((np.linalg.norm(q.astype(float), axis=1) < 20).sum()))
