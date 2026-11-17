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
from pathlib import Path

from web.productos import CATALOGO_MANIFEST_NOMBRE, CATALOGO_MANIFEST_VERSION, _escribir_json_atomico

_USADO = re.compile(r"(?i)\busad[oa]s?\b")
_TRABA = threading.Lock()


def es_usado(nombre):
    return bool(_USADO.search(nombre or ""))


def _leer(ruta, por_defecto):
    try:
        return json.loads(Path(ruta).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return por_defecto


def dar_de_baja(detalle, productos_path):
    """Saca del catálogo los usados vendidos en `detalle`. Devuelve sus nombres."""
    vendidos = [i for i in detalle or [] if es_usado(i.get("nombre"))]
    if not vendidos:
        return []
    productos_path = Path(productos_path)
    with _TRABA:
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
