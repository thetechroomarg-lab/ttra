---
name: imagen
description: Genera o edita imágenes con OpenAI (gpt-image) desde el chat — placas para redes, banners de mailing, fotos de producto, fondos, cards del catálogo. Usar cuando Vladimir pide "generá una imagen", "haceme una placa", "armá un banner", "editá esta foto", "/imagen" o algo que requiera crear una imagen.
---

# Imágenes con OpenAI

Script: `.claude/skills/imagen/scripts/openai_imagen.py` (solo stdlib, usar `python3`).

```bash
python3 ".claude/skills/imagen/scripts/openai_imagen.py" "<prompt>" [--ref foto.jpg] [--aspect 1:1] [--calidad high] [--nombre placa-iphone] [--out carpeta]
```

- Key: `OPENAI_API_KEY` en el `.env` de la raíz del repo (ignorado por git) o en el entorno. Nunca leer ese archivo, escribir la key en otro lado ni repetirla en el chat. Si falta, decirle a Vladimir que la cargue ahí.
- Modelo: `gpt-image-1.5` por defecto (`gpt-image-1` ya no existe en la API); se cambia con `OPENAI_IMAGE_MODEL` o `--modelo`.
- Cada imagen cuesta plata (high ≈ US$0,17, medium ≈ US$0,04, low ≈ US$0,01). Para pruebas usar `--calidad low`.
- Salida por defecto: `/Users/toraba/Precios Claude/Imagenes/`. El script imprime la ruta de cada imagen.
- `--transparente` pide PNG con fondo transparente, recortado en su contorno (sin cuadrado blanco): usarlo para las cards del catálogo.
- `--ref` (repetible) manda imágenes de referencia para editar o mantener un producto real (p. ej. una foto de `web/static/catalog-images/`).
- Tamaños: solo cuadrado (1024×1024), apaisado (1536×1024) o vertical (1024×1536). `--aspect` elige el más cercano: `1:1` post, `4:5`/`9:16` feed e historia, `16:9` banner/mailing. Si hace falta un recorte exacto, recortar después.

## Cómo armar el prompt

- Escribir el prompt en inglés, descriptivo (escena, luz, estilo, encuadre). Texto que deba aparecer en la imagen, entre comillas y en español.
- Marca: THE TECH ROOM ARG. No inventar precios, descuentos ni promos que Vladimir no dio textual.
- Nunca mencionar proveedores ni equipos usados salvo pedido explícito.

## Después de generar

Mirar la imagen con Read antes de pasarla, y mandarla con SendUserFile. Si salió mal, ajustar el prompt y reintentar (máx. 2 intentos sin consultar).
