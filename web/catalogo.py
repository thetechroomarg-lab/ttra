import re

SECCIONES = [
    "Celulares",
    "Accesorios Celulares",
    "Tablets",
    "Notebooks y Macbooks",
    "Gaming",
]

_CELULARES_CATEGORIAS = {
    "Apple - iPhone", "Apple - iPhone Usado", "Samsung", "Xiaomi", "Motorola", "Realme",
}
_NOTEBOOK_CATEGORIAS = {"Mac", "Notebook"}
_TABLET_CATEGORIAS = {"Apple - iPad"}
_ACCESORIO_CATEGORIAS = {"Apple - AirPods", "Apple - Watch"}

# Teléfonos de marcas que hoy caen en la categoría "Otros" del pipeline de precios.
_CELULAR_OTROS = re.compile(
    r"(?i)\boppo\b|\bnokia\b|\binfinix\b|\bhonor\b|\bitel\b|\bxiaomi\b|\bredmi\b|"
    r"\bpoco\b|\bsamsung\b|\bgalaxy\b|\bmotorola\b|\bmoto\b|\brealme\b|\bcelular\b|"
    r"\bhot\s*\d"
)

# Consolas y accesorios de gaming que también caen en "Otros".
_GAMING_OTROS = re.compile(
    r"(?i)playstation|\bps5\b|nintendo|\bswitch\b|\br36s\b|volante|logitech"
)


def _seccion_de(producto):
    categoria = producto.get("categoria", "")
    if categoria in _CELULARES_CATEGORIAS:
        return "Celulares"
    if categoria in _NOTEBOOK_CATEGORIAS:
        return "Notebooks y Macbooks"
    if categoria in _TABLET_CATEGORIAS:
        return "Tablets"
    if categoria in _ACCESORIO_CATEGORIAS:
        return "Accesorios Celulares"
    nombre = producto.get("nombre", "")
    if _CELULAR_OTROS.search(nombre):
        return "Celulares"
    if _GAMING_OTROS.search(nombre):
        return "Gaming"
    return "Accesorios Celulares"


def secciones_catalogo(productos):
    resultado = {seccion: [] for seccion in SECCIONES}
    for producto in productos:
        resultado[_seccion_de(producto)].append(producto)
    return resultado
