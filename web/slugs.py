"""Slugs deterministicos para armar/resolver links públicos de producto (/p/<slug>)."""
import re
import unicodedata


def slug(nombre):
    n = (nombre or "").replace("+", " plus ")
    n = unicodedata.normalize("NFKD", n).encode("ascii", "ignore").decode("ascii")
    n = n.lower()
    n = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    return n


def url_producto(nombre, base="https://thetechroomarg.com"):
    return f"{base}/p/{slug(nombre)}"
