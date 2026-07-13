# Generador de lista de precios (`/lista`) — Plan de Implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir el comando `/lista`: una skill de Claude Code que toma precios de proveedores (archivos adjuntos y/o texto pegado) y genera un Excel (.xlsx) con la lista consolidada de 4 columnas y una hoja de reporte.

**Architecture:** Dos capas. (1) Un **script Python testeable** que hace todo lo determinístico: tabla de bandas, redondeo, link de Google Imágenes, normalización de nombres, deduplicado por costo más barato, detección de posibles duplicados y escritura del .xlsx. (2) Un **SKILL.md** con las reglas de criterio (limpieza de texto, filtros, unificación, regla "slim", agrupado de baterías) que produce un JSON estructurado y llama al script. El script recibe el JSON y emite el .xlsx.

**Tech Stack:** Python 3, openpyxl (escritura .xlsx), pytest (tests). Skill de Claude Code (SKILL.md).

## Global Constraints

- Todo en USD. Si un ítem trae dos precios (USD y pesos), se usa solo el primero (USD).
- Margen: monto fijo por banda de costo (tabla en Task 2), sumado al costo.
- Redondeo: precio de venta **hacia arriba al múltiplo de $5** (resultado entero).
- Emparejamiento **conservador**: fusionar solo si el nombre normalizado coincide exactamente; los parecidos-no-idénticos van al reporte, nunca se fusionan.
- Nada se descarta en silencio: filtrados, posibles duplicados y dudas de precio van a la hoja "Reporte".
- Código y comentarios en español, consistente con el dominio.

---

## Estructura de archivos

```
TTRA Project/
├── requirements.txt          # openpyxl, pytest
├── .gitignore
├── conftest.py               # agrega la raíz al sys.path para los tests
├── bands.py                  # monto por banda + cálculo de precio
├── imagelink.py              # link de Google Imágenes
├── normalize.py              # normalización de nombres
├── consolidate.py            # dedup por más barato + posibles duplicados
├── xlsx_writer.py            # escritura del .xlsx (hojas Lista y Reporte)
├── generar_lista.py          # entrypoint CLI: JSON -> .xlsx
├── tests/
│   ├── test_bands.py
│   ├── test_imagelink.py
│   ├── test_normalize.py
│   ├── test_consolidate.py
│   ├── test_xlsx_writer.py
│   └── test_generar_lista.py
└── .claude/skills/lista/SKILL.md   # el comando /lista
```

**Contrato de datos del entrypoint (`generar_lista.py`):** recibe un JSON con esta forma:

```json
{
  "items": [ {"nombre": "iPhone 13 128GB", "costo": 615, "proveedor": "ProvA"} ],
  "filtrados": [ {"nombre": "iPhone 12 (caja abollada)", "motivo": "caja abollada"} ],
  "dudas_precio": [ {"texto": "Samsung A15 consultar", "motivo": "sin costo numérico"} ]
}
```

Produce un `.xlsx` con:
- **Hoja "Lista":** columnas `Nombre | Link Google Imágenes | País | Precio`.
- **Hoja "Reporte":** secciones Filtrados, Posibles duplicados, Dudas de precio.

---

## Task 1: Setup del proyecto Python

**Files:**
- Create: `requirements.txt`, `.gitignore`, `conftest.py`

**Interfaces:**
- Produces: entorno con `pytest` y `openpyxl` disponibles; la raíz del repo importable desde `tests/`.

- [ ] **Step 1: Crear `requirements.txt`**

```
openpyxl==3.1.5
pytest==8.3.2
```

- [ ] **Step 2: Crear `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.DS_Store
*.xlsx
```

- [ ] **Step 3: Crear `conftest.py` (para que los tests importen los módulos de la raíz)**

```python
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
```

- [ ] **Step 4: Crear entorno virtual e instalar dependencias**

Run:
```bash
cd "/Users/toraba/TTRA Project" && python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt
```
Expected: instala openpyxl y pytest sin errores.

- [ ] **Step 5: Verificar que pytest corre (sin tests todavía)**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest -q`
Expected: `no tests ran` (exit 5) — confirma que pytest funciona.

- [ ] **Step 6: Commit** (mensaje simple, en voz del usuario, SIN atribución a IA/herramientas, sin "Co-Authored-By")

```bash
git add requirements.txt .gitignore conftest.py
git commit -m "chore: setup del proyecto Python para el generador de lista"
```

---

## Task 2: Tabla de bandas y cálculo de precio (`bands.py`)

**Files:**
- Create: `bands.py`
- Test: `tests/test_bands.py`

**Interfaces:**
- Produces:
  - `monto_por_banda(costo: float) -> int` — monto fijo a sumar según la banda.
  - `calcular_precio(costo: float) -> int` — `costo + monto`, redondeado hacia arriba a múltiplo de 5.

- [ ] **Step 1: Escribir el test que falla** — `tests/test_bands.py`

```python
from bands import monto_por_banda, calcular_precio


def test_monto_por_banda_limites():
    assert monto_por_banda(0) == 30
    assert monto_por_banda(300) == 30       # límite superior inclusive
    assert monto_por_banda(300.01) == 40
    assert monto_por_banda(600) == 40
    assert monto_por_banda(900) == 50
    assert monto_por_banda(1300) == 70
    assert monto_por_banda(1600) == 85
    assert monto_por_banda(2000) == 130
    assert monto_por_banda(2400) == 160
    assert monto_por_banda(2400.01) == 200
    assert monto_por_banda(99999) == 200


def test_calcular_precio_suma_y_redondea_arriba_a_5():
    assert calcular_precio(100) == 130       # 100 + 30 = 130
    assert calcular_precio(611) == 665       # 611 + 50 = 661 -> 665
    assert calcular_precio(615) == 665       # 615 + 50 = 665 -> 665
    assert calcular_precio(300) == 330       # 300 + 30 = 330
    assert calcular_precio(2500) == 2700     # 2500 + 200 = 2700
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_bands.py -q`
Expected: FALLA (`ModuleNotFoundError: No module named 'bands'`).

- [ ] **Step 3: Implementación** — `bands.py`

```python
import math

# (limite_superior_inclusive, monto). La última banda es abierta (float('inf')).
_BANDAS = [
    (300, 30),
    (600, 40),
    (900, 50),
    (1300, 70),
    (1600, 85),
    (2000, 130),
    (2400, 160),
    (float("inf"), 200),
]


def monto_por_banda(costo):
    for limite, monto in _BANDAS:
        if costo <= limite:
            return monto
    return _BANDAS[-1][1]


def calcular_precio(costo):
    total = costo + monto_por_banda(costo)
    return int(math.ceil(total / 5) * 5)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_bands.py -q`
Expected: 2 tests PASAN.

- [ ] **Step 5: Commit**

```bash
git add bands.py tests/test_bands.py
git commit -m "feat: tabla de bandas y cálculo de precio con redondeo a 5"
```

---

## Task 3: Link de Google Imágenes (`imagelink.py`)

**Files:**
- Create: `imagelink.py`
- Test: `tests/test_imagelink.py`

**Interfaces:**
- Produces: `google_image_link(nombre: str) -> str`.

- [ ] **Step 1: Test que falla** — `tests/test_imagelink.py`

```python
from imagelink import google_image_link


def test_arma_link_reemplazando_espacios_por_mas():
    assert google_image_link("iPhone 13 128GB") == (
        "https://www.google.com/search?tbm=isch&q=iPhone+13+128GB"
    )


def test_colapsa_espacios_multiples_y_recorta():
    assert google_image_link("  Motorola  G54  ") == (
        "https://www.google.com/search?tbm=isch&q=Motorola+G54"
    )
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_imagelink.py -q`
Expected: FALLA (`ModuleNotFoundError`).

- [ ] **Step 3: Implementación** — `imagelink.py`

```python
_BASE = "https://www.google.com/search?tbm=isch&q="


def google_image_link(nombre):
    tokens = nombre.split()
    return _BASE + "+".join(tokens)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_imagelink.py -q`
Expected: 2 tests PASAN.

- [ ] **Step 5: Commit**

```bash
git add imagelink.py tests/test_imagelink.py
git commit -m "feat: generador de link de Google Imágenes"
```

---

## Task 4: Normalización de nombres (`normalize.py`)

**Files:**
- Create: `normalize.py`
- Test: `tests/test_normalize.py`

**Interfaces:**
- Produces: `normalizar(nombre: str) -> str` — minúsculas, sin acentos, sin puntuación, espacios colapsados.

- [ ] **Step 1: Test que falla** — `tests/test_normalize.py`

```python
from normalize import normalizar


def test_normaliza_mayusculas_acentos_y_espacios():
    assert normalizar("  iPhone  13   Pro ") == "iphone 13 pro"
    assert normalizar("Cámara") == "camara"


def test_quita_puntuacion():
    assert normalizar("iPhone-13 (128GB)") == "iphone 13 128gb"


def test_nombres_equivalentes_normalizan_igual():
    assert normalizar("MOTOROLA g54") == normalizar("motorola   G54")
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_normalize.py -q`
Expected: FALLA.

- [ ] **Step 3: Implementación** — `normalize.py`

```python
import re
import unicodedata


def normalizar(nombre):
    texto = nombre.lower()
    # quitar acentos
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    # reemplazar cualquier cosa que no sea alfanumérico por espacio
    texto = re.sub(r"[^a-z0-9]+", " ", texto)
    # colapsar espacios y recortar
    return " ".join(texto.split())
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_normalize.py -q`
Expected: 3 tests PASAN.

- [ ] **Step 5: Commit**

```bash
git add normalize.py tests/test_normalize.py
git commit -m "feat: normalización de nombres para emparejamiento"
```

---

## Task 5: Consolidación por costo más barato (`consolidate.py`)

**Files:**
- Create: `consolidate.py`
- Test: `tests/test_consolidate.py`

**Interfaces:**
- Consumes: `normalizar` de `normalize.py`.
- Produces: `consolidar(items: list[dict]) -> dict`.
  - `items`: cada uno `{"nombre": str, "costo": float, "proveedor": str}`.
  - Retorna `{"lista": [...], "duplicados_posibles": [...]}`.
    - `lista`: `{"nombre": str, "costo": float, "proveedor": str}` — una fila por nombre normalizado, con el costo más barato (y el nombre/proveedor de ese ítem más barato). Orden = primera aparición.
    - `duplicados_posibles`: `{"nombre_a": str, "nombre_b": str, "similitud": float}` — pares de nombres NO idénticos (normalizados) con similitud de tokens (Jaccard) >= 0.6.

- [ ] **Step 1: Test que falla** — `tests/test_consolidate.py`

```python
from consolidate import consolidar


def test_una_fila_por_producto_con_el_mas_barato():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 650, "proveedor": "A"},
        {"nombre": "iphone 13 128gb", "costo": 630, "proveedor": "B"},
        {"nombre": "Motorola G54", "costo": 200, "proveedor": "A"},
    ]
    r = consolidar(items)
    lista = r["lista"]
    assert len(lista) == 2
    iphone = [x for x in lista if "iPhone" in x["nombre"] or "iphone" in x["nombre"]][0]
    assert iphone["costo"] == 630
    assert iphone["proveedor"] == "B"


def test_reporta_posibles_duplicados_no_identicos():
    items = [
        {"nombre": "iPhone 13 128GB", "costo": 650, "proveedor": "A"},
        {"nombre": "iPhone 13 256GB", "costo": 720, "proveedor": "B"},
    ]
    r = consolidar(items)
    # No se fusionan (nombres distintos), pero se reportan como parecidos.
    assert len(r["lista"]) == 2
    dups = r["duplicados_posibles"]
    assert len(dups) == 1
    assert {dups[0]["nombre_a"], dups[0]["nombre_b"]} == {"iPhone 13 128GB", "iPhone 13 256GB"}


def test_productos_distintos_no_se_reportan():
    items = [
        {"nombre": "iPhone 13", "costo": 650, "proveedor": "A"},
        {"nombre": "Notebook Lenovo Slim 3", "costo": 500, "proveedor": "B"},
    ]
    r = consolidar(items)
    assert r["duplicados_posibles"] == []
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_consolidate.py -q`
Expected: FALLA.

- [ ] **Step 3: Implementación** — `consolidate.py`

```python
from normalize import normalizar

_UMBRAL_SIMILITUD = 0.6


def consolidar(items):
    grupos = {}  # clave normalizada -> lista de items (preserva orden de aparición)
    orden = []
    for it in items:
        clave = normalizar(it["nombre"])
        if clave not in grupos:
            grupos[clave] = []
            orden.append(clave)
        grupos[clave].append(it)

    lista = []
    for clave in orden:
        grupo = grupos[clave]
        barato = min(grupo, key=lambda x: x["costo"])
        lista.append({
            "nombre": barato["nombre"],
            "costo": barato["costo"],
            "proveedor": barato["proveedor"],
        })

    duplicados_posibles = []
    for i in range(len(orden)):
        for j in range(i + 1, len(orden)):
            ta = set(orden[i].split())
            tb = set(orden[j].split())
            if not ta or not tb:
                continue
            jaccard = len(ta & tb) / len(ta | tb)
            if jaccard >= _UMBRAL_SIMILITUD:
                duplicados_posibles.append({
                    "nombre_a": grupos[orden[i]][0]["nombre"],
                    "nombre_b": grupos[orden[j]][0]["nombre"],
                    "similitud": round(jaccard, 2),
                })

    return {"lista": lista, "duplicados_posibles": duplicados_posibles}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_consolidate.py -q`
Expected: 3 tests PASAN.

- [ ] **Step 5: Commit**

```bash
git add consolidate.py tests/test_consolidate.py
git commit -m "feat: consolidación por costo más barato con reporte de duplicados"
```

---

## Task 6: Escritura del .xlsx (`xlsx_writer.py`)

**Files:**
- Create: `xlsx_writer.py`
- Test: `tests/test_xlsx_writer.py`

**Interfaces:**
- Produces: `escribir_xlsx(lista: list[dict], reporte: dict, ruta: str) -> None`.
  - `lista`: cada fila `{"nombre": str, "link": str, "pais": str, "precio": int}`.
  - `reporte`: `{"filtrados": [{"nombre","motivo"}], "duplicados_posibles": [{"nombre_a","nombre_b","similitud"}], "dudas_precio": [{"texto","motivo"}]}`.
  - Escribe un archivo .xlsx con hoja "Lista" (encabezados `Nombre, Link Google Imágenes, País, Precio`) y hoja "Reporte".

- [ ] **Step 1: Test que falla** — `tests/test_xlsx_writer.py`

```python
import openpyxl
from xlsx_writer import escribir_xlsx


def test_escribe_hoja_lista_con_encabezados_y_datos(tmp_path):
    ruta = str(tmp_path / "salida.xlsx")
    lista = [
        {"nombre": "iPhone 13 128GB", "link": "http://x", "pais": "🇺🇸", "precio": 665},
    ]
    reporte = {"filtrados": [], "duplicados_posibles": [], "dudas_precio": []}
    escribir_xlsx(lista, reporte, ruta)

    wb = openpyxl.load_workbook(ruta)
    assert "Lista" in wb.sheetnames
    assert "Reporte" in wb.sheetnames
    hoja = wb["Lista"]
    assert [c.value for c in hoja[1]] == ["Nombre", "Link Google Imágenes", "País", "Precio"]
    assert [c.value for c in hoja[2]] == ["iPhone 13 128GB", "http://x", "🇺🇸", 665]


def test_reporte_incluye_secciones(tmp_path):
    ruta = str(tmp_path / "salida.xlsx")
    reporte = {
        "filtrados": [{"nombre": "iPhone (caja abollada)", "motivo": "caja abollada"}],
        "duplicados_posibles": [{"nombre_a": "iPhone 13 128GB", "nombre_b": "iPhone 13 256GB", "similitud": 0.75}],
        "dudas_precio": [{"texto": "Samsung consultar", "motivo": "sin costo"}],
    }
    escribir_xlsx([], reporte, ruta)
    wb = openpyxl.load_workbook(ruta)
    textos = [str(c.value) for fila in wb["Reporte"].iter_rows() for c in fila if c.value is not None]
    unido = " | ".join(textos)
    assert "Filtrados" in unido
    assert "caja abollada" in unido
    assert "Posibles duplicados" in unido
    assert "iPhone 13 256GB" in unido
    assert "Dudas de precio" in unido
    assert "Samsung consultar" in unido
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_xlsx_writer.py -q`
Expected: FALLA.

- [ ] **Step 3: Implementación** — `xlsx_writer.py`

```python
import openpyxl


def escribir_xlsx(lista, reporte, ruta):
    wb = openpyxl.Workbook()

    hoja = wb.active
    hoja.title = "Lista"
    hoja.append(["Nombre", "Link Google Imágenes", "País", "Precio"])
    for fila in lista:
        hoja.append([fila["nombre"], fila["link"], fila["pais"], fila["precio"]])

    rep = wb.create_sheet("Reporte")

    rep.append(["Filtrados"])
    rep.append(["Nombre", "Motivo"])
    for f in reporte.get("filtrados", []):
        rep.append([f.get("nombre", ""), f.get("motivo", "")])
    rep.append([])

    rep.append(["Posibles duplicados (revisar)"])
    rep.append(["Nombre A", "Nombre B", "Similitud"])
    for d in reporte.get("duplicados_posibles", []):
        rep.append([d.get("nombre_a", ""), d.get("nombre_b", ""), d.get("similitud", "")])
    rep.append([])

    rep.append(["Dudas de precio"])
    rep.append(["Texto", "Motivo"])
    for x in reporte.get("dudas_precio", []):
        rep.append([x.get("texto", ""), x.get("motivo", "")])

    wb.save(ruta)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_xlsx_writer.py -q`
Expected: 2 tests PASAN.

- [ ] **Step 5: Commit**

```bash
git add xlsx_writer.py tests/test_xlsx_writer.py
git commit -m "feat: escritura del .xlsx con hojas Lista y Reporte"
```

---

## Task 7: Entrypoint CLI (`generar_lista.py`)

**Files:**
- Create: `generar_lista.py`
- Test: `tests/test_generar_lista.py`

**Interfaces:**
- Consumes: `consolidar` (consolidate.py), `calcular_precio` (bands.py), `google_image_link` (imagelink.py), `escribir_xlsx` (xlsx_writer.py).
- Produces:
  - `procesar(datos: dict) -> tuple[list[dict], dict]` — dado el JSON de entrada, devuelve `(lista, reporte)` listos para `escribir_xlsx` (lista con `nombre/link/pais/precio`; reporte con las 3 secciones).
  - `main(argv)` — CLI: `python generar_lista.py <entrada.json> <salida.xlsx>`.
- CLI contract: lee el JSON de `<entrada.json>`, escribe el `.xlsx` en `<salida.xlsx>`, imprime la ruta de salida.

- [ ] **Step 1: Test que falla** — `tests/test_generar_lista.py`

```python
import json
import openpyxl
from generar_lista import procesar, main


def test_procesar_arma_lista_con_precio_link_y_pais():
    datos = {
        "items": [
            {"nombre": "iPhone 13 128GB", "costo": 650, "proveedor": "A"},
            {"nombre": "iphone 13 128gb", "costo": 630, "proveedor": "B"},
        ],
        "filtrados": [{"nombre": "iPhone 12 (caja abollada)", "motivo": "caja abollada"}],
        "dudas_precio": [],
    }
    lista, reporte = procesar(datos)
    assert len(lista) == 1
    fila = lista[0]
    assert fila["pais"] == "🇺🇸"
    assert fila["precio"] == 680        # 630 + 50 = 680 -> 680
    assert fila["link"].startswith("https://www.google.com/search?tbm=isch&q=")
    assert reporte["filtrados"][0]["motivo"] == "caja abollada"


def test_main_escribe_archivo(tmp_path):
    entrada = tmp_path / "in.json"
    salida = tmp_path / "out.xlsx"
    entrada.write_text(json.dumps({
        "items": [{"nombre": "Motorola G54", "costo": 200, "proveedor": "A"}],
        "filtrados": [],
        "dudas_precio": [],
    }), encoding="utf-8")

    main([str(entrada), str(salida)])

    wb = openpyxl.load_workbook(str(salida))
    hoja = wb["Lista"]
    assert [c.value for c in hoja[2]] == [
        "Motorola G54",
        "https://www.google.com/search?tbm=isch&q=Motorola+G54",
        "🇺🇸",
        230,  # 200 + 30 = 230
    ]
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest tests/test_generar_lista.py -q`
Expected: FALLA.

- [ ] **Step 3: Implementación** — `generar_lista.py`

```python
import json
import sys

from bands import calcular_precio
from consolidate import consolidar
from imagelink import google_image_link
from xlsx_writer import escribir_xlsx

PAIS_DEFECTO = "🇺🇸"


def procesar(datos):
    items = datos.get("items", [])
    cons = consolidar(items)

    lista = []
    for fila in cons["lista"]:
        lista.append({
            "nombre": fila["nombre"],
            "link": google_image_link(fila["nombre"]),
            "pais": PAIS_DEFECTO,
            "precio": calcular_precio(fila["costo"]),
        })

    reporte = {
        "filtrados": datos.get("filtrados", []),
        "duplicados_posibles": cons["duplicados_posibles"],
        "dudas_precio": datos.get("dudas_precio", []),
    }
    return lista, reporte


def main(argv):
    if len(argv) != 2:
        raise SystemExit("Uso: python generar_lista.py <entrada.json> <salida.xlsx>")
    ruta_entrada, ruta_salida = argv
    with open(ruta_entrada, encoding="utf-8") as f:
        datos = json.load(f)
    lista, reporte = procesar(datos)
    escribir_xlsx(lista, reporte, ruta_salida)
    print(ruta_salida)


if __name__ == "__main__":
    main(sys.argv[1:])
```

- [ ] **Step 4: Correr y verificar que pasa (y toda la suite)**

Run: `cd "/Users/toraba/TTRA Project" && ./.venv/bin/pytest -q`
Expected: TODOS los tests pasan (bands, imagelink, normalize, consolidate, xlsx_writer, generar_lista).

- [ ] **Step 5: Commit**

```bash
git add generar_lista.py tests/test_generar_lista.py
git commit -m "feat: entrypoint que arma la lista y genera el .xlsx"
```

---

## Task 8: La skill `/lista` (`SKILL.md`)

**Files:**
- Create: `.claude/skills/lista/SKILL.md`

**Interfaces:**
- Consumes: `generar_lista.py` (entrypoint), el entorno `.venv`.
- Produces: el comando `/lista` invocable en Claude Code.

Esta tarea no tiene test unitario (es un documento de instrucciones); se valida con una corrida de extremo a extremo (Step 3).

- [ ] **Step 1: Crear `.claude/skills/lista/SKILL.md`**

````markdown
---
name: lista
description: Genera un Excel de lista consolidada de precios a partir de archivos/textos de proveedores, aplicando el margen por bandas. Usar cuando el usuario adjunta o pega precios de proveedores y pide "la lista", "el listado" o "/lista".
---

# Generar lista consolidada de precios

Convierte los precios de proveedores (archivos adjuntos y/o texto pegado) en un Excel de
4 columnas + una hoja de reporte. La parte determinística (precio, redondeo, link, dedup,
.xlsx) la hace el script `generar_lista.py`; vos hacés la limpieza y clasificación de texto.

## Reglas para armar cada ítem (columna "Nombre")

1. **Limpieza:** quitar emojis, asteriscos de negrita, líneas de colores y textos de
   "Disponible".
2. **Filtros — NO van a la lista, van a `filtrados`:** ítems con "caja abollada", "caja
   manchada", o stock 0. Anotar el motivo.
3. **Unificación:** si el mismo modelo exacto se repite (distintos colores) → una sola fila.
   En **iPhones usados**, agrupar los porcentajes de batería entre paréntesis en el nombre:
   `iPhone 13 128GB (84%) (87%)`.
4. **Regla "slim":**
   - Celular (Motorola, Xiaomi, POCO, etc.) que dice "slim" → borrar "slim" y poner
     `(s/ cargador)`.
   - Notebook (ej. Lenovo Slim) → dejar "slim" intacto.

## Reglas de precio

- Usar el **costo en USD**. Si hay un segundo precio (pesos), ignorarlo.
- Si un ítem no tiene costo numérico claro → NO calcular; mandarlo a `dudas_precio` con el
  motivo. Nunca inventar un costo.
- El cálculo del precio final (banda + redondeo a $5) lo hace el script; vos solo pasás el
  costo USD.

## Procedimiento

1. Leé todos los archivos adjuntos y/o el texto pegado.
2. Armá un JSON con esta forma exacta:

   ```json
   {
     "items": [ {"nombre": "iPhone 13 128GB (84%)", "costo": 630, "proveedor": "ProvA"} ],
     "filtrados": [ {"nombre": "iPhone 12 (caja abollada)", "motivo": "caja abollada"} ],
     "dudas_precio": [ {"texto": "Samsung A15 consultar", "motivo": "sin costo numérico"} ]
   }
   ```

   - `costo` es el número USD (sin símbolos).
   - `proveedor` es una etiqueta para identificar la fuente (nombre del archivo o del chat).
3. Guardá ese JSON en el scratchpad, p. ej. `entrada.json`.
4. Ejecutá el script (usá el venv del proyecto):

   ```bash
   cd "/Users/toraba/TTRA Project" && ./.venv/bin/python generar_lista.py <ruta/entrada.json> <ruta/lista.xlsx>
   ```

5. Entregá el archivo `.xlsx` al usuario y resumí en el chat: cuántos productos quedaron,
   cuántos se filtraron, y cuántos posibles duplicados hay para revisar.

## Importante

- No modifiques el precio a mano: siempre sale del script (determinístico).
- El emparejamiento por más barato y el reporte de posibles duplicados los hace el script;
  vos NO fusiones productos parecidos por tu cuenta — dejá que el script los reporte.
````

- [ ] **Step 2: Verificar que la skill es reconocible (estructura y frontmatter)**

Run: `cd "/Users/toraba/TTRA Project" && cat .claude/skills/lista/SKILL.md | head -5`
Expected: muestra el frontmatter con `name: lista` y `description:`.

- [ ] **Step 3: Corrida de extremo a extremo (validación real)**

Crear un JSON de ejemplo en el scratchpad y correr el script para confirmar que produce el .xlsx correctamente:

```bash
cd "/Users/toraba/TTRA Project" && cat > /tmp/entrada_demo.json <<'JSON'
{
  "items": [
    {"nombre": "iPhone 13 128GB (84%)", "costo": 630, "proveedor": "ProvA"},
    {"nombre": "iPhone 13 128GB (87%)", "costo": 640, "proveedor": "ProvB"},
    {"nombre": "Motorola G54 (s/ cargador)", "costo": 200, "proveedor": "ProvA"}
  ],
  "filtrados": [{"nombre": "iPhone 12 (caja abollada)", "motivo": "caja abollada"}],
  "dudas_precio": []
}
JSON
./.venv/bin/python generar_lista.py /tmp/entrada_demo.json /tmp/lista_demo.xlsx && ./.venv/bin/python -c "import openpyxl; wb=openpyxl.load_workbook('/tmp/lista_demo.xlsx'); h=wb['Lista']; [print([c.value for c in r]) for r in h.iter_rows()]"
```
Expected: imprime los encabezados y las filas con precios calculados (ej. Motorola 200 → 230), país 🇺🇸 y links de Google.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/lista/SKILL.md
git commit -m "feat: comando /lista para generar la lista consolidada"
```

---

## Self-Review (cobertura del spec)

- ✅ Entrada mixta (archivos + texto pegado) → SKILL.md lee ambos (Task 8).
- ✅ Salida .xlsx de 4 columnas → xlsx_writer + generar_lista (Task 6, 7).
- ✅ Una lista consolidada desde cero → generar_lista (Task 7).
- ✅ USD, ignorar precio en pesos → regla en SKILL.md (Task 8).
- ✅ Margen por bandas + redondeo hacia arriba a $5 → bands.py (Task 2).
- ✅ Duplicados: una fila, el más barato → consolidate.py (Task 5).
- ✅ Emparejamiento conservador + reporte de parecidos → consolidate.py (Task 5).
- ✅ Nombre: limpieza, filtros, unificación, iPhone baterías, regla slim → SKILL.md (Task 8).
- ✅ Link Google Imágenes (espacios → +) → imagelink.py (Task 3).
- ✅ País 🇺🇸 en todas las filas → generar_lista.py (Task 7).
- ✅ Reporte: filtrados, posibles duplicados, dudas de precio → xlsx_writer + generar_lista (Task 6, 7).
- ✅ Casos borde: sin costo válido → dudas_precio; slim ambiguo → dejar como viene (SKILL.md, Task 8).
```
