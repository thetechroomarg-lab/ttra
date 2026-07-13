import re
import unicodedata


def normalizar(nombre):
    texto = nombre.lower()
    # quitar acentos
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    # reemplazar cualquier cosa que no sea alfanumérico por espacio
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    # colapsar espacios y recortar
    return " ".join(texto.split())
