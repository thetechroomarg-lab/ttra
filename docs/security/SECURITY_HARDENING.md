# Mejoras implementadas

Todas en `web/app.py`, con tests en `tests/test_security_hardening.py`.

1. **API docs apagadas**: `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)` salvo `ENABLE_API_DOCS=1`. Evita mapear gratis la superficie de ataque.
2. **Tope en cotización de envío**: 30/min por cliente con sesión, 120/min compartido sin sesión, usando el `LoginAttemptStore` existente. Responde 429. Los valores son holgados para uso normal.
3. **Links de noticias**: `_link_noticia_seguro` deja pasar solo `http`/`https`; evita `javascript:` si el feed se compromete.
4. **Feed XML**: se descarta si trae `<!DOCTYPE` o `<!ENTITY`.
5. **Tope de cuerpo**: middleware que responde 413 si `Content-Length` supera 16 MB (el mayor upload legítimo es 8 MB).
6. **Logging de seguridad** (`web.security`): login admin/cadete fallido o bloqueado (con IP del peer), Origin rechazado, cuerpo excedido, límite de cotizaciones. Nunca se registran contraseñas ni tokens.

Sin cambios de contratos de API, UI, precios ni dependencias. Costo adicional: ninguno.
