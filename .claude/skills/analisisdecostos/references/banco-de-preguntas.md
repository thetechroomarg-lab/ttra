# Banco de preguntas de la auditoría

No es un cuestionario para recitar. Es la lista de todo lo que puede existir,
para elegir de acá las 5–12 preguntas de cada ronda según lo que ya se sabe y lo
que Vladimir vaya contestando. Tachá mentalmente lo que ya está en el mapa.

## Índice
1. Modelo de negocio
2. Compra de mercadería y tipo de cambio
3. Logística e importación
4. Medios de pago y costo de cobro
5. Impuestos
6. Costos variables por venta
7. Garantías y postventa
8. Costos fijos
9. Publicidad y CAC
10. Tiempo del propietario
11. Inventario y depreciación
12. Capital y costo financiero
13. Riesgos, mermas y fraude
14. Objetivos de rentabilidad
15. Repreguntas típicas (lo "gratis")

---

## 1. Modelo de negocio

Primera ronda sugerida: productos, proveedores, monedas, volumen, facturación,
stock, canales, operaciones por mes, ticket promedio, modalidad de entrega.

- Qué vende: productos, servicios o ambos. Categorías (celulares, notebooks/Mac,
  accesorios, usados/CPO) y peso de cada una en la facturación.
- Stock propio, bajo pedido, preventa, o mezcla. Qué porcentaje de cada uno.
- Importa, compra local, a distribuidores. Cuántos proveedores (az, ba, em, fr,
  oh, va, master) y cuánto se le compra a cada uno.
- En qué moneda compra; en qué moneda cobra (USD billete, transferencia USD,
  USDT, pesos contado, transferencia pesos) y qué mix tiene.
- Operaciones por mes, unidades por mes, ticket promedio, facturación mensual.
- Estacionalidad: temporadas altas y bajas (lanzamientos de iPhone, fin de año,
  Día del Padre/Madre, vuelta a clases).
- Canales: web, WhatsApp, Instagram, marketplace, presencial. De dónde viene
  cada venta.
- Trabaja solo, empleados, tareas tercerizadas (cadete, diseño, contador).
- Entregas propias, envíos al interior, local, casa, depósito, vehículo.

## 2. Compra de mercadería y tipo de cambio

**Precio de proveedor:** precio base, moneda, descuentos por volumen,
bonificaciones, promociones, mínimo de compra, condiciones especiales, cada
cuánto cambian los precios, si el precio de lista es el que finalmente paga.

**Tipo de cambio** (clave con OH, que lista en pesos):
- Qué cotización usa y de dónde sale (blue, MEP, la del proveedor).
- Spread compra/venta; comisión por convertir; si compra USD o USDT.
- Exchange: comisión, comisión de red, spread contra el dólar.
- Costo de mantener dólares (oportunidad, riesgo de guardar billetes).
- Diferencia entre el día en que fija precio al cliente y el día en que le
  paga al proveedor.
- Calcular siempre **tipo de cambio efectivo** = pesos que realmente salieron /
  dólares que realmente llegaron.

## 3. Logística e importación

- Cómo llega la mercadería del proveedor: retira él, le mandan, cadete, costo
  de cada viaje, cuántos productos por viaje.
- Si importa: flete internacional, courier, consolidación, seguro, aduana,
  derechos, tasas, IVA importación, despachante, almacenaje, transporte desde
  aeropuerto/depósito.
- Packaging propio: bolsa, caja, cinta, protección, etiquetas, tarjeta.
- Si varios productos comparten un envío, proponer cómo repartirlo: por unidad,
  por peso, por volumen, por valor FOB, proporcional al costo. Para tecnología
  de valor alto y tamaño parecido suele ser más representativo **proporcional
  al valor** (el seguro y el riesgo escalan con el valor); por unidad sirve si
  el costo es un viaje fijo. Explicar la elección.

## 4. Medios de pago y costo de cobro

Para cada medio que acepta (efectivo USD, efectivo ARS, transferencia ARS,
transferencia USD, USDT, Mercado Pago, tarjeta, otros):
- Comisión % y fija; IVA sobre la comisión.
- Retenciones, percepciones, impuesto a débitos y créditos.
- Costo de retiro o de pasar a otra cuenta; costo de conversión; spread.
- Días de acreditación y costo financiero de esa demora (con inflación en
  pesos, 2 días también cuestan).
- Si el precio cambia según el medio (los 5 precios) y si ese recargo cubre el
  costo real del medio o no.
- Riesgo: billetes falsos, transferencias revertidas, USDT a red equivocada.

Resultado: **neto recibido por cada US$100 cobrados** en cada medio.

## 5. Impuestos

- Estructura: monotributo (categoría), responsable inscripto, informal,
  sociedad. Qué parte de las ventas se factura.
- IVA, Ingresos Brutos (alícuota y jurisdicción), Ganancias, tasas municipales,
  impuesto a débitos y créditos, percepciones en compras.
- Contador: honorario mensual.
- Modelar con los números que da Vladimir; aclarar que lo fiscal se confirma
  con el contador.

## 6. Costos variables por venta

Todo lo que aparece solo si hay venta:
- Entrega: cadete (Alejo) por entrega o por día, combustible, peajes,
  estacionamiento, viáticos.
- Regalos incluidos: bolsa, escarapela, calcomanía, llavero en toda venta;
  cargador en iPhone; mouse pad en notebook/Mac. Costo real de cada uno.
- Packaging e impresiones (recibo, etiquetas).
- Comisiones a vendedores o referidos; comisión de marketplace.
- Descuentos, códigos promo, cashback, fidelización.
- Costo esperado de garantía, devoluciones, fraude, productos defectuosos.
- Mensajes/llamadas por operación si tienen costo.

## 7. Garantías y postventa

- Qué garantía da por marca/categoría (ver `web/garantias.json`) y cuánto dura;
  garantía de usados (30 días).
- Tasa histórica de fallas por categoría, aunque sea aproximada ("de cada 50
  iPhones, ¿cuántos volvieron?").
- Costo promedio de resolver: reparación, reemplazo, traslado ida y vuelta,
  tiempo propio.
- Si el proveedor reconoce la garantía, en cuánto tiempo, y cuánto se recupera.
- **Costo esperado de garantía** = probabilidad de falla × (costo de resolver −
  lo que recupera del proveedor). Se suma al costo unitario.

## 8. Costos fijos

Barrido exhaustivo; preguntar por todo, incluso lo que parece no aplicar:
- Espacio: alquiler, expensas, luz, gas, agua, internet, seguridad, alarma,
  limpieza, seguro.
- Comunicación: celular(es), líneas, WhatsApp Business.
- Profesionales: contador, abogado.
- Web y software: hosting (Railway), Supabase, dominio, envío de mails,
  Google Workspace, Claude/ChatGPT y otras IA, Canva, Adobe, almacenamiento
  cloud, apps.
- Marketing fijo: diseñador, community manager, contenido.
- Vehículo: seguro, patente, mantenimiento, amortización.
- Equipamiento: computadora, teléfono, impresora, cámara — amortización
  mensual (valor / meses de vida útil).
- Cadete si cobra fijo y no por entrega.
- Preguntar abiertamente: "¿hay algo que pagás todos los meses y no nombramos?"

## 9. Publicidad y CAC

- Gasto mensual en Meta/Instagram, Google, TikTok, influencers, sorteos,
  contenido.
- Consultas que genera, ventas que genera, tasa de conversión.
- Clientes nuevos vs. recurrentes por mes; de dónde llega cada cliente
  (orgánico, referido, pauta).
- **CAC** = gasto comercial / clientes nuevos adquiridos. Después:
  ganancia por cliente (en su vida, si vuelve) − CAC.

## 10. Tiempo del propietario

- Horas por día y días por semana.
- Reparto del tiempo: consultas y presupuestos, compras a proveedores,
  entregas, administración, garantías, marketing, armado de listados, web.
- Cuánto considera que debería ganar por mes por ese trabajo (sueldo de
  mercado de alguien que haga lo mismo).
- **Costo hora** = sueldo objetivo / horas trabajadas al mes.
- Tiempo promedio por operación (consulta + presupuesto + compra + entrega +
  postventa), incluyendo consultas que no compran: **costo humano por venta**
  = costo hora × horas totales del mes atribuibles a ventas / ventas del mes.

## 11. Inventario y depreciación

- Valor promedio del stock propio; días promedio hasta vender por categoría;
  rotación; stock muerto o de baja rotación.
- Cuánto bajan de precio los equipos (por mes y al salir un modelo nuevo),
  calendario de lanzamientos, descuentos necesarios para liquidar.
- **Depreciación esperada** = valor del stock × caída esperada de precio en el
  tiempo que tarda en venderse.
- Caja abierta/abollada: cuánto se descuenta para venderla.

## 12. Capital y costo financiero

- Capital propio, crédito, tarjeta, préstamos, proveedor que financia, adelantos
  de clientes (señas), descubierto.
- Si hay financiación: tasa, plazo, cuotas, comisión, costo financiero total.
- Costo del dinero propio: lo que rendiría en otra parte (ej. plazo fijo en
  USD, staking de USDT). **Costo de capital inmovilizado** = capital × tasa
  anual × días / 365.
- Capital de trabajo necesario para el volumen actual y para crecer.

## 13. Riesgos, mermas y fraude

- Productos dañados, robos, pérdidas, errores de stock, devoluciones, fraude,
  billetes falsos, comprobantes de transferencia falsos.
- Riesgo de entregar antes de cobrar; riesgo en la calle durante entregas.
- Riesgo cambiario: cotización fijada al cliente vs. dólar al pagar al
  proveedor; precio en pesos para entrega al día siguiente.
- Convertir todo a **% esperado sobre ventas**.

## 14. Objetivos de rentabilidad

- Qué margen neto quiere (5%, 10%, 15%, 20%, 25%, 30%) y cuánto quiere ganar
  por mes en total, aparte de su sueldo.
- Contrastarlo con lo que necesita según fijos, rotación, riesgo, garantías,
  volatilidad y capital. Advertir si es bajo.
- Si prefiere volumen con margen chico o menos ventas con margen alto.

## 15. Repreguntas típicas (lo "gratis")

| Si dice… | Preguntá… |
|---|---|
| "Las entregas son gratis" | quién entrega, cuánto le pagás, cuánto tarda, km, combustible, estacionamiento, mantenimiento, seguro, tu tiempo, cuántas por día |
| "Acepto transferencia" | banco, comisión, impuestos, acreditación, spread, si el precio cambia |
| "Doy garantía" | cuántas vuelven, cuánto cuesta cada una, quién paga el traslado, cuánto reconoce el proveedor |
| "El cargador va de regalo" | cuánto te cuesta, de qué proveedor, cuántos regalás por mes |
| "No tengo stock, compro a pedido" | cuánto tiempo pasa entre que cobrás y pagás, qué pasa si el proveedor no tiene, señas |
| "La web no me cuesta nada" | hosting, base de datos, dominio, mails, herramientas de IA, horas tuyas de mantenimiento |
| "Lo hago yo" | cuántas horas, a qué costo hora |
| "Casi nunca falla" | de cada 100, cuántos; qué pasó la última vez |

## Costos que posiblemente estamos olvidando

Lista para revisar al final de cada ronda: tiempo propio, desplazamientos,
desgaste del vehículo/teléfono, garantías, devoluciones, software, comisiones,
impuesto al débito/crédito, depreciación de stock, capital parado, publicidad,
descuentos, diferencias de cambio, costos bancarios, errores, fraude, productos
dañados, regalos, consultas que no compran.
