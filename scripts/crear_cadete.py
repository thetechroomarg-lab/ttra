"""Crea (o resetea la contraseña de) una cuenta de cadete en Supabase.

Uso: python scripts/crear_cadete.py <email> <nombre> [--resetear]
Imprime la contraseña generada UNA sola vez; no se guarda en ningún lado.
Baja: update cadetes set activo = false where email = '...' (corta la sesión en <= 30 s).
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "web", ".env"))
from web import cadetes
from web.supabase_client import get_client


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    email, nombre, resetear = cadetes.normalizar_email(argv[1]), argv[2], "--resetear" in argv
    client = get_client()
    password = secrets.token_urlsafe(12)
    existe = client.table("cadetes").select("id").eq("email", email).execute().data
    if existe and not resetear:
        print("Ya existe esa cuenta; usá --resetear para cambiarle la contraseña.")
        return 1
    datos = {"password_hash": cadetes.hashear_password(password), "activo": True}
    if existe:
        client.table("cadetes").update(datos).eq("email", email).execute()
    else:
        client.table("cadetes").insert({"email": email, "nombre": nombre, **datos}).execute()
    print(f"Cuenta lista: {email}\nContraseña (se muestra una sola vez): {password}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
