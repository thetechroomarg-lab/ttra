"""Cuentas propias del cadete (email + contraseña) con rol decidido en el servidor.

Reemplazan a la contraseña única compartida: cada cuenta se puede dar de baja
sola (`activo = false`), y la sesión deja de valer en cuanto eso pasa o cambia
su contraseña.
"""
import base64
import hashlib
import hmac
import os
import re
import secrets
import time
import unicodedata
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


SLUG_PRIMER_CADETE = "alejo"  # el slug que ya tienen todas las entregas y movimientos existentes
_NOMBRES = {SLUG_PRIMER_CADETE: "Alejo"}


def _cuentas(client):
    return client.table("cadetes").select("*").execute().data or []


def hay_cuentas(client):
    return bool(_cuentas(client))


def slug_de(cuenta):
    return cuenta.get("slug") or SLUG_PRIMER_CADETE


def nombre_de(slug):
    """Nombre para mostrar de un slug de cadete; sin dato, el slug capitalizado."""
    return _NOMBRES.get(slug) or str(slug or "").capitalize()


def email_registrado(client, email):
    email = normalizar_email(email)
    return any(c.get("email") == email for c in _cuentas(client))


def activos(client):
    """Cuentas aprobadas y activas: a quienes se les puede derivar. Actualiza los nombres."""
    cuentas = [c for c in _cuentas(client) if c.get("activo") and c.get("aprobado")]
    for c in cuentas:
        _NOMBRES[slug_de(c)] = c.get("nombre") or nombre_de(slug_de(c))
    return sorted(cuentas, key=lambda c: (c.get("nombre") or "").lower())


def slug_valido(client, slug):
    return any(slug_de(c) == slug for c in activos(client))


def email_activo(client, slug=None):
    """Email de la cuenta activa del cadete `slug` (sin slug, la primera), o None."""
    for fila in activos(client):
        if fila.get("email") and (slug is None or slug_de(fila) == slug):
            return fila["email"]
    return None


def _slug_nuevo(nombre, existentes):
    base = re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFKD", nombre or "").encode("ascii", "ignore").decode().lower()).strip("-") or "cadete"
    slug, n = base, 2
    while slug in existentes:
        slug, n = f"{base}-{n}", n + 1
    return slug


def crear_cuenta(client, email, password, nombre):
    """Alta de una cuenta: siempre queda pendiente hasta que Vlad la apruebe. La
    primera de todas toma el slug histórico (el de las entregas y movimientos
    que ya existen); las siguientes, uno propio."""
    existentes = _cuentas(client)
    primera = not existentes
    cuenta = {"id": str(uuid.uuid4()), "nombre": (nombre or "").strip()[:100] or "Cadete",
              "email": normalizar_email(email), "password_hash": hashear_password(password),
              "rol": ROL_CADETE, "activo": True, "aprobado": False,
              "slug": SLUG_PRIMER_CADETE if primera else _slug_nuevo(nombre, {slug_de(c) for c in existentes})}
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
    session["cadete_slug"] = slug_de(cuenta)
    session["cadete_version"] = version_sesion(cuenta)


def cerrar_sesion(session):
    for clave in ("cadete_ok", "cadete_version", "cadete_id", "cadete_email", "cadete_slug", "cadete_alta_version"):
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
        ok = bool(cuenta and cuenta.get("activo") and cuenta.get("aprobado") and cuenta.get("rol") == ROL_CADETE
                  and hmac.compare_digest(version, version_sesion(cuenta)))
    except Exception:
        return False
    if len(_cache) > 200:
        _cache.clear()
    _cache[clave] = (ahora + _CACHE_SEG, ok)
    return ok
