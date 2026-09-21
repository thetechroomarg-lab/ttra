# TTRA Project — mapa para Claude

Negocio: THE TECH ROOM ARG. Vladimir trabaja solo. Dos mitades:
1. **Pipeline de precios** (raíz del repo): toma listas de proveedores y arma los listados.
2. **Web** (`web/`): FastAPI con catálogo, cuentas de cliente, pedidos y paneles de admin/cadete.

Rama de producción: `web-ttra`. **Nunca hacer push sin que Vladimir lo pida para ese cambio puntual.**

## Reglas de trabajo

- Antes de leer un archivo grande, buscá con `grep -n`. Ver "Dónde está cada cosa".
- Todo cambio en `web/` se verifica con `.venv/bin/python -m pytest tests/ -q` (399 tests, ~6s).
- Para levantar la app o sacar screenshots, usar la skill `run-ttra-web`.
- Para precios y presupuestos, usar la skill `Precios`. Para cargar clientes/pedidos, `pedido`.

## Dónde está cada cosa

### Web — backend (`web/`)

| Archivo | Qué tiene |
|---|---|
| `app.py` | La app FastAPI y **todas las rutas JSON/API**: auth, perfil, domicilios, pedidos, entregas, tareas, descuentos, códigos promo, catálogo, cotización, noticias, acciones de admin (mailing, recibos, borrado). Middlewares y el `StaticFiles` mount al final. |
| `paginas_admin.py` | Las **páginas HTML** del panel de admin: `/admin/clientes`, `/admin/clientes/lista`, `/admin/clientes/{id}/historial`. Son f-strings gigantes. |
| `paginas_cadete.py` | La página HTML del panel de entregas del cadete: `/admin/cadete`. |
| `ui_helpers.py` | Lo compartido por los paneles: guards de sesión, formateo (`_formatear_entero_ar`, `_formatear_fecha_ar`), `_json_para_script`, íconos SVG, constantes de estilo/PWA, `CADETE_SLUG`. |
| `ui/*.css.html` | El CSS de los paneles, en archivos aparte para que no infle el código. Se inyecta inline, igual que antes. **No** se sirve público (no está en `static/`). |
| `productos.py` | Carga del catálogo, resolución de proveedor, hash del manifest. |
| `catalogo.py` `buscador.py` `chat.py` | Secciones del catálogo, búsqueda sin IA, respuesta del chat. |
| `cuentas.py` `domicilios.py` | Alta/login de clientes, contraseñas, domicilios. |
| `pedidos.py` `entregas.py` `recibos.py` | Modelo de pedido, agenda de entregas (hora Argentina), PDF de recibo. |
| `mayoristas.py` | Precios mayoristas. |
| `interacciones.py` | Tracking de qué mira cada cliente (alimenta el ranking del historial). |
| `reglas.py` `slugs.py` `email_util.py` `supabase_client.py` | WhatsApp y reglas de negocio, slugs de `/p/<slug>`, envío de mails, cliente Supabase. |
| `generar_datos.py` | Genera `productos.json` desde `entrada.json` + cotización. |

Datos que lee la app: `web/productos.json`, `web/costos.json`, `web/proveedores.json`, `web/catalogo-manifest.json`.

### Web — frontend (`web/static/`)

| Archivo | Qué tiene |
|---|---|
| `index.html` + `landing.js` + `landing.css` | La landing. `landing.js` son ~5400 líneas en scope global: modo visual Fallout/Classic, carrito, geolocalización, menú de perfil, carrousel, noticias. **Buscá con grep, no lo leas entero.** |
| `boot.js` | Corre antes que `landing.js`: evita el flash de pantalla al cargar. |
| `classic.css` `theme.css` | Modo Classic y tokens de tema. |
| `login.*` `perfil.*` `catalogo.*` | Pantallas propias, cada una con su js/css/html. |
| `sw.js` | Service worker de las PWA de admin y cadete. |

### Pipeline de precios (raíz)

`generar_lista.py` orquesta; `normalize.py` parsea listas de proveedores; `consolidate.py` unifica; `bands.py` aplica el margen por bandas; `xlsx_writer.py` escribe el Excel; `imagelink.py` resuelve imágenes. Entradas: `entrada_*.json` (una por proveedor: az, ba, em, fr, oh, va, master).

## Tests

`tests/` — 399 tests, corren en segundos sin red (Supabase va mockeado en `tests/fakes_supabase.py`).
Los `test_app_*.py` parchean `web.app.get_client`, así que **cualquier módulo nuevo que use Supabase
debe resolverlo a través de `web.app`**, no importando `get_client` directo (ver `paginas_admin.py`).
Los `test_app_landing.py` afirman sobre el **texto** de `landing.js`, no lo ejecutan.

## Cosas que muerden

- `app.mount("/", StaticFiles(...))` va **último** en `app.py`: cualquier ruta nueva tiene que quedar antes.
- Las fechas se guardan en UTC y se muestran en hora Argentina (UTC-3 fijo, sin horario de verano).
- Usar `_json_para_script()` y no `json.dumps()` para meter datos de cliente dentro de un `<script>`.
- `ADMIN_CLIENTES_PASSWORD` y `CADETE_PASSWORD` no tienen default: sin ellas el server no arranca, a propósito.
- Al cambiar el dólar hay que tocar `web/productos.json`, los outputs en pesos, **y** `COTIZACION_DOLAR` en `web/app.py`.
