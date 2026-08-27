import uuid
from datetime import datetime, timezone
import random
import re
from collections import Counter

from web import catalogo


def guardar_interaccion(
    client,
    tipo_evento,
    *,
    cliente_id=None,
    anon_id=None,
    session_id=None,
    producto_nombre=None,
    categoria=None,
    marca=None,
    metadata=None,
):
    fila = {
        "id": str(uuid.uuid4()),
        "cliente_id": cliente_id,
        "anon_id": anon_id,
        "session_id": session_id,
        "tipo_evento": tipo_evento,
        "producto_nombre": producto_nombre,
        "categoria": categoria,
        "marca": marca,
        "metadata": metadata or {},
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    client.table("interacciones_cliente").insert(fila).execute()
    return fila


def vincular_interacciones_anonimas(client, anon_id, cliente_id):
    if not anon_id or not cliente_id:
        return []
    return (
        client.table("interacciones_cliente")
        .update({"cliente_id": cliente_id})
        .eq("anon_id", anon_id)
        .execute()
        .data
    )


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_TOKENS_IGNORADOS = {
    "de", "del", "con", "para", "por", "the", "room", "arg", "apple",
    "samsung", "xiaomi", "motorola", "realme", "oppo", "honor", "infinix",
    "nokia", "itel", "jbl", "logitech", "sony", "playstation", "nintendo",
    "gb", "ram", "wifi", "5g", "4g", "lte", "inch", "pulgadas",
}


def _es_producto_usado(producto):
    texto = f"{producto.get('nombre', '')} {producto.get('categoria', '')}".lower()
    return "usado" in texto or "cpo" in texto


def _tokens_producto(producto):
    nombre = (producto.get("nombre") or "").lower()
    return {
        token for token in _TOKEN_RE.findall(nombre)
        if len(token) > 1 and token not in _TOKENS_IGNORADOS
    }


def _normalizar_catalogo(productos):
    normalizados = []
    for producto in productos:
        if _es_producto_usado(producto):
            continue
        normalizados.append({
            **producto,
            "marca": producto.get("marca") or catalogo.marca_de(producto),
            "seccion": catalogo.seccion_de(producto),
            "_tokens": _tokens_producto(producto),
        })
    return normalizados


def _producto_publico(producto):
    limpio = dict(producto)
    limpio.pop("_tokens", None)
    return limpio


def _puntaje_similitud(base, candidato):
    puntaje = 0
    if base.get("seccion") == candidato.get("seccion"):
        puntaje += 5
    if base.get("marca") == candidato.get("marca"):
        puntaje += 4
    if base.get("categoria") == candidato.get("categoria"):
        puntaje += 2
    comunes = len(base.get("_tokens", set()) & candidato.get("_tokens", set()))
    puntaje += comunes * 3
    return puntaje


def _candidato_con_motivo(producto, motivo):
    return _producto_publico({**producto, "motivo_recomendacion": motivo})


def recomendar_productos(productos, filas_interacciones, limite=8):
    catalogo_actual = _normalizar_catalogo(productos)
    if not catalogo_actual or limite <= 0:
        return []

    por_nombre = {p["nombre"]: p for p in catalogo_actual}
    interacciones_producto = [
        fila for fila in (filas_interacciones or [])
        if fila.get("tipo_evento") in {"view_item", "select_product", "view_product"} and fila.get("producto_nombre")
    ]
    interacciones_producto.sort(key=lambda fila: fila.get("fecha", ""), reverse=True)

    if not interacciones_producto:
        mezcla = catalogo_actual[:]
        random.shuffle(mezcla)
        return [_candidato_con_motivo(p, "✨ Recomendado para vos") for p in mezcla[:limite]]

    frecuencia = Counter(fila["producto_nombre"] for fila in interacciones_producto)
    orden_reciente = []
    vistos = set()
    for fila in interacciones_producto:
        nombre = fila["producto_nombre"]
        if nombre not in vistos:
            vistos.add(nombre)
            orden_reciente.append(nombre)

    semillas = sorted(
        orden_reciente,
        key=lambda nombre: (-frecuencia[nombre], orden_reciente.index(nombre)),
    )

    recomendaciones = []
    nombres_agregados = set()

    def agregar(producto, motivo):
        nombre = producto["nombre"]
        if nombre in nombres_agregados or len(recomendaciones) >= limite:
            return
        recomendaciones.append(_candidato_con_motivo(producto, motivo))
        nombres_agregados.add(nombre)

    for nombre in semillas:
        producto = por_nombre.get(nombre)
        if producto:
            agregar(producto, "✨ Ya viste este producto")

    for nombre in semillas:
        base = por_nombre.get(nombre)
        if not base or len(recomendaciones) >= limite:
            continue
        similares = sorted(
            (
                candidato for candidato in catalogo_actual
                if candidato["nombre"] != base["nombre"]
                and candidato["nombre"] not in nombres_agregados
            ),
            key=lambda candidato: (
                -_puntaje_similitud(base, candidato),
                candidato["nombre"],
            ),
        )
        for candidato in similares:
            if _puntaje_similitud(base, candidato) <= 0:
                break
            agregar(candidato, f"✨ Similar a {base['nombre']}")
            if len(recomendaciones) >= limite:
                break

    if len(recomendaciones) < limite:
        restantes = [p for p in catalogo_actual if p["nombre"] not in nombres_agregados]
        random.shuffle(restantes)
        for producto in restantes[:limite - len(recomendaciones)]:
            agregar(producto, "✨ Recomendado para vos")

    return recomendaciones


def recomendar_nombres(productos, filas_interacciones, limite=8):
    """Rank public product names without making ranked objects response data."""
    return [
        {
            "nombre": producto["nombre"],
            "motivo_recomendacion": producto["motivo_recomendacion"],
        }
        for producto in recomendar_productos(productos, filas_interacciones, limite)
    ]
