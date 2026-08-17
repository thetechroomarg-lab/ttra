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

// Secciones que muestran un paso intermedio (marca o tipo) antes de la grilla.
const SECCIONES_CON_SUBNAV = new Set([
  "Celulares", "Tablets", "Accesorios Celulares", "Notebooks y Macbooks",
]);

// Orden preferido de marcas dentro del sub-nav; lo que no está acá se agrega
// al final, ordenado alfabéticamente.
const ORDEN_MARCAS = [
  "Apple", "Samsung", "Xiaomi", "Motorola", "Realme",
  "Oppo", "Honor", "Infinix", "Nokia", "Itel", "JBL", "Logitech", "Otras marcas",
];

const CLAVE_CARRITO = "ttra_carrito";
const WHATSAPP_NUMERO = "543512145217";

let SECCIONES_DATA = {};
let seccionActiva = null; // clave de sección elegida en la pantalla principal, o null
let subFiltroActivo = null; // marca elegida, o "Notebooks"/"Macbooks", o null
let modoVista = "cards"; // "cards" | "lista"

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
      subFiltroActivo = null;
      document.getElementById("input-busqueda").value = "";
      actualizarVista();
    });
  });
}

// Devuelve las opciones del sub-nav para la sección dada: marcas presentes
// en sus productos, o los 2 tipos fijos para Notebooks y Macbooks.
function opcionesSubNav(seccion) {
  if (seccion === "Notebooks y Macbooks") {
    return ["Notebooks", "Macbooks"];
  }
  const productos = SECCIONES_DATA[seccion] || [];
  const presentes = new Set(productos.map((p) => p.marca || "Otras marcas"));
  const ordenadas = ORDEN_MARCAS.filter((m) => presentes.has(m));
  const resto = [...presentes].filter((m) => !ORDEN_MARCAS.includes(m)).sort();
  return [...ordenadas, ...resto];
}

function pintarSubNav(seccion) {
  const el = document.getElementById("sub-nav");
  const opciones = opcionesSubNav(seccion);
  el.innerHTML = opciones.map(
    (o) => `<button data-clave="${escapeHtml(o)}" class="btn-categoria" type="button">${escapeHtml(o)}</button>`
  ).join("");
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      subFiltroActivo = btn.dataset.clave;
      actualizarVista();
    });
  });
}

// Productos de una sección que corresponden al sub-filtro elegido (marca, o
// tipo Notebook/Mac).
function productosDeSubFiltro(seccion, subFiltro) {
  const productos = SECCIONES_DATA[seccion] || [];
  if (seccion === "Notebooks y Macbooks") {
    const categoriaBuscada = subFiltro === "Notebooks" ? "Notebook" : "Mac";
    return productos.filter((p) => p.categoria === categoriaBuscada);
  }
  return productos.filter((p) => (p.marca || "Otras marcas") === subFiltro);
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

function controlVistaHtml() {
  return `
    <div class="control-vista">
      <button type="button" class="btn-vista ${modoVista === "cards" ? "activo" : ""}" data-modo="cards">Cards</button>
      <button type="button" class="btn-vista ${modoVista === "lista" ? "activo" : ""}" data-modo="lista">Lista</button>
    </div>
  `;
}

function pintarGrilla(el, productos, mensajeVacio) {
  if (!productos || productos.length === 0) {
    el.innerHTML = `<p class="mensaje-vacio">${mensajeVacio}</p>`;
    return;
  }
  const claseModo = modoVista === "lista" ? "lista" : "";
  el.innerHTML = `${controlVistaHtml()}<div class="grilla ${claseModo}">${productos.map(tarjetaProducto).join("")}</div>`;
  el.querySelectorAll(".btn-agregar").forEach((btn) => {
    btn.addEventListener("click", () => {
      const producto = productos.find((p) => p.nombre === btn.dataset.nombre);
      if (producto) agregarAlCarrito(producto);
    });
  });
  el.querySelectorAll(".btn-vista").forEach((btn) => {
    btn.addEventListener("click", () => {
      modoVista = btn.dataset.modo;
      actualizarVista();
    });
  });
}

// Decide qué mostrar según la sección elegida (si hay), el sub-filtro (marca
// o tipo) y el término de búsqueda, y pinta categorías/sub-nav/grilla/volver.
function actualizarVista() {
  const termino = document.getElementById("input-busqueda").value.trim().toLowerCase();
  const categoriasEl = document.getElementById("categorias");
  const subNavEl = document.getElementById("sub-nav");
  const volverBtn = document.getElementById("btn-volver");
  const productosEl = document.getElementById("productos");

  const enInicio = !seccionActiva && termino === "";
  const enSubNav = !!seccionActiva && SECCIONES_CON_SUBNAV.has(seccionActiva) &&
    !subFiltroActivo && termino === "";

  categoriasEl.classList.toggle("oculto", !enInicio);
  subNavEl.classList.toggle("oculto", !enSubNav);
  volverBtn.classList.toggle("oculto", enInicio);

  if (enInicio) {
    productosEl.innerHTML = "";
    return;
  }

  if (enSubNav) {
    pintarSubNav(seccionActiva);
    productosEl.innerHTML = "";
    return;
  }

  let base;
  if (!seccionActiva) {
    base = Object.values(SECCIONES_DATA).flat(); // búsqueda global
  } else if (subFiltroActivo) {
    base = productosDeSubFiltro(seccionActiva, subFiltroActivo);
  } else {
    base = SECCIONES_DATA[seccionActiva] || []; // sección sin sub-nav (Gaming), o buscando antes de elegir
  }

  const productos = termino
    ? base.filter((p) => (p.nombre || "").toLowerCase().includes(termino))
    : base;

  const mensajeVacio = termino
    ? "Lo siento, pero no hay resultados :("
    : "Todavía no hay productos cargados acá.";

  pintarGrilla(productosEl, productos, mensajeVacio);
}

// Retrocede un paso a la vez: primero limpia la búsqueda, después el
// sub-filtro (marca/tipo), y por último vuelve a la pantalla principal.
function volverUnPaso() {
  const input = document.getElementById("input-busqueda");
  if (input.value.trim() !== "") {
    input.value = "";
  } else if (subFiltroActivo) {
    subFiltroActivo = null;
  } else {
    seccionActiva = null;
  }
  actualizarVista();
}

function volverAPantallaPrincipal() {
  seccionActiva = null;
  subFiltroActivo = null;
  document.getElementById("input-busqueda").value = "";
  actualizarVista();
}

function ocultarNavegacionCatalogo() {
  document.getElementById("categorias").classList.add("oculto");
  document.getElementById("sub-nav").classList.add("oculto");
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
document.getElementById("btn-volver").addEventListener("click", volverUnPaso);
document.getElementById("titulo-inicio").addEventListener("click", volverAPantallaPrincipal);
document.getElementById("input-busqueda").addEventListener("input", actualizarVista);

// --- Frase del pie, con referencia a personajes de videojuegos ---

const FRASES_GAMING = [
  { texto: "War. War never changes.", autor: "The Narrator" },
  { texto: "It's dangerous to go alone! Take this.", autor: "Old Man" },
  { texto: "Stay awhile and listen.", autor: "Deckard Cain" },
  { texto: "The cake is a lie.", autor: "GLaDOS" },
  { texto: "Finish him!", autor: "Shao Kahn" },
  { texto: "Hey! Listen!", autor: "Navi" },
  { texto: "A man chooses, a slave obeys.", autor: "Andrew Ryan" },
  { texto: "Wake up, samurai. We have a city to burn.", autor: "Johnny Silverhand" },
  { texto: "Do a barrel roll!", autor: "Peppy Ainsworth" },
  { texto: "I used to be an adventurer like you, until I took an arrow in the knee.", autor: "Guardia de Whiterun" },
  { texto: "Praise the sun!", autor: "Solaire de Astora" },
  { texto: "Would you kindly?", autor: "Andrew Ryan" },
];

function pintarFrasePie() {
  const el = document.getElementById("pie-frase");
  if (!el) return;
  const horaBucket = Math.floor(Date.now() / (60 * 60 * 1000));
  const frase = FRASES_GAMING[horaBucket % FRASES_GAMING.length];
  el.textContent = `"${frase.texto}" -- (${frase.autor})`;
}

pintarFrasePie();
setInterval(pintarFrasePie, 60 * 60 * 1000);

pintarCarrousel();
renderCarrito();
cargarCatalogo();
