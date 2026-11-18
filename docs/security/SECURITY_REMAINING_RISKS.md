# Riesgos restantes

1. **CSP en report-only**: hay `<script>` inline; pasar a enforce requiere nonces/hashes y pruebas visuales. Requiere aprobación.
2. **IP del cliente = peer del proxy** (`--no-proxy-headers`): en Railway todos los logins comparten el mismo balde de intentos y los logs muestran la IP del proxy. Decisión previa a propósito; cambiarla exige configurar proxies de confianza.
3. **Contraseña única de admin/cadete** sin MFA ni cuentas individuales. Mejora con fricción: requiere aprobación.
4. **Tope de cuerpo** solo cubre `Content-Length`; cuerpos chunked no se limitan.
5. **RLS y permisos de Supabase** revisados solo en `schema.sql`, no en la base viva.
6. **Escáneres no ejecutados**: Gitleaks, Semgrep, Trivy. Revisar el historial git en busca de secretos antiguos.
7. **HSTS** sin `includeSubDomains`/preload (decisión consciente por subdominios desconocidos).
8. **Test preexistente en falla** (`test_panel_admin_maneja_sesion_vencida_al_guardar`).
9. **Rotación**: no se encontraron secretos expuestos; no hay rotación pendiente por esta auditoría.
