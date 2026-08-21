import re
import secrets
import string
import time
import uuid


class CelularDuplicadoError(Exception):
    pass


class EmailDuplicadoError(Exception):
    pass


class EmailNoConfirmadoError(Exception):
    pass


class UsernameDuplicadoError(Exception):
    pass


class PasswordActualIncorrectaError(Exception):
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


def registrar_cliente(client, nombre, apellido, celular, email, password, username):
    nombre = nombre.strip()
    apellido = apellido.strip()
    celular_norm = normalizar_celular(celular)
    email = email.strip().lower()
    username = (username or "").strip()
    if not celular_norm:
        raise ValueError("El celular ingresado no es válido")
    if not username:
        raise ValueError("El nombre de usuario es obligatorio")

    # El username es un campo propio, no una llave de vinculación de leads
    # invitados (esa sigue siendo solo el celular) — simplemente tiene que
    # ser único entre cuentas ya activas.
    existentes_username = client.table("clientes").select("*").eq("username", username).execute().data
    if any(f.get("auth_id") for f in existentes_username):
        raise UsernameDuplicadoError(f"Ya existe una cuenta con el usuario {username}")

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

    datos = {"auth_id": auth_id, "nombre": nombre, "apellido": apellido, "email": email, "username": username}
    if lead_invitado:
        propio_id = lead_invitado["id"]
        datos["celular"] = celular_norm
        guardar_datos = lambda: client.table("clientes").update(datos).eq("id", propio_id).execute()
    else:
        propio_id = str(uuid.uuid4())
        datos.update({"id": propio_id, "celular": celular_norm})
        guardar_datos = lambda: client.table("clientes").insert(datos).execute()

    # Justo después del sign_up, el usuario nuevo puede tardar una fracción
    # de segundo en quedar visible para el chequeo de foreign key de
    # clientes_auth_id_fkey (ventana de propagación de Supabase Auth) — sin
    # este reintento, esa carrera hace fallar registros legítimos con un
    # falso "ya existe" o "no pudimos conectar". Los duplicados reales
    # (email/celular ya usados) no dependen del timing y fallan igual en el
    # primer intento.
    error_final = None
    for intento in range(4):
        try:
            guardar_datos()
            error_final = None
            break
        except Exception as e:
            error_final = e
            if "clientes_auth_id_fkey" in str(e) and intento < 3:
                time.sleep(0.4 * (intento + 1))
                continue
            break

    if error_final is not None:
        try:
            client.auth.admin.delete_user(auth_id)
        except Exception:
            # Si Supabase tampoco ve todavía al usuario para borrarlo, no hay
            # nada que limpiar — no tapemos el error real de arriba con este.
            pass
        error_msg = str(error_final).lower()
        if "email" in error_msg or "clientes_email_key" in error_msg:
            raise EmailDuplicadoError(f"Ya existe una cuenta con el email {email}") from error_final
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}") from error_final

    return {"id": propio_id, "auth_id": auth_id, "nombre": nombre,
            "apellido": apellido, "celular": celular_norm, "email": email, "username": username}


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
            "apellido": perfil["apellido"], "celular": perfil["celular"], "email": perfil["email"],
            "username": perfil.get("username"),
            "debe_cambiar_password": bool(perfil.get("debe_cambiar_password"))}


def obtener_cliente(client, cliente_id):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        return None
    perfil = filas[0]
    return {"id": perfil["id"], "nombre": perfil["nombre"], "apellido": perfil["apellido"],
            "celular": perfil.get("celular"), "email": perfil.get("email"),
            "username": perfil.get("username"),
            "debe_cambiar_password": bool(perfil.get("debe_cambiar_password"))}


def actualizar_cliente(client, cliente_id, nombre, apellido, celular, username):
    nombre = nombre.strip()
    apellido = apellido.strip()
    celular_norm = normalizar_celular(celular)
    username = (username or "").strip()
    if not celular_norm:
        raise ValueError("El celular ingresado no es válido")
    if not username:
        raise ValueError("El nombre de usuario es obligatorio")

    existentes_username = client.table("clientes").select("*").eq("username", username).execute().data
    if any(f.get("auth_id") and f["id"] != cliente_id for f in existentes_username):
        raise UsernameDuplicadoError(f"Ya existe una cuenta con el usuario {username}")

    existentes_celular = client.table("clientes").select("*").eq("celular", celular_norm).execute().data
    if any(f.get("auth_id") and f["id"] != cliente_id for f in existentes_celular):
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}")

    datos = {"nombre": nombre, "apellido": apellido, "celular": celular_norm, "username": username}
    client.table("clientes").update(datos).eq("id", cliente_id).execute()
    return obtener_cliente(client, cliente_id)


def cambiar_password_propio(client, client_verificacion, cliente_id, password_actual, password_nueva):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        raise ValueError(f"No existe un cliente con id {cliente_id}")
    perfil = filas[0]
    auth_id = perfil.get("auth_id")
    email = perfil.get("email")
    if not auth_id:
        raise ValueError("Este cliente todavía no tiene una cuenta activa")
    try:
        client_verificacion.auth.sign_in_with_password({"email": email, "password": password_actual})
    except Exception as e:
        mensaje = str(e).lower()
        if "invalid" in mensaje or "credentials" in mensaje:
            raise PasswordActualIncorrectaError("La contraseña actual no es correcta") from e
        raise
    client.auth.admin.update_user_by_id(auth_id, {"password": password_nueva})


def generar_password_temporal():
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(12))


def resetear_password_cliente(client, cliente_id):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        raise ValueError(f"No existe un cliente con id {cliente_id}")
    perfil = filas[0]
    auth_id = perfil.get("auth_id")
    if not auth_id:
        raise ValueError("Este cliente todavía no tiene una cuenta activa (es un lead sin registrar)")
    nueva_password = generar_password_temporal()
    # email_confirm=True: el reseteo lo hace un admin de confianza, así que
    # la cuenta queda habilitada para entrar aunque nunca haya confirmado el
    # mail original de registro.
    client.auth.admin.update_user_by_id(auth_id, {"password": nueva_password, "email_confirm": True})
    client.table("clientes").update({"debe_cambiar_password": True}).eq("id", cliente_id).execute()
    return {"email": perfil["email"], "password": nueva_password}


def cambiar_password_obligatorio(client, cliente_id, nueva_password):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        raise ValueError(f"No existe un cliente con id {cliente_id}")
    perfil = filas[0]
    auth_id = perfil.get("auth_id")
    if not auth_id:
        raise ValueError("Este cliente todavía no tiene una cuenta activa")
    client.auth.admin.update_user_by_id(auth_id, {"password": nueva_password})
    client.table("clientes").update({"debe_cambiar_password": False}).eq("id", cliente_id).execute()
