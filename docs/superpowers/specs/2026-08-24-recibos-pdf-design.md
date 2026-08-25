# Diseño: Recibos PDF con Evidencias y Garantías

## Objetivo

Evitar solapamientos en las tablas del recibo, incluir las fotos de serie
adjuntadas al correo dentro del PDF y mostrar condiciones de garantía resumidas
por tipo de producto.

## Diseño

`web.recibos.pdf_recibo(cliente, pedido, fotos=None)` recibirá bytes de fotos
JPEG opcionales. Las celdas de la tabla serán `Paragraph` de ReportLab, para
que los nombres se partan dentro de su columna. Las fotos se mostrarán bajo
"Fotos de entrega", escaladas y en grilla, sin exceder el ancho de A4.

El endpoint de envío validará y reunirá las fotos antes de construir el PDF.
Las guardará en el bucket privado como hasta ahora, las adjuntará al correo y
pasará los mismos bytes al PDF. El endpoint que abre un recibo histórico
descargará las rutas persistidas del bucket y generará el PDF con ellas.

Las garantías se resolverán por Apple, Samsung, Motorola, Xiaomi, notebooks y
electrónica/accesorios. Cada texto conservará vigencia, cobertura, exclusiones,
requisitos y plazos relevantes, en una versión apta para recibos.

## Restricciones

- No se exponen URLs públicas de fotos de serie.
- Todas las imágenes siguen limitadas a JPEG comprimido de hasta 2,5 MB.
- Un producto de nombre largo nunca puede invadir otra columna.
- El PDF puede usar más de una página si garantía o fotos lo requieren.
