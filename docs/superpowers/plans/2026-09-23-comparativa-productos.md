# Comparativa de productos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** comparar dos productos vigentes de la misma sección con fichas web citadas y guardadas por modelo.

**Architecture:** componente de búsqueda compartido por ambas implementaciones de cards; servicio backend independiente para validar productos, obtener fichas y persistirlas en SQLite. La página /comparativa consume datos comerciales del catálogo autorizado y fichas técnicas públicas, manteniendo el shell de navegación.

**Tech Stack:** FastAPI, Pydantic, SQLite, SDK Anthropic existente, JavaScript/CSS nativos, pytest y Playwright.

**Spec:** `docs/superpowers/specs/2026-09-23-comparativa-productos-design.md` (aprobada).

## Global Constraints
- Misma categoría significa `web.catalogo.seccion_de`, no marca ni condición.
- Búsqueda de candidatos únicamente en catálogo actual; nunca búsqueda web para sugerencias.
- Guardar fichas por modelo/configuración durante 30 días, con versión de esquema.
- No enviar a IA datos personales, costos, proveedores, pedidos ni cookies.
- Dos columnas en desktop/mobile; controles de 44 px, temas claro/oscuro y textos en castellano.
- No reiniciar header, dock ni gato al navegar.
- Fuentes reales vinculadas a atributos; datos no verificables: «No confirmado».
- No incluir cambios anteriores ajenos al feature en commits ni publicar sin autorización puntual.

## Review Focus
1. Un nombre parecido puede ser otra generación/configuración: no reutilizar fichas entre Pro/Max/capacidades distintas.
2. Usuarios pueden manipular identificadores/categorías en URL: validar contra catálogo en servidor.
3. Solicitudes simultáneas pueden duplicar costo: bloqueo persistente con propietario y vencimiento, liberación solo por propietario.
4. Una respuesta IA válida como JSON puede contener fuentes inventadas o HTML: rechazar referencias no obtenidas y renderizar texto.
5. Un enlace abierto dentro del iframe puede recrear el header: verificar identidad del nodo antes/después de comparar y volver.

## Task 1 — Contrato de productos y fichas
**Files:** crear `web/comparativa.py`, `tests/test_comparativa.py`; modificar rutas puntuales en `web/app.py`.
**Interfaces:** `product_id(nombre) -> str` (SHA256 del nombre exacto), `resolve_pair(productos, a, b) -> tuple[dict, dict]`, `spec_key(producto) -> str`, `validate_sheet(payload, searched_urls) -> dict`.
- [ ] Escribir primero pruebas de resolución y rechazo. Ejemplo:
```python
with pytest.raises(ValueError):
    resolve_pair([phone, tablet], product_id(phone['nombre']), product_id(tablet['nombre']))
assert resolve_pair([phone, other_phone], product_id(phone['nombre']), product_id(other_phone['nombre'])) == (phone, other_phone)
```
- [ ] Ejecutar `.venv/bin/python -m pytest tests/test_comparativa.py -q`; comprobar fallo por módulo inexistente.
- [ ] Implementar resolución por identificadores derivados del nombre, comparación de `seccion_de`, rechazo de mismo ID, inexistentes y colisiones. Clave de ficha conserva configuración y generación; limpieza de condición solo para términos inequívocos, sin borrar números de modelo.
- [ ] Definir esquema de ficha: `model`, `attributes[{key,label,value,source_urls}]`, `sources[{url,title}]`, `fetched_at`. Limitar 16 atributos, longitud de valores y fuentes; validar URLs HTTP(S) sin credenciales y referencias contenidas en resultados web reales. Campos no confirmados sin afirmaciones.
- [ ] Agregar `GET /comparativa` para HTML y `GET /api/comparativa?a=&b=` para resolver la pareja usando `_catalogo_autorizado(request)`. No serializar filas internas completas: lista explícita de campos públicos.
- [ ] Probar que una pareja entre marcas dentro de Celulares pasa, una pareja teléfono/tablet falla, costos/proveedor nunca aparecen y el mismo modelo no puede ocupar ambos lados.

## Task 2 — Investigación con IA y persistencia
**Files:** crear `web/comparativa_specs.py`, `tests/test_comparativa_specs.py`.
**Interfaces:** `SpecStore(path).get(key)`, `.claim(key, owner, now)`, `.save(key, owner, sheet)`, `.fail(key, owner)`, `research(producto, client) -> dict`; ruta `POST /api/comparativa/ficha` recibe los dos IDs y el ID del lado solicitado.
- [ ] Escribir pruebas con cliente Anthropic ficticio para éxito con citas, fuente inventada, modelo distinto, dato ausente, timeout y clave ausente. Probar dos instancias de SpecStore contra el mismo archivo.
- [ ] Crear tablas `sheets` y `leases` con transacciones cortas: adquirir lease antes de red; nunca mantener transacción durante llamada IA. TTL 30 días, lease 120 segundos y cooldown de errores 60 segundos. Base fuera de static en el directorio de datos.
- [ ] Leer documentación oficial antes de integrar el protocolo de búsqueda/citas. Usar SDK existente con cliente de timeout acotado y sin reintentos ilimitados; máximo dos búsquedas por ficha y salida acotada. Recolectar URLs de resultados de búsqueda, exigir que cada dato confirmado esté respaldado por ellas. Continuaciones `pause_turn` acotadas; respuesta incompleta produce error recuperable.
- [ ] Prompt en castellano: modelo exacto, fuentes oficiales prioritarias, esquema por sección, prohibición de inventar y distinción entre batería nominal y salud de una unidad usada. Enviar exclusivamente identidad pública; verificar el payload en tests.
- [ ] Cache hit devuelve ficha sin llamar IA. Cache miss requiere presupuesto persistente por solicitante y global, usando el mecanismo de límites existente con claves independientes. Máximo dos generaciones concurrentes mediante leases persistentes globales.
- [ ] Respuestas controladas: ready, pending, unavailable, retry_after. No exponer excepciones del proveedor. La UI recibe la pareja comercial aunque falle una ficha.
- [ ] Pruebas: expiración, recuperación de lease vencido, propietario obsoleto incapaz de sobreescribir, cuota, duplicados concurrentes y no caché de contenido inválido.

## Task 3 — Icono y buscador embebido
**Files:** crear `web/static/comparar-productos.js`, `web/static/comparar-productos.css`; modificar `catalogo.js`, `landing.js`, `catalogo.html`, `index.html`.
**Interfaces:** `window.TTRAComparar.buttonHtml()`, `window.TTRAComparar.bind(container, productos)`; resolver producto desde índice/dataset local y calcular SHA256 con Web Crypto para el ID.
- [ ] Prueba de DOM: cada card tiene un botón «Comparar producto» después de compartir; tocarlo no agrega al carrito ni cambia el color.
- [ ] Implementar SVG propio de dos flechas y círculos con currentColor, círculo y foco acordes a `.btn-foto`, 44 px táctiles.
- [ ] Buscador con label, combobox/listbox, aria-expanded/activedescendant, resultados limitados y navegación Flechas/Enter/Escape. Usar textContent para nombres. Un único buscador abierto; botón cerrar y clic fuera lo cierran.
- [ ] Filtrar candidatos con la sección del catálogo ya cargado y normalización de tildes/mayúsculas. Excluir el origen. Solo IDs en URL; navegación por anchor interno compatible con el shell.
- [ ] Probar teclado, nombres con comillas/HTML, ninguna coincidencia, misma marca y distinta marca, exclusión del mismo producto y categorías distintas.

## Task 4 — Página /comparativa e integración
**Files:** crear `web/static/comparativa.html`, `comparativa.css`, `comparativa.js`; modificar `cat-navigation.js`.
- [ ] Crear prueba de navegador con respuestas API ficticias: dos columnas visibles, orden izquierda/derecha y estados independientes de carga/error.
- [ ] Cargar estilos de tema/header comunes y scripts existentes de navegación. Añadir /comparativa a la lista de rutas admitidas del shell.
- [ ] Mostrar productos a partir de API autorizada y fichas guardadas, precios del catálogo y atributos en orden común. Solicitar ficha faltante mediante POST; sondeo de pending con límite y cancelación al salir.
- [ ] Renderizar bullets de atributos por filas alineadas en ambos lados; encabezados legibles y sin scroll horizontal a 320 px. Mostrar «No confirmado» para datos ausentes. No reducir tipografía hasta hacerla ilegible.
- [ ] Mostrar fuentes clicables seguras, fecha de consulta y aviso aprobado. Errores accesibles con reintentar y regreso al catálogo; URL inválida no dispara IA.
- [ ] Browser tests en 320/390/1440 y ambos temas, comparación desde catálogo y desde cards anteriores, recarga, Atrás, cambio de tema, preservación del header y cierre de buscador.

## Task 5 — Verificación y entrega local
- [ ] Ejecutar `.venv/bin/python -m pytest tests/ -q` y `node --test tests/test_catalogo_precios.js` junto a nuevas pruebas JS.
- [ ] Ejecutar Playwright para carrito, acciones de producto, filtro Nuevo/Usado/CPO y comparativa. No escribir pedidos ni datos reales.
- [ ] Prueba real acotada de una pareja del catálogo si la credencial del proveedor está disponible: comprobar fuentes, reutilización sin nueva llamada y ausencia de datos sensibles en payload. Documentar límites si falta configuración.
- [ ] Revisar diff, seguridad de URLs/texto, contratos de datos y consumo. Conservar todos los cambios locales previos; commits solo con archivos/hunks de esta funcionalidad.
- [ ] Entregar URL local de /comparativa accesible desde las cards y resultados de pruebas. No desplegar a producción en este paso.

## Método propuesto
Ejecución nativa en esta sesión: los contratos de catálogo, búsqueda y ficha están estrechamente vinculados. Revisar este plan y confirmar el método antes de implementar, conforme al skill writing-plans.
