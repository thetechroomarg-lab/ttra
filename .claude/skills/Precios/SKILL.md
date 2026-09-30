---
name: precios
description: Consulta precios de productos de The Tech Room Arg (celulares, notebooks, accesorios) en las listas consolidadas de /Users/toraba/Precios Claude, calcula los 5 precios (USD, transferencia USD, USDT, pesos contado, transferencia pesos) y arma el mensaje listo para pasarle a un cliente. Usar cuando Vladimir pregunta "cuánto sale", "mejor precio de", pide un presupuesto para un cliente, quiere ver el stock/listado de una categoría, o pide precio mayorista de algo.
---

# Precios TTRA

Consulta las listas **consolidadas** (ya con proveedor ganador y margen aplicado)
en `/Users/toraba/Precios Claude` y arma respuestas de precio siguiendo las
reglas de negocio de Vladimir (ver memoria del proyecto).

Cada consulta cierra con un apartado interno ("Nota interna — NO mostrar al
cliente") con el proveedor y el costo de ese producto, sacados de
`web/proveedores.json` + `web/costos.json` — el mismo par de archivos que usa
la web en producción (`resolver_proveedor` en `web/productos.py`), generados
juntos en cada regeneración de catálogo, así que siempre están sincronizados
entre sí. **Ojo:** solo se actualizan cuando se regenera el catálogo completo
(no con `/lista` — ese script solo arma el Excel intermedio, no toca estos
JSON). Si pasó tiempo desde la última regeneración de catálogo, puede estar
desactualizado — el aviso muestra hace cuántos días se regeneró.

## Quick start

```bash
cd "/Users/toraba/TTRA Project"
python3 .claude/skills/precios/scripts/consultar_precio.py "s26 ultra"
```

Busca por palabras (todas deben aparecer en el nombre, sin importar orden ni
mayúsculas) en `Celulares.csv`, `Accesorios.csv` y `Notebooks_Macbooks.csv`, y
por cada coincidencia imprime: nombre, colores, los 5 precios, accesorios
incluidos y si es un equipo usado (para agregar el disclaimer).

Otros usos:

```bash
# precio mayorista, calculado EN VIVO (no lee Lista_Mayorista.csv, que se
# desactualiza si no se regenera cada vez que cambia costos.json)
python3 .claude/skills/precios/scripts/consultar_precio.py "s26 ultra" --mayorista

# listar todo el stock de una categoría
python3 .claude/skills/precios/scripts/consultar_precio.py --listar Celulares
# categorías válidas: Celulares, Accesorios, Notebooks_Macbooks

# forzar una cotización distinta a la de web/app.py
python3 .claude/skills/precios/scripts/consultar_precio.py "s26 ultra" --cotizacion 1580
```

El script lee `COTIZACION_DOLAR` de `web/app.py` automáticamente. Si cambió
la cotización y no se actualizó ahí, pasar `--cotizacion` explícito.

## Cómo se calculan los 5 precios

Fórmulas verificadas contra `web/app.py` y `web/productos.json` (no inventadas):

- **USD (billete)** = el campo `USD` del CSV tal cual (ya incluye el margen de venta).
- **Transferencia USD** = `ceil(usd / 0.975)` — mismo divisor que usa `web/app.py:461`.
- **USDT** = `ceil(usd / 0.99)` — mismo divisor que usa `web/app.py:462`.
- **Pesos contado** = `round(usd * cotización)` — verificado exacto contra `productos.json`.
- **Transferencia pesos** = `round(pesos / 0.97)` — verificado exacto contra `productos.json`.

**Mayorista (`--mayorista`)** no lee `Lista_Mayorista.csv` (puede quedar
desactualizado si no se regenera tras cada cambio de `costos.json` — pasó de
hecho con el S26 Ultra: el CSV decía $1050 y el cálculo real daba $1030).
En cambio calcula en vivo con la fórmula real de `web/mayoristas.py::descuento_por_margen`,
usando el costo de `web/costos.json`:

```
margen = usd_publico − costo
si margen < $35 → no elegible para mayorista
objetivo = min($50, floor(margen/5)*5 − 30)
descuento = max(0, min(objetivo, margen − 27))
usd_mayorista = usd_publico − descuento
```

Nunca descuenta más de $50 ni deja menos de $27 de margen. Los otros 4 precios
se recalculan igual que arriba a partir de ese USD mayorista. Ver
[[feedback-mayorista-3-precios]].

## Armar un presupuesto para un cliente

Después de correr el script, formatear la respuesta customer-facing aplicando
estas reglas ya guardadas en memoria (no repetirlas de memoria si ya están
claras acá, pero respetarlas siempre):

1. **Colores van como texto**, nunca como emoji ([[colores-como-emoji]] — se
   probó el emoji y Vladimir pidió revertirlo).
2. **Accesorios incluidos**: NO mencionarlos al cotizar precio
   ([[feedback-accesorios-solo-en-confirmacion]]) — esa lista (bolsa, escarapela,
   calcomanía, llavero; cargador gratis si es iPhone nuevo; mouse pad si es
   notebook/Macbook, ver [[feedback-accesorios-incluidos-por-producto]]) solo va
   cuando el cliente ya confirmó la compra y se arma el pedido/recibo.
3. **Nunca mencionar al proveedor** — la mercadería siempre se presenta como
   stock propio de Vladimir ([[feedback-nunca-mencionar-proveedor]]).
4. **Hablar en singular** — "te lo mando", "te coordino", nunca "nosotros"
   ([[feedback-hablar-en-singular]]).
5. Si el equipo es **usado** (el script lo marca con ⚠️), agregar el bloque de
   condiciones completo de [[disclaimer-iphones-usados]].
6. **Sin glosario** explicando los 5 precios — se probó y Vladimir lo revirtió
   ([[feedback-glosario-precios]]). El mensaje al cliente termina en los 5
   precios, sin explicación adicional.
7. **Nota de proveedor SIEMPRE aparte**, nunca mezclada con el texto del
   cliente ([[formato-mensaje-luego-proveedor]]) — es la que imprime el script
   al final, marcada "NO mostrar al cliente".
8. Ver también [[feedback-siempre-colores]] (siempre pasar colores) y
   [[respuestas-clientes-3-precios]].

## Consultar stock / listado completo

Para "qué tenés de Samsung" o "mostrame las notebooks", usar `--listar` con la
categoría y filtrar el resultado por marca/palabra si hace falta (o pasar el
término de marca directo al buscador normal, ej. `"samsung"`).

## Gotchas

- Los nombres de producto no son consistentes: mayúsculas mezcladas, "USADO"
  a veces en el nombre y a veces implícito en el color (`"Red 63%"`). El
  script detecta usados solo por la palabra "USADO" en el nombre — si un
  producto usado no la tiene en el nombre, no se va a marcar el disclaimer
  automáticamente; revisar el campo Colores a mano si hay "%" de batería.
- `Celulares.csv` mezcla iPhones y Android en el mismo archivo — la regla de
  "cargador gratis" solo aplica a los que tienen "iphone" en el nombre.
- Los 3 CSV retail (`Celulares`, `Accesorios`, `Notebooks_Macbooks`) ya tienen
  el margen aplicado; no restar ni sumar nada extra sobre el USD que traen.
