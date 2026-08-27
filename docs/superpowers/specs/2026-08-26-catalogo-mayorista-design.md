# Catálogo mayorista con acceso por cliente

## Objetivo

Permitir que un administrador habilite o revoque el acceso mayorista de una cuenta desde Admin → Clientes. El cliente habilitado utilizará la misma web y la misma interfaz, pero recibirá un catálogo preferencial calculado desde el costo real. El flujo normal no debe cambiar para visitantes, clientes minoristas ni contactos sin cuenta.

## Reglas comerciales

- Gasto operativo estimado: USD 7 por unidad.
- Ganancia limpia mínima: USD 20 por unidad.
- Piso absoluto del precio mayorista: `costo proveedor + USD 27`.
- Descuento máximo: USD 50 por unidad.
- Los descuentos se asignan según el margen bruto actual (`precio público USD - costo proveedor`) y se aplican en escalones de USD 5.
- El descuento efectivo siempre será el menor entre el valor de la banda y `precio público - costo - 27`.
- Los productos con margen bruto menor a USD 35 no forman parte del catálogo mayorista.
- Los productos sin costo interno válido tampoco forman parte del catálogo mayorista.
- En modo mayorista no existen el descuento por cantidad ni los códigos de descuento de mailing. No se acumulan promociones monetarias con el precio mayorista.

### Tabla de descuentos

| Margen bruto actual | Descuento objetivo |
|---:|---:|
| USD 80 o más | USD 50 |
| USD 75–79,99 | USD 45 |
| USD 70–74,99 | USD 40 |
| USD 65–69,99 | USD 35 |
| USD 60–64,99 | USD 30 |
| USD 55–59,99 | USD 25 |
| USD 50–54,99 | USD 20 |
| USD 45–49,99 | USD 15 |
| USD 40–44,99 | USD 10 |
| USD 35–39,99 | USD 5 |
| Menos de USD 35 | Producto excluido |

El precio final se obtiene con:

```text
capacidad_segura = precio_publico - costo - 27
descuento = min(descuento_banda, capacidad_segura)
precio_mayorista = precio_publico - descuento
```

Como defensa adicional, el backend verifica después del cálculo que `precio_mayorista >= costo + 27`. Los valores normales generados por las bandas producen descuentos enteros de USD 5; si un dato excepcional reduce la capacidad segura por debajo de la banda, se usa la capacidad segura exacta sin perforar el piso.

## Persistencia y datos internos

El campo existente `clientes.tipo_cliente` representa el acceso. El valor `mayorista` habilita el modo; cualquier otro valor se trata como minorista. Sólo una cuenta con `auth_id` puede habilitarse.

La generación del catálogo conservará dos salidas separadas:

- `productos.json`: catálogo público actual, sin cambios en su contrato para usuarios normales.
- `costos.json`: mapa interno de nombre normalizado a costo consolidado del proveedor.

`costos.json` se genera junto con `productos.json` y `proveedores.json`, utiliza el mismo producto consolidado y vive en almacenamiento del servidor. Nunca se sirve como archivo estático ni se incluye en respuestas de API. Su ruta podrá configurarse con `COSTOS_PATH`, con una ubicación predeterminada junto a `PRODUCTOS_PATH`.

Si el catálogo y los costos quedan desincronizados, el modo minorista sigue funcionando. En el modo mayorista sólo se incluyen productos con una coincidencia de costo válida y positiva.

## Autorización y panel administrativo

La lista de clientes muestra:

- Insignia `Mayorista` para cuentas habilitadas.
- Botón `Habilitar mayorista` para cuentas minoristas registradas.
- Botón `Quitar mayorista` para cuentas habilitadas.
- Control deshabilitado con la explicación `El cliente todavía no tiene una cuenta` para contactos sin `auth_id`.

Una ruta administrativa autenticada alterna exclusivamente entre `mayorista` y `minorista`. La acción exige confirmación en la interfaz. El backend valida la sesión administrativa, la existencia del cliente y que posea una cuenta antes de habilitar el acceso. La revocación surte efecto en la siguiente consulta al servidor.

El tipo de cliente no se confía a datos enviados por el navegador. Se resuelve desde Supabase usando el `cliente_id` de la sesión.

## Catálogo y precios por sesión

La API de catálogo conserva la respuesta actual para usuarios anónimos y minoristas. Para una sesión mayorista:

1. Resuelve el cliente autenticado en el servidor.
2. Carga el catálogo público y el mapa interno de costos.
3. Calcula margen, elegibilidad, descuento y precio mayorista por producto.
4. Filtra productos con margen menor a USD 35 o costo inválido.
5. Recalcula desde el precio USD mayorista los valores de pesos, transferencia, banco USA y USDT con las reglas vigentes.
6. Devuelve sólo datos públicos y precios finales; no devuelve costo, margen, proveedor ni capacidad de descuento.

La respuesta indica únicamente que corresponde al modo `mayorista`, para que la interfaz muestre `Cuenta mayorista · precios preferenciales`.

## Interfaz del cliente

Se reutilizan la landing, las categorías, el buscador, las tarjetas, el carrito y el checkout actuales. No habrá una segunda aplicación ni una URL paralela.

En modo mayorista:

- Las tarjetas muestran directamente el precio preferencial, sin precio público tachado.
- Sólo se renderizan productos elegibles.
- Se muestra una etiqueta discreta indicando el modo mayorista.
- Se ocultan el descuento por cantidad y los controles de códigos de mailing.
- El carrito, el mensaje de WhatsApp y el checkout utilizan precios mayoristas.
- Si se revoca el acceso, la siguiente carga sustituye los productos guardados por los precios minoristas actuales o elimina del carrito los que ya no existan.

## Seguridad del pedido

El navegador no es autoridad sobre precios. Al crear un pedido, el backend:

1. Resuelve nuevamente el tipo de cliente.
2. Reconstruye el catálogo autorizado para esa sesión.
3. Valida nombre, cantidad y precio unitario de cada ítem.
4. Recalcula subtotales y total.
5. Rechaza productos fuera del catálogo y cualquier precio manipulado.

Los pedidos guardan `modo_precio` (`minorista` o `mayorista`), los precios unitarios efectivos y `descuento_mayorista_usd`. Estos datos permiten emitir recibos y auditar la operación sin depender del catálogo futuro.

Los pedidos minoristas conservan su comportamiento actual. La validación de servidor se incorpora de forma compatible con las estructuras existentes.

## Promociones

Para una sesión mayorista:

- `descuentoPorUnidad` no se aplica ni se muestra.
- Los códigos de mailing no se validan ni consumen.
- Un descuento de mailing guardado previamente en el navegador se elimina al detectar el modo mayorista.
- Los códigos promocionales monetarios futuros deberán declararse explícitamente compatibles; por defecto no lo serán.

Los regalos no monetarios quedan fuera de este cambio y conservan su funcionamiento, porque no alteran el precio ni el piso de margen del producto vendido.

## Errores y comportamiento seguro

- Falta de costo o costo inválido: producto oculto sólo en mayorista.
- Fallo al cargar el archivo interno de costos: catálogo mayorista vacío con mensaje de actualización; catálogo minorista intacto.
- Cliente inexistente o sin cuenta al habilitar: respuesta de error sin modificar datos.
- Precio enviado distinto del autorizado: pedido rechazado y carrito obligado a refrescar precios.
- Revocación durante una sesión: la siguiente carga o intento de compra utiliza precios minoristas.

No se utilizará como fallback el precio mayorista calculado por el navegador.

## Pruebas y criterios de aceptación

- El generador conserva el costo consolidado correcto sin exponerlo en `productos.json`.
- Visitantes y clientes minoristas reciben exactamente el catálogo y los descuentos actuales.
- Sólo un cliente con cuenta puede ser habilitado como mayorista desde Admin.
- Habilitar y revocar actualiza `tipo_cliente` y cambia el catálogo en la siguiente consulta.
- Cada banda aplica el descuento esperado, incluido el máximo de USD 50.
- Ningún precio mayorista queda por debajo de `costo + 27`.
- Un margen menor a USD 35 excluye el producto.
- Un producto sin costo interno se excluye sólo del catálogo mayorista.
- Los precios derivados en cada moneda se recalculan desde el USD mayorista.
- En mayorista no se aplica descuento por cantidad ni código de mailing.
- El backend rechaza cantidades, productos, subtotales o precios manipulados.
- Los pedidos guardan el modo y el descuento mayorista auditables.
- La interfaz normal no presenta cambios visuales ni funcionales.

## Fuera de alcance

- Listas mayoristas distintas por cliente.
- Edición manual de descuentos por producto.
- Descuentos acumulables.
- Exposición de costos o proveedores al cliente.
- Una segunda web o catálogo independiente.
- Cambios a la experiencia minorista actual.
