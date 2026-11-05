# Rutina de actualización del catálogo

## Instrucciones del usuario — 04/11/2026

- Priorizar las planillas directas confirmadas en la sección **Fuentes directas vigentes**. WhatsApp Web queda como fuente únicamente para proveedores o categorías sin planilla directa.
- Para cada chat/proveedor, usar como fuente base el **primer mensaje extenso/completo del día de la fecha** (la lista larga del día). Ignorar para la consolidación los mensajes posteriores de promociones, ofertas o novedades parciales: no deben reemplazar, complementar ni recortar la lista base. Si no existe una lista extensa/completa ese día, conservar la última lista completa registrada y no eliminar productos por mensajes parciales.
- Frecuencia solicitada: todos los días a las 11:00, hora de Argentina (America/Argentina/Cordoba).
- Leer precios, aplicar las reglas existentes de márgenes y actualizar el catálogo.
- El usuario autoriza los pushes de esta rutina a staging y main. Verificar antes de publicar y comprobar staging antes de promover a main.
- Conservar las imágenes y asociaciones según AGENTS.md.
- Cotización general: tomar la cotización vigente de AZ en su planilla directa. Si las columnas autorizadas A:C no contienen una cotización numérica inequívoca, detener la publicación e informar el dato faltante; no buscarla en columnas no autorizadas.
- Cotización OH: calcular como cotización AZ menos 30 pesos. No tomar una cotización independiente de OH.
- Registrar el mensaje y fecha de la cotización AZ utilizada. Si no se puede determinar una cotización numérica vigente sin ambigüedad, detener la publicación e informar el dato faltante; no inventar ni sustituir la fuente.

## Flujo diario en dos etapas — confirmado el 04/11/2026

1. A las 11:00 ART, leer y preparar todas las fuentes directas disponibles: AZ, EM, BA, OH y FR-notebooks, más cualquier otra fuente diaria verificable que no sea VA ni FR-celulares/resto.
2. Guardar un candidato preliminar y registrar fechas, filtros y cotización, pero **no consolidar definitivamente ni publicar** mientras falten las listas completas del día de VA y FR.
3. Avisar al usuario en el chat que el candidato está preparado y solicitar las listas completas del día de **VA** y **FR**. No pedir promociones ni novedades parciales.
4. Cuando el usuario pegue o adjunte ambas listas, guardarlas como snapshots fechados de esa jornada, incorporar VA y FR al candidato y continuar la misma ejecución.
5. Recién después ejecutar consolidación final, reutilización/generación de imágenes, tests, `check_catalog_images.py`, verificación de staging y promoción de los mismos cambios a main.
6. No publicar un catálogo parcial sin VA o FR. Si solo llega una de las dos listas, conservar el candidato en espera y avisar cuál falta, sin duplicar el trabajo ya preparado.

## Correspondencias confirmadas por el usuario

| Chat (nombre observado en WhatsApp) | Proveedor |
| --- | --- |
| Lista mayorista | Mike (`mike`) |
| Franco celu (lista y novedades) | FR |
| Tienda Porte (Nueva Difusion) | AZ |
| NICOLÁS VANGUARDIA GC | VA |
| IMPO CBA | EM |

Mike usa el identificador interno **`mike`**, confirmado por el usuario el 04/11/2026. Es un proveedor independiente: no corresponde a `master` ni debe fusionarse con proveedores históricos. Sus entradas se guardan como `entrada_mike.json` y deben incluirse explícitamente en la consolidación diaria.

## Fuentes directas vigentes — confirmadas el 04/11/2026

### AZ

- URL: https://docs.google.com/spreadsheets/d/1RIKmRi8HWjyH-iwLk3aiAbBRrhjTVTks7ZEeYdIjzsc/edit?gid=1096248826#gid=1096248826
- Pestaña autorizada: `TELEFONOS` (`gid=1096248826`).
- Leer **únicamente las columnas A, B y C**. No leer otras columnas ni modificar la planilla.
- Aunque el título interno del archivo sea `Lista de precios - Mike`, el usuario asignó explícitamente esta fuente a AZ; conservar esa asignación y no fusionarla con `mike`.

### EM

- URL: https://docs.google.com/spreadsheets/d/1hz5MBX-R6vuzyQDse7khDNqmngrqYBcp-B06TI4xV6M/edit?gid=0#gid=0
- Leer todas las pestañas visibles: `Mac`, `iPad`, `iPhone`, `iWatch`, `AirPods`, `Accesorios Varios y Cargadores` y `Parlantes`.
- No modificar la planilla.

### BA

- URL: https://docs.google.com/spreadsheets/d/1QvOvgzcHOsu6aSt1ApifUPd4gcLbRqSJYYybWVHDi1E/edit?gid=0#gid=0
- Pestaña: `NOTEBOOK` (`gid=0`). Aplicar además el filtro obligatorio detallado abajo.

### OH

- URL: https://docs.google.com/spreadsheets/d/10ctdf9EFesEGQOglIzKvypX4i_4tZiI0mfmLAhhRjow/edit?gid=1460927496#gid=1460927496
- Pestaña: `Texto` (`gid=1460927496`).
- Leer `Rubro`, `Producto`, `Precio`, `Stock`, `Colores` y `Novedades y Ofertas`.
- Incluir únicamente filas con `Stock = SI` y precio numérico válido. Registrar como filtradas las filas sin stock o sin precio.
- No usar `Novedades y Ofertas` para reemplazar el precio unitario base; registrar por separado las promociones por cantidad.
- Los precios están en pesos: convertir el costo a USD con dólar OH = cotización AZ − $30 y registrar ambas cotizaciones y la fecha de lectura.
- No modificar la planilla ni leer las pestañas ocultas de importación.

### FR — notebooks solamente

- URL: https://docs.google.com/spreadsheets/d/1-D4tjaHht4rfXzboRekz5tq_CK4731e5kAVauuglof4/edit?gid=0#gid=0
- Pestaña principal: `Hoja 1` (`gid=0`). Esta planilla cubre únicamente notebooks de FR y no reemplaza su lista de celulares.
- No modificar la planilla.

### FR — celulares y resto

- Snapshot completo del **04/11/2026** entregado por el usuario: `/Users/toraba/.codex/attachments/a29d3106-0748-45ab-b966-c58a768e21be/Pasted text.txt`.
- Usar este archivo como lista completa de FR únicamente para la actualización del 04/11/2026. En fechas posteriores no presentarlo como lista vigente del día.
- Hasta recibir un nuevo snapshot completo de FR, conservar estas ofertas como la última lista completa registrada, sin bajas, recortes ni actualización de precios. La planilla de notebooks sí puede seguir actualizándose diariamente.
- El archivo contiene 403 líneas y 17.969 bytes. Conservarlo sin modificaciones como evidencia de fuente.
- Ignorar promociones o novedades parciales de WhatsApp posteriores; no deben complementar ni reemplazar este archivo.

### Fuentes todavía sin planilla directa

- **VA:** snapshot completo del **04/11/2026** entregado por el usuario: `/Users/toraba/.codex/attachments/04c70cb3-f30f-450e-818c-1a0577e63baf/Pasted text.txt`.
- El archivo de VA contiene 815 líneas y 14.603 bytes, con Motorola, Samsung, Apple, Xiaomi y productos varios. Conservarlo sin modificaciones como evidencia de fuente.
- Usar este archivo como lista vigente únicamente para la actualización del 04/11/2026. En fechas posteriores conservarlo como última lista completa registrada, sin bajas, recortes ni actualización de precios, hasta que el usuario entregue un snapshot nuevo.
- Ignorar promociones o novedades parciales de WhatsApp posteriores; no deben complementar ni reemplazar el archivo completo de VA.
- **FR celulares y resto no-notebooks:** usar el archivo completo entregado por el usuario indicado arriba. La planilla de notebooks lo complementa; no lo reemplaza.
- VA y FR cuentan con snapshots completos fechados del 04/11/2026, no con fuentes permanentes. No sustituirlos por lecturas parciales de WhatsApp ni presentarlos como listas nuevas en corridas posteriores.

## Fuente directa de BA — confirmada el 04/11/2026

- Proveedor: **BA**.
- Planilla: **Notebook Mayorista**, pestaña `gid=0`.
- URL: https://docs.google.com/spreadsheets/d/1QvOvgzcHOsu6aSt1ApifUPd4gcLbRqSJYYybWVHDi1E/edit?gid=0#gid=0
- Consultar directamente cada día; no sale de WhatsApp ni depende de un mensaje nuevo allí. Registrar fecha de lectura y preservar las cantidades, estados y especificaciones informadas. No editar la fuente.
- **Filtro obligatorio BA:** excluir antes de consolidar productos que indiquen `ENTRANTE` (sin distinguir mayúsculas/minúsculas) o tengan cantidad `0`, aunque informen precio. Registrar el motivo en `filtrados`; no usar esas ofertas para precios ni disponibilidad. Esta regla reemplaza el tratamiento anterior de entrantes de BA.
- Al actualizar, retirar la oferta BA excluida también si estaba publicada anteriormente. Conservar el producto cuando exista otra oferta válida de otro proveedor o stock propio. Verificar el filtro antes de publicar.

## Estado

- Acceso interactivo a WhatsApp Web verificado el 04/11/2026; fue posible leer la etiqueta y contenido de listas.
- También se observaron Ohmy Gadgets Mayorista y Back Up Notebooks en la etiqueta. Sus correspondencias internas todavía no fueron confirmadas por el usuario.
- Regla de cotización confirmada por el usuario: general = AZ; OH = AZ − $30.
- Automatización creada y activa el 04/11/2026 en este chat: `actualizar-cat-logo-desde-proveedores`, todos los días a las 11:00, hora de Argentina. Todavía no se verificó el flujo completo desatendido.
- No se publicó una actualización como parte de esta configuración.
- Regla de selección de mensajes confirmada el 04/11/2026: tomar la primera lista extensa/completa del día por proveedor e ignorar promociones posteriores.
- Correspondencia interna confirmada el 04/11/2026: `Lista mayorista` = Mike = `mike`, separado de `master`.
- Fuentes del 04/11/2026: AZ, EM, BA, OH y FR-notebooks pasan a planillas directas; FR-celulares/resto y VA usan snapshots entregados solo para esa fecha y luego quedan como última lista completa registrada hasta recibir reemplazos.
- Flujo diario confirmado el 04/11/2026: preparar las fuentes directas, detenerse antes de consolidar/publicar, avisar en el chat y reanudar únicamente cuando el usuario entregue las listas completas del día de VA y FR.
