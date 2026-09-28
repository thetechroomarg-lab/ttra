# Integración de imágenes de catálogo

Base de producción: `307957ddd1c85504572112cd41eabe4290d658bd`.
Paquete aislado: `/tmp/ttra-image-release`, construido con `git archive`; no incluye otros cambios locales.
Servicio: Railway `glistening-warmth`, `ttra`, entorno `production`.

Se agregan `catalog-images.js`, `catalog-images.css` e índice público exacto producto/color con 228 WebP reutilizables (8,4 MB). Se conectan en index/catalogo y sus renderizadores. Se conserva el catálogo de producción; no se exportan precios al índice de imágenes.

Cobertura comprobada con GET del catálogo público: 537 productos; 200 con todas las imágenes de sus variantes, 337 con la card previa. Los productos parcialmente ilustrados conservan su card anterior para no mostrar un color incorrecto. Productos sin color usan referencia sin selector. Estados de revisión del manifest original intactos.

Precios tomados de `preciosDe(producto)` al renderizar, sin cachear importes. Botones y enlaces existentes se conservan con sus eventos. Si falla índice, coincidencia o carga de imagen, se conserva/restaura la card anterior. Se protegen renderizados asíncronos al filtrar rápidamente.

Validación: tests/browser/catalog_images.py sobre snapshot de producción (API simulada; sin transacciones reales), 320/390/1440px, carrito real en localStorage, color, cinco precios, compartir, comparación, imágenes rotas y referencia sin selector. Landing en 390/1440px. Sin errores JS ni desborde. 10 pruebas tests/test_catalogo_precios.js aprobadas.

Actualizaciones: `scripts/export_catalog_images.py` exporta desde manifest sin modificar originales. Incorporar asociaciones exactas al manifest y volver a exportar; no inferir modelos parecidos. No reutilizar nombres de archivo al corregir imágenes: versionarlos para evitar caché obsoleta.

Rollback: restaurar despliegue previo `8fccdafc-683a-4f81-98fb-78f228f56b87` de Railway. Ninguna migración ni escritura de datos requerida.
