# Ganancias en USD y saldos por forma de pago

## Objetivo acordado

Mostrar cuánto falta pagar en cada alternativa del recibo. Agregar al panel una sección privada de ganancias, exclusivamente en dólares, con filtro de fechas, ingresos manuales y reconstrucción histórica desde el primer recibo disponible. Descontar costos de productos, comisiones y gastos, incluidos los pagos a Alejo.

## Saldos del recibo

Sin pagos elegidos, cada alternativa muestra su total. Después de ingresar un pago parcial, las alternativas sin seleccionar muestran el saldo pendiente convertido a su moneda con el ajuste y redondeo existentes. Seleccionar una alternativa copia exactamente el importe mostrado a su campo editable. Las opciones seleccionadas muestran el importe asignado a cada una; los importes manuales no se sobrescriben. El saldo automático se recalcula cuando cambian los otros pagos o el precio. El envío continúa sujeto a que los pagos cubran el total.

## Integración dentro de la app

Las secciones se llaman **Cotización del dólar** y **Ganancia**. Ambas se abren dentro del panel existente, con la misma navegación, sesión, diseño y comportamiento móvil, sin pestañas nuevas ni páginas de apariencia independiente. Conservar el acceso directo a cotización redirigiendo a la sección integrada.

## Sección Ganancia

Acceso exclusivo del administrador, adaptado al celular. Filtro desde/hasta por fecha argentina. Mostrar ingreso por ventas, costo de mercadería, comisiones, gastos de Alejo, otros gastos, ingresos manuales y resultado neto. Todos los importes financieros de esta sección se muestran en USD; las monedas de origen se conservan internamente como evidencia.

Cada venta se identifica por pedido/recibo original. Un reenvío no crea otro ingreso. Congelar precio efectivamente vendido, cantidades, costo por producto, descuentos, fecha y fuentes. Los costos no se recalculan con futuras listas. Evitar descontar nuevamente descuentos ya incluidos en el precio final. Si se parte del importe neto del cobro, no descontar otra vez la comisión usada para llegar a ese neto.

Registrar cada pago efectivo a Alejo una sola vez, por su identificador y fecha de pago, como gasto del período. No restar además los movimientos de entrega cubiertos por ese mismo pago. Los saldos internos, anulaciones y créditos no se importan como nuevos pagos. Los pagos reconstruidos desde movimientos deben conciliarse con los pagos reales para evitar duplicados. Mostrar los gastos pendientes aparte, sin confundirlos con pagos realizados.

La vista resume ventas por fecha de emisión del recibo y pagos a Alejo por fecha del desembolso; dejar esas fechas explícitas en el detalle. Los pagos por adelantado también se identifican como tales. No atribuir arbitrariamente un pago agrupado a una sola venta.

Ingresos manuales: fecha, concepto e importe USD; permitir también gastos manuales USD para cubrir otros costos. Correcciones y anulaciones conservan trazabilidad. Cada acción de registro utiliza una clave de idempotencia para evitar duplicación por doble toque o reintento.

## Conversión a dólares

Para operaciones nuevas conservar el tipo de cambio aplicado junto al movimiento original. Para históricos en pesos usar primero la cotización documentada de la operación o fecha. No convertir retrospectivamente usando la cotización actual sin marcarlo como estimado. Conservar internamente monto original, moneda, cotización, fecha y fuente, aunque el panel muestre únicamente USD.

Las comisiones reales comprobadas prevalecen sobre reglas comerciales. El recargo publicado de un método no demuestra por sí solo la comisión efectivamente cobrada. Cuando se use una regla como aproximación, clasificar el resultado como estimado.

## Reconstrucción histórica

Inventariar recibos emitidos, pedidos, ventas importadas y archivos históricos de costos. Buscar la primera operación disponible sin asumir numeración correlativa ni interpretar un número inicial alto como comprobantes faltantes. Conciliar registros importados y recibos de la misma venta antes de cargarlos.

Clasificar por evidencia: confirmado, estimado o pendiente. Un costo ausente nunca se trata como cero. Los pendientes no se suman como ganancia confirmada. Mostrar cantidades y totales confirmados y estimados por separado, y permitir completar datos faltantes.

Preparar un informe previo con cobertura, faltantes, duplicados y estimaciones. La importación persistente debe ser idempotente y registrar procedencia, método de cálculo y versión. No modificar recibos originales ni reenviar correos al reconstruir el historial.

## Implementación y seguridad

Reutilizar autenticación del panel, las reglas actuales de pagos y las tablas de pedidos y saldo del cadete. Agregar tablas privadas para los registros financieros y sus referencias, con RLS y escritura solamente desde el servidor administrativo. No incluir costos en respuestas del catálogo, recibos ni APIs de clientes.

Capturar costos y tipos de cambio en los eventos nuevos, incluyendo carga administrativa y flujo web; registrar la venta al confirmar la emisión. Reintentos y reenvíos no duplican datos. Los fallos del registro financiero quedan pendientes de conciliación sin repetir correos ni marcar falsamente el registro como completo.

Mantener la vista local con datos simulados. El desarrollo y la validación no modifican las finanzas de producción.

## Verificación

Pruebas de saldo mostrado versus campo completado, múltiples monedas, redondeos, pagos mixtos y edición USD. Pruebas de resultado neto, descuentos y comisiones sin doble cómputo, pagos agrupados y anticipos de Alejo, conversiones históricas, costos ausentes, conciliación e importación repetida. Comprobar permisos, filtros de fechas y formulario móvil de ingresos/gastos manuales. Validar que costos nunca se expongan al cliente.
