"""Repositorio y transiciones atómicas para versiones de campañas de mailing."""
import uuid


class InvalidTransition(RuntimeError):
    """La campaña no pudo avanzar desde el estado esperado."""


def crear_version(client, manifiesto):
    manifiesto = dict(manifiesto)
    parent_id = manifiesto.get("parent_id")
    campaign_id = manifiesto.get("campaign_id") or str(uuid.uuid4())
    version = 1
    if parent_id:
        padre = obtener_version(client, parent_id)
        if not padre:
            raise ValueError("La campaña padre no existe")
        campaign_id = padre["campaign_id"]
        version = int(padre["version"]) + 1
    manifiesto["campaign_id"] = campaign_id
    fila = {
        "campaign_id": campaign_id,
        "parent_id": parent_id,
        "version": version,
        "estado": "previsualizado",
        "manifest": manifiesto,
    }
    respuesta = client.table("mailing_campanias").insert(fila).execute().data
    if not respuesta:
        raise RuntimeError("Supabase no devolvió la campaña creada")
    return respuesta[0]


def obtener_version(client, version_id):
    filas = (
        client.table("mailing_campanias")
        .select("*")
        .eq("id", str(version_id))
        .execute()
        .data
    )
    return filas[0] if filas else None


def transicionar(client, version_id, desde, hacia, cambios=None):
    try:
        return client.rpc(
            "transicionar_mailing_campania",
            {
                "p_id": str(version_id),
                "p_desde": desde,
                "p_hacia": hacia,
                "p_cambios": cambios or {},
            },
        ).execute().data
    except Exception as exc:
        raise InvalidTransition(f"No se pudo pasar de {desde} a {hacia}") from exc
