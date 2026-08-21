import re
import uuid


class CelularDuplicadoError(Exception):
    pass


class EmailDuplicadoError(Exception):
    pass


def normalizar_celular(celular):
    return re.sub(r"\D", "", celular or "")


def registrar_cliente(client, nombre, apellido, celular, email, password):
    nombre = nombre.strip()
    apellido = apellido.strip()
    celular_norm = normalizar_celular(celular)
    email = email.strip().lower()
    if not celular_norm:
        raise ValueError("El celular ingresado no es válido")

    existentes = client.table("clientes").select("*").eq("celular", celular_norm).execute().data
    if any(f.get("auth_id") for f in existentes):
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}")
    lead_invitado = next((f for f in existentes if not f.get("auth_id")), None)

    try:
        auth_resp = client.auth.sign_up({"email": email, "password": password})
    except Exception:
        raise EmailDuplicadoError(f"Ya existe una cuenta con el email {email}")
    auth_id = auth_resp.user.id

    datos = {"auth_id": auth_id, "nombre": nombre, "apellido": apellido, "email": email}
    try:
        if lead_invitado:
            propio_id = lead_invitado["id"]
            client.table("clientes").update(datos).eq("celular", celular_norm).execute()
        else:
            propio_id = str(uuid.uuid4())
            datos.update({"id": propio_id, "celular": celular_norm})
            client.table("clientes").insert(datos).execute()
    except Exception:
        client.auth.admin.delete_user(auth_id)
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}")

    return {"id": propio_id, "auth_id": auth_id, "nombre": nombre,
            "apellido": apellido, "celular": celular_norm, "email": email}


def login_cliente(client, email, password):
    email = (email or "").strip().lower()
    try:
        auth_resp = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return None
    auth_id = auth_resp.user.id
    filas = client.table("clientes").select("*").eq("auth_id", auth_id).execute().data
    if not filas:
        return None
    perfil = filas[0]
    return {"id": perfil["id"], "auth_id": auth_id, "nombre": perfil["nombre"],
            "apellido": perfil["apellido"], "celular": perfil["celular"], "email": email}
