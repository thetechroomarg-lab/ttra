"""Login de cadete para tests: crea una cuenta aprobada en la base fake activa y entra con ella."""
import web.app as appmod
from web import cadetes

EMAIL = "alejo@example.com"
PASSWORD = "clave-cadete-123"


def login_cadete(cliente_http):
    base = appmod.get_client()
    if not base.table("cadetes").select("*").eq("email", EMAIL).execute().data:
        base.table("cadetes").insert({
            "id": "cadete-test", "nombre": "Alejo", "email": EMAIL, "rol": "cadete", "slug": "alejo",
            "aprobado": True, "activo": True, "password_hash": cadetes.hashear_password(PASSWORD),
        }).execute()
    r = cliente_http.post("/admin/cadete/login", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r
