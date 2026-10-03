"""Reglas puras para preparar campañas visuales desde el catálogo vigente."""
import hashlib
import json
import re
import secrets
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID


def seleccionar_productos(catalogo, nombres):
    por_nombre = {producto.get("nombre"): producto for producto in catalogo}
    faltantes = [nombre for nombre in nombres if nombre not in por_nombre]
    if faltantes:
        raise ValueError(f"Productos inexistentes: {', '.join(faltantes)}")
    return [dict(por_nombre[nombre]) for nombre in nombres]


def huella_comercial(productos):
    campos = [
        {campo: producto.get(campo) for campo in ("nombre", "usd", "pesos", "transferencia")}
        for producto in productos
    ]
    bruto = json.dumps(campos, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(bruto.encode("utf-8")).hexdigest()


def verificar_asset(root: Path, campaign_id, hero, base_url):
    try:
        uuid_campania = UUID(str(campaign_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Identificador de campaña inválido") from exc
    url = str(hero.get("url", "")).strip()
    parsed = urlparse(url)
    expected = urlparse(base_url)
    if parsed.scheme != "https" and expected.hostname != "testserver":
        raise ValueError("La URL del arte debe usar HTTPS")
    if parsed.netloc != expected.netloc:
        raise ValueError("El arte debe estar publicado en el dominio de la web")
    prefijo = f"/mailing/assets/{uuid_campania}/"
    if not parsed.path.startswith(prefijo):
        raise ValueError("La URL no corresponde a esta campaña")
    filename = parsed.path[len(prefijo):]
    match = re.fullmatch(r"([0-9a-f]{64})\.(jpg|png|webp)", filename)
    if not match or not secrets.compare_digest(match.group(1), str(hero.get("sha256", ""))):
        raise ValueError("El hash del arte no coincide con el manifiesto")
    path = Path(root) / str(uuid_campania) / filename
    if not path.is_file():
        raise ValueError("El arte aprobado no existe en el almacenamiento persistente")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if not secrets.compare_digest(digest, match.group(1)):
        raise ValueError("El arte publicado no coincide con su hash")
    return path
