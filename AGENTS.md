# Imágenes al actualizar el catálogo

Regla permanente del usuario (28/09/2026): conservar y reutilizar la base de imágenes existente. En cada actualización del catálogo, asociar correctamente cada producto y color con su imagen y generar únicamente imágenes faltantes para modelos o variantes nuevas.

- Consultar `outputs/catalogo-imagenes/manifest.json`, sus asociaciones y alias antes de generar. Ver `outputs/catalogo-imagenes/ESTADO.md` para el avance y las revisiones pendientes.
- Emparejar por marca, modelo exacto, generación, tamaño/diseño y color. Reutilizar entre capacidades de almacenamiento/RAM o condiciones comerciales solo cuando el aspecto físico sea el mismo. No confundir modelos Pro/Max/Plus, generaciones ni acabados; no asumir equivalencias ambiguas.
- Conservar archivos, identificadores, asociaciones y estados de revisión. No reiniciar el inventario ni regenerar imágenes existentes por cambios de precio, stock o nombre comercial.
- Crear solo las imágenes que falten. Las correcciones de imágenes defectuosas se versionan conservando el original. Una imagen pendiente de revisión no se considera aprobada por haber sido reutilizada.
- Para productos sin color informado, usar una imagen de referencia sin selector de color, según la decisión del usuario.
- Mantener el formato de card aprobado, con precios programáticos, logo e interacciones independientes de la imagen. La base aún está incompleta; no declarar cobertura total sin verificar el manifest.

- Una sola imagen por modelo físico exacto y color: NEW/nuevo, usado/USED, activado, CPO, porcentaje de batería, RAM y almacenamiento no crean variantes visuales. Por ejemplo, todos los iPhone 15 azules reutilizan la misma imagen. Ejecutar `reutilizar.py` antes de armar lotes; generar solo identificadores canónicos faltantes, nunca sus alias. Conservar imágenes anteriores aunque se unifiquen asociaciones.

- Prioridad de generación: celulares, notebooks, MacBooks, accesorios/resto. Desde 30/09, continuar de a una y desplegar automáticamente cada 20 imágenes nuevas guardadas, con verificación previa y posterior. Llevar conteo persistente; reutilizaciones no cuentan como imágenes nuevas.


# Correos obligatorios al cargar clientes y pedidos

Regla permanente del usuario (19/10/2026): al cargar un cliente nuevo, enviarle el correo de acceso a su cuenta; al cargar un pedido, enviar siempre su confirmación por correo. El usuario autoriza estos envíos como parte de cada carga. Verificar el resultado de ambos envíos antes de dar la tarea por completada; si alguno falla, informarlo y resolverlo sin duplicar el cliente ni el pedido. Distinguir envío aceptado de entrega confirmada.

# Cotizaciones al usuario

Regla permanente del usuario (19/10/2026): cada vez que se pasa precio de uno o varios productos, incluir el enlace directo de cada producto en la web propia https://thetechroomarg.com. Usar el nombre exacto vigente del catálogo en el parámetro `producto`, codificado con `urllib.parse.urlencode` (espacios como `+`), tal como el enlace copiado manualmente por el usuario. No convertir el nombre a slug. Ejemplo aprobado: `https://thetechroomarg.com/?producto=AirPods+5+Noise+Cancellation`. No reemplazarlo por links de Google Imágenes ni por la página general del catálogo.

- Formato para WhatsApp: entregar siempre la URL completa visible como texto plano; nunca usar enlaces Markdown con etiqueta (`[texto](url)`). Si se entrega un mensaje listo para copiar, usar un bloque de texto para conservar la URL literal.

- Regla permanente del usuario (22/10/2026): acompañar cada cotización con un apartado separado de información para el usuario que indique qué proveedor tiene el producto y color cotizados. Mantenerlo fuera del mensaje para el cliente; indicar la fecha de la lista consultada y no confundir disponibilidad informada con stock confirmado.
