---
name: lista
description: Genera un Excel de lista consolidada de precios a partir de archivos/textos de proveedores, aplicando el margen por bandas. Usar cuando el usuario adjunta o pega precios de proveedores y pide "la lista", "el listado" o "/lista".
---

# Generar lista consolidada de precios

Convierte los precios de proveedores (archivos adjuntos y/o texto pegado) en un Excel de
4 columnas + una hoja de reporte. La parte determinística (precio, redondeo, link, dedup,
.xlsx) la hace el script `generar_lista.py`; vos hacés la limpieza y clasificación de texto.

## REGLA OBLIGATORIA — proveedores completos

Antes de generar CUALQUIER listado, verificá que estén los **5 proveedores**:
**az, em, fr, va, ba**.

- **az**: export Excel del portal (archivo).
- **em**: archivo .xlsx del proveedor (o texto).
- **fr**: texto de difusión pegado.
- **va**: texto de difusión pegado.
- **ba**: se baja solo por URL publicada (Google Sheets export CSV).

Si falta alguno, **NO generes el listado**: avisale al usuario exactamente cuál/es
falta(n) y esperá a que lo pase. También pedí la **cotización del día** si no la dio.
Nunca armes una lista parcial salvo que el usuario diga explícitamente que quiere seguir
sin ese proveedor.

## Consulta puntual para un cliente (sin generar Excel)

Cuando Vladimir pega la consulta de un cliente por **un producto puntual** junto con los
precios crudos que tenga a mano de sus proveedores (no hace falta tener los 5, ni correr
`generar_lista.py`): buscá manualmente cuál proveedor lo tiene más barato para ese ítem,
calculá el precio final con la misma banda de márgenes (ver `bands.py` / reglas de margen
en memoria), y respondé con el mensaje de WhatsApp de 3 precios. Aparte del mensaje para el
cliente, decile a Vladimir qué proveedor era (esa parte nunca va en el texto del cliente).
Esto es independiente del flujo batch de más abajo — no genera ningún Excel.

## Disponibilidad (qué NO incluir)

- **em**: incluir SOLO los ítems con Estado = "Disponible". Ignorar "No Disponible" y
  "En Tránsito".
- **ba**: ignorar los ítems marcados "ENTRANTE" y los de cantidad 0.
- General: fuera perfumes, vapers, repuestos y paletas de pádel (ya excluidos).

## Respuestas a clientes (cuando Vladimir pega el chat de un cliente)

- **Siempre en formato WhatsApp**, listo para copiar y pegar (tono cordial, emojis,
  cerrando con una pregunta).
- Mostrar SIEMPRE los **3 precios** por producto: 🇺🇸 U$D · 🇦🇷 $ pesos · 🏦 $ transferencia
  (pesos ÷ 0,97).
- **NUNCA** mostrar el proveedor (sigla az/em/fr/va/ba) en el texto que se copia al cliente:
  es info solo de Vladimir. Si hace falta, dársela aparte, marcada "solo para vos".
- Ceñirse a lo que pide el cliente; no ofrecer extras salvo que él lo pida.

## Reglas para armar cada ítem (columna "Nombre")

1. **Limpieza:** quitar emojis, asteriscos de negrita, líneas de colores y textos de
   "Disponible".
2. **Filtros — NO van a la lista, van a `filtrados`:** ítems con "caja abollada", "caja
   manchada", "sin stock", o stock 0. Anotar el motivo.
3. **Unificación:** si el mismo modelo exacto se repite (distintos colores) → una sola fila.
   **Excepción — iPhones usados:** conservar cada combinación real de **color y
   porcentaje de batería** informada por el proveedor. En el dropdown de variantes,
   cada opción debe mostrar ambos datos juntos, por ejemplo: `Negro · batería 84%`
   y `Blanco · batería 87%`. No agrupar colores y porcentajes por separado ni generar
   combinaciones que el proveedor no ofreció.
   **Título limpio:** el nombre debe contener solo modelo, capacidad y condición,
   por ejemplo `iPhone 13 Pro Max 128GB (Usado)`. Nunca añadir porcentajes de batería
   al título. Guardar las opciones en `colores`/variantes: por ejemplo
   `Blue 93%`, `Gold 100%`, `Grafito 95%`, `Green 95%`, `Green 100%`.
   Conservar colores distintos aunque compartan porcentaje. Si la fuente solo
   informa porcentajes, usarlos como opciones sin inventar colores. Preservar estas
   variantes separadas al generar el listado y al cargar/publicar el catálogo.
   No inventar colores ni porcentajes faltantes:
   señalar el dato no informado para revisión. Esta regla rige para todos los
   próximos listados de iPhones usados.
   **Dropdown obligatorio (regla general, todos los productos):** si hay colores o
   variantes informados, mostrar siempre el dropdown, incluso cuando exista una
   única opción. No preseleccionar ninguna variante: el selector debe iniciar con
   **Elegí una opción de color** como placeholder, y **Agregar al carrito** desactivado.
   Al abrirlo, mostrar solo las opciones reales disponibles; si existe un único color,
   será la única opción seleccionable. Activar el CTA únicamente después de que el
   usuario seleccione explícitamente una opción. Nunca reemplazar el selector por
   texto fijo. Para nuevos, el título es
   **Colores disponibles:**; para usados, **Color y % de batería:**.
   Conservar la combinación original de color y batería y no inventar datos.
   **Fechas de cobertura:** conservarlas completas dentro de su variante (por ejemplo,
   `Mist Blue 89% Grado A+ Cobertura 1/02/27`). Nunca dividir una fecha por sus barras
   ni convertir día, mes o año en opciones de color. Para separar variantes de texto,
   usar `normalize.separar_variantes` y contrastar el resultado con la fuente.
5. **Batería (iPhones usados):** mantener el % de batería que declara el proveedor al
   lado del nombre. **Filtrar (mandar a `filtrados`) todo usado con batería < 80%.**
6. **Colores (regla general, todos los productos):** si el proveedor especifica color(es),
   declararlos al lado del nombre (ej. `Moto Edge 60 Pro 12GB 512GB (Gris / Uva)`). NO crear
   una columna de color. Si no lo especifica, dejar sin color.
7. **Sin marca en el nombre:** la sección ya indica la marca, así que quitá el prefijo de
   marca del nombre y dejá nombres uniformes (`A07 128GB`, no `Samsung A07 128GB`).
8. **Excluir "caja abierta"** además de caja abollada/manchada.
4. **Regla "slim":**
   - Celular (Motorola, Xiaomi, POCO, etc.) que dice "slim" → borrar "slim" y poner
     `(s/ cargador)`.
   - NO celular (notebook, consola como PS5 Slim, tablet, etc.) → dejar "slim" intacto.

## Reglas de precio

- Usar el **costo en USD**. Si hay un segundo precio (pesos), ignorarlo.
- Si un ítem no tiene costo numérico claro → NO calcular; mandarlo a `dudas_precio` con el
  motivo. Nunca inventar un costo.
- El cálculo del precio final (banda + redondeo a $5) lo hace el script; vos solo pasás el
  costo USD.

## Procedimiento

1. Leé todos los archivos adjuntos y/o el texto pegado.
2. Armá un JSON con esta forma exacta:

   ```json
   {
     "items": [ {"nombre": "iPhone 13 128GB (84%)", "costo": 630, "proveedor": "ProvA"} ],
     "filtrados": [ {"nombre": "iPhone 12 (caja abollada)", "motivo": "caja abollada"} ],
     "dudas_precio": [ {"texto": "Samsung A15 consultar", "motivo": "sin costo numérico"} ]
   }
   ```

   - `costo` es el número USD (sin símbolos).
   - `proveedor` es la **sigla del proveedor** = el nombre del archivo/fuente (az, em, fr,
     ba, va, …). Sale como columna "Proveedor" en el Excel para saber quién tiene cada
     producto. Con "una fila, el más barato", queda la sigla del proveedor más barato.
   - Cada ítem de `items` DEBE tener `costo` numérico. Si no lo tiene, va a `dudas_precio`.
3. Guardá ese JSON en el scratchpad, p. ej. `entrada.json`.
4. Ejecutá el script (usá el venv del proyecto):

   ```bash
   cd "/Users/toraba/TTRA Project" && ./.venv/bin/python generar_lista.py <ruta/entrada.json> <ruta/lista.xlsx>
   ```

5. Entregá el archivo `.xlsx` al usuario y resumí en el chat: cuántos productos quedaron,
   cuántos se filtraron, y cuántos posibles duplicados hay para revisar.

## Importante

- No modifiques el precio a mano: siempre sale del script (determinístico).
- El emparejamiento por más barato y el reporte de posibles duplicados los hace el script;
  vos NO fusiones productos parecidos por tu cuenta — dejá que el script los reporte.
