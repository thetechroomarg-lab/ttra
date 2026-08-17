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
let filtroMarcaGlobal = null; // marca elegida desde el carrousel, busca en TODO el catálogo
let modoVista = "cards"; // "cards" | "lista"

// Fotos decorativas de la ciudad, solo visibles en la pantalla principal.
const IMAGENES_CIUDAD = [
  "ciudad/catedral-cordoba.png",
  "ciudad/plaza-san-martin.png",
  "ciudad/manzana-jesuitica.png",
  "ciudad/puente-del-bicentenario.png",
  "ciudad/batalla-de-la-toma.png",
  "ciudad/parque-sarmiento.png",
  "ciudad/paseo-del-buen-pastor.png",
];
let indiceCiudad = 0;
let intervaloCiudad = null;

function detenerCarrouselCiudad() {
  if (intervaloCiudad) {
    clearInterval(intervaloCiudad);
    intervaloCiudad = null;
  }
}

function pintarCarrouselCiudad(el) {
  if (IMAGENES_CIUDAD.length === 0) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = `<div class="carrousel-ciudad"><img class="visible" src="${IMAGENES_CIUDAD[indiceCiudad]}" alt="Córdoba"></div>`;
  if (IMAGENES_CIUDAD.length <= 1) return;
  intervaloCiudad = setInterval(() => {
    const contenedor = el.querySelector(".carrousel-ciudad");
    if (!contenedor) return;
    indiceCiudad = (indiceCiudad + 1) % IMAGENES_CIUDAD.length;
    const actual = contenedor.querySelector("img.visible");
    const siguiente = document.createElement("img");
    siguiente.alt = "Córdoba";
    siguiente.src = IMAGENES_CIUDAD[indiceCiudad];
    contenedor.appendChild(siguiente);
    requestAnimationFrame(() => siguiente.classList.add("visible"));
    if (actual) {
      actual.classList.remove("visible");
      setTimeout(() => actual.remove(), 1400);
    }
  }, 10000);
}

// --- Efecto de interferencia (transición estilo TV de tubo entre secciones) ---

let canvasRuidoTV = null; // canvas chico interno, escalado hacia arriba para look pixelado

function dibujarCuadroRuidoTV(canvas) {
  const ctx = canvas.getContext("2d");
  if (!canvasRuidoTV) {
    canvasRuidoTV = document.createElement("canvas");
    canvasRuidoTV.width = 160;
    canvasRuidoTV.height = 90;
  }
  const ctxRuido = canvasRuidoTV.getContext("2d");
  const imagen = ctxRuido.createImageData(canvasRuidoTV.width, canvasRuidoTV.height);
  for (let i = 0; i < imagen.data.length; i += 4) {
    const v = Math.random() * 255;
    imagen.data[i] = 0;
    imagen.data[i + 1] = v;
    imagen.data[i + 2] = v * 0.3;
    imagen.data[i + 3] = 255;
  }
  ctxRuido.putImageData(imagen, 0, 0);
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(canvasRuidoTV, 0, 0, canvas.width, canvas.height);
}

// Muestra estática de interferencia, cambia el contenido a la mitad (tapado
// por el ruido) y lo oculta al terminar. `cambiarContenido` corre una sola vez.
function reproducirTransicionTV(cambiarContenido) {
  const canvas = document.getElementById("rc-transicion");
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  canvas.classList.remove("oculto");

  const duracionMs = 380;
  const inicio = performance.now();
  let yaCambio = false;

  function cuadro(ahora) {
    const transcurrido = ahora - inicio;
    dibujarCuadroRuidoTV(canvas);
    if (!yaCambio && transcurrido >= duracionMs / 2) {
      yaCambio = true;
      cambiarContenido();
    }
    if (transcurrido < duracionMs) {
      requestAnimationFrame(cuadro);
    } else {
      canvas.classList.add("oculto");
    }
  }
  requestAnimationFrame(cuadro);
}

function pintarCarrousel() {
  const el = document.getElementById("carrousel");
  const marcas = [...MARCAS, ...MARCAS];
  el.innerHTML = marcas.map(
    (m) => `<span data-marca="${escapeHtml(m)}" tabindex="0" role="button">${escapeHtml(m)}</span>`
  ).join("");
  el.querySelectorAll("span").forEach((span) => {
    span.addEventListener("click", () => {
      filtroMarcaGlobal = span.dataset.marca;
      seccionActiva = null;
      subFiltroActivo = null;
      document.getElementById("input-busqueda").value = "";
      reproducirTransicionTV(actualizarVista);
    });
    span.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        span.click();
      }
    });
  });
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
      reproducirTransicionTV(actualizarVista);
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
      reproducirTransicionTV(actualizarVista);
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

  const enInicio = !seccionActiva && !filtroMarcaGlobal && termino === "";
  const enSubNav = !!seccionActiva && SECCIONES_CON_SUBNAV.has(seccionActiva) &&
    !subFiltroActivo && termino === "";

  categoriasEl.classList.toggle("oculto", !enInicio);
  subNavEl.classList.toggle("oculto", !enSubNav);
  volverBtn.classList.toggle("oculto", enInicio);

  detenerCarrouselCiudad();

  if (enInicio) {
    pintarCarrouselCiudad(productosEl);
    return;
  }

  if (enSubNav) {
    pintarSubNav(seccionActiva);
    productosEl.innerHTML = "";
    return;
  }

  let base;
  let mensajeVacioSinFiltro;
  if (filtroMarcaGlobal) {
    base = Object.values(SECCIONES_DATA).flat()
      .filter((p) => (p.marca || "Otras marcas") === filtroMarcaGlobal);
    mensajeVacioSinFiltro = `Todavía no hay productos de ${filtroMarcaGlobal} cargados.`;
  } else if (seccionActiva) {
    base = subFiltroActivo
      ? productosDeSubFiltro(seccionActiva, subFiltroActivo)
      : SECCIONES_DATA[seccionActiva] || []; // sección sin sub-nav (Gaming), o buscando antes de elegir
    mensajeVacioSinFiltro = "Todavía no hay productos cargados acá.";
  } else {
    base = Object.values(SECCIONES_DATA).flat(); // búsqueda global (sin marca ni sección)
    mensajeVacioSinFiltro = "Todavía no hay productos cargados acá.";
  }

  const productos = termino
    ? base.filter((p) => (p.nombre || "").toLowerCase().includes(termino))
    : base;

  const mensajeVacio = termino ? "Lo siento, pero no hay resultados :(" : mensajeVacioSinFiltro;

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
  } else if (seccionActiva) {
    seccionActiva = null;
  } else if (filtroMarcaGlobal) {
    filtroMarcaGlobal = null;
  }
  reproducirTransicionTV(actualizarVista);
}

function volverAPantallaPrincipal() {
  seccionActiva = null;
  subFiltroActivo = null;
  filtroMarcaGlobal = null;
  document.getElementById("input-busqueda").value = "";
  reproducirTransicionTV(actualizarVista);
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
  { texto: "La guerra. La guerra nunca cambia.", autor: "El Narrador", juego: "Fallout" },
  { texto: "¡Es peligroso ir solo! Toma esto.", autor: "Anciano", juego: "The Legend of Zelda" },
  { texto: "Quédate un rato y escucha.", autor: "Deckard Cain", juego: "Diablo II" },
  { texto: "El pastel es mentira.", autor: "GLaDOS", juego: "Portal" },
  { texto: "¡Termínalo!", autor: "Shao Kahn", juego: "Mortal Kombat" },
  { texto: "¡Oye! ¡Escucha!", autor: "Navi", juego: "The Legend of Zelda: Ocarina of Time" },
  { texto: "Un hombre elige, un esclavo obedece.", autor: "Andrew Ryan", juego: "BioShock" },
  { texto: "Despierta, samurái. Tenemos una ciudad que quemar.", autor: "Johnny Silverhand", juego: "Cyberpunk 2077" },
  { texto: "¡Haz un barrel roll!", autor: "Peppy Ainsworth", juego: "Star Fox 64" },
  { texto: "Yo era un aventurero como tú, hasta que recibí una flecha en la rodilla.", autor: "Guardia de Whiterun", juego: "The Elder Scrolls V: Skyrim" },
  { texto: "¡Alabado sea el sol!", autor: "Solaire de Astora", juego: "Dark Souls" },
  { texto: "¿Serías tan amable?", autor: "Andrew Ryan", juego: "BioShock" },
];

function pintarFrasePie() {
  const el = document.getElementById("pie-frase");
  if (!el) return;
  const horaBucket = Math.floor(Date.now() / (60 * 60 * 1000));
  const frase = FRASES_GAMING[horaBucket % FRASES_GAMING.length];
  el.textContent = `"${frase.texto}" -- ${frase.autor} (${frase.juego})`;
}

pintarFrasePie();
setInterval(pintarFrasePie, 60 * 60 * 1000);

// --- Carita animada de caracteres, junto al título ---

const CARAS_ANIMADAS = [":)", ":D", ":P", ":O", ":B", ":]", ":3", "xD", ":|"];
let indiceCara = 0;

function animarCara() {
  const el = document.getElementById("cara-animada");
  if (!el) return;
  el.classList.add("oculto-fade");
  setTimeout(() => {
    indiceCara = (indiceCara + 1) % CARAS_ANIMADAS.length;
    el.textContent = CARAS_ANIMADAS[indiceCara];
    el.classList.remove("oculto-fade");
  }, 220);
}

setInterval(animarCara, 1600);

// --- Fecha, hora, ciudad y temperatura del usuario, a la izquierda del carrito ---
// La ciudad y la temperatura corresponden a la ubicación real del visitante
// (pide permiso de geolocalización al navegador); si lo rechaza o no está
// disponible, se usa Córdoba Capital como respaldo.

const COORD_RESPALDO = { lat: -31.4201, lon: -64.1888 };
let temperaturaActual = null;
let ciudadActual = null;

function formatearFechaHora() {
  const ahora = new Date();
  const fecha = ahora.toLocaleDateString("es-AR");
  const hora = ahora.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
  return `${fecha} ${hora}`;
}

function pintarFechaHoraTemp() {
  const el = document.getElementById("fecha-hora-temp");
  if (!el) return;
  const partes = [formatearFechaHora()];
  if (ciudadActual) partes.push(ciudadActual);
  if (temperaturaActual !== null) partes.push(`${temperaturaActual}°C`);
  el.textContent = partes.join(" · ");
}

async function cargarClimaYCiudad(lat, lon) {
  try {
    const [climaR, ciudadR] = await Promise.all([
      fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m`),
      fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=es`),
    ]);
    if (climaR.ok) {
      const datosClima = await climaR.json();
      temperaturaActual = Math.round(datosClima.current.temperature_2m);
    }
    if (ciudadR.ok) {
      const datosCiudad = await ciudadR.json();
      ciudadActual = datosCiudad.locality || datosCiudad.city || null;
    }
  } catch {
    // se mantiene lo último cargado si algo falla
  }
  pintarFechaHoraTemp();
}

function iniciarUbicacionYClima() {
  if (!("geolocation" in navigator)) {
    cargarClimaYCiudad(COORD_RESPALDO.lat, COORD_RESPALDO.lon);
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (posicion) => cargarClimaYCiudad(posicion.coords.latitude, posicion.coords.longitude),
    () => cargarClimaYCiudad(COORD_RESPALDO.lat, COORD_RESPALDO.lon),
    { timeout: 8000 }
  );
}

pintarFechaHoraTemp();
setInterval(pintarFechaHoraTemp, 60 * 1000);
iniciarUbicacionYClima();
setInterval(iniciarUbicacionYClima, 15 * 60 * 1000);

pintarCarrousel();
renderCarrito();
cargarCatalogo();
