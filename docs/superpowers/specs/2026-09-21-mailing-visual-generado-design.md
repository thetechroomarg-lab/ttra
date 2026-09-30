# Mailing visual generado con IA

## Objetivo

Extender la campaña de novedades existente para que cada borrador pueda incluir una pieza promocional generada con IA, sin convertir el correo en una imagen opaca ni permitir envíos accidentales. El resultado será un mail híbrido: arte visual protagonista y contenido esencial en HTML real.

La preparación y el envío serán acciones separadas. Preparar una campaña nunca enviará correos; enviar exigirá que exista un borrador aprobado y una confirmación explícita en una orden posterior.

## Decisiones confirmadas

- La propuesta visual se genera automáticamente a partir de los productos, precios y nota de campaña.
- Vladimir puede agregar un brief o dirección artística opcional.
- Siempre se produce una vista previa antes de aprobar.
- La aprobación no envía la campaña.
- El envío se ejecuta mediante una orden separada y explícita.
- La pieza visual no contendrá el CTA principal como única forma de interacción: el botón, los precios críticos, el texto alternativo y la baja seguirán siendo HTML.

## Alternativas consideradas

### Una única imagen como correo completo

Se descarta porque un cliente que bloquee imágenes recibiría un correo prácticamente vacío. También perjudica accesibilidad, selección de texto, adaptación móvil y confiabilidad del CTA.

### HTML tradicional con varias fotografías de producto

Es una opción robusta, pero ofrece menos libertad creativa y exige disponer de fotografías consistentes para cada producto. No cumple tan bien el objetivo de producir una campaña visual distintiva a partir de un brief corto.

### Correo híbrido con hero generado — elegido

Combina una imagen promocional generada con IA con encabezado, precio, CTA, contacto y baja en HTML. Conserva el impacto visual y mantiene funcional el mensaje cuando las imágenes no cargan.

## Experiencia de uso

La skill vivirá en `.claude/skills/mailing/` y reconocerá cuatro intenciones:

1. **Preparar**: seleccionar productos vigentes, validar precios, interpretar la nota o brief y crear una propuesta de campaña.
2. **Regenerar**: producir otra variante visual sin modificar ni enviar la campaña aprobada anterior.
3. **Aprobar**: congelar una versión concreta de la imagen, contenido, enlaces, productos y precios.
4. **Enviar**: cargar exclusivamente la versión aprobada, volver a validar sus condiciones y pedir confirmación final antes de contactar a los destinatarios.

El uso esperado será conversacional, por ejemplo:

```text
/mailing preparar iPhone 16 con foco en cuotas, estilo premium minimalista
/mailing regenerar con menos texto y más contraste
/mailing aprobar
/mailing enviar
```

`preparar`, `regenerar` y `aprobar` no podrán invocar el envío. `enviar` no podrá generar contenido nuevo ni sustituir silenciosamente el borrador aprobado.

## Composición de la campaña

### Arte generado

La imagen será un hero promocional en formato horizontal y adaptable, optimizado para una columna de correo de aproximadamente 600 px. El archivo maestro podrá generarse a mayor resolución, pero la versión publicada deberá estar comprimida para correo.

La dirección visual usará la identidad actual de The Tech Room Arg: fondo carbón, blanco o crema, acento coral y una presentación tecnológica limpia. El prompt deberá indicar que los textos críticos no se rastericen en la imagen. Los nombres, precios y condiciones comerciales se renderizarán en HTML para evitar errores tipográficos generativos.

Cuando el brief solicite texto decorativo dentro de la imagen, deberá considerarse no contractual y repetirse correctamente en HTML cuando sea relevante.

### Contenido HTML

El template conservará estilos inline compatibles con clientes de correo y contendrá:

- nombre de The Tech Room Arg;
- asunto y preheader;
- hero generado con dimensiones y texto alternativo;
- título y mensaje principal;
- producto o productos destacados;
- precios leídos del catálogo vigente, sin recalcularlos en la skill;
- CTA HTML hacia el producto, categoría o catálogo;
- enlace de WhatsApp;
- datos de contacto;
- enlace de baja personalizado.

Si la imagen no carga, el correo seguirá comunicando la oferta y permitiendo la conversión.

## Fuente de verdad y validaciones

`productos.json` será la fuente de verdad de nombres, disponibilidad, precios y enlaces. La skill podrá sugerir productos, pero no inventar artículos ni precios.

Al preparar:

- cada producto debe existir en el catálogo actual;
- se excluyen artículos usados o CPO de las campañas automáticas, salvo pedido explícito;
- se registran los datos exactos utilizados para la vista previa;
- se rechaza un catálogo vacío o ilegible.

Al enviar:

- el borrador debe estar en estado `aprobado` y no haber sido usado;
- la imagen publicada debe existir y corresponder a la versión aprobada;
- se comparan productos y precios aprobados contra el catálogo vigente;
- cualquier cambio de precio, retiro de producto o enlace inválido invalida la aprobación y devuelve la campaña a revisión;
- se recalcula la audiencia, excluyendo emails ausentes y `no_mailing=true`;
- se muestra cantidad de destinatarios y resumen final antes de pedir confirmación.

Esta revalidación evita enviar una oferta vieja aunque el borrador se haya preparado correctamente días antes.

## Estados y persistencia

El registro de campaña tendrá un identificador y una versión. Sus estados serán:

```text
borrador -> previsualizado -> aprobado -> enviando -> enviado
    ^             |             |
    +--- regenerar+             +-- invalidado si cambió el catálogo
```

El snapshot y la nota pendiente seguirán usando el mecanismo existente de `mailing_estado`. Las versiones de campaña se almacenarán en una tabla dedicada `mailing_campanias`, porque el registro clave–valor actual sobrescribe el borrador anterior y no permite una trazabilidad confiable.

Cada fila de `mailing_campanias` representará una versión inmutable identificada por UUID, con relación opcional a la campaña anterior. Su manifiesto incluirá como mínimo:

- identificador y número de versión;
- timestamps de creación, aprobación y envío;
- brief y nota utilizados;
- productos y precios congelados;
- asunto, preheader y contenido HTML;
- ruta y URL del arte;
- hash del archivo visual;
- estado, usuario aprobador y marca de borrador usado;
- resultado agregado del envío.

Una regeneración crea una fila y versión nueva. La versión anterior se conserva para trazabilidad, pero deja de ser la candidata activa. Las transiciones de estado se harán de forma atómica y condicionadas al estado anterior para que dos procesos no puedan aprobar o enviar la misma versión simultáneamente.

## Almacenamiento y publicación de imágenes

Las piezas se guardarán en almacenamiento persistente de producción, fuera del paquete estático del deploy. La aplicación expondrá únicamente lectura pública mediante URLs no predecibles, por ejemplo:

```text
https://thetechroomarg.com/mailing/assets/<campaign-id>/<content-hash>.jpg
```

La carga será una operación administrativa autenticada. El nombre final derivará del identificador de campaña y del hash del contenido, evitando colisiones y problemas de caché. El endpoint público solo entregará tipos de imagen permitidos y nunca listará el directorio.

Esto permite crear campañas nuevas sin volver a desplegar la aplicación. Un deploy inicial sí será necesario para incorporar el endpoint, la autenticación de carga y el template híbrido.

La configuración deberá permitir que producción use un directorio de volumen persistente y que los tests usen un directorio temporal. Si el volumen no está configurado, preparar la campaña debe fallar claramente antes de aprobar, no guardar el activo dentro del filesystem efímero por accidente.

## Vista previa y aprobación

La preparación generará estos artefactos locales:

- imagen optimizada;
- HTML completo de la campaña;
- vista previa renderizada o URL local;
- JSON de manifiesto con versión, productos, precios, enlaces y hashes.

La respuesta mostrará el arte y un resumen legible. La aprobación deberá referirse al identificador y versión visibles; no bastará con aprobar implícitamente “el último” si existen varias variantes indistinguibles.

Cuando se apruebe, el contenido quedará congelado. Cualquier regeneración, edición de texto, cambio de producto o actualización de precio creará una versión nueva que deberá aprobarse otra vez.

## Envío

El envío reutilizará `web.email_util.enviar_email` y el filtro actual de destinatarios. Cada correo personalizará el enlace de baja sin modificar el contenido comercial aprobado.

Antes de enviar, la skill presentará:

- campaña y versión;
- asunto;
- productos y precios;
- cantidad actual de destinatarios;
- imagen aprobada;
- advertencias de validación;
- pregunta de confirmación explícita.

Los fallos individuales se registrarán y no detendrán al resto. La campaña se marcará `enviado` una sola vez al finalizar, guardando cantidades exitosas y fallidas. Una reejecución sobre la misma versión deberá ser rechazada para evitar duplicados.

## Seguridad y límites

- Solo una sesión administrativa podrá subir activos, aprobar o enviar.
- La ruta pública de imágenes será de solo lectura.
- Se aceptarán únicamente JPEG, PNG o WebP dentro de límites definidos de peso y dimensiones.
- El HTML no admitirá scripts ni contenido activo.
- Los enlaces se limitarán a esquemas seguros y dominios previstos.
- Las claves de Resend, Supabase y administración no se escribirán en artefactos ni logs.
- Nunca se usará la generación de imágenes para modificar precios, destinatarios o reglas comerciales.
- Ninguna orden ambigua como “hacelo”, “publicalo” o “aprobado” ejecutará un envío; el envío requerirá la intención explícita `enviar` y su confirmación posterior.

## Compatibilidad y degradación

- El layout será de una columna y compatible con móvil.
- La imagen tendrá ancho fluido, dimensiones declaradas y `alt` descriptivo.
- Se conservarán tablas y estilos inline para clientes antiguos.
- El mail seguirá siendo comprensible con imágenes desactivadas.
- Los botones tendrán área táctil suficiente y texto centrado.
- El peso total del HTML se mantendrá por debajo del umbral de recorte habitual de Gmail; la imagen se servirá externamente y no se incrustará como base64.

## Pruebas y criterios de aceptación

### Skill

- Sin la skill, registrar escenarios base que demuestren los riesgos esperados: envío ambiguo, precio inventado o aprobación perdida tras regenerar.
- Con la skill, verificar que cada escenario produzca el flujo y artefactos correctos.
- Validar estructura y frontmatter con las herramientas de `skill-creator`.

### Aplicación

- TDD para transiciones de estado válidas e inválidas.
- Preparar no llama al proveedor de email.
- Aprobar no llama al proveedor de email.
- Enviar rechaza borradores no aprobados, usados o desactualizados.
- Una variación de precio invalida la aprobación.
- La carga administrativa rechaza sesión ausente, tipo inválido, archivo excesivo y traversal de rutas.
- El endpoint público entrega el activo correcto, no lista archivos y devuelve `404` para rutas desconocidas.
- El template incluye HTML útil, CTA, baja y `alt` aunque la imagen no esté disponible.
- La selección de destinatarios excluye `no_mailing=true`.
- El envío parcial registra éxitos y fallos sin duplicar destinatarios.

### Verificación visual

- Renderizar y revisar la vista previa en escritorio y móvil.
- Verificar el mail con imágenes activadas y desactivadas.
- Confirmar que el CTA sea visible, centrado y clickeable.
- Enviar primero a una dirección de prueba y revisar al menos Gmail web y móvil antes de habilitar una campaña real.

## Fuera de alcance inicial

- A/B testing y optimización automática de asuntos.
- Métricas de apertura basadas en píxeles de tracking.
- Editor visual completo dentro del admin.
- Segmentación avanzada por comportamiento.
- Generación automática de campañas sin una orden humana.
- Envío por canales distintos de email.

## Despliegue

La primera entrega requiere un deploy para agregar almacenamiento público, endpoints administrativos, estados versionados y el template híbrido. Después de ese despliegue, generar, aprobar y publicar nuevas imágenes de campaña no requerirá deploy.

La habilitación será gradual:

1. pruebas automatizadas y almacenamiento temporal;
2. prueba de carga y lectura en producción sin enviar correo;
3. campaña de prueba a una única dirección;
4. revisión en clientes de correo;
5. habilitación del envío a la audiencia elegible.
