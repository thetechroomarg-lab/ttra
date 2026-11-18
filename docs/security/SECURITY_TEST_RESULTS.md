# Resultados de tests

Entorno: `.venv` del proyecto, con `ADMIN_CLIENTES_PASSWORD`, `CADETE_PASSWORD` y `SESSION_SECRET` de prueba.

| Momento | Comando | Resultado |
|---|---|---|
| Baseline (staging) | `python -m pytest tests/ -q` | 1003 pasan, 1 falla |
| Con cambios | `python -m pytest tests/ -q` | 1009 pasan, 1 falla (la misma) |

La falla previa, `tests/test_admin_cotizacion.py::test_panel_admin_maneja_sesion_vencida_al_guardar`, ocurre igual sin mis cambios; no se investigó su causa.

Tests nuevos (6): docs apagadas, 413 por cuerpo grande, esquema de links de noticias, feed con DTD, tope de cotización (429 tras 120), log de login fallido sin la clave.

Otros: `pip-audit` limpio; `bandit` como en la auditoría.

## No ejecutado / límites
Gitleaks, Semgrep, Trivy; pruebas contra Supabase real (los tests usan un fake); pruebas visuales de UI (no se tocó frontend); revisión de políticas RLS contra la base viva; navegador real para CSP.
