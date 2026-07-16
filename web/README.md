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

## Levantar el chat

```bash
./.venv/bin/uvicorn web.app:app --reload --port 8000
```
Abrir en el navegador: http://localhost:8000
(El micrófono funciona en Chrome/Edge.)
