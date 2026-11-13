"""Banco de imágenes del catálogo: mapeo permanente producto -> imagen.

El mapeo vive en catalogo-imagenes-originales/banco.json y NUNCA pierde alias: si un
producto sale de stock y vuelve (aunque otro proveedor lo nombre distinto), se reutiliza
la imagen ya generada en vez de crear otra.

Uso (desde la raíz del repo):
  python scripts/banco_imagenes.py construir              # suma al banco lo que hay en index.json
  python scripts/banco_imagenes.py buscar "NOMBRE" [COLOR]  # qué imagen le toca a ese nombre
  python scripts/banco_imagenes.py sincronizar [--aplicar]  # productos sin imagen que el banco ya conoce
  python scripts/banco_imagenes.py validar                # mide aciertos del reconocimiento
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
WEB_IMAGENES = RAIZ / "web/static/catalog-images"
INDEX = WEB_IMAGENES / "index.json"
BANCO = RAIZ / "catalogo-imagenes-originales/banco.json"
ORIGINALES = RAIZ / "catalogo-imagenes-originales"
PRODUCTOS = RAIZ / "web/productos.json"

# Palabras que cambian de un proveedor a otro sin cambiar el producto.
RUIDO = {
    "nuevo", "original", "activado", "con", "sin", "de", "la", "el", "y", "en", "para", "cargador",
    "s", "c", "ram", "ssd", "emmc", "hz", "wifi", "wi", "fi", "5g", "4g", "lte", "nfc", "dual", "sim",
    "pulgadas", "pantalla", "notebook", "nb", "laptop", "celular", "smartphone", "parlante", "tablet",
    "usb", "cable", "incluye", "color", "colores", "varios", "windows", "win11", "w11", "gaming", "gamer",
}
UMBRAL_ALTO = 0.6      # se asigna sola
UMBRAL_REVISAR = 0.4   # se propone, pero Vladimir la confirma


def _plain(s):
    s = unicodedata.normalize("NFD", str(s or "").strip().lower().replace("\xa0", " "))
    return "".join(c for c in s if not unicodedata.combining(c))


SINONIMOS = {  # español -> forma canónica, para que "Negro" y "Black" sean el mismo color
    "negro": "black", "blanco": "white", "azul": "blue", "gris": "gray", "grey": "gray", "rojo": "red", "verde": "green",
    "rosa": "pink", "dorado": "gold", "plata": "silver", "plateado": "silver", "naranja": "orange", "violeta": "purple",
    "celeste": "blue", "aluminium": "aluminum", "plus": "plus", "inalambrico": "wireless",
}


def _normalizar(nombre):
    s = _plain(nombre)
    s = re.sub(r"\+", " plus ", s) if re.search(r"\w\+(?!\w)", s) else s  # "Pro+" == "Pro Plus"
    s = re.sub(r"\b[a-z]\d{2}_[a-z0-9_]+", " ", s)                # SKU de proveedor: A01_OC01_008066
    s = re.sub(r"\b\d+\s*/\s*\d+\s*(gb)?\b", " ", s)             # 12/512: memoria
    s = re.sub(r"\b\d+\s*(gb|tb|mb)\b", " ", s)                  # almacenamiento / RAM: no cambian la foto
    s = re.sub(r"\b\d+\.\d+\s*(hz|mm|ghz|mhz|k)?\b", " ", s)       # pulgadas / GHz: 15.6, 13.4, 4.5
    s = re.sub(r"\b\d+\s*(hz|mm|ghz|mhz)\b", " ", s)
    return s


def tokens(nombre):
    ts = (SINONIMOS.get(t, t) for t in re.sub(r"[^a-z0-9+]+", " ", _normalizar(nombre)).split())
    return frozenset(t for t in ts if t not in RUIDO and len(t) > 0)


def color_key(c):
    base = re.sub(r"\s+", " ", re.sub(r"\b(pantone|awesome|awesomw|cosmic|deep)\b", " ", _plain(c))).strip()
    return " ".join(SINONIMOS.get(t, t) for t in base.split())


# Palabras que distinguen un producto de otro parecido: si una está en un nombre y no en el otro, no es el mismo.
VARIANTES = {
    "pro", "max", "plus", "ultra", "mini", "lite", "fe", "se", "air", "edge", "fold", "flip", "neo", "go",
    "essential", "stage", "encore", "box", "x", "xl", "s", "t", "e", "c", "r", "gt", "m", "ti", "oled", "cpo", "usado",
}
VARIANTES -= {"s", "c", "t", "e", "r", "m", "x", "go", "box"}   # demasiado cortas/genéricas: ya las cubren los códigos
COLORES = {
    "negro", "blanco", "azul", "gris", "rojo", "verde", "rosa", "dorado", "plata", "naranja", "violeta", "celeste",
    "black", "white", "blue", "gray", "grey", "red", "green", "pink", "gold", "silver", "purple", "violet", "orange",
    "yellow", "starlight", "midnight", "titanium", "natural", "inox", "steel", "lavender", "sage", "teal", "bronze",
}


MARCAS = {
    "apple", "iphone", "ipad", "airpods", "macbook", "samsung", "galaxy", "xiaomi", "poco", "redmi", "motorola", "moto",
    "hp", "acer", "asus", "lenovo", "dell", "msi", "gigabyte", "jbl", "sony", "oppo", "infinix", "realme", "nintendo",
    "playstation", "dji", "hetzer", "wubian", "cecotec", "aiper", "noax", "amazon", "meta", "ray-ban", "amazfit",
    "doogee", "aoc", "gmktec", "ecovacs", "anthbot", "cookut", "pinnacle", "logitech", "huawei", "honor", "zte", "tcl",
}


def similitud(a, b):
    """0..1 entre dos conjuntos de tokens. Conservadora: ante la duda prefiere 'no sé' a una imagen equivocada."""
    if a == b:
        return 1.0
    inter = a & b
    if len(inter) < 2:
        return 0.0
    dif = a ^ b
    if any(t.isdigit() or t in VARIANTES for t in dif):          # 17 vs 17 pro, 30 vs 32 ltr, pro vs pro max
        return 0.0
    ma, mb = a & MARCAS, b & MARCAS
    if ma and mb and not (ma & mb) and not ({"apple"} <= ma | mb and ma | mb <= {"apple", "iphone", "ipad", "airpods", "macbook"}):
        return 0.0                                                  # HP vs Acer, Samsung vs Xiaomi
    ca, cb = a & COLORES, b & COLORES
    if ca and cb and ca != cb:                                      # negro vs blanco
        return 0.0
    corto, largo = (a, b) if len(a) <= len(b) else (b, a)
    codigos = {t for t in corto if any(ch.isdigit() for ch in t)}
    if codigos and not codigos <= largo:
        return 0.0
    jaccard = len(inter) / len(a | b)
    contencion = len(inter) / len(corto)
    return max(jaccard, 0.9 * contencion if len(corto) >= 3 else 0.0)


def cargar_banco():
    if BANCO.exists():
        return json.loads(BANCO.read_text())
    return {"version": 1, "imagenes": {}, "mapeo": []}


def guardar_banco(banco):
    banco["mapeo"].sort(key=lambda r: (r["imagen"], r["nombre"], r.get("color") or ""))
    banco["imagenes"] = dict(sorted(banco["imagenes"].items()))
    BANCO.parent.mkdir(parents=True, exist_ok=True)
    BANCO.write_text(json.dumps(banco, ensure_ascii=False, indent=1))


def construir():
    """Suma al banco todo lo que index.json ya mapea. Nunca borra alias ni imágenes."""
    banco = cargar_banco()
    index = json.loads(INDEX.read_text())
    hay = {(r["nombre"], r.get("color"), r["imagen"]) for r in banco["mapeo"]}
    nuevos = 0
    for nombre, variantes in index.items():
        for v in variantes:
            src = v.get("src") or ""
            if not src.startswith("/catalog-images/"):
                continue
            archivo = src[len("/catalog-images/"):]
            clave = (nombre, v.get("color"), archivo)
            if clave not in hay:
                banco["mapeo"].append({"nombre": nombre, "color": v.get("color"), "imagen": archivo})
                hay.add(clave)
                nuevos += 1
            meta = banco["imagenes"].setdefault(archivo, {})
            orig = ORIGINALES / archivo
            if orig.exists():
                meta["original"] = f"catalogo-imagenes-originales/{archivo}"
            if (WEB_IMAGENES / "zoom" / archivo).exists():
                meta["zoom"] = f"web/static/catalog-images/zoom/{archivo}"
    guardar_banco(banco)
    print(f"banco: {len(banco['imagenes'])} imágenes, {len(banco['mapeo'])} alias (+{nuevos} nuevos)")


def _indice(banco, excluir=None):
    por_nombre = {}
    for r in banco["mapeo"]:
        if excluir and r["nombre"] in excluir:
            continue
        por_nombre.setdefault(r["nombre"], []).append(r)
    return {n: (tokens(n), rs) for n, rs in por_nombre.items()}


def buscar_en(indice, nombre, color=None):
    """-> (estado, imagen, alias_parecido, puntaje). estado: exacto | alto | revisar | nada.

    Se juntan todos los nombres del banco que se parecen lo suficiente y se elige el más parecido
    que tenga ese color. Si ninguno tiene el color pedido, no se inventa: queda para revisar."""
    tk = tokens(nombre)
    candidatos = []
    for n, (tn, rs) in indice.items():
        s = 1.0 if n == nombre else similitud(tk, tn)
        if s >= UMBRAL_REVISAR:
            candidatos.append((s, n, rs))
    if not candidatos:
        return "nada", None, None, 0.0
    candidatos.sort(key=lambda c: -c[0])
    ck = color_key(color)
    for s, n, rs in candidatos:
        elegido = next((r for r in rs if color_key(r.get("color")) == ck), None)
        if elegido is None and not ck and rs:
            elegido = rs[0]
        if elegido is None and ck and all(not r.get("color") for r in rs) and len({r["imagen"] for r in rs}) == 1:
            elegido = rs[0]                       # alias sin colores cargados: la imagen sirve para cualquiera
        if elegido:
            estado = "exacto" if s == 1.0 else ("alto" if s >= UMBRAL_ALTO else "revisar")
            return estado, elegido["imagen"], n, s
    s, n, rs = candidatos[0]
    return "revisar", rs[0]["imagen"], n, s       # producto reconocido, pero ese color no está en el banco


def buscar(nombre, color=None):
    banco = cargar_banco()
    estado, imagen, alias, puntaje = buscar_en(_indice(banco), nombre, color)
    print(f"{estado}\t{imagen}\tparecido a: {alias}\tpuntaje {puntaje:.2f}")


def sincronizar(aplicar=False):
    sys.path.insert(0, str(RAIZ / "scripts"))
    from check_catalog_images import con_imagen

    banco = cargar_banco()
    index = json.loads(INDEX.read_text())
    productos = json.loads(PRODUCTOS.read_text())
    ok = con_imagen(productos, index)
    indice = _indice(banco)
    nuevos = 0
    pendientes = []
    for p in productos:
        if p["nombre"] in ok:
            continue
        variantes, dudas = [], False
        for c in p.get("colores") or [None]:
            estado, imagen, alias, puntaje = buscar_en(indice, p["nombre"], c)
            if estado in ("exacto", "alto"):
                variantes.append({"color": c, "src": "/catalog-images/" + imagen})
            else:
                dudas = True
                pendientes.append((p["nombre"], c, estado, imagen, alias, puntaje))
        if variantes and not dudas:
            nuevos += 1
            print(f"RECUPERA {p['nombre']}  <-  {alias} ({puntaje:.2f})")
            if aplicar:
                index[p["nombre"]] = variantes
    for n, c, e, i, a, s in pendientes:
        print(f"{e.upper():8} {n} [{c}]  ->  {i} (parecido a: {a}, {s:.2f})")
    if aplicar and nuevos:
        INDEX.write_text(json.dumps(index, ensure_ascii=False, separators=(",", ":")))
        print(f"index.json actualizado con {nuevos} productos")
    print(f"{nuevos} se resuelven solos, {len(pendientes)} para revisar o sin imagen")


def validar():
    """Deja afuera cada nombre y comprueba que el banco igual lo reconozca por los demás nombres."""
    banco = cargar_banco()
    grupos = {}
    for r in banco["mapeo"]:
        grupos.setdefault(r["imagen"], set()).add(r["nombre"])
    total = altos = aciertos = sin_pred = 0
    for r in banco["mapeo"]:
        if len(grupos[r["imagen"]]) < 2:
            continue
        total += 1
        estado, pred, alias, s = buscar_en(_indice(banco, excluir={r["nombre"]}), r["nombre"], r.get("color"))
        if estado == "nada":
            sin_pred += 1
        elif estado in ("alto", "exacto"):
            altos += 1
            if pred == r["imagen"]:
                aciertos += 1
            else:
                print(f"FALSO  {r['nombre']} [{r.get('color')}]  ->  {alias} ({s:.2f})")
    print(f"registros con hermanos: {total}; sugeridos con confianza alta: {altos} "
          f"(acertados {aciertos}, equivocados {altos - aciertos}); sin sugerencia: {sin_pred}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "construir":
        construir()
    elif cmd == "buscar" and len(sys.argv) > 2:
        buscar(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    elif cmd == "sincronizar":
        sincronizar("--aplicar" in sys.argv)
    elif cmd == "validar":
        validar()
    else:
        print(__doc__)
