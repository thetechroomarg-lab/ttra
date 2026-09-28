# Imágenes al actualizar el catálogo

Regla permanente del usuario (28/09/2026): conservar y reutilizar la base de imágenes existente. En cada actualización del catálogo, asociar correctamente cada producto y color con su imagen y generar únicamente imágenes faltantes para modelos o variantes nuevas.

- Consultar `outputs/catalogo-imagenes/manifest.json`, sus asociaciones y alias antes de generar. Ver `outputs/catalogo-imagenes/ESTADO.md` para el avance y las revisiones pendientes.
- Emparejar por marca, modelo exacto, generación, tamaño/diseño y color. Reutilizar entre capacidades de almacenamiento/RAM o condiciones comerciales solo cuando el aspecto físico sea el mismo. No confundir modelos Pro/Max/Plus, generaciones ni acabados; no asumir equivalencias ambiguas.
- Conservar archivos, identificadores, asociaciones y estados de revisión. No reiniciar el inventario ni regenerar imágenes existentes por cambios de precio, stock o nombre comercial.
- Crear solo las imágenes que falten. Las correcciones de imágenes defectuosas se versionan conservando el original. Una imagen pendiente de revisión no se considera aprobada por haber sido reutilizada.
- Para productos sin color informado, usar una imagen de referencia sin selector de color, según la decisión del usuario.
- Mantener el formato de card aprobado, con precios programáticos, logo e interacciones independientes de la imagen. La base aún está incompleta; no declarar cobertura total sin verificar el manifest.
