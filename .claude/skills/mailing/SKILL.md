---
name: mailing
description: Use when Vladimir asks to prepare, regenerate, approve, or send a visual email campaign for The Tech Room Arg from current catalog products, especially when an image preview or a separate send confirmation is needed.
---

# Campañas visuales de mailing

Prepara un correo híbrido para The Tech Room Arg: hero visual generado, contenido comercial en HTML real y CTA funcional. La preparación, aprobación y envío son tres acciones distintas.

Lee [references/brand.md](references/brand.md) antes de construir el prompt de imagen. Usa el generador de imágenes integrado de Codex por defecto; si no está disponible, explica que hay un modo CLI que requiere configuración y espera a que Vladimir lo solicite.

## Preparar una campaña

1. Consulta productos y precios actuales desde la API pública:

   ```bash
   ./.venv/bin/python .claude/skills/mailing/scripts/catalogo.py --buscar "iphone" --buscar "16"
   ```

   Usa los nombres exactos devueltos por el catálogo. No inventes productos, precios, stock, cuotas, garantías o descuentos. Incluye en la campaña solo productos cuya selección tenga sentido para el pedido de Vladimir. Una nota promocional se copia exactamente de lo que él dio.

2. Propón el asunto y el preheader usando solo hechos confirmados. Genera un hero horizontal de marketing con el generador de imágenes. Sigue `references/brand.md`; no pidas que se rastericen precios, CTA, URLs ni condiciones. Para productos reconocibles, evita logos o detalles de hardware que no puedas verificar.

3. Copia el archivo final que devolvió la herramienta de imágenes al proyecto con un nombre nuevo bajo `outputs/mailing/arte/`; crea la carpeta si aún no existe y no sobrescribas artes anteriores. Pasa ese archivo a `preparar.py`, junto con los nombres exactos y el brief:

   ```bash
   ./.venv/bin/python .claude/skills/mailing/scripts/preparar.py \
     --imagen "outputs/mailing/arte/hero-iphone-16-v1.png" \
     --producto "IPHONE 16 128GB" \
     --brief "tecnología premium, minimalista, alto contraste" \
     --asunto "Novedades Apple" \
     --preheader "Equipos disponibles esta semana" \
     --alt "Teléfono sobre un fondo oscuro con luz coral"
   ```

   Repite `--producto` por cada artículo. Si el usuario pide regenerar una campaña, pasa `--parent-id <version-id>` para conservar la campaña y crear una versión hija nueva. El script sube el arte, valida los nombres contra el catálogo y crea la versión `previsualizado`. Guarda los archivos bajo `outputs/mailing/<campaign_id>/<version_id>/`.

4. Abre `preview.html` con la skill `browser:control-in-app-browser` y revisa escritorio y móvil. Confirma que el hero cargue, que los precios/CTA HTML sean correctos, que el texto siga teniendo sentido con las imágenes desactivadas y que la baja esté presente. Presenta en el chat la imagen, el HTML de vista previa, los productos y precios, el asunto y el ID de versión. No apruebes por el usuario.

## Aprobar una versión

Aprueba solo cuando Vladimir se refiera de forma inequívoca al ID de versión mostrado. Una aprobación guarda el estado `aprobado`, pero todavía no envía el correo.

```bash
./.venv/bin/python .claude/skills/mailing/scripts/aprobar.py <version-id>
```

Confirma que quedó aprobada y recuérdale que aún no se envió. Si la campaña se regenera o se edita, la versión nueva requiere su propia aprobación.

## Enviar la versión aprobada

Antes de pedir confirmación final, vuelve a consultar el estado, los precios y la audiencia actuales:

```bash
./.venv/bin/python .claude/skills/mailing/scripts/resumen.py <version-id>
./.venv/bin/python .claude/skills/mailing/scripts/catalogo.py --buscar "iphone" --buscar "16"
```

Continúa solo si la versión está `aprobado`, `catalogo_vigente` y `asset_disponible` son `true`, y `envio_disponible` es `true`. Muestra el asunto, la versión, los productos/precios congelados y la cantidad actual de destinatarios. La API excluye las direcciones vacías y `no_mailing=true`.

Si un precio cambió o el arte ya no existe, no intentes aprobar la versión vieja. Crea una versión nueva con `--parent-id`, muestra la vista previa y vuelve a pedir aprobación.

Después del resumen, solicita una confirmación aparte que mencione ese ID. Solo al recibirla ejecuta el script con el texto exacto:

```bash
./.venv/bin/python .claude/skills/mailing/scripts/enviar.py \
  <version-id> --confirmacion "ENVIAR <version-id>"
```

El script y la API vuelven a comprobar el catálogo y el arte antes del primer correo. Nunca repitas el envío si la versión está `enviando` o `enviado`; ante una interrupción, informa el estado y los resultados guardados. Al completar, comunica enviados y fallidos.

## Límites operativos

- “Me gusta”, “hacelo”, “publicalo” o una aprobación de otra versión no autorizan el envío.
- No ejecutes el paso de envío desde una rutina programada.
- No inventes precios ni claims. El arte aporta la identidad visual; el HTML contiene nombres, precios, condiciones, CTA y baja.
- No escribas `ADMIN_TOKEN`, `RESEND_API_KEY` ni credenciales en prompts, archivos de preview o logs.
- Si un comando falla o devuelve un estado distinto del esperado, detente y presenta el error sin reintentar un posible envío parcial.
