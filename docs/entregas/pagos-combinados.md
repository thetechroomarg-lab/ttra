# Cobro de entregas

El panel `/admin/clientes` muestra productos por fila y cinco alternativas para el total neto de cada pedido. La ventana de envío registra lo efectivamente recibido. Un método calcula el importe completo; varios requieren un importe positivo por moneda y validan su equivalencia con el total base.

## Cálculo

Se conservan los factores del catálogo: USD contado 1; banco USA 0,975; USDT 0,99; pesos contado 1; transferencia pesos 0,97. En pesos se usa la cotización del catálogo al abrir la ventana. El ajuste se aplica solo a la parte cubierta por cada método. Los precios de banco USA, USDT y transferencia pesos se redondean hacia arriba a la unidad, como en el catálogo. Los importes monetarios se guardan con hasta dos decimales.

La validación admite únicamente el excedente mínimo producido por redondear las opciones publicadas. El servidor recalcula y valida; no confía en el total ni en los factores enviados por el navegador. Si la cotización o el total cambian antes de guardar el cobro, responde 409 para que se revise.

## Persistencia y correo

`pedidos.recibo_pago` guarda métodos, moneda, importe recibido, factores, cotización y total base como snapshot. Se guarda antes del envío del correo. Si falla el proveedor, el pedido permanece pendiente y al reabrir se recuperan el cobro y la cotización original. Los reenvíos de recibos emitidos ignoran cualquier intento de modificar métodos.

El correo, el PDF descargable y el historial muestran el desglose guardado. Los recibos antiguos sin snapshot no se reinterpretan. Se mantienen compatibles los puntos de envío existentes del panel de clientes y del cadete que no mandan la selección nueva; esta interfaz está incorporada en la pantalla de entregas del admin.

## Despliegue

1. Aplicar `supabase/migrations/20261019_recibo_pago.sql` en la base del entorno destino, antes de publicar el código. Agrega una columna nullable; no transforma pedidos existentes.
2. Publicar el branch y comprobar en staging una entrega de prueba, sus fotos y el recibo.
3. El éxito del proveedor de correo significa envío aceptado, no entrega confirmada en la casilla.

No se aplicó la migración ni se desplegó como parte del desarrollo local.

## Verificación local

- `python -m pytest tests`
- `python -m pytest tests/browser/entregas_pagos.py` (requiere Playwright y Chromium instalados).

Las pruebas usan una base y un servicio de correo simulados. Las del navegador cubren escritorio, tablet y móvil, temas claro y oscuro, pagos simples/combinados, saldo insuficiente, Escape y retorno de foco, dirección, fotos y reintento tras fallo del correo. La prueba de extracción del PDF requiere Poppler.
