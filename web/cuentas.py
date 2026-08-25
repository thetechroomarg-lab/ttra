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


def capitalizar_nombre(valor):
    """Normaliza espacios y deja cada nombre o apellido con inicial mayúscula."""
    return " ".join(parte.capitalize() for parte in (valor or "").split())


def registrar_cliente(client, nombre, apellido, celular, email, password, provincia="Córdoba", direccion=None, email_redirect_to=None):
    nombre = capitalizar_nombre(nombre)
    apellido = capitalizar_nombre(apellido)
    celular_norm = normalizar_celular(celular)
    email = email.strip().lower()
    provincia = provincia.strip()
    direccion = (direccion or "").strip() or None
    if not celular_norm:
        raise ValueError("El celular ingresado no es válido")
    if not provincia:
        raise ValueError("Seleccioná tu provincia")

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
        credenciales = {"email": email, "password": password}
        if email_redirect_to:
            # Si el proyecto de Supabase tiene el "Site URL" mal cargado
            # (ej. localhost viejo de desarrollo), el mail de confirmación
            # igual puede apuntar al destino correcto si se lo pasamos acá.
            credenciales["options"] = {"email_redirect_to": email_redirect_to}
        auth_resp = client.auth.sign_up(credenciales)
    except Exception as e:
        # Solo es EmailDuplicadoError si el mensaje indica email duplicado
        if "already registered" in str(e).lower() or "already exists" in str(e).lower():
            raise EmailDuplicadoError(f"Ya existe una cuenta con el email {email}") from e
        # Si es otro tipo de error, relanzarlo sin enmascarar
        raise
    auth_id = auth_resp.user.id

    datos = {
        "auth_id": auth_id,
        "nombre": nombre,
        "apellido": apellido,
        "email": email,
        "provincia": provincia,
        "direccion": direccion,
    }
    if lead_invitado:
        propio_id = lead_invitado["id"]
        datos["celular"] = celular_norm
        guardar_datos = lambda: client.table("clientes").update(datos).eq("id", propio_id).execute()
    else:
        propio_id = str(uuid.uuid4())
        datos.update({"id": propio_id, "celular": celular_norm})
        guardar_datos = lambda: client.table("clientes").insert(datos).execute()

    # Justo después del sign_up, el usuario nuevo puede tardar unos segundos
    # en quedar visible para el chequeo de foreign key de
    # clientes_auth_id_fkey (ventana de propagación de Supabase Auth, más
    # marcada todavía en producción que en local) — sin este reintento, esa
    # carrera hace fallar registros legítimos. Los duplicados reales
    # (email/celular/usuario ya usados) no dependen del timing y fallan
    # igual en el primer intento, así que no hace falta reintentarlos.
    error_final = None
    for intento in range(8):
        try:
            guardar_datos()
            error_final = None
            break
        except Exception as e:
            error_final = e
            if "clientes_auth_id_fkey" in str(e) and intento < 7:
                time.sleep(min(0.3 * (intento + 1), 1.5))
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
        if "clientes_email_key" in error_msg:
            raise EmailDuplicadoError(f"Ya existe una cuenta con el email {email}") from error_final
        if "clientes_auth_id_fkey" in error_msg:
            # Se agotaron los reintentos y la ventana de propagación del
            # auth_id nunca cerró: no es un duplicado de ningún campo, así
            # que no le mintamos al usuario — que se relance tal cual y lo
            # maneje el 503 genérico del caller.
            raise error_final
        # Cualquier otra falla no identificada (incluida clientes_celular_key)
        # se trata como duplicado de celular, que es el caso más común.
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}") from error_final

    requiere_confirmacion_email = (
        getattr(auth_resp, "session", None) is None
        and not getattr(getattr(auth_resp, "user", None), "email_confirmed_at", None)
    )

    return {
        "id": propio_id,
        "auth_id": auth_id,
        "nombre": nombre,
        "apellido": apellido,
        "celular": celular_norm,
        "email": email,
        "requiere_confirmacion_email": requiere_confirmacion_email,
    }


def login_cliente(client, client_datos, email, password):
    # `client` hace el sign_in y queda con el contexto de ESE usuario (ya no
    # service_role) — el supabase-py sincroniza el token de auth con el
    # cliente de postgrest del mismo objeto. Consultar clientes con ese
    # mismo objeto después del sign_in corre como "authenticated" y RLS lo
    # bloquea (devuelve 0 filas siempre, no es un problema de timing). Por
    # eso la lectura posterior usa `client_datos`, un cliente aparte que
    # nunca se loguea y se mantiene como service_role.
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
    filas = client_datos.table("clientes").select("*").eq("auth_id", auth_id).execute().data
    if not filas:
        return None
    perfil = filas[0]
    return {"id": perfil["id"], "auth_id": auth_id, "nombre": perfil["nombre"],
            "apellido": perfil["apellido"], "celular": perfil["celular"], "email": perfil["email"],
            "debe_cambiar_password": bool(perfil.get("debe_cambiar_password"))}


def obtener_cliente(client, cliente_id):
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        return None
    perfil = filas[0]
    return {"id": perfil["id"], "nombre": perfil["nombre"], "apellido": perfil["apellido"],
            "celular": perfil.get("celular"), "email": perfil.get("email"),
            "direccion": perfil.get("direccion"),
            "debe_cambiar_password": bool(perfil.get("debe_cambiar_password"))}


def actualizar_cliente(client, cliente_id, nombre, apellido, celular, direccion=None):
    nombre = capitalizar_nombre(nombre)
    apellido = capitalizar_nombre(apellido)
    celular_norm = normalizar_celular(celular)
    if not celular_norm:
        raise ValueError("El celular ingresado no es válido")

    existentes_celular = client.table("clientes").select("*").eq("celular", celular_norm).execute().data
    if any(f.get("auth_id") and f["id"] != cliente_id for f in existentes_celular):
        raise CelularDuplicadoError(f"Ya existe una cuenta con el celular {celular_norm}")

    datos = {"nombre": nombre, "apellido": apellido, "celular": celular_norm}
    if direccion is not None:
        datos["direccion"] = direccion.strip() or None
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


def eliminar_cliente(client, cliente_id):
    """Elimina definitivamente un perfil y su cuenta de autenticación."""
    filas = client.table("clientes").select("*").eq("id", cliente_id).execute().data
    if not filas:
        raise ValueError(f"No existe un cliente con id {cliente_id}")

    auth_id = filas[0].get("auth_id")
    if auth_id:
        # El trigger en Supabase borra el perfil y sus registros relacionados
        # antes de eliminar auth.users. Esto también cubre migraciones previas.
        client.auth.admin.delete_user(auth_id)
    client.table("clientes").delete().eq("id", cliente_id).execute()


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
