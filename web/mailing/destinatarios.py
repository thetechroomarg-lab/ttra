"""Selección de clientes elegibles para recibir una campaña de mailing de
novedades (tienen email y no se dieron de baja)."""


def clientes_elegibles(client):
    filas = client.table("clientes").select("*").execute().data
    return [
        {"id": fila["id"], "email": fila["email"]}
        for fila in filas
        if fila.get("email") and not fila.get("no_mailing")
    ]
