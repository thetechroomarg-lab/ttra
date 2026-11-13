import re

from web.slugs import slug

SECCIONES = [
    "Celulares",
    "Accesorios Celulares",
    "Tablets",
    "Notebooks y Macbooks",
    "Gaming",
    "Electro",
]

_CELULARES_CATEGORIAS = {
    "Apple - iPhone", "Apple - iPhone Usado", "Samsung", "Xiaomi", "Motorola", "Realme",
}
_NOTEBOOK_CATEGORIAS = {"Mac", "Notebook"}
_TABLET_CATEGORIAS = {"Apple - iPad"}
_ACCESORIO_CATEGORIAS = {"Apple - AirPods", "Apple - Watch"}
# Categorías de Apple y de las notebooks propias: se clasifican solo por categoría.
_CATEGORIAS_FIJAS_APPLE = {"Apple - iPhone", "Apple - iPhone Usado", "Apple - iPad", "Apple - AirPods", "Apple - Watch", "Mac", "Notebook"}

# Tablets de Samsung/Xiaomi vienen con la misma categoría que sus celulares
# (p.ej. "Samsung", "Xiaomi"), así que hay que detectarlas por nombre ANTES de
# aplicar las reglas de categoría — si no, terminan mezcladas con los celulares.
_TABLET_PATTERN = re.compile(
    r"(?i)\btablet\b|\bgalaxy\s*tab\b|\bmi\s*pad\b|\bredmi\s*pad\b|\bpoco\s*pad\b|\btab\s*s\d"
)

# Los cargadores de celular de stock propio llevan la categoría de su marca
# ("Apple - iPhone", "Samsung") para la marca y el orden del listado, pero en
# la web son accesorios. Los de MacBook siguen con las notebooks.
_CARGADOR_CELULAR = re.compile(r"(?i)^\s*cargador\b(?!.*macbook)")

# Teléfonos de marcas que hoy caen en la categoría "Otros" del pipeline de precios.
_CELULAR_OTROS = re.compile(
    r"(?i)\boppo\b|\bnokia\b|\binfinix\b|\bhonor\b|\bitel\b|\bxiaomi\b|\bredmi\b|"
    r"\bpoco\b|\bsamsung\b|\bgalaxy\b|\bmotorola\b|\bmoto\b|\brealme\b|\bcelular\b|"
    r"\bhot\s*\d|\balcatel\b|\bpixel\s*\d|^\s*a\d{2}s?\s+\d"
)

# Consolas y accesorios de gaming que también caen en "Otros".
_GAMING_OTROS = re.compile(
    r"(?i)playstation|\bps5\b|nintendo|\bswitch\b|\br36s\b|volante|logitech"
)


# Las marcas de celulares (Samsung, Xiaomi, ...) también venden monitores, notebooks, scooters,
# aspiradoras, relojes, auriculares, cargadores... y el pipeline los trae con la categoría de la marca.
# Si el nombre dice que no es un teléfono, no va a Celulares (ver _seccion_de).
_CHROMEBOOK = re.compile(r"(?i)\bchromebook\b|^\s*nb\s|\bmini\s*pc\b")
_MONITOR_GAMER = re.compile(r"(?i)\bmonitor(?:es)?\b|\bodyssey\b")
_NO_ES_CELULAR = re.compile(
    r"(?i)^\s*carg\b|^\s*cargador|\bcable\b|power\s*bank|\bbuds\b|earphone|auricular|neo\s+wireless|"
    r"\bspeaker\b|parlante|\bsmart\s*tag\b|\blocalizador\b|\bmi\s+band\b|\bxiaomi\s+band\b|\bband\s+\d|"
    r"\bamazfit\b|\bwatch\b|scooter|patinete|vacuum|aspirador|cerradura|compresor|cafetera|"
    r"humidifier|\bscale\b|\bprinter\b|impresora|\blamp\b|lightstrip|tira\s+led|enchufe|smart\s+plug|"
    r"range\s+extender|lint\s+remover|\bpilas\b|\bbottle\b|botella|fanny\s+pack|selfie\s+stick|"
    r"\bsmart\s+c\d+|\bmini\s+asm|\btv\b|televisor|\bairfryer\b"
)


# Electrodomésticos: cada tipo con las palabras que lo reconocen en el nombre.
# El orden importa (gana el primero que coincide): "Aspiradora Robot" es una
# aspiradora, no un robot. Para sumar un tipo nuevo basta una línea acá; el
# filtro "Tipo" de la sección sale solo de los tipos que tengan productos.
ELECTRO_TIPOS = (
    ("Limpiapiscinas", re.compile(r"(?i)piscina|\baiper\b")),
    ("Aspiradoras", re.compile(r"(?i)aspirad|aspiraci[oó]n|vacuum|\bmop\b|fregona")),
    ("Robots", re.compile(r"(?i)\brobot(?!\s+de\s+cocina)")),
    ("Cafeteras", re.compile(r"(?i)cafetera|espresso|\bcoffee\b")),
    ("Freidoras de aire", re.compile(r"(?i)air\s*fryer|freidora|cecofry")),
    ("Humidificadores", re.compile(r"(?i)humidif")),
    ("Purificadores de aire", re.compile(r"(?i)purificador|air\s*purifier")),
    ("Balanzas", re.compile(r"(?i)balanza|\bscale\b")),
    ("Ventiladores y climatización", re.compile(r"(?i)ventilador|calefactor|estufa|aire\s+acondicionado|climatiz")),
    ("Licuadoras y batidoras", re.compile(r"(?i)licuadora|batidora|procesadora|\bblender\b")),
    ("Ollas y sartenes", re.compile(r"(?i)\bcookut\b|sart[eé]n|sartenes|\bolla\b|\bollas\b")),
    ("Cocina", re.compile(r"(?i)microondas|\bpava\b|hervidor|\bkettle\b|tostador|\bhorno\b|sandwichera|robot\s+de\s+cocina|\bmambo\b")),
    ("Cuidado personal", re.compile(r"(?i)secador|planchita|afeitadora|depiladora|cortadora\s+de\s+pelo|cepillo\s+modelador")),
    ("Cuidado de ropa", re.compile(r"(?i)\bplancha\b|\bsteamer\b|lint\s+remover")),
    ("Heladeras", re.compile(r"(?i)heladera|\bfreezer\b|refrigerador")),
    ("Televisores", re.compile(r"(?i)televisor|\bsmart\s*tv\b")),
)
ELECTRO_OTROS = "Otros electro"


def tipo_electro_de(producto):
    """Tipo de electrodoméstico del producto, o None si no es un electro."""
    nombre = producto.get("nombre", "")
    for tipo, patron in ELECTRO_TIPOS:
        if patron.search(nombre):
            return tipo
    # El pipeline puede traer la categoría "Electro" explícita para algo que
    # todavía no tiene regla de tipo.
    return ELECTRO_OTROS if producto.get("categoria") == "Electro" else None


# Accesorios que llegan bajo la categoría de un equipo (mochilas de notebook, teclados y lápices de iPad).
_ACCESORIO_DE_EQUIPO = re.compile(r"(?i)\bmochila\b|\bpencil\b|magic\s+keyboard|\bfunda\b|\bcase\b")


def _seccion_de(producto):
    nombre = producto.get("nombre", "")
    # Categoría "Electro" explícita (pestañas Hogar y Deco / Cafeteras del proveedor):
    # va a Electro sin mirar el nombre.
    if producto.get("categoria") == "Electro":
        return "Electro"
    if _ACCESORIO_DE_EQUIPO.search(nombre):
        return "Accesorios Celulares"
    categoria_marca = producto.get("categoria", "")
    if categoria_marca not in _CATEGORIAS_FIJAS_APPLE:
        if tipo_electro_de(producto):
            return "Electro"
        if _CHROMEBOOK.search(nombre):
            return "Notebooks y Macbooks"
        if _MONITOR_GAMER.search(nombre):
            return "Gaming"
        if _NO_ES_CELULAR.search(nombre) and not _TABLET_PATTERN.search(nombre):
            return "Accesorios Celulares"
    if _TABLET_PATTERN.search(nombre):
        return "Tablets"
    if _CARGADOR_CELULAR.search(nombre):
        return "Accesorios Celulares"
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
    # Notebooks: el pipeline las trae todas bajo la categoría "Notebook".
    (re.compile(r"(?i)\bhp\b"), "HP"),
    (re.compile(r"(?i)\blenovo\b"), "Lenovo"),
    (re.compile(r"(?i)\basus\b"), "Asus"),
    (re.compile(r"(?i)\bacer\b"), "Acer"),
    (re.compile(r"(?i)\bdell\b"), "Dell"),
    (re.compile(r"(?i)\bmsi\b"), "MSI"),
    (re.compile(r"(?i)\bgigabyte\b"), "Gigabyte"),
    (re.compile(r"(?i)\bxtrem\b"), "Xtrem"),
    (re.compile(r"(?i)\bapple\b"), "Apple"),
    (re.compile(r"(?i)\bsamsung\b|\bgalaxy\b|^\s*a\d{2}s?\s+\d"), "Samsung"),
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
    nombre = producto.get("nombre", "")
    # El pipeline manda todo reloj a "Apple - Watch" (Xiaomi, Haylou, ...):
    # ahí solo es Apple si el nombre lo dice.
    ambigua = categoria == "Apple - Watch" and not re.search(r"(?i)apple", nombre)
    if categoria in _MARCA_POR_CATEGORIA and not ambigua:
        return _MARCA_POR_CATEGORIA[categoria]
    for patron, marca in _MARCA_POR_PALABRA:
        if patron.search(nombre):
            return marca
    return "Otras marcas"


def secciones_catalogo(productos):
    resultado = {seccion: [] for seccion in SECCIONES}
    for producto in productos:
        enriquecido = {**producto, "marca": marca_de(producto), "slug": slug(producto["nombre"])}
        seccion = _seccion_de(producto)
        if seccion == "Electro":
            enriquecido["tipo_electro"] = tipo_electro_de(producto)
        resultado[seccion].append(enriquecido)
    return resultado
