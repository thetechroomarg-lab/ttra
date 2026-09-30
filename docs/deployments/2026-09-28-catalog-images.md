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

Publicado mediante Git en web-ttra: commit 6172943bd0b8b0546dd88ea0f23f0b6ab7550d8b. Railway eb163b74-33a5-42aa-899f-fdcae36a4609 SUCCESS. La subida directa fue rechazada por 413 debido a assets heredados; el paquete final se publicó desde checkout aislado, sin cambios ajenos. Verificación pública 390/1440px: 537 productos, 200 cards nuevas, 1000 importes, imágenes cargadas, sin errores JS ni desbordamiento.


28/09 — Segundo despliegue: c7db2524d74a027e79e5c75b084318149d93558f, Railway 273e3103-b4c0-4b93-ba7f-94085b65fdf3 SUCCESS. +23 WebP, 251 imágenes reutilizables publicadas. Pruebas locales 320/390/1440, landing y fallback aprobadas. Verificación pública 390/1440: 537 productos preservados, 227 cards con imágenes, 1135 precios, sin errores JS ni overflow. Después se reanudó generación de MacBook Air M2; esas nuevas imágenes todavía son locales.

28/09 — Publicado backlight coral y MacBook Air M2 con asociaciones unificadas. Commit f9b5292; Railway 13878a05-67f7-486b-9990-ad3a81ec4e14 SUCCESS. QA pública 390/1440: 537 productos, 229 cards AI, 1145 precios, box-shadow activo, sin errores JS ni overflow. 253 imágenes reutilizables exportadas.
