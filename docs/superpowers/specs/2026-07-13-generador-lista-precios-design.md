# Generador de lista consolidada de precios (comando `/lista`)

**Fecha:** 2026-07-13
**Estado:** Diseño aprobado — pendiente de plan de implementación

## Problema

Se reciben precios de varios proveedores en formatos heterogéneos (export Excel/CSV de
un portal con login, planillas de Google Sheets, y mensajes de chat pegados a mano). Hoy
consolidar todo y aplicar el margen es manual y lento. Se busca un proceso repetible que
tome esas entradas y devuelva una única lista de venta con el margen aplicado.

## Objetivo

Un comando reutilizable (`/lista`, una skill de Claude Code) que, dado uno o más archivos
adjuntos y/o texto de proveedores pegado en el chat, genere un **archivo Excel (.xlsx)**
con la lista consolidada de 4 columnas y una hoja de reporte con lo que requiere criterio
humano.

## Enfoque

Flujo asistido en el chat con **reglas fijas** encapsuladas en una skill. El usuario aporta
las entradas y ejecuta `/lista`; la skill aplica siempre las mismas reglas de limpieza,
consolidación y cálculo, y produce el .xlsx. Se eligió este enfoque (sobre un script
autónomo) por la alta variabilidad de los formatos de entrada, que se manejan mejor con
procesamiento de texto flexible. Puede evolucionar a un script determinístico más adelante,
cuando los formatos estén estables.

## Decisiones tomadas

| Tema | Decisión |
|------|----------|
| Origen | Precios de proveedores → mi lista de venta. |
| Entradas | Archivos adjuntos (Excel/CSV) + texto pegado en el chat. Varios proveedores por corrida. |
| Salida | Un archivo Excel (.xlsx) descargable. |
| Lista de salida | Una sola lista consolidada, generada desde cero en cada corrida (sin catálogo previo). |
| Moneda | Todo en USD. Si un ítem trae dos precios (USD y pesos), se usa solo el primero (USD). |
| Margen | Monto fijo por banda de costo (tabla abajo). |
| Redondeo | Precio de venta redondeado **hacia arriba al múltiplo de $5**. |
| Duplicados entre proveedores | Una fila por producto, con el **costo más barato**. |
| Emparejamiento de nombres | **Conservador**: fusiona solo si el nombre normalizado coincide; los parecidos no idénticos van al reporte, no se fusionan. |

## Tabla de bandas (margen por costo, en USD)

Límites interpretados de forma que cubran decimales (cada banda es "hasta X inclusive"):

| Costo (USD) | Monto a sumar |
|-------------|---------------|
| hasta $300 | +$30 |
| $300,01 – $600 | +$40 |
| $600,01 – $900 | +$50 |
| $900,01 – $1.300 | +$70 |
| $1.300,01 – $1.600 | +$85 |
| $1.600,01 – $2.000 | +$130 |
| $2.000,01 – $2.400 | +$160 |
| más de $2.400 | +$200 |

## Reglas de procesamiento

### A) Columna "Nombre" (descripción limpia y unificada)

1. **Limpieza de texto:** quitar emojis, asteriscos de negrita del chat, líneas de colores
   y textos de "Disponible".
2. **Filtros (eliminar por completo):** ítems que digan "caja abollada", "caja manchada",
   o con stock en 0.
3. **Unificación:** si el mismo modelo exacto se repite (por venir en distintos colores),
   dejarlo en una sola fila. En **iPhones usados**, agrupar los porcentajes de batería
   entre paréntesis en la misma celda, por ejemplo: `(84%) (87%)`.
4. **Regla "slim":**
   - Si el producto es un celular (Motorola, Xiaomi, POCO, etc.) y dice "slim": borrar
     "slim" y reemplazar por `(s/ cargador)`.
   - Si es una notebook (ej. Lenovo Slim): dejar "slim" intacto (es parte del modelo).

### B) Consolidación entre proveedores

- Mismo producto en varios proveedores → una sola fila con el **costo más barato**.
- Emparejamiento **conservador**: fusionar solo cuando el nombre normalizado (sin
  mayúsculas/acentos/espacios de más) coincide. Los nombres parecidos pero no idénticos
  NO se fusionan; se listan en el reporte para decisión manual.

### C) Columna "Precio"

- Tomar el **costo base en USD** (ignorar el precio en pesos si viene un segundo valor).
- Buscar la banda del costo → sumar el monto fijo → **redondear hacia arriba a múltiplo
  de $5**. Resultado: número entero.

### D) Columna "Link Google Imágenes"

- Generar automáticamente: `https://www.google.com/search?tbm=isch&q=` + el nombre del
  modelo, con los espacios reemplazados por `+`.

### E) Columna "País"

- Siempre el emoji de bandera de EE.UU. (🇺🇸) en todas las filas.

## Salida (archivo .xlsx)

**Hoja 1 — Lista:** 4 columnas, en este orden.

| Nombre | Link Google Imágenes | País | Precio |
|--------|----------------------|------|--------|
| iPhone 13 128GB (84%) (87%) | https://www.google.com/search?tbm=isch&q=iPhone+13+128GB | 🇺🇸 | 645 |

**Hoja 2 — Reporte:**
- **Filtrados:** ítems removidos por "caja abollada / caja manchada / stock 0".
- **Posibles duplicados:** nombres parecidos no fusionados, para decisión manual.
- **Dudas de precio:** ítems sin costo válido (texto, vacío, 0) o formato no interpretable.

## Casos borde

- Ítem sin costo válido → no va a la Hoja 1; va a "Dudas de precio" en el Reporte.
- Producto que no se puede clasificar como celular/notebook para la regla "slim" → se
  aplica el criterio más seguro (dejar el texto como viene) y se anota en el Reporte si
  hay duda.

## Fuera de alcance (por ahora)

- Scraping automático del portal con login (se usa su export Excel/CSV).
- Emparejamiento aproximado agresivo de nombres (se hace conservador + reporte).
- Mantener un catálogo propio con historial (la lista se genera desde cero cada vez).
- Script/herramienta autónoma fuera del chat (posible evolución futura).

## Criterios de éxito

- Dadas entradas de varios proveedores, `/lista` produce un .xlsx con las 4 columnas
  correctamente armadas y los precios calculados según la tabla de bandas + redondeo.
- Nada se descarta en silencio: todo lo filtrado o dudoso aparece en la hoja Reporte.
- El emparejamiento nunca fusiona productos distintos por nombre parecido.
