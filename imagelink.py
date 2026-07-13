_BASE = "https://www.google.com/search?tbm=isch&q="


def google_image_link(nombre):
    tokens = nombre.split()
    return _BASE + "+".join(tokens)
