# Métricas, precios y estructuras de salida

## Índice
1. Definiciones y fórmulas
2. Distribución de costos fijos
3. Niveles de precio
4. Descuento máximo sostenible
5. Ficha por producto
6. Comparación de productos
7. Retorno sobre capital
8. Escenarios y sensibilidad
9. Mapa Financiero del Negocio

---

## 1. Definiciones y fórmulas

| Métrica | Fórmula |
|---|---|
| Costo de adquisición | precio proveedor convertido al tipo de cambio efectivo |
| Landed cost | adquisición + logística de entrada + importación + packaging |
| Neto recibido | precio cobrado − comisión − IVA s/comisión − impuestos al cobro − retiro/conversión |
| Costo variable | landed cost + costo de cobro + entrega + regalos + garantía esperada + mermas % + CAC (si se asigna por venta) |
| Margen bruto | venta − landed cost |
| Margen bruto % | (venta − landed cost) / venta × 100 |
| Markup | (venta − landed cost) / landed cost × 100 |
| Margen de contribución | venta − costos variables |
| Contribución % | contribución / venta × 100 |
| Beneficio operativo | contribución total − costos fijos (incluye sueldo del dueño) |
| Beneficio neto | operativo − costo financiero − impuestos sobre ganancia |
| Break-even (operaciones) | costos fijos mensuales / contribución promedio por operación |
| Break-even (facturación) | costos fijos mensuales / contribución % promedio |

**Margen vs. markup:** markup mide la ganancia contra el costo; margen contra el
precio. Mismo número de dólares, porcentajes distintos. Relación:
margen = markup / (1 + markup). 25% de markup = 20% de margen; 50% de markup =
33,3% de margen. Confundirlos lleva a creer que se gana más de lo que se gana y
a calcular mal los descuentos.

**Tipo de cambio efectivo:** pesos realmente pagados / dólares realmente
recibidos, con spread y comisiones adentro. Si el nominal es 1.565 y entre
spread y comisión se pierde 1,5%, el efectivo es 1.565 × 1,015 = 1.588,48.

## 2. Distribución de costos fijos

Antes de repartir, tené ventas mensuales, unidades, tickets, facturación,
categorías y margen por categoría. Presentá los modelos y recomendá uno:

- **A — Por operación:** fijos / operaciones. Simple; castiga productos baratos
  (un cable carga lo mismo que una MacBook).
- **B — Proporcional a facturación:** fijos × (venta del producto / facturación).
  Representa bien si el esfuerzo escala con el valor.
- **C — Proporcional al margen:** fijos × (contribución del producto /
  contribución total). Útil para ver qué sostiene la estructura; no sirve para
  fijar precios (es circular).
- **D — Activity Based Costing:** se asigna por actividad real (presupuestos,
  compras, entregas, garantías) con su costo hora. Lo más fiel cuando el tiempo
  del dueño es el costo fijo principal — suele ser el caso acá.

Para un negocio de un solo dueño, con entrega a domicilio y tickets muy
distintos entre accesorios y equipos, lo más representativo suele ser una mezcla:
**D para tiempo y entregas** (lo que escala por operación) + **B para el resto**
(web, software, contador). Explicá por qué con los números del mapa.

## 3. Niveles de precio

| Nivel | Cubre | Fórmula (sobre neto recibido) |
|---|---|---|
| Supervivencia | solo variables | costo variable / (1 − % costo de cobro) |
| Equilibrio | variables + fijo asignado | (variable + fijo asignado) / (1 − % cobro) |
| Objetivo | + margen neto deseado | (variable + fijo asignado) / (1 − % cobro − margen objetivo) |
| Recomendado | objetivo ajustado a mercado y riesgo | objetivo + colchón por riesgo cambiario/garantía; contrastar con precio de mercado |
| Promocional mínimo | temporal, sin destruir rentabilidad | entre supervivencia y equilibrio; solo con motivo (liquidar stock, gancho) y plazo |

Por debajo de supervivencia, cada venta pierde plata aunque "se mueva".

## 4. Descuento máximo sostenible

Un descuento sale entero de la contribución. Mostralo así:

- Descuento de US$D sobre contribución C → se pierde D / C de la ganancia.
- Ventas extra necesarias para compensar = C / (C − D) − 1.

Ejemplo: contribución US$60, descuento US$10 → se va el 16,7% de la ganancia y
hacen falta 20% más de ventas para ganar lo mismo. Descuento máximo sostenible =
contribución − (fijo asignado + margen mínimo aceptable).

## 5. Ficha por producto

```
PRODUCTO:
Costo proveedor:                [moneda, fuente]
Tipo de cambio:                 nominal / efectivo
Costo producto USD / ARS:
Logística:
Importación:
Medio de pago:
Comisiones de cobro:
Regalos incluidos:
Entrega:
Costo de garantía esperado:
Mermas / fraude (%):
CAC asignado:
Costo operativo asignado:       (tiempo del dueño + fijos, método usado)
Costo total estimado:
Precio venta:
Dinero neto recibido:
Ganancia bruta:
Margen bruto %:
Markup %:
Margen de contribución:
Margen de contribución %:
Ganancia neta estimada:
Margen neto estimado %:
Precio supervivencia / equilibrio / objetivo / recomendado / promo mínimo:
Descuento máximo sostenible:
Confianza:
```

Cada línea con su etiqueta 🟢🟡🔵🔴. Guardala en
`/Users/toraba/Precios Claude/Analisis de costos/fichas/<producto>.md` con la
fecha y el dólar usado, para poder recalcularla después.

## 6. Comparación de productos

Ordená por facturación, margen absoluto, margen %, contribución, rotación,
retorno sobre capital, riesgo y velocidad de venta. Clasificá:

- **Estrella:** alta rotación + buena rentabilidad. Cuidar disponibilidad.
- **Gancho:** margen bajo, pero trae clientes o ventas adicionales. Medir si
  realmente las trae.
- **Problemático:** mucho capital + poca rentabilidad.
- **A discontinuar:** baja rotación + bajo margen + alto riesgo.

## 7. Retorno sobre capital

Margen % solo no alcanza. Calculá:

- ROC por ciclo = ganancia / capital invertido.
- ROC mensualizado = ROC por ciclo × (30 / días hasta vender).
- ROC anualizado = ROC por ciclo × (365 / días hasta vender).

Ejemplo: A deja 10% y rota 10 veces al mes (3 días) → ~100% mensual sobre el
capital. B deja 25% y tarda 180 días → ~4,2% mensual. A es muchísimo mejor
negocio aunque su margen se vea peor. Si compra a pedido (cobra antes de pagar),
el capital propio es casi cero y el ROC tiende a infinito: ahí el límite es el
tiempo y el riesgo, no el capital — decilo.

## 8. Escenarios y sensibilidad

**Escenarios** (pesimista, conservador, base, optimista) moviendo: dólar,
ventas, costo de proveedor, comisiones, tasa de fallas, descuentos, CAC,
rotación. Tabla con ganancia por operación y ganancia mensual en cada uno.

**Riesgo cambiario** cuando compra y vende en monedas distintas: favorable,
base, desfavorable, extremo. Ej: si fija el precio en pesos hoy y le paga al
proveedor en dólares mañana, ¿cuánto pierde si el dólar sube 3%, 5%, 10%?

**Sensibilidad:** mover una variable por vez y medir el impacto en la ganancia
mensual. Casos mínimos: dólar +5%, proveedor +5%, ventas −20%, precio +5%,
publicidad +50%, fallas ×2, descuento US$10 y US$20, logística +20%. Ordenar de
más a menos peligrosa y decir cuál vigilar.

## 9. Mapa Financiero del Negocio

Estructura del archivo `mapa-financiero.md` y del informe final de auditoría:

```
# Mapa Financiero — THE TECH ROOM ARG
Actualizado: <fecha> · Dólar de referencia: <cotización y fuente>

## Ingresos           (facturación, operaciones, ticket, mix de categorías y medios de pago)
## Costos variables   (por operación y por categoría)
## Costos fijos       (mensuales, con amortizaciones)
## Costos financieros (capital, financiación, costo del dinero)
## Costos comerciales (publicidad, CAC, descuentos, regalos)
## Costos logísticos  (entrada y entrega)
## Costos administrativos (contador, software, tiempo de administración)
## Costos de garantía (tasa de fallas, costo esperado por categoría)
## Costos fiscales
## Capital inmovilizado (stock, días, depreciación)
## Riesgos
## Tiempo del propietario (horas, costo hora, costo humano por venta)
## Objetivos
## Datos faltantes 🔴 y cómo conseguirlos
## Costos que posiblemente estamos olvidando
## Historial de cambios (fecha — qué cambió)
```

Después del mapa, calculá: margen promedio, contribución promedio, punto de
equilibrio (operaciones y facturación), estructura mensual, facturación mínima
necesaria y rentabilidad estimada. Cerrá con confianza y recomendaciones
ejecutivas.
