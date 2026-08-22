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

# Tablets de Samsung/Xiaomi vienen con la misma categoría que sus celulares
# (p.ej. "Samsung", "Xiaomi"), así que hay que detectarlas por nombre ANTES de
# aplicar las reglas de categoría — si no, terminan mezcladas con los celulares.
_TABLET_PATTERN = re.compile(
    r"(?i)\btablet\b|\bgalaxy\s*tab\b|\bmi\s*pad\b|\bredmi\s*pad\b|\bpoco\s*pad\b|\btab\s*s\d"
)

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
    nombre = producto.get("nombre", "")
    if _TABLET_PATTERN.search(nombre):
        return "Tablets"
    categoria = producto.get("categoria", "")
    if categoria in _CELULARES_CATEGORIAS:
        return "Celulares"
    if categoria in _NOTEBOOK_CATEGORIAS:
        return "Notebooks y Macbooks"
    if categoria in _TABLET_CATEGORIAS:
        return "Tablets"
    if categoria in _ACCESORIO_CATEGORIAS:
        return "Accesorios Celulares"
    if _CELULAR_OTROS.search(nombre):
        return "Celulares"
    if _GAMING_OTROS.search(nombre):
        return "Gaming"
    return "Accesorios Celulares"


def seccion_de(producto):
    return _seccion_de(producto)


# Marca por producto, usada por la web para armar los botones de sub-navegación
# dentro de Celulares/Tablets/Accesorios Celulares (no afecta a qué sección va
# cada producto, solo cómo se agrupa dentro de la sección).
_MARCA_OTROS = re.compile(
    r"(?i)\boppo\b|\bhonor\b|\binfinix\b|\bhot\s*\d|\bnokia\b|\bitel\b|\bjbl\b|"
    r"\blogitech\b|\bapple\b|\bsamsung\b|\bgalaxy\b|\bxiaomi\b|\bredmi\b|\bpoco\b|"
    r"\bmotorola\b|\bmoto\b|\brealme\b"
)

_MARCA_POR_PALABRA = (
    (re.compile(r"(?i)\boppo\b"), "Oppo"),
    (re.compile(r"(?i)\bhonor\b"), "Honor"),
    (re.compile(r"(?i)\binfinix\b|\bhot\s*\d"), "Infinix"),
    (re.compile(r"(?i)\bnokia\b"), "Nokia"),
    (re.compile(r"(?i)\bitel\b"), "Itel"),
    (re.compile(r"(?i)\bjbl\b"), "JBL"),
    (re.compile(r"(?i)\blogitech\b"), "Logitech"),
    (re.compile(r"(?i)\bplaystation\b|\bps5\b|\bsony\b"), "PlayStation"),
    (re.compile(r"(?i)\bnintendo\b|\bswitch\b"), "Nintendo"),
    (re.compile(r"(?i)\bapple\b"), "Apple"),
    (re.compile(r"(?i)\bsamsung\b|\bgalaxy\b"), "Samsung"),
    (re.compile(r"(?i)\bxiaomi\b|\bredmi\b|\bpoco\b"), "Xiaomi"),
    (re.compile(r"(?i)\bmotorola\b|\bmoto\b"), "Motorola"),
    (re.compile(r"(?i)\brealme\b"), "Realme"),
)

_MARCA_POR_CATEGORIA = {
    "Apple - iPhone": "Apple",
    "Apple - iPhone Usado": "Apple",
    "Apple - AirPods": "Apple",
    "Apple - Watch": "Apple",
    "Apple - iPad": "Apple",
    "Mac": "Apple",
    "Samsung": "Samsung",
    "Xiaomi": "Xiaomi",
    "Motorola": "Motorola",
    "Realme": "Realme",
}


def marca_de(producto):
    categoria = producto.get("categoria", "")
    if categoria in _MARCA_POR_CATEGORIA:
        return _MARCA_POR_CATEGORIA[categoria]
    nombre = producto.get("nombre", "")
    for patron, marca in _MARCA_POR_PALABRA:
        if patron.search(nombre):
            return marca
    return "Otras marcas"


def secciones_catalogo(productos):
    resultado = {seccion: [] for seccion in SECCIONES}
    for producto in productos:
        enriquecido = {**producto, "marca": marca_de(producto)}
        resultado[_seccion_de(producto)].append(enriquecido)
    return resultado
