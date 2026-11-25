"""Stock de equipos usados: cada unidad es única y propia, así que se da de baja
del catálogo en cuanto se envía el recibo de la venta.

Se saca de los cuatro archivos del catálogo (productos, costos, proveedores y
manifest) para que el manifest siga coincidiendo con los hashes y el catálogo
mayorista no quede cerrado.
"""
import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from web.productos import CATALOGO_MANIFEST_NOMBRE, CATALOGO_MANIFEST_VERSION, _escribir_json_atomico

_USADO = re.compile(r"(?i)\busad[oa]s?\b")
_TRABA = threading.Lock()

CATEGORIA = "Apple - iPhone Usado"
REGISTRO_NOMBRE = "usados-publicados.json"
FOTOS_DIR = "usados-fotos"
# Se publican las seis fotos del equipo (frente, reverso, lados y bordes). Las
# dos capturas de pantalla (batería, piezas y servicio) quedan solo para Vlad.
FOTOS_PUBLICAS = 6


class UsadoError(Exception):
    pass


def es_usado(nombre):
    return bool(_USADO.search(nombre or ""))


def _leer(ruta, por_defecto):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return por_defecto


def _retirar(productos_path, vendidos):
    """Saca (nombre, color) del catálogo. Devuelve los nombres retirados.
    Quien llama ya tiene `_TRABA`."""
    productos = _leer(productos_path, None)
    if not isinstance(productos, list):
        return []
    retirados, quitar_del_todo = [], set()
    for item in vendidos:
        nombre, color = item.get("nombre"), (item.get("color") or "").strip()
        for producto in productos:
            if producto.get("nombre") != nombre:
                continue
            colores = producto.get("colores") or []
            if color and len(colores) > 1 and color in colores:
                producto["colores"] = [c for c in colores if c != color]
            else:
                quitar_del_todo.add(nombre)
            retirados.append(nombre)
            break
    if not retirados:
        return []
    productos = [p for p in productos if p.get("nombre") not in quitar_del_todo]
    costos_path = productos_path.with_name("costos.json")
    proveedores_path = productos_path.with_name("proveedores.json")
    manifiesto_path = productos_path.with_name(CATALOGO_MANIFEST_NOMBRE)
    costos = _leer(costos_path, None)
    proveedores = _leer(proveedores_path, None)
    manifiesto = _leer(manifiesto_path, None)
    productos_hash = _escribir_json_atomico(productos_path, productos)
    if isinstance(proveedores, dict):
        for nombre in quitar_del_todo:
            proveedores.pop(nombre, None)
        _escribir_json_atomico(proveedores_path, proveedores)
    costos_hash = None
    if isinstance(costos, dict):
        for nombre in quitar_del_todo:
            costos.pop(nombre, None)
        costos_hash = _escribir_json_atomico(costos_path, costos)
    if isinstance(manifiesto, dict):
        _escribir_json_atomico(manifiesto_path, {
            **manifiesto,
            "version": manifiesto.get("version", CATALOGO_MANIFEST_VERSION),
            "generacion": str(uuid.uuid4()),
            "productos_sha256": productos_hash,
            **({"costos_sha256": costos_hash} if costos_hash else {}),
        })
    return retirados


def dar_de_baja(detalle, productos_path):
    """Saca del catálogo los usados vendidos en `detalle`. Devuelve sus nombres."""
    vendidos = [i for i in detalle or [] if es_usado(i.get("nombre"))]
    if not vendidos:
        return []
    with _TRABA:
        return _retirar(Path(productos_path), vendidos)


# ---- Usados publicados desde Plan Canje ----

def _ahora():
    return datetime.now(timezone.utc).isoformat()


def _registro_path(productos_path):
    return Path(productos_path).with_name(REGISTRO_NOMBRE)


def _fotos_dir(productos_path):
    return Path(productos_path).with_name(FOTOS_DIR)


def leer_registro(productos_path):
    datos = _leer(_registro_path(productos_path), {})
    return datos if isinstance(datos, dict) else {}


def nombre_producto(canje, color_con_bateria):
    """Cada unidad usada es su propia card, y el servidor busca precios por
    nombre: el nombre lleva color y batería para que sea único.
    "iPhone 15 Pro" + "128 GB" + "Black 87%" -> "iPhone 15 Pro 128GB (Usado) Black 87%"."""
    capacidad = (canje.get("capacidad") or "").replace(" ", "")
    return f"{canje['modelo']} {capacidad} (Usado) {color_con_bateria}"


def color_publicado(color, bateria):
    return f"{color.strip()} {int(bateria)}%"


def publicar(productos_path, canje, fotos, usd, color, bateria, cotizacion):
    """Pone el equipo de un canje aprobado en la tienda, con las fotos que mandó
    el cliente. Cada unidad es su propia card, con su precio."""
    productos_path = Path(productos_path)
    usd = int(usd)
    colores = color_publicado(color, bateria)
    nombre = nombre_producto(canje, colores)
    with _TRABA:
        registro = leer_registro(productos_path)
        previo = registro.get(canje["id"]) or {}
        if previo.get("estado") == "vendido":
            raise UsadoError("Este equipo ya se vendió")
        if previo.get("estado") == "publicado":
            raise UsadoError("Este equipo ya está en la tienda")
        productos = _leer(productos_path, None)
        if not isinstance(productos, list):
            raise UsadoError("El catálogo no está disponible")
        if any(p.get("nombre") == nombre for p in productos):
            raise UsadoError(f"Ya hay un {nombre} en la tienda: cambiá el color o la batería para distinguirlo")
        carpeta = _fotos_dir(productos_path) / canje["id"]
        carpeta.mkdir(parents=True, exist_ok=True)
        rutas = []
        for i, contenido in enumerate(fotos[:FOTOS_PUBLICAS], start=1):
            (carpeta / f"{i}.jpg").write_bytes(contenido)
            rutas.append(f"/catalog-images/usados/{canje['id']}/{i}.jpg")
        pesos = round(usd * cotizacion)
        productos.append({
            "nombre": nombre, "categoria": CATEGORIA, "usd": usd, "pesos": pesos,
            "transferencia": round(pesos / 0.97),
            "link_imagen": f"https://www.google.com/search?tbm=isch&q={nombre.replace(' ', '+')}",
            "colores": [colores],
        })
        productos_hash = _escribir_json_atomico(productos_path, productos)
        manifiesto_path = productos_path.with_name(CATALOGO_MANIFEST_NOMBRE)
        manifiesto = _leer(manifiesto_path, None)
        if isinstance(manifiesto, dict):
            _escribir_json_atomico(manifiesto_path, {
                **manifiesto, "version": manifiesto.get("version", CATALOGO_MANIFEST_VERSION),
                "generacion": str(uuid.uuid4()), "productos_sha256": productos_hash,
            })
        registro[canje["id"]] = {
            "estado": "publicado", "nombre": nombre, "color": colores, "usd": usd,
            "fotos": rutas, "publicado_en": _ahora(),
        }
        _escribir_json_atomico(_registro_path(productos_path), registro)
        return registro[canje["id"]]


def quitar(productos_path, canje_id):
    """Lo saca de la tienda sin borrar el registro ni las fotos: se puede volver a publicar."""
    productos_path = Path(productos_path)
    with _TRABA:
        registro = leer_registro(productos_path)
        entrada = registro.get(canje_id) or {}
        if entrada.get("estado") == "vendido":
            raise UsadoError("Este equipo ya se vendió")
        if entrada.get("estado") != "publicado":
            raise UsadoError("Este equipo no está en la tienda")
        _retirar(productos_path, [{"nombre": entrada["nombre"], "color": entrada["color"]}])
        registro[canje_id] = {**entrada, "estado": "quitado", "quitado_en": _ahora()}
        _escribir_json_atomico(_registro_path(productos_path), registro)


def marcar_vendidos(detalle, productos_path):
    """Con el recibo enviado, los publicados que figuran en `detalle` pasan a
    "vendido". El canje queda en su historial; solo sale de la tienda."""
    vendidos = [i for i in detalle or [] if es_usado(i.get("nombre"))]
    if not vendidos:
        return []
    productos_path = Path(productos_path)
    with _TRABA:
        registro = leer_registro(productos_path)
        marcados = []
        for item in vendidos:
            color = (item.get("color") or "").strip()
            for canje_id, entrada in registro.items():
                if (entrada.get("estado") == "publicado" and entrada.get("nombre") == item.get("nombre")
                        and entrada.get("color") == color):
                    registro[canje_id] = {**entrada, "estado": "vendido", "vendido_en": _ahora()}
                    marcados.append(canje_id)
                    break
        if marcados:
            _escribir_json_atomico(_registro_path(productos_path), registro)
        return marcados


def entradas_de_imagenes(productos_path):
    """Entradas de catalog-images/index.json de los usados que hoy están en la tienda."""
    resultado = {}
    for entrada in leer_registro(productos_path).values():
        if entrada.get("estado") == "publicado" and entrada.get("fotos"):
            resultado.setdefault(entrada["nombre"], []).append(
                {"color": entrada["color"], "src": entrada["fotos"][0], "fotos": entrada["fotos"]})
    return resultado


def ruta_foto(productos_path, canje_id, archivo):
    """Ruta de una foto publicada, o None si el equipo no está en la tienda."""
    entrada = leer_registro(productos_path).get(canje_id) or {}
    if entrada.get("estado") != "publicado":
        return None
    ruta = _fotos_dir(productos_path) / canje_id / archivo
    return ruta if ruta.is_file() else None
