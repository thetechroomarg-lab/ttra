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
   manchada", o stock 0. Anotar el motivo.
3. **Unificación:** si el mismo modelo exacto se repite (distintos colores) → una sola fila.
   En **iPhones usados**, agrupar los porcentajes de batería entre paréntesis en el nombre:
   `iPhone 13 128GB (84%) (87%)`.
4. **Regla "slim":**
   - Celular (Motorola, Xiaomi, POCO, etc.) que dice "slim" → borrar "slim" y poner
     `(s/ cargador)`.
   - Notebook (ej. Lenovo Slim) → dejar "slim" intacto.

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
   - `proveedor` es una etiqueta para identificar la fuente (nombre del archivo o del chat).
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
