"""Validación y almacenamiento persistente de imágenes promocionales."""
import hashlib
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import UUID

from PIL import Image, UnidentifiedImageError


MAX_BYTES = 3 * 1024 * 1024
MIN_WIDTH, MAX_WIDTH = 600, 2400
MIN_HEIGHT, MAX_HEIGHT = 300, 1800
FORMATOS = {
    "image/jpeg": ("JPEG", ".jpg"),
    "image/png": ("PNG", ".png"),
    "image/webp": ("WEBP", ".webp"),
}


@dataclass(frozen=True)
class Asset:
    path: Path
    filename: str
    sha256: str
    content_type: str
    width: int
    height: int


def guardar_asset(root: Path, campaign_id, content: bytes, content_type: str) -> Asset:
    """Valida una imagen por sus bytes y la guarda bajo UUID + hash."""
    try:
        campaign_id = UUID(str(campaign_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("Identificador de campaña inválido") from exc

    if not isinstance(content, bytes) or not content:
        raise ValueError("El archivo está vacío")
    if len(content) > MAX_BYTES:
        raise ValueError("La imagen supera 3 MiB")
    if content_type not in FORMATOS:
        raise ValueError("Tipo de imagen no permitido")

    formato_esperado, extension = FORMATOS[content_type]
    try:
        with Image.open(BytesIO(content)) as imagen:
            formato_real = imagen.format
            imagen.verify()
        with Image.open(BytesIO(content)) as imagen:
            ancho, alto = imagen.size
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("El archivo no contiene una imagen válida") from exc

    if formato_real != formato_esperado:
        raise ValueError("El contenido no coincide con el tipo declarado")
    if not (MIN_WIDTH <= ancho <= MAX_WIDTH and MIN_HEIGHT <= alto <= MAX_HEIGHT):
        raise ValueError("Dimensiones fuera de rango")

    digest = hashlib.sha256(content).hexdigest()
    filename = f"{digest}{extension}"
    destino = Path(root) / str(campaign_id) / filename
    destino.parent.mkdir(parents=True, exist_ok=True)
    if not destino.exists():
        destino.write_bytes(content)
    return Asset(destino, filename, digest, content_type, ancho, alto)
