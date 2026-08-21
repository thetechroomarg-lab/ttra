import re
import uuid


class CelularDuplicadoError(Exception):
    pass


class EmailDuplicadoError(Exception):
    pass


class EmailNoConfirmadoError(Exception):
    pass


def normalizar_celular(celular):
    digitos = re.sub(r"\D", "", celular or "")
    # "+543513017015" y "3513017015" son el mismo celular argentino con y
    # sin código de país — sin esto quedan como dos clientes distintos.
    if digitos.startswith("549") and len(digitos) == 13:
        digitos = digitos[3:]
    elif digitos.startswith("54") and len(digitos) == 12:
        digitos = digitos[2:]
    return digitos


def registrar_cliente(client, nombre, apellido, celular, email, password):
    nombre = nombre.strip()
    apellido = apellido.strip()
    celular_norm = normalizar_celular(celular)
    email = email.strip().lower()
    if not celular_norm:
        raise ValueError("El celular ingresado no es válido")

    # La vinculación de fila "invitada" es SOLO por celular, nunca por email:
    # el email no prueba que quien se registra sea el dueño real de la
    # cuenta (cualquiera puede escribir el email de otra persona en el
    # formulario), así que usarlo como llave de vinculación abriría una
    # forma de apropiarse de la fila de otro cliente sin verificación real.
    existentes_celular = client.table("clientes").select("*").eq("celular", celular_norm).execute().data
    if any(f.get("auth_id") for f in existentes_celular):
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}")
    lead_invitado = next((f for f in existentes_celular if not f.get("auth_id")), None)

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
        # "confirm" se chequea primero: un mensaje futuro más específico
        # (ej. "invalid credentials: email not confirmed") no debe caer en
        # la rama de "contraseña incorrecta" solo porque también contenga
        # esas palabras.
        if "confirm" in mensaje:
            raise EmailNoConfirmadoError(
                "Confirmá tu email antes de ingresar — revisá tu bandeja de entrada"
            ) from e
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
