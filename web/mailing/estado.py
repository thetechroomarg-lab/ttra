"""Persistencia del estado de las campañas de mailing (snapshot del catálogo,
nota pendiente, borrador actual, log de envíos) en Supabase — no en disco.
Así tanto un script corrido a mano en la máquina local como la rutina
programada corriendo en la nube leen y escriben el mismo estado."""
from datetime import datetime, timezone

_TABLA_ESTADO = "mailing_estado"
_TABLA_ENVIOS = "mailing_envios"


def _leer_clave(client, clave):
    filas = client.table(_TABLA_ESTADO).select("*").eq("clave", clave).execute().data
    return filas[0]["valor"] if filas else None


def _escribir_clave(client, clave, valor):
    existente = client.table(_TABLA_ESTADO).select("*").eq("clave", clave).execute().data
    fila = {
        "clave": clave,
        "valor": valor,
        "actualizado_en": datetime.now(timezone.utc).isoformat(),
    }
    if existente:
        client.table(_TABLA_ESTADO).update(fila).eq("clave", clave).execute()
    else:
        client.table(_TABLA_ESTADO).insert(fila).execute()


def leer_snapshot(client):
    return _leer_clave(client, "snapshot")


def guardar_snapshot(client, productos):
    _escribir_clave(client, "snapshot", productos)


def leer_nota_pendiente(client):
    datos = _leer_clave(client, "nota_pendiente")
    return (datos or {}).get("texto")


def guardar_nota_pendiente(client, texto):
    _escribir_clave(client, "nota_pendiente", {
        "texto": texto,
        "creada_en": datetime.now(timezone.utc).isoformat(),
    })


def limpiar_nota_pendiente(client):
    _escribir_clave(client, "nota_pendiente", {"texto": None, "creada_en": None})


def leer_borrador(client):
    return _leer_clave(client, "borrador_actual")


def guardar_borrador(client, borrador):
    _escribir_clave(client, "borrador_actual", borrador)


def marcar_borrador_usado(client):
    borrador = leer_borrador(client)
    if borrador is not None:
        borrador["usado"] = True
        guardar_borrador(client, borrador)


def registrar_envio(client, productos, ok, fallidos):
    client.table(_TABLA_ENVIOS).insert({
        "productos": productos,
        "ok": ok,
        "fallidos": fallidos,
    }).execute()
