"""Cliente HTTP pequeño para los endpoints administrativos de mailing."""
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_DIR / "web" / ".env")


class MailingApi:
    def __init__(self, base_url=None, admin_token=None, transport=None):
        base_url = (base_url or os.environ.get("MAILING_BASE_URL") or "https://thetechroomarg.com").rstrip("/")
        admin_token = admin_token or os.environ.get("ADMIN_TOKEN")
        if not admin_token:
            raise RuntimeError("ADMIN_TOKEN no está configurado en web/.env ni en el entorno")
        self.client = httpx.Client(
            base_url=base_url,
            transport=transport,
            headers={"x-admin-token": admin_token},
            timeout=45,
        )

    def _json(self, metodo, path, **kwargs):
        try:
            respuesta = getattr(self.client, metodo)(path, **kwargs)
        except httpx.HTTPError as exc:
            raise RuntimeError("No se pudo conectar con la web de mailing") from exc
        if respuesta.status_code >= 400:
            raise RuntimeError(f"La web de mailing rechazó la operación ({respuesta.status_code})")
        return respuesta.json()

    def get(self, path):
        return self._json("get", path)

    def post(self, path, **kwargs):
        return self._json("post", path, **kwargs)

    def post_file(self, path, file_path):
        import mimetypes

        ruta = Path(file_path)
        mime = mimetypes.guess_type(ruta.name)[0] or "application/octet-stream"
        with ruta.open("rb") as archivo:
            return self.post(
                path,
                files={"archivo": (ruta.name, archivo, mime)},
            )

    def close(self):
        self.client.close()
