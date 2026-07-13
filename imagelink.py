from urllib.parse import quote_plus

_BASE = "https://www.google.com/search?tbm=isch&q="


def google_image_link(nombre):
    tokens = nombre.split()
    return _BASE + "+".join(quote_plus(t) for t in tokens)
