# Matriz de controles (orientativa, no es una certificación)

| Control | Referencia | Estado |
|---|---|---|
| Control de acceso server-side en admin/cadete | OWASP A01, ASVS V4, ISO 27002 5.15 | Implementado (previo) |
| Hash/credenciales con comparación en tiempo constante | ASVS V2, NIST 800-63B | Implementado (previo) |
| Anti fuerza bruta en login | ASVS V2.2, CIS 5 | Implementado (previo) |
| CSRF por Origin + SameSite | OWASP A01/ASVS V4 | Implementado (previo) |
| Exposición de superficie (docs/OpenAPI) | OWASP A05, ASVS V14 | Implementado (nuevo) |
| Límites de recursos / abuso de API | OWASP API4 | Parcial (cotización y cuerpo; resto sin límite) |
| Validación de contenido externo (feed) | OWASP A03/A08 | Implementado (nuevo) |
| Logging de eventos de seguridad | OWASP A09, NIST CSF DE, ISO 27002 8.15 | Parcial (logins y rechazos; sin alertas) |
| Cabeceras de seguridad | OWASP A05 | Parcial (CSP en report-only) |
| Gestión de secretos | OWASP A02, ISO 27002 8.24 | Implementado (previo) |
| Dependencias/SCA | OWASP A06, NIST 800-218 | Implementado (pip-audit limpio, manual) |
| RLS en base de datos | ASVS V4 | Implementado en schema; no verificado en vivo |
| MFA | NIST 800-63B | No implementado (requiere aprobación) |
| CI de seguridad, contenedores | CIS 16 | No aplicable / no existe |
