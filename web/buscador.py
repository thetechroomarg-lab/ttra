"""Motor de chat SIN IA (gratis): búsqueda por palabras + máquina de estados simple.
Mantiene: pedir nombre, buscar productos, carrito, garantía, envíos, pedido por WhatsApp
y avatar por género. No usa ninguna API paga."""
import re
import sys
from urllib.parse import quote

sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.dirname(__file__)))
from normalize import normalizar
from web.reglas import WHATSAPP

SESIONES = {}  # sesion -> estado

# nombres típicos masculinos que terminan en vocal distinta al patrón "a=mujer"
_EXCEP_HOMBRE = {"luca", "lucca", "matias", "tomas", "elias", "jonas", "nicolas", "andrea"}


def _estado(sesion):
    return SESIONES.setdefault(sesion, {"nombre": None, "genero": "", "carrito": [],
                                        "ultimos": [], "sel": None})


def _genero(nombre):
    n = normalizar(nombre).split()[0] if nombre else ""
    if not n:
        return ""
    if n in _EXCEP_HOMBRE:
        return "hombre"
    return "mujer" if n.endswith("a") else "hombre"


def _money(v):
    return f"{v:,}".replace(",", ".")


def _precios(p):
    return (f"🇺🇸 U$D {p['usd']} · 🇦🇷 $ {_money(p['pesos'])} · "
            f"🏦 $ {_money(p['transferencia'])}")


_MARCAS = {"samsung", "xiaomi", "motorola", "moto", "apple", "realme"}


def _buscar(query, productos):
    toks = [t for t in normalizar(query).split() if len(t) >= 2]
    if not toks:
        return []
    res = [p for p in productos if all(t in normalizar(p["nombre"]) for t in toks)]
    if not res:
        # la marca suele no estar en el nombre del catálogo: reintento sin marcas
        rest = [t for t in toks if t not in _MARCAS]
        if rest and len(rest) < len(toks):
            res = [p for p in productos if all(t in normalizar(p["nombre"]) for t in rest)]
    return sorted(res, key=lambda p: p["usd"])


def _listar(res, nombre):
    lineas = [f"¡Genial, {nombre}! Encontré esto 👇", ""]
    for i, p in enumerate(res, 1):
        lineas.append(f"{i}. {p['nombre']}")
        lineas.append(_precios(p))
        lineas.append("")
    lineas.append("🇺🇸 = dólares · 🇦🇷 = pesos · 🏦 = transferencia en pesos")
    lineas.append("Respondé con el número del que te interesa 🙂")
    return "\n".join(lineas)


def _mostrar_sel(p):
    return (f"Elegiste:\n\n{p['nombre']}\n{_precios(p)}\n\n"
            "¿Qué querés hacer?\nA. Agregar al carrito\n"
            "B. Agregar y cerrar compra\nC. Seguir comprando")


def _resumen_carrito(carrito):
    lineas = ["🛒 Tu carrito:", ""]
    tu = tp = tt = 0
    for p in carrito:
        lineas.append(f"• {p['nombre']}")
        lineas.append(f"  {_precios(p)}")
        tu += p["usd"]; tp += p["pesos"]; tt += p["transferencia"]
    lineas.append("")
    lineas.append(f"💰 TOTAL: 🇺🇸 U$D {tu} · 🇦🇷 $ {_money(tp)} · 🏦 $ {_money(tt)}")
    return "\n".join(lineas), tu, tp, tt


def _cerrar(st):
    if not st["carrito"]:
        return "Todavía no agregaste nada al carrito 🙂 ¿Qué estás buscando?"
    resumen, tu, tp, tt = _resumen_carrito(st["carrito"])
    pedido = [f"¡Hola! Soy {st['nombre']}, quiero hacer este pedido:", ""]
    for p in st["carrito"]:
        pedido.append(f"- {p['nombre']} (U$D {p['usd']} / $ {_money(p['pesos'])})")
    pedido.append("")
    pedido.append(f"TOTAL: U$D {tu} / $ {_money(tp)} / transferencia $ {_money(tt)}")
    link = WHATSAPP + "?text=" + quote("\n".join(pedido))
    return (resumen + "\n\n👉 Tocá este enlace para enviarme tu pedido por WhatsApp "
            "y coordinar pago y envío:\n" + link)


def _garantia(ml):
    if "notebook" in ml or "laptop" in ml:
        return ("🛡️ Garantía notebooks: 6 meses desde la entrega. Cubre solo fallas de "
                "fábrica (no caídas, humedad ni mal uso). Requiere caja y accesorios.")
    if any(k in ml for k in ("iphone", "ipad", "mac", "apple", "airpod", "watch")):
        return ("🛡️ Garantía Apple (productos nuevos): 12 meses. Se ejecuta directamente en "
                "One Click (Córdoba Shopping) o MacStation (Nuevocentro Shopping).")
    marca = "Samsung" if "samsung" in ml else ("Motorola" if "moto" in ml else
             ("Xiaomi" if any(k in ml for k in ("xiaomi", "redmi", "poco")) else "el equipo"))
    return (f"🛡️ Garantía {marca}: 3 meses desde la entrega. Cubre solo fallas de fábrica "
            "(no caídas, rayones, humedad ni mal uso). Pantalla/accesorios: 7 días. Requiere "
            "caja original, accesorios y sin cuentas activas. Soy intermediario con el "
            "importador; te mantengo informado durante el proceso.")


def _envios():
    return ("📦 Envíos: tengo cadetería sin costo.\n"
            "🕕 Lunes a viernes después de las 18:00 y sábados por la mañana hasta las 13:00.\n"
            "Para el mismo día (lun a vie) confirmá antes de las 14:00; para el sábado, antes "
            "del viernes 14:00.\n"
            "💵 En pesos por transferencia: se abona el mismo día del pedido. En efectivo al "
            "recibir: cotización del momento. En dólares: el precio no cambia.\n"
            "🔐 Por seguridad no entrego en zonas peligrosas; si hace falta coordinamos un "
            "punto seguro. Siempre prefiero entregar en tu domicilio.")


def responder_sin_ia(mensaje, sesion, productos):
    """Devuelve (texto, genero, datos_lead)."""
    st = _estado(sesion)
    m = (mensaje or "").strip()
    ml = m.lower()

    # 1) primero el nombre (obligatorio)
    if not st["nombre"]:
        nombre = re.sub(r"^(hola|buenas|hi|hey)\b[\s,]*", "", m, flags=re.IGNORECASE).strip()
        nombre = re.sub(r"^(soy|me llamo|mi nombre es)\s+", "", nombre, flags=re.IGNORECASE).strip()
        nombre = nombre.split(",")[0].split(".")[0].strip()[:40]
        if not nombre:
            return ("Necesito tu nombre para atenderte 🙂 ¿Cómo te llamás?", "", None)
        st["nombre"] = nombre
        st["genero"] = _genero(nombre)
        saludo = (f"¡Genial, {nombre}! 🙌 ¿Qué estás buscando? Escribime un modelo "
                  "(ej.: iPhone 13, Samsung A16, notebook) y te muestro precios.")
        return (saludo, st["genero"], {"nombre": nombre, "genero": st["genero"], "productos": []})

    # 2) comandos globales
    if "garant" in ml:
        return (_garantia(ml), st["genero"], None)
    if any(k in ml for k in ("envio", "envío", "entrega", "cadeter")):
        return (_envios(), st["genero"], None)
    if ml in ("listo", "cerrar", "terminar", "finalizar", "eso es todo", "cerrar compra",
              "pagar", "cerramos"):
        return (_cerrar(st), st["genero"], None)

    # 3) acción A/B/C sobre el ítem seleccionado
    if st["sel"] is not None and ml in ("a", "b", "c"):
        sel = st["sel"]
        if ml == "a":
            st["carrito"].append(sel); st["sel"] = None
            resumen, *_ = _resumen_carrito(st["carrito"])
            return (f"✅ Lo agregué al carrito.\n\n{resumen}\n\n¿Buscás algo más? "
                    "Escribime otro modelo, o poné *listo* para cerrar.",
                    st["genero"], {"productos": [sel["nombre"]]})
        if ml == "b":
            st["carrito"].append(sel); st["sel"] = None
            return (_cerrar(st), st["genero"], {"productos": [sel["nombre"]]})
        st["sel"] = None
        return ("¡Dale! ¿Qué otro modelo estás buscando?", st["genero"], None)

    # 4) selección por número de la última lista
    if ml.isdigit() and st["ultimos"]:
        idx = int(ml) - 1
        if 0 <= idx < len(st["ultimos"]):
            st["sel"] = st["ultimos"][idx]
            return (_mostrar_sel(st["sel"]), st["genero"], None)
        return ("Ese número no está en la lista 🙈 Probá con otro.", st["genero"], None)

    # 5) búsqueda por palabras
    res = _buscar(m, productos)
    st["ultimos"] = res
    if not res:
        return (f"Uy, no encontré nada para \"{m}\" 😅. Probá con otro modelo o marca "
                "(ej.: iPhone, Samsung, Xiaomi, Motorola, notebook).", st["genero"],
                {"productos": [m]})
    res_top = res[:12]
    st["ultimos"] = res_top
    return (_listar(res_top, st["nombre"]), st["genero"],
            {"productos": [p["nombre"] for p in res_top[:5]]})
