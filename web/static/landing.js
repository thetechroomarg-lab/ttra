const MARCAS = [
  "Apple", "Samsung", "Xiaomi", "Motorola", "Realme", "Oppo", "Honor",
  "Infinix", "Nokia", "PlayStation", "Nintendo", "JBL", "Logitech",
];

// Orden y etiquetas de los botones de categoría en la pantalla principal.
// "clave" es el nombre de sección tal cual lo devuelve /api/catalogo;
// "etiqueta" es lo que se muestra en el botón (más corto en el caso de accesorios).
const CATEGORIAS_BOTONES = [
  { clave: "Celulares", etiqueta: "Celulares" },
  { clave: "Tablets", etiqueta: "Tablets" },
  { clave: "Notebooks y Macbooks", etiqueta: "Notebooks y Macbooks" },
  { clave: "Gaming", etiqueta: "Gaming" },
  { clave: "Accesorios Celulares", etiqueta: "Accesorios" },
];

const CLAVE_CARRITO = "ttra_carrito";
const WHATSAPP_NUMERO = "543512145217";

let SECCIONES_DATA = {};
let seccionActiva = null; // null = pantalla principal (categorías o búsqueda global)

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

function pintarCategorias() {
  const el = document.getElementById("categorias");
  el.innerHTML = CATEGORIAS_BOTONES.map(
    (c) => `<button data-seccion="${escapeHtml(c.clave)}" class="btn-categoria" type="button">${escapeHtml(c.etiqueta)}</button>`
  ).join("");
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      seccionActiva = btn.dataset.seccion;
      document.getElementById("input-busqueda").value = "";
      actualizarVista();
    });
  });
}

function formatearPesos(valor) {
  return valor === undefined || valor === null ? "-" : Number(valor).toLocaleString("es-AR");
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
        $ ${formatearPesos(p.pesos)} contado<br>
        $ ${formatearPesos(p.transferencia)} transferencia
      </p>
      <button class="btn-agregar" data-nombre="${escapeHtml(p.nombre)}" type="button">Agregar al carrito</button>
    </div>
  `;
}

function pintarGrilla(el, productos, mensajeVacio) {
  if (!productos || productos.length === 0) {
    el.innerHTML = `<p class="mensaje-vacio">${mensajeVacio}</p>`;
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

// Decide qué mostrar según la sección elegida (si hay) y el término de búsqueda,
// y pinta categorías/grilla/botón "volver" en consecuencia.
function actualizarVista() {
  const termino = document.getElementById("input-busqueda").value.trim().toLowerCase();
  const categoriasEl = document.getElementById("categorias");
  const volverBtn = document.getElementById("btn-volver");
  const productosEl = document.getElementById("productos");

  const enPantallaPrincipal = !seccionActiva && termino === "";
  categoriasEl.classList.toggle("oculto", !enPantallaPrincipal);
  volverBtn.classList.toggle("oculto", enPantallaPrincipal);

  if (enPantallaPrincipal) {
    productosEl.innerHTML = "";
    return;
  }

  let base;
  if (seccionActiva) {
    base = SECCIONES_DATA[seccionActiva] || [];
  } else {
    base = Object.values(SECCIONES_DATA).flat();
  }

  const productos = termino
    ? base.filter((p) => (p.nombre || "").toLowerCase().includes(termino))
    : base;

  const mensajeVacio = termino
    ? "Lo siento, pero no hay resultados :("
    : `Todavía no hay productos cargados en ${seccionActiva}.`;

  pintarGrilla(productosEl, productos, mensajeVacio);
}

function volverAPantallaPrincipal() {
  seccionActiva = null;
  document.getElementById("input-busqueda").value = "";
  actualizarVista();
}

function ocultarNavegacionCatalogo() {
  document.getElementById("categorias").classList.add("oculto");
  document.getElementById("btn-volver").classList.add("oculto");
}

async function cargarCatalogo() {
  let datos;
  try {
    const r = await fetch("/api/catalogo");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    datos = await r.json();
  } catch {
    ocultarNavegacionCatalogo();
    document.getElementById("productos").innerHTML =
      '<p class="mensaje-vacio">No pudimos cargar el catálogo. Escribinos por WhatsApp: ' +
      '<a href="https://wa.me/543512145217" target="_blank" rel="noopener">wa.me/543512145217</a></p>';
    return;
  }
  SECCIONES_DATA = datos.secciones || {};
  refrescarPreciosCarrito();
  if (datos.mensaje) {
    ocultarNavegacionCatalogo();
    document.getElementById("productos").innerHTML = `<p class="mensaje-vacio">${datos.mensaje}</p>`;
    return;
  }
  pintarCategorias();
  actualizarVista();
}

function refrescarPreciosCarrito() {
  const catalogoPlano = {};
  Object.values(SECCIONES_DATA).forEach((productos) => {
    (productos || []).forEach((p) => {
      catalogoPlano[p.nombre] = p;
    });
  });

  const carrito = cargarCarrito();
  const carritoActualizado = carrito
    .filter((it) => catalogoPlano[it.nombre])
    .map((it) => {
      const p = catalogoPlano[it.nombre];
      return { ...it, usd: p.usd, pesos: p.pesos, transferencia: p.transferencia };
    });

  guardarCarrito(carritoActualizado);
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
    : `Total: U$D ${t.usd} · $ ${formatearPesos(t.pesos)} contado · $ ${formatearPesos(t.transferencia)} transferencia`;
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
  const total = `Total: U$D ${t.usd} · $ ${formatearPesos(t.pesos)} contado · $ ${formatearPesos(t.transferencia)} transferencia`;
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
document.getElementById("btn-volver").addEventListener("click", volverAPantallaPrincipal);
document.getElementById("titulo-inicio").addEventListener("click", volverAPantallaPrincipal);
document.getElementById("input-busqueda").addEventListener("input", actualizarVista);

pintarCarrousel();
renderCarrito();
cargarCatalogo();
