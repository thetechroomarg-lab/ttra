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

    existentes_celular = client.table("clientes").select("*").eq("celular", celular_norm).execute().data
    if any(f.get("auth_id") for f in existentes_celular):
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}")
    lead_por_celular = next((f for f in existentes_celular if not f.get("auth_id")), None)

    # Además del celular, buscamos una fila invitada por email: los mayoristas
    # migrados quedan con un celular placeholder (no tenían celular real en
    # usuarios.db), así que su única forma de vincular la cuenta es por email.
    existentes_email = client.table("clientes").select("*").eq("email", email).execute().data
    lead_por_email = next((f for f in existentes_email if not f.get("auth_id")), None)

    # Si hay invitados distintos por celular y por email (no debería pasar en la
    # práctica), priorizamos el de celular.
    lead_invitado = lead_por_celular or lead_por_email

    try:
        auth_resp = client.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        # Solo es EmailDuplicadoError si el mensaje indica email duplicado
        if "already registered" in str(e).lower() or "already exists" in str(e).lower():
            raise EmailDuplicadoError(f"Ya existe una cuenta con el email {email}") from e
        # Si es otro tipo de error, relanzarlo sin enmascarar
        raise
    auth_id = auth_resp.user.id

    datos = {"auth_id": auth_id, "nombre": nombre, "apellido": apellido, "email": email}
    try:
        if lead_invitado:
            propio_id = lead_invitado["id"]
            datos["celular"] = celular_norm
            client.table("clientes").update(datos).eq("id", propio_id).execute()
        else:
            propio_id = str(uuid.uuid4())
            datos.update({"id": propio_id, "celular": celular_norm})
            client.table("clientes").insert(datos).execute()
    except Exception as e:
        client.auth.admin.delete_user(auth_id)
        # Inspecciona el mensaje para determinar qué tipo de duplicado es
        error_msg = str(e).lower()
        if "email" in error_msg or "clientes_email_key" in error_msg:
            raise EmailDuplicadoError(f"Ya existe una cuenta con el email {email}") from e
        # Si no se puede determinar con certeza, asume que es de celular
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}") from e

    return {"id": propio_id, "auth_id": auth_id, "nombre": nombre,
            "apellido": apellido, "celular": celular_norm, "email": email}


def login_cliente(client, email, password):
    email = (email or "").strip().lower()
    try:
        auth_resp = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception as e:
        mensaje = str(e).lower()
        if "invalid" in mensaje or "credentials" in mensaje:
            return None
        # No parece una credencial inválida (ej. Supabase caído): no lo
        # disfracemos de "usuario no encontrado", que lo relance el llamador.
        raise
    auth_id = auth_resp.user.id
    filas = client.table("clientes").select("*").eq("auth_id", auth_id).execute().data
    if not filas:
        return None
    perfil = filas[0]
    return {"id": perfil["id"], "auth_id": auth_id, "nombre": perfil["nombre"],
            "apellido": perfil["apellido"], "celular": perfil["celular"], "email": perfil["email"]}
