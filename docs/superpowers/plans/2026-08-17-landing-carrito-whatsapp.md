# Landing con carrito y cierre por WhatsApp — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la página raíz (`/`, hoy el chat) por una landing pública con
secciones, grilla de productos y un carrito en `localStorage` que cierra el pedido
abriendo WhatsApp con el detalle precargado.

**Architecture:** `GET /api/catalogo` pasa a ser pública (sin sesión). La landing
(`web/static/index.html` + `landing.css` + `landing.js`) reemplaza el chat viejo como
contenido de `/`, reutilizando el tema RobCo/CRT (`theme.css`, `boot.js`) ya existente.
El chat viejo (`styles.css`, `chat.js`) y el login/registro/`/catalogo` con tabs quedan
intactos en el repo, sin ningún link hacia ellos desde la landing nueva.

**Tech Stack:** FastAPI (backend sin cambios de infraestructura, solo se quita un
chequeo de sesión), HTML/CSS/JS plano (sin frameworks) para el frontend, `localStorage`
para el carrito.

**Spec:** `docs/superpowers/specs/2026-08-17-landing-carrito-whatsapp-design.md`

## Global Constraints

- No se agrega login ni cuenta al flujo de compra — la landing y el carrito son
  100% públicos.
- El carrito vive solo en `localStorage` (clave `ttra_carrito`), identificado por el
  `nombre` del producto. No hay backend de carrito.
- El mensaje de WhatsApp usa el mismo número que `web/reglas.py::WHATSAPP`
  (`543512145217`) y muestra el total en las 3 formas: U$D, pesos contado,
  transferencia.
- No se borra nada de lo ya construido (chat viejo, login/registro, `/catalogo` con
  tabs) — solo se deja de enlazar desde la landing.
- El tema visual (RobCo/CRT, `theme.css`, `boot.js`) se reutiliza tal cual, sin
  reescribirlo.

---

## Task 1: `/api/catalogo` pública

**Files:**
- Modify: `web/app.py:171-179`
- Modify: `tests/test_app_catalogo.py`

**Interfaces:**
- Consumes: nada nuevo — `catalogo.SECCIONES`, `catalogo.secciones_catalogo`,
  `_cargar_productos` ya existen.
- Produces: `GET /api/catalogo` responde 200 siempre (con o sin sesión), con el mismo
  cuerpo que antes (`{"secciones": {...}}` o `{"secciones": {...}, "mensaje": "..."}`).
  `GET /catalogo` (la página con tabs) sigue exigiendo sesión, sin cambios.

- [ ] **Step 1: Escribir el test que falla**

Reemplazar el contenido completo de `tests/test_app_catalogo.py` por:

```python
from fastapi.testclient import TestClient

import web.app as appmod
from web import auth


def _cliente_autenticado(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    c = TestClient(appmod.app)
    c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    return c


def test_api_catalogo_es_publica_sin_sesion(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [])
    c = TestClient(appmod.app)
    r = c.get("/api/catalogo")
    assert r.status_code == 200


def test_pagina_catalogo_sin_sesion_redirige_a_login(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    c = TestClient(appmod.app, follow_redirects=False)
    r = c.get("/catalogo")
    assert r.status_code in (302, 307)
    assert "login" in r.headers["location"]


def test_api_catalogo_sin_productos(tmp_path, monkeypatch):
    c = _cliente_autenticado(tmp_path, monkeypatch)
    monkeypatch.setattr(appmod, "_cargar_productos", lambda: [])
    r = c.get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["mensaje"] == "Estamos actualizando los precios"


def test_api_catalogo_con_productos(tmp_path, monkeypatch):
    c = _cliente_autenticado(tmp_path, monkeypatch)
    monkeypatch.setattr(
        appmod, "_cargar_productos",
        lambda: [{"nombre": "iPhone 15", "categoria": "Apple - iPhone"}],
    )
    r = c.get("/api/catalogo")
    assert r.status_code == 200
    secciones = r.json()["secciones"]
    assert secciones["Celulares"][0]["nombre"] == "iPhone 15"
    assert secciones["Gaming"] == []


def test_flujo_completo_registro_logout_login_catalogo(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "DB_PATH", tmp_path / "usuarios.db")
    monkeypatch.setattr(
        appmod, "_cargar_productos",
        lambda: [{"nombre": "iPhone 15", "categoria": "Apple - iPhone"}],
    )
    c = TestClient(appmod.app)

    r = c.post("/registro", json={"nombre": "Juan", "email": "juan@x.com", "password": "clave123"})
    assert r.status_code == 200

    r = c.post("/logout")
    assert r.status_code == 200

    r = c.post("/login", json={"email": "juan@x.com", "password": "clave123"})
    assert r.status_code == 200

    r = c.get("/catalogo")
    assert r.status_code == 200

    r = c.get("/api/catalogo")
    assert r.status_code == 200
    assert r.json()["secciones"]["Celulares"][0]["nombre"] == "iPhone 15"

    r = c.post("/logout")
    assert r.status_code == 200

    # /api/catalogo ahora es pública: sigue respondiendo 200 incluso sin sesión.
    r = c.get("/api/catalogo")
    assert r.status_code == 200
```

- [ ] **Step 2: Correr el test para confirmar que falla**

Run: `./.venv/bin/pytest tests/test_app_catalogo.py -v`
Expected: FAIL — `test_api_catalogo_es_publica_sin_sesion` recibe 401 (el código
viejo todavía exige sesión); la última aserción de
`test_flujo_completo_registro_logout_login_catalogo` también falla (espera 200,
recibe 401).

- [ ] **Step 3: Quitar el chequeo de sesión en `web/app.py`**

El bloque actual (alrededor de la línea 171):

```python
@app.get("/api/catalogo")
def api_catalogo(request: Request):
    if not _sesion_activa(request):
        return JSONResponse({"error": "No autenticado"}, status_code=401)
    productos = _cargar_productos()
    if not productos:
        return {"secciones": {s: [] for s in catalogo.SECCIONES},
                "mensaje": "Estamos actualizando los precios"}
    return {"secciones": catalogo.secciones_catalogo(productos)}
```

pasa a ser:

```python
@app.get("/api/catalogo")
def api_catalogo():
    productos = _cargar_productos()
    if not productos:
        return {"secciones": {s: [] for s in catalogo.SECCIONES},
                "mensaje": "Estamos actualizando los precios"}
    return {"secciones": catalogo.secciones_catalogo(productos)}
```

No tocar `GET /catalogo` (la página con tabs, línea 164-168) — sigue exigiendo sesión
igual que hoy.

- [ ] **Step 4: Correr el test para confirmar que pasa**

Run: `./.venv/bin/pytest tests/test_app_catalogo.py -v`
Expected: 5 PASSED.

- [ ] **Step 5: Correr toda la suite para confirmar que no rompió nada**

Run: `./.venv/bin/pytest -q`
Expected: todos los tests existentes (auth, catalogo, chat) siguen en PASSED.

- [ ] **Step 6: Commit**

```bash
git add web/app.py tests/test_app_catalogo.py
git commit -m "feat: /api/catalogo publica, sin exigir sesion"
```

---

## Task 2: Landing pública con secciones, grilla y carrito

**Files:**
- Modify: `web/static/index.html` (reemplaza el contenido del chat)
- Create: `web/static/landing.css`
- Create: `web/static/landing.js`

**Interfaces:**
- Consumes: `GET /api/catalogo` (Task 1, ahora pública) — misma forma de respuesta que
  ya usa `web/static/catalogo.js`: `{"secciones": {<5 nombres>: [productos]}}` o con
  `"mensaje"` si no hay productos. `theme.css` y `boot.js` ya existentes (no se tocan).
- Produces: la landing en `/` (servida como archivo estático, sin ruta nueva en
  `web/app.py` — el mount de `StaticFiles` con `html=True` ya sirve `index.html` en
  `/`). Carrito persistido en `localStorage["ttra_carrito"]` como
  `[{nombre, usd, pesos, transferencia, cantidad}]`.

- [ ] **Step 1: Reemplazar `web/static/index.html`**

Contenido completo nuevo (reemplaza el chat viejo — `styles.css` y `chat.js` dejan de
enlazarse desde acá, pero no se borran del repo):

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>THE TECH ROOM ARG — Catálogo</title>
  <link rel="stylesheet" href="theme.css">
  <link rel="stylesheet" href="landing.css">
</head>
<body>
  <div id="rc-boot"></div>
  <div class="rc-crt"></div>
  <header>
    <h1>THE TECH ROOM ARG</h1>
    <button id="btn-carrito" type="button">🛒 <span id="carrito-contador">0</span></button>
  </header>

  <div class="carrousel-wrap">
    <div class="carrousel" id="carrousel"></div>
  </div>

  <nav class="secciones-nav" id="secciones-nav"></nav>
  <main id="productos"></main>

  <aside id="panel-carrito" class="oculto">
    <div class="panel-carrito-header">
      <h2>Tu pedido</h2>
      <button id="btn-cerrar-carrito" type="button">✕</button>
    </div>
    <div id="items-carrito"></div>
    <div class="panel-carrito-footer">
      <p id="total-carrito"></p>
      <button id="btn-vaciar-carrito" type="button">Vaciar carrito</button>
      <button id="btn-whatsapp" type="button">Cerrar pedido por WhatsApp</button>
    </div>
  </aside>
  <div id="overlay-carrito" class="oculto"></div>

  <script src="boot.js"></script>
  <script src="landing.js"></script>
</body>
</html>
```

- [ ] **Step 2: Crear `web/static/landing.css`**

```css
* { box-sizing: border-box; }
body {
  margin: 0; font-family: var(--rc-font); background: var(--rc-bg); color: var(--rc-green);
  min-height: 100vh;
}
header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; background: var(--rc-bg-panel); border-bottom: 1px solid var(--rc-green-faint);
}
header h1 { margin: 0; font-size: 18px; letter-spacing: .06em; text-transform: uppercase;
            color: var(--rc-green-bright); }
#btn-carrito { padding: 8px 14px; font-size: 15px; }

.carrousel-wrap { overflow: hidden; background: var(--rc-bg-panel); border-bottom: 1px solid var(--rc-green-faint); }
.carrousel {
  display: flex; gap: 48px; white-space: nowrap; padding: 14px 0;
  animation: desplazar 25s linear infinite;
  width: max-content;
}
.carrousel span {
  font-size: 15px; letter-spacing: .12em; text-transform: uppercase; color: var(--rc-green-dim);
}
@keyframes desplazar {
  from { transform: translateX(0); }
  to { transform: translateX(-50%); }
}

.secciones-nav {
  display: flex; gap: 10px; padding: 20px; flex-wrap: wrap;
}
.secciones-nav button {
  padding: 14px 20px; font-size: 14px; text-transform: uppercase; letter-spacing: .04em;
}
.secciones-nav button.activa {
  background: var(--rc-green-faint); color: var(--rc-green-bright); border-color: var(--rc-green);
  font-weight: 600;
}

main { padding: 0 20px 40px; }
.grilla { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; }
.card {
  background: var(--rc-bg-panel); border: 1px solid var(--rc-green-faint); padding: 16px;
  display: flex; flex-direction: column; gap: 8px;
}
.card h3 { margin: 0; font-size: 15px; color: var(--rc-green-bright); }
.card .precios { font-size: 13px; color: var(--rc-green-dim); line-height: 1.6; margin: 0; }
.card .precios strong { color: var(--rc-green-bright); }
.card .colores { margin: 0; font-size: 12px; color: var(--rc-green-dim); font-style: italic; }
.card .btn-agregar { margin-top: 8px; font-size: 13px; }
.mensaje-vacio { color: var(--rc-green-dim); padding: 40px; text-align: center; }

#overlay-carrito {
  position: fixed; inset: 0; background: rgba(0, 0, 0, .6); z-index: 9990;
}
#overlay-carrito.oculto { display: none; }

#panel-carrito {
  position: fixed; top: 0; right: 0; bottom: 0; width: min(360px, 90vw);
  background: var(--rc-bg-panel); border-left: 1px solid var(--rc-green-dim);
  z-index: 9995; display: flex; flex-direction: column; padding: 20px;
  overflow-y: auto;
}
#panel-carrito.oculto { display: none; }
.panel-carrito-header { display: flex; align-items: center; justify-content: space-between; }
.panel-carrito-header h2 { margin: 0; font-size: 16px; text-transform: uppercase; letter-spacing: .04em; }
#items-carrito { flex: 1; margin: 16px 0; display: flex; flex-direction: column; gap: 12px; }
.item-carrito { border: 1px solid var(--rc-green-faint); padding: 10px; }
.item-nombre { margin: 0 0 6px; font-size: 13px; }
.item-controles { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.item-controles button { padding: 4px 10px; font-size: 13px; }
.panel-carrito-footer { border-top: 1px solid var(--rc-green-faint); padding-top: 14px; display: flex; flex-direction: column; gap: 10px; }
#total-carrito { margin: 0; font-size: 14px; color: var(--rc-green-bright); }
```

- [ ] **Step 3: Crear `web/static/landing.js`**

```javascript
const MARCAS = [
  "Apple", "Samsung", "Xiaomi", "Motorola", "Realme", "Oppo", "Honor",
  "Infinix", "Nokia", "PlayStation", "Nintendo", "JBL", "Logitech",
];

const SECCIONES = [
  "Celulares", "Accesorios Celulares", "Tablets", "Notebooks y Macbooks", "Gaming",
];

const CLAVE_CARRITO = "ttra_carrito";
const WHATSAPP_NUMERO = "543512145217";

let SECCIONES_DATA = {};

function pintarCarrousel() {
  const el = document.getElementById("carrousel");
  const marcas = [...MARCAS, ...MARCAS];
  el.innerHTML = marcas.map((m) => `<span>${m}</span>`).join("");
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  return div.innerHTML;
}

function pintarSeccionesNav(activa) {
  const el = document.getElementById("secciones-nav");
  el.innerHTML = SECCIONES.map(
    (s) => `<button data-seccion="${s}" class="${s === activa ? "activa" : ""}">${s}</button>`
  ).join("");
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      pintarSeccionesNav(btn.dataset.seccion);
      pintarProductos(btn.dataset.seccion);
    });
  });
}

function tarjetaProducto(p) {
  const colores = Array.isArray(p.colores) && p.colores.length > 0
    ? `<p class="colores">${escapeHtml(p.colores.join(", "))}</p>`
    : "";
  return `
    <div class="card">
      <h3>${escapeHtml(p.nombre)}</h3>
      ${colores}
      <p class="precios">
        <strong>U$D ${p.usd ?? "-"}</strong><br>
        $ ${p.pesos ?? "-"} contado<br>
        $ ${p.transferencia ?? "-"} transferencia
      </p>
      <button class="btn-agregar" data-nombre="${escapeHtml(p.nombre)}" type="button">Agregar al carrito 🛒</button>
    </div>
  `;
}

function pintarProductos(seccion) {
  const el = document.getElementById("productos");
  const productos = SECCIONES_DATA[seccion] || [];
  if (productos.length === 0) {
    el.innerHTML = `<p class="mensaje-vacio">Todavía no hay productos cargados en ${seccion}.</p>`;
    return;
  }
  el.innerHTML = `<div class="grilla">${productos.map(tarjetaProducto).join("")}</div>`;
  el.querySelectorAll(".btn-agregar").forEach((btn) => {
    btn.addEventListener("click", () => {
      const producto = productos.find((p) => p.nombre === btn.dataset.nombre);
      if (producto) agregarAlCarrito(producto);
    });
  });
}

async function cargarCatalogo() {
  const r = await fetch("/api/catalogo");
  const datos = await r.json();
  SECCIONES_DATA = datos.secciones || {};
  if (datos.mensaje) {
    document.getElementById("productos").innerHTML = `<p class="mensaje-vacio">${datos.mensaje}</p>`;
    pintarSeccionesNav(null);
    return;
  }
  pintarSeccionesNav(SECCIONES[0]);
  pintarProductos(SECCIONES[0]);
}

// --- Carrito ---

function cargarCarrito() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_CARRITO)) || [];
  } catch {
    return [];
  }
}

function guardarCarrito(carrito) {
  localStorage.setItem(CLAVE_CARRITO, JSON.stringify(carrito));
  renderCarrito();
}

function agregarAlCarrito(producto) {
  const carrito = cargarCarrito();
  const existente = carrito.find((it) => it.nombre === producto.nombre);
  if (existente) {
    existente.cantidad += 1;
  } else {
    carrito.push({
      nombre: producto.nombre,
      usd: producto.usd,
      pesos: producto.pesos,
      transferencia: producto.transferencia,
      cantidad: 1,
    });
  }
  guardarCarrito(carrito);
  abrirCarrito();
}

function cambiarCantidad(nombre, delta) {
  const carrito = cargarCarrito();
  const item = carrito.find((it) => it.nombre === nombre);
  if (!item) return;
  item.cantidad += delta;
  const nuevo = item.cantidad > 0 ? carrito : carrito.filter((it) => it.nombre !== nombre);
  guardarCarrito(nuevo);
}

function quitarDelCarrito(nombre) {
  guardarCarrito(cargarCarrito().filter((it) => it.nombre !== nombre));
}

function vaciarCarrito() {
  guardarCarrito([]);
}

function totales(carrito) {
  return carrito.reduce(
    (acc, it) => ({
      usd: acc.usd + (it.usd || 0) * it.cantidad,
      pesos: acc.pesos + (it.pesos || 0) * it.cantidad,
      transferencia: acc.transferencia + (it.transferencia || 0) * it.cantidad,
    }),
    { usd: 0, pesos: 0, transferencia: 0 }
  );
}

function itemCarritoHtml(it) {
  return `
    <div class="item-carrito">
      <p class="item-nombre">${escapeHtml(it.nombre)}</p>
      <div class="item-controles">
        <button class="btn-menos" data-nombre="${escapeHtml(it.nombre)}" type="button">-</button>
        <span>${it.cantidad}</span>
        <button class="btn-mas" data-nombre="${escapeHtml(it.nombre)}" type="button">+</button>
        <button class="btn-quitar" data-nombre="${escapeHtml(it.nombre)}" type="button">Quitar</button>
      </div>
    </div>
  `;
}

function renderCarrito() {
  const carrito = cargarCarrito();
  const cantidadTotal = carrito.reduce((n, it) => n + it.cantidad, 0);
  document.getElementById("carrito-contador").textContent = cantidadTotal;

  const el = document.getElementById("items-carrito");
  el.innerHTML = carrito.length === 0
    ? '<p class="mensaje-vacio">Tu carrito está vacío.</p>'
    : carrito.map(itemCarritoHtml).join("");

  el.querySelectorAll(".btn-menos").forEach((btn) => {
    btn.addEventListener("click", () => cambiarCantidad(btn.dataset.nombre, -1));
  });
  el.querySelectorAll(".btn-mas").forEach((btn) => {
    btn.addEventListener("click", () => cambiarCantidad(btn.dataset.nombre, 1));
  });
  el.querySelectorAll(".btn-quitar").forEach((btn) => {
    btn.addEventListener("click", () => quitarDelCarrito(btn.dataset.nombre));
  });

  const t = totales(carrito);
  document.getElementById("total-carrito").textContent = carrito.length === 0
    ? ""
    : `Total: U$D ${t.usd} · $ ${t.pesos} contado · $ ${t.transferencia} transferencia`;
}

function abrirCarrito() {
  document.getElementById("panel-carrito").classList.remove("oculto");
  document.getElementById("overlay-carrito").classList.remove("oculto");
}

function cerrarCarrito() {
  document.getElementById("panel-carrito").classList.add("oculto");
  document.getElementById("overlay-carrito").classList.add("oculto");
}

function armarMensajeWhatsapp(carrito) {
  const lineas = carrito.map(
    (it) => `- ${it.nombre} x${it.cantidad} — U$D ${(it.usd || 0) * it.cantidad}`
  );
  const t = totales(carrito);
  const total = `Total: U$D ${t.usd} · $ ${t.pesos} contado · $ ${t.transferencia} transferencia`;
  return `Hola! Quiero encargar:\n${lineas.join("\n")}\n\n${total}`;
}

document.getElementById("btn-carrito").addEventListener("click", abrirCarrito);
document.getElementById("btn-cerrar-carrito").addEventListener("click", cerrarCarrito);
document.getElementById("overlay-carrito").addEventListener("click", cerrarCarrito);
document.getElementById("btn-vaciar-carrito").addEventListener("click", vaciarCarrito);
document.getElementById("btn-whatsapp").addEventListener("click", () => {
  const carrito = cargarCarrito();
  if (carrito.length === 0) return;
  const mensaje = armarMensajeWhatsapp(carrito);
  window.open(`https://wa.me/${WHATSAPP_NUMERO}?text=${encodeURIComponent(mensaje)}`, "_blank");
});

pintarCarrousel();
renderCarrito();
cargarCatalogo();
```

- [ ] **Step 4: Verificación manual**

Run: `./.venv/bin/uvicorn web.app:app --reload --port 8000`
Abrir `http://localhost:8000/`. Confirmar:
- Se ve el boot sequence (si es la primera vez en esta sesión de navegador), después
  la landing con carrousel de marcas, botones de sección y grilla de productos.
- Elegir una sección distinta a la primera y confirmar que cambia la grilla.
- Click en "Agregar al carrito 🛒" en un producto: se abre el panel del carrito con
  ese ítem, cantidad 1, y el contador del header en 1.
- Click en "+"/"-" cambia la cantidad; bajar a 0 quita el ítem.
- Recargar la página (F5): el carrito sigue teniendo lo agregado (persiste en
  `localStorage`).
- Click en "Cerrar pedido por WhatsApp" con ítems en el carrito: abre una pestaña
  nueva a `https://wa.me/543512145217?text=...` con el mensaje armado (nombre,
  cantidad, precio U$D por ítem, y el total en las 3 formas).
- Click en "Vaciar carrito": el panel queda vacío y el contador en 0.

Expected: todos los pasos anteriores se comportan como se describe, sin errores en la
consola del navegador.

- [ ] **Step 5: Commit**

```bash
git add web/static/index.html web/static/landing.css web/static/landing.js
git commit -m "feat: landing publica con secciones, grilla y carrito con cierre por WhatsApp"
```

---

## Self-Review Notes

- **Cobertura de la spec:** landing pública sin login (Task 2), 5 secciones desde
  `/api/catalogo` ahora pública (Task 1), carrito en `localStorage` con +/-/quitar
  (Task 2), mensaje de WhatsApp con los 3 totales (Task 2), nada del chat/login/
  `/catalogo` viejo se borra (ambas tareas solo agregan/editan lo estrictamente
  necesario) — todo cubierto.
- **Consistencia de tipos:** el carrito guarda `{nombre, usd, pesos, transferencia,
  cantidad}` — mismos campos que ya trae cada producto de `/api/catalogo`, sin
  inventar una forma nueva. `SECCIONES` en `landing.js` es idéntica a la ya usada en
  `catalogo.js`/`web/catalogo.py` (mismo orden y nombres).
- **No placeholders:** cada paso tiene el código completo a escribir, sin "TODO" ni
  referencias a pasos anteriores sin repetir el código.
