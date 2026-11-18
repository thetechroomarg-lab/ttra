# Auditoría de seguridad — TTRA (noviembre 2026)

Base: `staging` @ 0519cb1. Rama: `security/comprehensive-platform-hardening`.

## Inventario
- Backend: FastAPI (`web/app.py`, ~134 rutas), sesiones firmadas (itsdangerous), Supabase (service_role solo en servidor), Resend (mails), Google Maps/Routes, Web Push, Anthropic (chat), Railway.
- Frontend: HTML/JS/CSS estático servido por `PublicStaticFiles`; paneles admin/cadete con HTML server-side.
- Sin Dockerfile ni CI en el repo (Railway construye desde `Procfile`).

## Superficies externas
Login/registro de clientes, login admin/cadete (contraseña única), API pública de catálogo, `/api/envio/cotizar`, `/api/noticias` (feed externo), baja de mailing, assets de mailing, subida de comprobantes, endpoints con `X-Admin-Token`.

## Controles ya existentes (verificados leyendo código/tests)
Cookie de sesión con `https_only` en Railway, SameSite Lax; defensa CSRF por Origin; rate limit persistente en logins; `compare_digest` en credenciales; RLS habilitado en las tablas de Supabase; sin secretos en el repo; subida de assets validada por hash y extensión; errores de validación sin eco de contraseñas; cabeceras nosniff/XFO/Referrer/Permissions/HSTS y CSP en modo report-only.

## Hallazgos
| # | Sev. | Hallazgo | Estado |
|---|------|----------|--------|
| 1 | Media | `/docs`, `/redoc`, `/openapi.json` públicos: listan todas las rutas, incluidas las de admin | Corregido |
| 2 | Media | `/api/envio/cotizar` sin sesión ni tope: cada coordenada nueva consume Google Routes (costo) | Corregido |
| 3 | Baja | Link de noticias del feed externo se usaba como `href` sin validar el esquema | Corregido |
| 4 | Baja | `ET.fromstring` sobre feed externo sin descartar DTD/entidades (bandit B314) | Corregido |
| 5 | Baja | Sin tope de tamaño de cuerpo global | Corregido (Content-Length) |
| 6 | Baja | Logins fallidos/bloqueados y Origin rechazado sin registro | Corregido |
| 7 | Info | CSP real solo en report-only (hay `<script>` inline) | Pendiente (ver riesgos) |

## Evidencia de escaneo
- `pip-audit -r requirements.txt`: sin vulnerabilidades conocidas.
- `bandit -r web`: 1 medio real (B314, corregido), B310 (URL fija https, falso positivo), resto bajos (try/except/pass, `random` no criptográfico, falsos positivos B105).
- Búsqueda de secretos por patrones: sin hallazgos; `.env` está en `.gitignore`, solo `web/.env.example` versionado.
- Gitleaks, Semgrep y Trivy no estaban instalados; no se ejecutaron.
