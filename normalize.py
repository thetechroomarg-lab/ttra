import re
import unicodedata


def normalizar(nombre):
    texto = nombre.lower()
    # quitar acentos
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    # unir specs escritas con "/": 64/2gb -> 64gb 2gb ; 128gb/4gb -> 128gb 4gb
    texto = re.sub(r"(\d+)gb\s*/\s*(\d+)gb", r"\1gb \2gb", texto)
    texto = re.sub(r"(\d+)\s*/\s*(\d+)\s*gb", r"\1gb \2gb", texto)
    # preservar el "+" como distintivo (Pro vs Pro+)
    texto = texto.replace("+", " plus ")
    # reemplazar cualquier cosa que no sea alfanumérico por espacio
    texto = re.sub(r"[^a-z0-9]+", " ", texto)

    # ordenar las capacidades (GB/TB) al final, sin importar el orden de origen,
    # para que "64/2GB", "2GB 64GB" y "64GB 2GB" normalicen igual.
    tokens = texto.split()
    caps, resto = [], []
    for t in tokens:
        if re.fullmatch(r"\d+(gb|tb)", t):
            caps.append(t)
        else:
            resto.append(t)

    def _tamano(t):
        n = int(re.match(r"\d+", t).group())
        return n * 1024 if t.endswith("tb") else n

    caps = sorted(set(caps), key=_tamano)
    return " ".join(resto + caps)
