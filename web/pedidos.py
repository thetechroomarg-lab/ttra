import uuid
from datetime import datetime, timezone


def guardar_pedido(client, cliente_id, productos, origen="whatsapp"):
    fila = {
        "id": str(uuid.uuid4()),
        "cliente_id": cliente_id,
        "productos": productos,
        "origen": origen,
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    client.table("pedidos").insert(fila).execute()
    return fila
