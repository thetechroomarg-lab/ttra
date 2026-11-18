"""Cuentas propias del cadete (email + contraseña) con rol decidido en el servidor.

Reemplazan a la contraseña única compartida: cada cuenta se puede dar de baja
sola (`activo = false`), y la sesión deja de valer en cuanto eso pasa o cambia
su contraseña. El acceso viejo por contraseña única sigue andando hasta que se
lo apague con CADETE_LOGIN_CONTRASENA_UNICA=0 (ver app.py).
"""
import base64
import hashlib
import hmac
import os
import secrets
import time
import uuid

ROL_CADETE = "cadete"
_SCRYPT = {"n": 2**14, "r": 8, "p": 1}
_CACHE_SEG = 30  # una baja o cambio de clave corta la sesión en <= 30 s
_cache = {}  # (id, version) -> (vence, ok)


def normalizar_email(email):
    return (email or "").strip().lower()


def hashear_password(password):
    sal = os.urandom(16)
    h = hashlib.scrypt(password.encode(), salt=sal, dklen=32, **_SCRYPT)
    return "scrypt$" + base64.b64encode(sal).decode() + "$" + base64.b64encode(h).decode()


def verificar_password(password, almacenado):
    try:
        _, sal_b64, h_b64 = (almacenado or "").split("$")
        esperado = base64.b64decode(h_b64)
        h = hashlib.scrypt(password.encode(), salt=base64.b64decode(sal_b64), dklen=len(esperado), **_SCRYPT)
    except Exception:
        return False
    return hmac.compare_digest(h, esperado)


_HASH_FALSO = hashear_password(secrets.token_hex(8))


def version_sesion(cuenta):
    clave = os.environ.get("SESSION_SECRET", "").encode()
    return hmac.new(clave, f"cadete-cuenta:{cuenta['id']}:{cuenta['password_hash']}".encode(),
                    hashlib.sha256).hexdigest()


def hay_cuentas(client):
    return bool(client.table("cadetes").select("id").execute().data)


def email_activo(client):
    """Email de la cuenta activa del cadete (hoy hay una sola), o None."""
    for fila in client.table("cadetes").select("*").execute().data or []:
        if fila.get("activo") and fila.get("email"):
            return fila["email"]
    return None


def crear_cuenta(client, email, password, nombre="Alejo"):
    cuenta = {"id": str(uuid.uuid4()), "nombre": nombre, "email": normalizar_email(email),
              "password_hash": hashear_password(password), "rol": ROL_CADETE, "activo": True}
    client.table("cadetes").insert(cuenta).execute()
    return cuenta


def autenticar(client, email, password):
    """Devuelve la cuenta si email+contraseña son válidos y está activa; si no, None.
    Siempre gasta un scrypt, exista o no el email, para no revelar cuentas."""
    filas = client.table("cadetes").select("*").eq("email", normalizar_email(email)).execute().data
    cuenta = filas[0] if filas else None
    ok = verificar_password(password, cuenta["password_hash"] if cuenta else _HASH_FALSO)
    if cuenta and ok and cuenta.get("activo") and cuenta.get("rol") == ROL_CADETE:
        return cuenta
    return None


def iniciar_sesion(session, cuenta):
    session["cadete_ok"] = True
    session["cadete_id"] = str(cuenta["id"])
    session["cadete_email"] = cuenta["email"]
    session["cadete_version"] = version_sesion(cuenta)


def cerrar_sesion(session):
    for clave in ("cadete_ok", "cadete_version", "cadete_id", "cadete_email", "cadete_alta_version"):
        session.pop(clave, None)


def sesion_de_cuenta_valida(session, get_client):
    """Revalida contra la base (con caché corta) que la cuenta siga activa y
    que la sesión corresponda a su contraseña actual. Falla cerrado."""
    cuenta_id, version = str(session.get("cadete_id", "")), str(session.get("cadete_version", ""))
    clave, ahora = (cuenta_id, version), time.time()
    visto = _cache.get(clave)
    if visto and visto[0] > ahora:
        return visto[1]
    try:
        filas = get_client().table("cadetes").select("*").eq("id", cuenta_id).execute().data
        cuenta = filas[0] if filas else None
        ok = bool(cuenta and cuenta.get("activo") and cuenta.get("rol") == ROL_CADETE
                  and hmac.compare_digest(version, version_sesion(cuenta)))
    except Exception:
        return False
    if len(_cache) > 200:
        _cache.clear()
    _cache[clave] = (ahora + _CACHE_SEG, ok)
    return ok
