# Comparativa: activar las fichas técnicas

La UI y el servicio están implementados. La investigación real requiere una clave de servidor.

## Opción predeterminada económica

Crear una API key en https://aistudio.google.com/apikey y configurarla como `GEMINI_API_KEY` en `web/.env` (local) y en las variables del servicio Railway (producción). No colocarla en JavaScript, repositorio ni chat. Reiniciar el servidor local después de configurarla.

`COMPARISON_AI_PROVIDER=gemini` es el valor predeterminado. Usa `gemini-2.5-flash-lite` y Google Search. La documentación publica un nivel gratuito, pero la disponibilidad y cuotas efectivas dependen del proyecto Google; no se garantiza consumo gratuito si el proyecto está vinculado a facturación. No hay cambio automático a otro proveedor al alcanzar un límite.

El nivel gratuito puede usar las consultas para mejorar productos de Google. La aplicación envía únicamente modelo y categoría públicos; no envía datos de clientes, costos ni proveedores.

Referencias oficiales consultadas:
- https://ai.google.dev/gemini-api/docs/pricing#gemini-2.5-flash-lite
- https://ai.google.dev/gemini-api/docs/generate-content/google-search

## Persistencia y límites

- Caché de 30 días por modelo/configuración, fuera de archivos públicos: directorio `.security` junto al `PRODUCTOS_PATH` configurado.
- Dos consultas simultáneas como máximo, lease con vencimiento de 120 segundos.
- 12 fichas nuevas por hora por dirección del peer y 100 por día globales, con presupuestos persistentes separados. Detrás de un proxy varios usuarios pueden compartir el mismo presupuesto.
- Timeout de proveedor de 45 segundos; no reintentos automáticos de pago ni fallback automático a otro proveedor.
- Datos sin soporte en grounding: «No confirmado». Errores: mensaje recuperable; nunca fichas inventadas.
- Gemini: las fuentes se extraen de groundingMetadata, no de enlaces escritos libremente por el modelo. Las sugerencias de búsqueda exigidas por Google se conservan y muestran en iframe sandbox sin scripts ni acceso al origen de la tienda.

## Alternativa explícita

La integración Anthropic preexistente queda disponible con `COMPARISON_AI_PROVIDER=anthropic` y `ANTHROPIC_API_KEY`. No se activa automáticamente.

## Estado de verificación

Probado con respuestas sintéticas de ambos proveedores, caché persistente, límites, errores, separación de categorías, privacidad y navegador responsive. No fue posible validar una respuesta real: no había clave de ninguno de los proveedores configurada. Antes de publicar, configurar Gemini y comprobar una ficha real y un segundo acceso servido desde caché.

Verificación final: 453 tests Python, 10 tests JS y recorridos Playwright de comparación/carrito aprobados. Citas Gemini vinculadas por offsets UTF-8 y partIndex, con pruebas de valores solapados y repetidos.
