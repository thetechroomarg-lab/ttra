"""Revalidación y envío único de una versión de campaña aprobada."""
import hashlib
import logging
import re
import secrets
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

from web.mailing import campanias, destinatarios

logger = logging.getLogger(__name__)


class CampaniaDesactualizada(RuntimeError):
    pass


class AssetAusente(RuntimeError):
    pass


@dataclass(frozen=True)
class ResultadoEnvio:
    total: int
    ok: int
    fallidos: int


def _validar_catalogo(manifiesto, catalogo):
    from web.mailing.servicio import huella_comercial

    nombres = [producto.get("nombre") for producto in manifiesto.get("productos", [])]
    por_nombre = {producto.get("nombre"): producto for producto in catalogo}
    if not nombres or any(nombre not in por_nombre for nombre in nombres):
        return False
    actuales = [por_nombre[nombre] for nombre in nombres]
    return secrets.compare_digest(
        huella_comercial(actuales), str(manifiesto.get("catalog_sha256", ""))
    )


def _asset_aprobado_existe(manifiesto, assets_root):
    hero = manifiesto.get("hero") or {}
    url = urlparse(str(hero.get("url", "")))
    digest_esperado = str(manifiesto.get("asset_sha256", ""))
    partes = url.path.strip("/").split("/")
    if len(partes) != 4 or partes[:2] != ["mailing", "assets"]:
        return False
    try:
        campaign_id = str(UUID(partes[2]))
    except ValueError:
        return False
    match = re.fullmatch(r"([0-9a-f]{64})\.(jpg|png|webp)", partes[3])
    if not match or not secrets.compare_digest(match.group(1), digest_esperado):
        return False
    path = Path(assets_root) / campaign_id / partes[3]
    if not path.is_file():
        return False
    digest_actual = hashlib.sha256(path.read_bytes()).hexdigest()
    return secrets.compare_digest(digest_actual, digest_esperado)


def _personalizar_baja(html, cliente_id):
    marcador = "__CLIENTE_ID__"
    if html.count(marcador) != 1:
        raise ValueError("El HTML no contiene un marcador único para la baja")
    cliente_id = str(UUID(str(cliente_id)))
    return html.replace(marcador, cliente_id)


def _registrar_detalle(client, version_id, cliente_id, estado, error=None):
    client.table("mailing_envios_detalle").insert({
        "version_id": str(version_id),
        "cliente_id": str(cliente_id),
        "estado": estado,
        "error": error,
    }).execute()


def enviar_version(client, version_id, catalogo, sender, assets_root):
    version = campanias.obtener_version(client, version_id)
    if not version:
        raise ValueError("La campaña no existe")
    if version.get("estado") != "aprobado":
        raise campanias.InvalidTransition("La campaña no está aprobada para envío")

    manifiesto = version["manifest"]
    if not _validar_catalogo(manifiesto, catalogo):
        campanias.transicionar(client, version_id, "aprobado", "invalidado")
        raise CampaniaDesactualizada("El catálogo cambió desde que se aprobó la campaña")
    if not _asset_aprobado_existe(manifiesto, assets_root):
        raise AssetAusente("No se encuentra el arte aprobado en el almacenamiento")

    campanias.transicionar(client, version_id, "aprobado", "enviando")
    clientes = destinatarios.clientes_elegibles(client)
    ok = 0
    fallidos = 0
    for cliente in clientes:
        estado = "ok"
        error = None
        try:
            html_cliente = _personalizar_baja(manifiesto["html"], cliente["id"])
            sender(cliente["email"], manifiesto["asunto"], html_cliente)
            ok += 1
        except Exception as exc:
            estado = "fallido"
            error = type(exc).__name__
            fallidos += 1
            logger.warning(
                "Falló envío de mailing versión %s a cliente %s (%s)",
                version_id, cliente.get("id"), error,
            )
        try:
            _registrar_detalle(client, version_id, cliente["id"], estado, error)
        except Exception:
            # El estado enviando queda bloqueado ante una falla de persistencia;
            # nunca se reintenta una campaña que pudo haber sido enviada.
            logger.exception("No se pudo registrar resultado del mailing versión %s", version_id)

    resultado = ResultadoEnvio(total=len(clientes), ok=ok, fallidos=fallidos)
    campanias.transicionar(
        client, version_id, "enviando", "enviado", {"resultado": asdict(resultado)}
    )
    return resultado
