---
name: lista
description: Genera un Excel de lista consolidada de precios a partir de archivos/textos de proveedores, aplicando el margen por bandas. Usar cuando el usuario adjunta o pega precios de proveedores y pide "la lista", "el listado" o "/lista".
---

# Generar lista consolidada de precios

Convierte los precios de proveedores (archivos adjuntos y/o texto pegado) en un Excel de
4 columnas + una hoja de reporte. La parte determinística (precio, redondeo, link, dedup,
.xlsx) la hace el script `generar_lista.py`; vos hacés la limpieza y clasificación de texto.

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
