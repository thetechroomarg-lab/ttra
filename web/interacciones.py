import uuid
from datetime import datetime, timezone


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
