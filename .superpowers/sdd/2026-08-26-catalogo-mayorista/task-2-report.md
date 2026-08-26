# Task 2 — Motor puro de precios mayoristas

## Resultado

Implementado `web/mayoristas.py` con las constantes y las interfaces del brief:

- `descuento_por_margen(precio_publico, costo)` calcula la banda de descuento,
  rechaza márgenes menores a USD 35 y limita la ganancia neta segura.
- `catalogo_mayorista(productos, costos)` filtra productos sin costo o no
  elegibles, copia cada diccionario sin mutarlo y recalcula proporcionalmente
  `usd`, `pesos` y `transferencia` sin agregar costos ni márgenes.

## Evidencia RED

Comando:

```powershell
$env:PYTHONUTF8='1'; & 'D:\Git\TTRA\.venv\Scripts\python.exe' -m pytest tests/test_mayoristas.py -q
```

Resultado: fallo esperado durante la colección con
`ModuleNotFoundError: No module named 'web.mayoristas'`.

## Evidencia GREEN

Comando:

```powershell
$env:PYTHONUTF8='1'; & 'D:\Git\TTRA\.venv\Scripts\python.exe' -m pytest tests/test_mayoristas.py -q
```

Resultado: `13 passed in 0.06s`.

Suite completa (usando secretos efímeros de prueba requeridos por la app):

```powershell
$env:PYTHONUTF8='1'; $env:ADMIN_CLIENTES_PASSWORD='local-dev-only'; $env:SESSION_SECRET='local-session-secret'; & 'D:\Git\TTRA\.venv\Scripts\python.exe' -m pytest -q
```

Resultado: `287 passed, 2 warnings in 26.41s`.

Las advertencias son preexistentes: `reportlab` usa `ast.NameConstant`
deprecado y `web/app.py` usa `datetime.utcnow()` deprecado.

## Fix round 1

Se atendieron los hallazgos de revisión:

- La salida elimina explícitamente `costo`, `margen`, `proveedor` y
  `capacidad`, conservando los demás campos públicos.
- Los costos deben ser numéricos reales, finitos y estrictamente positivos;
  valores nulos, texto, no finitos y no positivos excluyen el producto sin
  excepción.

### RED

Comando:

```powershell
$env:PYTHONUTF8='1'; & 'D:\Git\TTRA\.venv\Scripts\python.exe' -m pytest tests/test_mayoristas.py -q
```

Resultado: `5 failed, 15 passed in 0.56s`; falló el nuevo caso de campos
privados y los casos de costos inválidos (incluyendo la excepción para texto y
NaN), confirmando que las pruebas cubrían el defecto.

### GREEN

Comando:

```powershell
$env:PYTHONUTF8='1'; & 'D:\Git\TTRA\.venv\Scripts\python.exe' -m pytest tests/test_mayoristas.py -q
```

Resultado: `20 passed in 0.06s`.

Suite completa:

```powershell
$env:PYTHONUTF8='1'; $env:ADMIN_CLIENTES_PASSWORD='local-dev-only'; $env:SESSION_SECRET='local-session-secret'; & 'D:\Git\TTRA\.venv\Scripts\python.exe' -m pytest -q
```

Resultado: `294 passed, 2 warnings` (las mismas advertencias preexistentes).
