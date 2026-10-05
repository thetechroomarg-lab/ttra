"""Mail automático a los 30 días del recibo: le recomienda al cliente 5
productos que combinan con lo que compró. Corre en el mismo cron diario que
el seguimiento de 7 días (ver seguimiento.py), con la misma mecánica: ventana
de días para no depender de la hora exacta y una columna que marca el envío.

La recomendación es por reglas, sin IA: se detecta la "familia" de lo que
compró (iPhone, Android, Mac, notebook...) y se eligen complementos de esa
familia, uno por grupo antes de repetir. Nunca entran usados/CPO, cargadores
(los únicos que se venden son de stock propio y no están en el catálogo
como tales) ni otro equipo de la misma familia que el que ya compró."""
import random
from datetime import datetime, timezone

from web import email_util, entregas
from web.mailing import template
from web.mailing.catalogo_diff import es_usado

DIAS_HASTA_RECOMENDACION = 30
# Igual que en el seguimiento: acota la primera corrida y los reintentos.
DIAS_MAXIMOS_RECOMENDACION = 37
CANTIDAD = 5

_TELEFONOS_ANDROID = {"Samsung", "Xiaomi", "Motorola", "Realme"}
_MARCAS_ANDROID = ("galaxy", "redmi", "xiaomi", "poco ", "motorola", "moto ", "realme", "oppo", "infinix", "pixel")

# Grupo -> palabras que tiene que tener el nombre (en minúscula) o la categoría exacta.
_GRUPOS = {
    "airpods": {"categoria": "Apple - AirPods"},
    "apple_watch": {"categoria": "Apple - Watch"},
    "airtag": {"palabras": ("airtag",)},
    "magsafe": {"palabras": ("magsafe",)},
    "parlante": {"palabras": ("parlante",)},
    "auriculares": {"palabras": ("auricular", "qcy", "jbl tune", "haylou s", "haylou mori", "haylou hq",
                                 "kz edx", "jbl endurance", "jbl quantum")},
    "smartwatch": {"palabras": ("haylou solar", "haylou ls", "haylou iron", "amazfit", "garmin")},
    "memoria": {"palabras": ("micro sd", "pendrive")},
    "mouse": {"palabras": ("mouse",)},
    "hub": {"palabras": ("hub", "adaptador multifuncion")},
    "mochila": {"palabras": ("mochila",)},
    "monitor": {"palabras": ("monitor",)},
    "pencil": {"palabras": ("apple pencil",)},
    "teclado_ipad": {"palabras": ("magic keyboard",)},
    "malla": {"palabras": ("malla silicona",)},
    "joystick": {"palabras": ("joystick", "dualsense")},
}

_COMPLEMENTOS = {
    "iphone": ("airpods", "apple_watch", "airtag", "magsafe", "parlante"),
    "android": ("auriculares", "smartwatch", "memoria", "parlante"),
    "mac": ("mouse", "hub", "airpods", "mochila", "monitor", "memoria"),
    "notebook": ("mouse", "hub", "mochila", "auriculares", "monitor", "memoria"),
    "ipad": ("pencil", "teclado_ipad", "airpods", "hub"),
    "watch": ("airpods", "airtag", "malla", "magsafe"),
    "airpods": ("apple_watch", "airtag", "parlante"),
    "consola": ("joystick", "auriculares", "parlante"),
    "otros": ("auriculares", "parlante", "smartwatch", "airpods"),
}

_CATEGORIAS_ACCESORIOS = {"Otros", "Apple - AirPods", "Apple - Watch"}


def _familia(nombre, categoria=""):
    texto = (nombre or "").lower()
    if "iphone" in texto:
        return "iphone"
    if "macbook" in texto or categoria == "Mac":
        return "mac"
    if "ipad" in texto or categoria == "Apple - iPad":
        return "ipad"
    if "airpods" in texto or categoria == "Apple - AirPods":
        return "airpods"
    if "apple watch" in texto or categoria == "Apple - Watch":
        return "watch"
    if "notebook" in texto or categoria == "Notebook":
        return "notebook"
    if "joystick" in texto or "dualsense" in texto:
        return "otros"
    if any(consola in texto for consola in ("playstation", "nintendo", "xbox", "consola")):
        return "consola"
    if categoria in _TELEFONOS_ANDROID or any(marca in texto for marca in _MARCAS_ANDROID):
        return "android"
    return "otros"


def _en_grupo(producto, grupo):
    regla = _GRUPOS[grupo]
    if "categoria" in regla:
        return producto.get("categoria") == regla["categoria"]
    texto = (producto.get("nombre") or "").lower()
    return any(palabra in texto for palabra in regla["palabras"])


def _nombres_comprados(pedido):
    detalle = pedido.get("detalle") or []
    nombres = [item.get("nombre") for item in detalle if item.get("nombre")]
    return nombres or [n for n in (pedido.get("productos") or []) if n]


def recomendar(pedido, catalogo, cantidad=CANTIDAD):
    comprados = _nombres_comprados(pedido)
    categorias = {p.get("nombre"): p.get("categoria", "") for p in catalogo}
    familias = []
    for nombre in comprados:
        familia = _familia(nombre, categorias.get(nombre, ""))
        if familia not in familias:
            familias.append(familia)
    # Un accesorio suelto no excluye a los demás accesorios; un equipo sí
    # excluye a los de su familia (no le ofrecemos otro iPhone a quien compró uno).
    familias_excluidas = set(familias) - {"otros"}
    # Nada más caro que lo más caro que compró: a quien gastó US$1500 en una
    # Mac no le sugerimos un monitor de US$2200.
    precios = {p.get("nombre"): p.get("usd") or 0 for p in catalogo}
    tope = max((precios.get(nombre, 0) for nombre in comprados), default=0) or None

    elegibles = [
        p for p in catalogo
        if p.get("nombre") not in comprados
        and not es_usado(p)
        and "cargador" not in (p.get("nombre") or "").lower()
        and 0 < (p.get("usd") or 0) <= (tope or float("inf"))
        and _familia(p.get("nombre"), p.get("categoria", "")) not in familias_excluidas
    ]
    rng = random.Random(str(pedido.get("id")))
    rng.shuffle(elegibles)

    grupos = []
    for familia in familias or ["otros"]:
        for grupo in _COMPLEMENTOS[familia]:
            if grupo not in grupos:
                grupos.append(grupo)
    candidatos = {grupo: [p for p in elegibles if _en_grupo(p, grupo)] for grupo in grupos}

    elegidos = []
    nombres_elegidos = set()

    def _sumar(producto):
        if producto.get("nombre") not in nombres_elegidos and len(elegidos) < cantidad:
            elegidos.append(producto)
            nombres_elegidos.add(producto.get("nombre"))

    # Una vuelta por grupo antes de repetir: variedad antes que cinco auriculares.
    hubo_cambios = True
    while len(elegidos) < cantidad and hubo_cambios:
        hubo_cambios = False
        for grupo in grupos:
            restantes = [p for p in candidatos[grupo] if p.get("nombre") not in nombres_elegidos]
            if restantes:
                _sumar(restantes[0])
                hubo_cambios = True

    for producto in elegibles:
        if producto.get("categoria") in _CATEGORIAS_ACCESORIOS:
            _sumar(producto)
    for producto in elegibles:
        _sumar(producto)
    return elegidos


def _fecha_recibo_argentina(recibo_enviado_en):
    return datetime.fromisoformat(recibo_enviado_en).astimezone(entregas.ZONA_HORARIA).date()


def pedidos_para_recomendar(client, hoy=None):
    hoy = hoy or entregas.ahora_argentina().date()
    resultado = []
    for pedido in client.table("pedidos").select("*").execute().data:
        if not pedido.get("cliente_id") or pedido.get("recomendacion_enviado_en"):
            continue
        if not pedido.get("recibo_enviado_en"):
            continue
        dias = (hoy - _fecha_recibo_argentina(pedido["recibo_enviado_en"])).days
        if DIAS_HASTA_RECOMENDACION <= dias <= DIAS_MAXIMOS_RECOMENDACION:
            resultado.append(pedido)
    return resultado


def html_recomendacion(cliente, pedido, productos):
    nombre = (cliente.get("nombre") or "").strip()
    saludo = f"Hola {nombre}," if nombre else "Hola,"
    compra = ", ".join(_nombres_comprados(pedido)) or "tu compra"
    intro = (
        f"{saludo} hace un mes te entregué {compra}. Espero que lo estés disfrutando. "
        "Te dejo algunos productos que combinan con tu compra:"
    )
    return template.armar_html(
        productos,
        cliente_id=cliente["id"],
        subtitulo="Elegidos para vos",
        intro=intro,
        preheader="Algunas ideas para acompañar tu compra",
    )


def _marcar(client, pedido_id):
    client.table("pedidos").update({
        "recomendacion_enviado_en": datetime.now(timezone.utc).isoformat(),
    }).eq("id", pedido_id).execute()


def enviar_recomendaciones(client, catalogo, hoy=None, enviar_email_fn=None):
    if not catalogo:
        raise ValueError("Sin catálogo no se puede recomendar nada")
    enviar_email_fn = enviar_email_fn or email_util.enviar_email
    # Si la columna todavía no existe en la base, esto falla antes de mandar
    # nada: sin poder marcar los pedidos, cada corrida volvería a mailearlos.
    client.table("pedidos").select("id, recomendacion_enviado_en").execute()
    enviados = 0
    fallidos = 0
    for pedido in pedidos_para_recomendar(client, hoy=hoy):
        filas = client.table("clientes").select("*").eq("id", pedido["cliente_id"]).execute().data
        cliente = filas[0] if filas else {}
        email = (cliente.get("email") or "").strip()
        if not email or cliente.get("no_mailing"):
            # Se marca igual: si mañana se suscribe, no tiene sentido mandarle
            # una recomendación de una compra ya vieja.
            if cliente:
                _marcar(client, pedido["id"])
            continue
        productos = recomendar(pedido, catalogo)
        try:
            enviar_email_fn(
                email,
                "Algunas ideas para acompañar tu compra — The Tech Room Arg",
                html_recomendacion(cliente, pedido, productos),
            )
        except email_util.EnvioEmailError:
            fallidos += 1
            continue
        _marcar(client, pedido["id"])
        enviados += 1
    return {"enviados": enviados, "fallidos": fallidos}
