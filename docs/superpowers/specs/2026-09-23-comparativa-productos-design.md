# Comparación de productos — diseño

## Objetivo y decisiones
Añadir a las cards un icono de comparación junto a Compartir. Abre una búsqueda embebida para elegir un segundo producto del catálogo actual, de la misma sección. La selección navega a /comparativa y muestra ambos equipos lado a lado con especificaciones en bullets y aviso de extracción web y análisis por IA.

Decisión confirmada por Vladimir: consultar las especificaciones cuando se solicita un modelo por primera vez y guardar la ficha con sus fuentes para reutilizarla.

## Interacción y presentación
- Icono SVG propio inspirado en las dos flechas y círculos de la referencia; mismo tamaño, borde, trazo, foco y colores que los accesos de fotos/especificaciones/compartir. Área táctil mínima 44 px y etiqueta «Comparar producto».
- El buscador aparece dentro de la card, con nombre del primer producto visible. Busca por nombre y marca, sin distinción de mayúsculas ni tildes, exclusivamente en los datos actuales del catálogo. Excluye el mismo producto. No consulta Internet ni IA para autocompletar.
- Solo un buscador de comparación abierto; se cierra con su botón, Escape o clic fuera. Lista accesible por teclado con estados sin coincidencias y selección inequívoca.
- Misma categoría significa la sección devuelta por web.catalogo.seccion_de: Celulares, Tablets, Notebooks y Macbooks, Gaming o Accesorios Celulares. Puede cruzar marcas y condición nuevo/usado/CPO dentro de una sección. La restricción se valida también en servidor.
- /comparativa?a=<identificador>&b=<identificador> permite recarga, enlaces y navegación Atrás. Resolver identificadores determinísticos desde productos actuales; rechazar desconocidos, idénticos o de secciones distintas.
- Producto original a la izquierda, elegido a la derecha. Dos columnas en desktop y mobile, títulos ajustables y bullets alineados por atributo, sin desbordar la página. No incorporar imágenes inventadas ni fotos genéricas como si fueran del modelo exacto.
- Mantener header y dock persistentes, ambos temas y animación del gato sin reiniciarla; incluir /comparativa en el contrato de navegación existente.
- Mostrar nombres y datos comerciales vigentes del catálogo. Las fichas web no deciden precios, stock, colores, salud de batería ni condición de las unidades usadas.
- Aviso: «Las especificaciones fueron extraídas de fuentes web y analizadas por una IA. Pueden contener errores o variar según la versión del equipo. Revisá las fuentes antes de decidir.» Mostrar enlaces a fuentes y fecha de consulta.

## Especificaciones y fuentes
- Reutilizar la integración Anthropic del servidor, en un módulo separado del chat. Preferir páginas oficiales del fabricante; no inferir una ficha a partir del nombre sin fuentes.
- Campos comunes ordenados por sección: teléfonos/tablets (pantalla, procesador, memoria, almacenamiento, cámaras, batería nominal, carga, conectividad y sistema); computadoras (pantalla, CPU, GPU, RAM, almacenamiento, conexiones, sistema); gaming/accesorios (tipo, compatibilidad, conexiones y características verificadas pertinentes).
- Identificar modelo y configuración exactos. No confundir Pro/Pro Max, generación, capacidad, región o versión. Cuando la fuente no confirma un campo: «No confirmado». No afirmar especificaciones de productos no anunciados usando rumores.
- Salida estructurada y validada con límites de tamaño. Cada atributo confirmado debe referenciar una fuente obtenida realmente por la búsqueda. URLs externas HTTP(S) seguras; texto renderizado como texto, no HTML del modelo.
- No enviar datos de usuarios, domicilios, costos, proveedores, sesiones ni pedidos al servicio IA. Solo nombre/modelo y atributos públicos necesarios.

## Persistencia, costos y errores
- Guardar fichas por identidad de modelo/configuración y versión de esquema en almacenamiento persistente del servidor; SQLite en el volumen de datos existente, fuera de static.
- Usar una ficha por modelo/configuración; diferencias de color o salud de batería no alteran la ficha técnica general, pero sí deben permanecer visibles como datos propios del producto cuando corresponda.
- TTL propuesto: 30 días. Evitar generación duplicada concurrente para el mismo modelo mediante bloqueo persistente con vencimiento. Cachear solo resultados validados con fuentes; errores con breve espera de reintento.
- Limitar solicitudes y concurrencia del servicio de generación; límites de búsquedas, tokens y timeout. La comparación de fichas ya guardadas no vuelve a llamar a la IA.
- La interfaz muestra carga por columna y mantiene los datos del catálogo disponibles. Ante ausencia de clave, cuota, timeout o falta de fuentes: aviso honesto y reintento, sin fabricar especificaciones. Nunca exponer mensajes internos ni credenciales.
- No modificar clientes, pedidos ni paneles admin/cadete. No desplegar sin solicitud para estos cambios.

## Integración prevista
- Nuevo módulo backend de comparación/fichas y rutas de lectura/generación validadas en web/app.py.
- Componente frontend compartido para icono y buscador en catalogo.js y cards de landing.js; no duplicar búsqueda ni control de categoría.
- Nuevos comparativa.html/css/js y adaptación puntual de cat-navigation.js para conservar el header.
- El catálogo actual sigue siendo la fuente de productos; ningún resultado externo se incorpora al inventario.

## Verificación
- Tests: misma sección entre marcas, rechazo entre secciones/mismo producto/ID inválido, búsqueda solo catálogo, cache/reutilización/concurrencia, expiración, fuentes inválidas, timeout, clave ausente, saneamiento y ausencia de datos privados enviados a IA.
- Pruebas de navegador: abrir/cerrar buscador, selección por teclado/touch, ruta y recarga, header persistente, modo claro/oscuro y pantallas 320/390/1440 px.
- Ejecutar suite Python y pruebas JS existentes de precios, carrito y catálogo. Simular IA en tests; una prueba real acotada al validar integración, sin datos personales.

## Referencias revisadas
- Código existente: web/catalogo.py, web/chat.py, web/static/catalogo.js, web/static/landing.js y web/static/cat-navigation.js.
- Documentación oficial: https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-search-tool (citas, límites de búsqueda y fuentes).

Estado: diseño preparado para revisión; implementación pendiente.

## Ajuste confirmado durante implementación
Vladimir pidió la opción barata o gratuita. Gemini 2.5 Flash-Lite queda como proveedor predeterminado con Google Search; Anthropic requiere selección explícita. Se conserva la caché por modelo y la validación de fuentes. Activación pendiente de GEMINI_API_KEY. Ver docs/comparativa-configuracion.md.
