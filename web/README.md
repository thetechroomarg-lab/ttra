# Web de consulta (chat) — THE TECH ROOM ARG

Chat local que responde consultas de clientes usando el listado de precios.

## Configuración (una vez)

1. Instalar dependencias:
   ```bash
   ./.venv/bin/pip install -r requirements.txt
   ```
2. Copiar `web/.env.example` a `web/.env` y pegar la API key:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```

## Cada vez que actualizás precios

Generar el `productos.json` desde el `entrada.json` del pipeline + la cotización del día:
```bash
./.venv/bin/python web/generar_datos.py entrada.json 1540 web/productos.json
```

## Cotización desde el panel

En **Pedidos y recibos** o **Clientes**, entrar a **Cotización del dólar**.
El formulario `/admin/cotizacion` requiere la sesión de administrador, ofrece
teclado numérico móvil y acepta pesos enteros positivos, sin separadores.
Al guardar, las siguientes consultas del catálogo y del carrito usan el nuevo
valor para pesos y transferencia. Las páginas ya abiertas deben recargarse.
También se usa en los nuevos correos de pedido y en el cálculo de cobros.

La cotización manual se guarda atómicamente en `cotizacion-admin.json`, junto a
`PRODUCTOS_PATH`; puede configurarse otra ubicación con `COTIZACION_PATH`.
En Railway esa ubicación **debe estar dentro del volumen persistente** y staging
debe usar un volumen separado del de producción. No compartir este archivo entre
ambientes ni usar discos independientes para réplicas del mismo servicio.
La cotización manual tiene prioridad sobre posteriores publicaciones del
catálogo; los archivos originales y sus hashes no se modifican. Si todavía no
se guardó una cotización manual, se mantiene el comportamiento anterior.

Verificación local:
```bash
./.venv/bin/python -m pytest tests -q
./.venv/bin/python tests/browser/admin_cotizacion.py
```

## Levantar el chat

```bash
./.venv/bin/uvicorn web.app:app --reload --port 8000
```
Abrir en el navegador: http://localhost:8000
(El micrófono funciona en Chrome/Edge.)
