// --- Beep sutil estilo computadora vieja, en cada interacción con la web ---

let audioCtxInteraccion;
function beepInteraccion() {
  try {
    audioCtxInteraccion = audioCtxInteraccion
      || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtxInteraccion.state === "suspended") audioCtxInteraccion.resume();
    const osc = audioCtxInteraccion.createOscillator();
    const gain = audioCtxInteraccion.createGain();
    osc.type = "square";
    osc.frequency.value = 740;
    gain.gain.setValueAtTime(0.025, audioCtxInteraccion.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtxInteraccion.currentTime + 0.05);
    osc.connect(gain).connect(audioCtxInteraccion.destination);
    osc.start();
    osc.stop(audioCtxInteraccion.currentTime + 0.05);
  } catch {
    // Web Audio no disponible: seguimos sin sonido, no es crítico.
  }
}

document.addEventListener("click", (e) => {
  if (e.target.closest("button, a, [role='button']")) beepInteraccion();
});

const MARCAS = [
  "Apple", "Samsung", "Xiaomi", "Motorola", "Realme", "Oppo", "Honor",
  "Infinix", "Nokia", "PlayStation", "Nintendo", "JBL", "Logitech",
];

// Orden y etiquetas de los botones de categoría en la pantalla principal.
// "clave" es el nombre de sección tal cual lo devuelve /api/catalogo;
// "etiqueta" es lo que se muestra en el botón (más corto en el caso de accesorios).
const BUSQUEDA_MARCA_CLAVE = "BusquedaMarca";

const CATEGORIAS_BOTONES = [
  { clave: "Celulares", etiqueta: "Celulares" },
  { clave: "Tablets", etiqueta: "Tablets" },
  { clave: "Notebooks y Macbooks", etiqueta: "Notebooks y Macbooks" },
  { clave: "Gaming", etiqueta: "Gaming" },
  { clave: "Accesorios Celulares", etiqueta: "Accesorios" },
  { clave: BUSQUEDA_MARCA_CLAVE, etiqueta: "Búsqueda por Marca" },
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
let subFiltrosActivos = new Set(); // marcas (o "Notebooks"/"Macbooks") elegidas, acumulables
let filtroMarcaGlobal = null; // marca elegida desde el carrousel o "Búsqueda por Marca", busca en TODO el catálogo
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
  "ciudad/dique.png",
  "ciudad/lago-san-roque.png",
  "ciudad/puente-14-de-agosto.png",
  "ciudad/reserva-san-martin.png",
];
let indiceCiudad = Math.floor(Math.random() * IMAGENES_CIUDAD.length);

// Elige un índice al azar distinto del actual, para que nunca se repita la
// misma foto dos veces seguidas.
function siguienteIndiceCiudadAlAzar() {
  if (IMAGENES_CIUDAD.length <= 1) return 0;
  let candidato;
  do {
    candidato = Math.floor(Math.random() * IMAGENES_CIUDAD.length);
  } while (candidato === indiceCiudad);
  return candidato;
}
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
    indiceCiudad = siguienteIndiceCiudadAlAzar();
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

// --- Transición entre pantallas: deformación rápida tipo CRT, sin ruido ---
// Aplica un glitch corto (skew/escala/flicker de brillo) al contenido en vez
// de tapar toda la pantalla con estática; `cambiarContenido` corre una sola
// vez, a mitad del glitch, mientras la UI está distorsionada.
function reproducirTransicionTV(cambiarContenido) {
  const contenedor = document.querySelector(".fila-principal");
  if (!contenedor) {
    cambiarContenido();
    return;
  }
  contenedor.classList.remove("rc-deformando");
  // Forzar reflow para poder re-disparar la animación si ya estaba corriendo.
  void contenedor.offsetWidth;
  contenedor.classList.add("rc-deformando");
  setTimeout(cambiarContenido, 150);
  setTimeout(() => contenedor.classList.remove("rc-deformando"), 320);
}

function pintarCarrousel() {
  const el = document.getElementById("carrousel");
  const tanda = MARCAS.map(
    (m) => `<span data-marca="${escapeHtml(m)}" tabindex="0" role="button">${escapeHtml(m)}</span>`
  ).join("");
  el.innerHTML = `
    <div class="carrousel-tanda">${tanda}</div>
    <div class="carrousel-tanda">${tanda}</div>
  `;
  el.querySelectorAll("span").forEach((span) => {
    span.addEventListener("click", () => {
      filtroMarcaGlobal = span.dataset.marca;
      seccionActiva = null;
      subFiltrosActivos = new Set();
      document.getElementById("input-busqueda").value = "";
      pushEstadoNav();
      reproducirTransicionTV(actualizarVista);
    });
    span.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        span.click();
      }
    });
  });
  iniciarDesplazamientoCarrousel(el);
}

// Desplaza el carrousel de marcas a los saltos, en píxeles reales, en vez de
// una animación CSS por porcentaje: evita el corte/glitch al llegar al final
// de la primera tanda, porque el ancho de wrap se mide en píxeles exactos.
// El ancho se vuelve a medir en cada vuelta (no se cachea una sola vez), así
// un reflow tardío (p. ej. la fuente Share Tech Mono terminando de cargar)
// nunca deja desincronizado el punto de reinicio del loop.
function iniciarDesplazamientoCarrousel(el) {
  const primeraTanda = el.querySelector(".carrousel-tanda");
  let posicion = 0;
  let anchoTanda = 0;
  let intervalo = null;

  function medirAncho() {
    const estilo = getComputedStyle(el);
    anchoTanda = primeraTanda.getBoundingClientRect().width + parseFloat(estilo.gap || "48");
  }

  function paso() {
    posicion += 3;
    if (posicion >= anchoTanda) {
      posicion -= anchoTanda;
      medirAncho();
    }
    el.style.transform = `translateX(-${posicion}px)`;
  }

  function iniciar() {
    medirAncho();
    if (anchoTanda <= 0) return;
    if (intervalo) clearInterval(intervalo);
    intervalo = setInterval(paso, 60);
  }

  const listoParaMedir = document.fonts && document.fonts.ready
    ? document.fonts.ready
    : Promise.resolve();
  listoParaMedir.then(iniciar);

  window.addEventListener("resize", () => {
    posicion = 0;
    el.style.transform = "translateX(0)";
    iniciar();
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
      subFiltrosActivos = new Set();
      document.getElementById("input-busqueda").value = "";
      pushEstadoNav();
      reproducirTransicionTV(actualizarVista);
    });
  });
}

// Pantalla de "Búsqueda por Marca": lista todas las marcas presentes en
// TODO el catálogo (cualquier categoría); elegir una filtra el catálogo
// entero por esa marca, sin importar la sección.
function todasLasMarcasDelCatalogo() {
  const productos = Object.values(SECCIONES_DATA).flat();
  const presentes = new Set(productos.map((p) => p.marca || "Otras marcas"));
  const ordenadas = ORDEN_MARCAS.filter((m) => presentes.has(m));
  const resto = [...presentes].filter((m) => !ORDEN_MARCAS.includes(m)).sort();
  return [...ordenadas, ...resto];
}

function pintarSelectorMarcas(el) {
  const marcas = todasLasMarcasDelCatalogo();
  el.innerHTML = `<div class="selector-marcas">${marcas.map(
    (m) => `<button class="btn-categoria" data-marca="${escapeHtml(m)}" type="button">${escapeHtml(m)}</button>`
  ).join("")}</div>`;
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      filtroMarcaGlobal = btn.dataset.marca;
      seccionActiva = null;
      subFiltrosActivos = new Set();
      pushEstadoNav();
      reproducirTransicionTV(actualizarVista);
    });
  });
}

// Devuelve las opciones del sub-nav para la sección dada: "Todos" primero,
// después las marcas presentes en sus productos (o los 2 tipos fijos para
// Notebooks y Macbooks). Estos botones filtran la grilla, que ya muestra
// todo el catálogo de la sección apenas se entra.
function opcionesSubNav(seccion) {
  if (seccion === "Notebooks y Macbooks") {
    return ["Todos", "Notebooks", "Macbooks"];
  }
  const productos = SECCIONES_DATA[seccion] || [];
  const presentes = new Set(productos.map((p) => p.marca || "Otras marcas"));
  const ordenadas = ORDEN_MARCAS.filter((m) => presentes.has(m));
  const resto = [...presentes].filter((m) => !ORDEN_MARCAS.includes(m)).sort();
  return ["Todos", ...ordenadas, ...resto];
}

// Los botones de marca/tipo son acumulables: tocar "Todos" limpia la
// selección; tocar una marca la suma o la saca sin afectar a las demás.
function pintarSubNav(seccion) {
  const el = document.getElementById("sub-nav");
  const opciones = opcionesSubNav(seccion);
  el.innerHTML = opciones.map((o) => {
    const activo = o === "Todos" ? subFiltrosActivos.size === 0 : subFiltrosActivos.has(o);
    return `<button data-clave="${escapeHtml(o)}" class="btn-categoria ${activo ? "activo" : ""}" type="button">${escapeHtml(o)}</button>`;
  }).join("");
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      const clave = btn.dataset.clave;
      if (clave === "Todos") {
        subFiltrosActivos = new Set();
      } else if (subFiltrosActivos.has(clave)) {
        subFiltrosActivos.delete(clave);
      } else {
        subFiltrosActivos.add(clave);
      }
      pushEstadoNav();
      reproducirTransicionTV(actualizarVista);
    });
  });
}

// Productos de una sección que corresponden a los sub-filtros elegidos
// (una o varias marcas, o tipo Notebook/Mac). Sin selección, no filtra nada.
function productosDeSubFiltro(seccion, subFiltros) {
  const productos = SECCIONES_DATA[seccion] || [];
  if (subFiltros.size === 0) return productos;
  if (seccion === "Notebooks y Macbooks") {
    const categoriasBuscadas = new Set(
      [...subFiltros].map((f) => (f === "Notebooks" ? "Notebook" : "Mac"))
    );
    return productos.filter((p) => categoriasBuscadas.has(p.categoria));
  }
  return productos.filter((p) => subFiltros.has(p.marca || "Otras marcas"));
}

function formatearPesos(valor) {
  return valor === undefined || valor === null ? "-" : Number(valor).toLocaleString("es-AR");
}

function tarjetaProducto(p) {
  const tieneColores = Array.isArray(p.colores) && p.colores.length > 0;
  const colores = tieneColores
    ? `<div class="selector-colores">
        <strong>Colores:</strong>
        <div class="botones-color">
          ${p.colores.map((c) => `<button type="button" class="btn-color" data-color="${escapeHtml(c)}">${escapeHtml(c)}</button>`).join("")}
        </div>
      </div>`
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
      <button class="btn-agregar" data-nombre="${escapeHtml(p.nombre)}" type="button" ${tieneColores ? "disabled" : ""}>Agregar al carrito</button>
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
  el.querySelectorAll(".card").forEach((card) => {
    const btnAgregar = card.querySelector(".btn-agregar");
    const botonesColor = card.querySelectorAll(".btn-color");
    botonesColor.forEach((btnColor) => {
      btnColor.addEventListener("click", () => {
        botonesColor.forEach((b) => b.classList.remove("seleccionado"));
        btnColor.classList.add("seleccionado");
        btnAgregar.dataset.color = btnColor.dataset.color;
        btnAgregar.disabled = false;
      });
    });
    btnAgregar.addEventListener("click", () => {
      const producto = productos.find((p) => p.nombre === btnAgregar.dataset.nombre);
      if (producto) agregarAlCarrito(producto, btnAgregar.dataset.color || null);
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
  const mostrarSubNav = !!seccionActiva && SECCIONES_CON_SUBNAV.has(seccionActiva) &&
    termino === "";

  categoriasEl.classList.toggle("oculto", !enInicio);
  subNavEl.classList.toggle("oculto", !mostrarSubNav);
  volverBtn.classList.toggle("oculto", enInicio);

  detenerCarrouselCiudad();

  if (enInicio) {
    pintarCarrouselCiudad(productosEl);
    return;
  }

  if (mostrarSubNav) {
    pintarSubNav(seccionActiva);
  }

  if (seccionActiva === BUSQUEDA_MARCA_CLAVE && termino === "") {
    pintarSelectorMarcas(productosEl);
    return;
  }

  let base;
  let mensajeVacioSinFiltro;
  if (filtroMarcaGlobal) {
    base = Object.values(SECCIONES_DATA).flat()
      .filter((p) => (p.marca || "Otras marcas") === filtroMarcaGlobal);
    mensajeVacioSinFiltro = `Todavía no hay productos de ${filtroMarcaGlobal} cargados.`;
  } else if (seccionActiva && seccionActiva !== BUSQUEDA_MARCA_CLAVE) {
    base = productosDeSubFiltro(seccionActiva, subFiltrosActivos); // sección sin sub-nav (Gaming) devuelve todo igual
    mensajeVacioSinFiltro = "Todavía no hay productos cargados acá.";
  } else {
    base = Object.values(SECCIONES_DATA).flat(); // búsqueda global, o buscando dentro de "Búsqueda por Marca"
    mensajeVacioSinFiltro = "Todavía no hay productos cargados acá.";
  }

  const productos = termino
    ? base.filter((p) => (p.nombre || "").toLowerCase().includes(termino))
    : base;

  const mensajeVacio = termino ? "Lo siento, pero no hay resultados :(" : mensajeVacioSinFiltro;

  pintarGrilla(productosEl, productos, mensajeVacio);
}

// --- Integración con el botón/gesto de back nativo (Android e historial del navegador) ---
// Cada vez que el usuario entra un nivel más adentro (sección, sub-nav, marca
// del carrousel) se apila una entrada de historial. El botón "Volver" y el
// back nativo terminan en el mismo lugar: retrocederPasoDesdeHistorial().
let profundidadHistorial = 0;

function pushEstadoNav() {
  profundidadHistorial++;
  history.pushState({ ttraProfundidad: profundidadHistorial }, "", "");
}

// Retrocede un paso a la vez: primero limpia la búsqueda, después el
// sub-filtro (marca/tipo), y por último vuelve a la pantalla principal.
function retrocederPasoDesdeHistorial() {
  const input = document.getElementById("input-busqueda");
  if (input.value.trim() !== "") {
    input.value = "";
  } else if (subFiltrosActivos.size > 0) {
    subFiltrosActivos = new Set();
  } else if (seccionActiva) {
    seccionActiva = null;
  } else if (filtroMarcaGlobal) {
    filtroMarcaGlobal = null;
  }
  reproducirTransicionTV(actualizarVista);
}

// El botón "Volver" dispara el back del navegador (para mantener el
// historial sincronizado); popstate es quien realmente aplica el cambio.
function volverUnPaso() {
  if (profundidadHistorial > 0) {
    history.back();
  } else {
    retrocederPasoDesdeHistorial();
  }
}

window.addEventListener("popstate", () => {
  if (profundidadHistorial > 0) profundidadHistorial--;
  retrocederPasoDesdeHistorial();
});

function volverAPantallaPrincipal() {
  seccionActiva = null;
  subFiltrosActivos = new Set();
  filtroMarcaGlobal = null;
  profundidadHistorial = 0;
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

function mismoItemCarrito(it, nombre, color) {
  return it.nombre === nombre && (it.color || null) === (color || null);
}

function agregarAlCarrito(producto, color) {
  const carrito = cargarCarrito();
  const existente = carrito.find((it) => mismoItemCarrito(it, producto.nombre, color));
  if (existente) {
    existente.cantidad += 1;
  } else {
    carrito.push({
      nombre: producto.nombre,
      color: color || null,
      usd: producto.usd,
      pesos: producto.pesos,
      transferencia: producto.transferencia,
      cantidad: 1,
    });
  }
  guardarCarrito(carrito);
  abrirCarrito();
}

function cambiarCantidad(nombre, color, delta) {
  const carrito = cargarCarrito();
  const item = carrito.find((it) => mismoItemCarrito(it, nombre, color));
  if (!item) return;
  item.cantidad += delta;
  const nuevo = item.cantidad > 0 ? carrito : carrito.filter((it) => !mismoItemCarrito(it, nombre, color));
  guardarCarrito(nuevo);
}

function quitarDelCarrito(nombre, color) {
  guardarCarrito(cargarCarrito().filter((it) => !mismoItemCarrito(it, nombre, color)));
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
  const colorTexto = it.color ? ` (${escapeHtml(it.color)})` : "";
  const colorAttr = escapeHtml(it.color || "");
  return `
    <div class="item-carrito">
      <p class="item-nombre">${escapeHtml(it.nombre)}${colorTexto}</p>
      <div class="item-controles">
        <button class="btn-menos" data-nombre="${escapeHtml(it.nombre)}" data-color="${colorAttr}" type="button">-</button>
        <span>${it.cantidad}</span>
        <button class="btn-mas" data-nombre="${escapeHtml(it.nombre)}" data-color="${colorAttr}" type="button">+</button>
        <button class="btn-quitar" data-nombre="${escapeHtml(it.nombre)}" data-color="${colorAttr}" type="button">Quitar</button>
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
    btn.addEventListener("click", () => cambiarCantidad(btn.dataset.nombre, btn.dataset.color || null, -1));
  });
  el.querySelectorAll(".btn-mas").forEach((btn) => {
    btn.addEventListener("click", () => cambiarCantidad(btn.dataset.nombre, btn.dataset.color || null, 1));
  });
  el.querySelectorAll(".btn-quitar").forEach((btn) => {
    btn.addEventListener("click", () => quitarDelCarrito(btn.dataset.nombre, btn.dataset.color || null));
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
  const lineas = carrito.map((it) => {
    const color = it.color ? ` (${it.color})` : "";
    return `- ${it.nombre}${color} x${it.cantidad} — U$D ${(it.usd || 0) * it.cantidad}`;
  });
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
  vaciarCarrito();
  cerrarCarrito();
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

const CARAS_ANIMADAS = [":D", ":O", ":I"];
let indiceCara = 0;
let capaCaraVisible = "a"; // alterna entre las dos capas superpuestas para el crossfade

function animarCara() {
  const capaActual = document.getElementById(`cara-animada-${capaCaraVisible}`);
  const siguienteLetra = capaCaraVisible === "a" ? "b" : "a";
  const capaSiguiente = document.getElementById(`cara-animada-${siguienteLetra}`);
  if (!capaActual || !capaSiguiente) return;
  indiceCara = (indiceCara + 1) % CARAS_ANIMADAS.length;
  capaSiguiente.textContent = CARAS_ANIMADAS[indiceCara];
  capaSiguiente.classList.add("visible");
  capaActual.classList.remove("visible");
  capaCaraVisible = siguienteLetra;
}

setInterval(animarCara, 380);

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
  const hora = ahora.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
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

// Traduce el código de clima de Open-Meteo a una descripción corta en castellano.
function descripcionClima(codigo) {
  if (codigo === 0) return "cielo despejado";
  if ([1, 2].includes(codigo)) return "parcialmente nublado";
  if (codigo === 3) return "nublado";
  if ([45, 48].includes(codigo)) return "con niebla";
  if ([51, 53, 55, 56, 57].includes(codigo)) return "con llovizna";
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(codigo)) return "con lluvia";
  if ([71, 73, 75, 77, 85, 86].includes(codigo)) return "con nieve";
  if ([95, 96, 99].includes(codigo)) return "con tormenta";
  return "variable";
}

async function cargarClimaYCiudad(lat, lon) {
  try {
    const [climaR, ciudadR, pronosticoR] = await Promise.all([
      fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=temperature_2m`),
      fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=es`),
      fetch(`https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto`),
    ]);
    if (climaR.ok) {
      const datosClima = await climaR.json();
      temperaturaActual = Math.round(datosClima.current.temperature_2m);
    }
    if (ciudadR.ok) {
      const datosCiudad = await ciudadR.json();
      ciudadActual = datosCiudad.locality || datosCiudad.city || null;
    }
    if (pronosticoR.ok) {
      const datosPronostico = await pronosticoR.json();
      const max = Math.round(datosPronostico.daily.temperature_2m_max[1]);
      const min = Math.round(datosPronostico.daily.temperature_2m_min[1]);
      const desc = descripcionClima(datosPronostico.daily.weathercode[1]);
      pronosticoManana = `Mañana en ${ciudadActual || "Córdoba"}: máxima de ${max}°, mínima de ${min}°, ${desc}`;
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
setInterval(pintarFechaHoraTemp, 1000);

// --- Personaje narrador de noticias (política/finanzas), tipo noticiero ---

let titularesNoticias = [];
let indiceNoticia = 0;
let cotizacionActual = null;
let cicloNoticiero = 0; // cuenta narraciones para intercalar cotización/clima cada tanto

async function cargarNoticias() {
  try {
    const r = await fetch("/api/noticias");
    if (!r.ok) return;
    const datos = await r.json();
    if (Array.isArray(datos.titulares) && datos.titulares.length > 0) {
      titularesNoticias = datos.titulares;
    }
  } catch {
    // si falla, se sigue narrando con lo último cargado
  }
}

async function cargarCotizacion() {
  try {
    const r = await fetch("/api/cotizacion");
    if (!r.ok) return;
    const datos = await r.json();
    if (typeof datos.valor === "number") cotizacionActual = datos.valor;
  } catch {
    // se mantiene lo último cargado si algo falla
  }
}

// Cada 4ta narración se reemplaza por una frase especial (cotización o
// clima), alternando entre las dos, en vez de un titular de noticias real.
function siguienteFraseEspecial() {
  const usarClima = cicloNoticiero % 8 === 7;
  if (usarClima && pronosticoManana) return pronosticoManana;
  if (cotizacionActual !== null) {
    return `La cotización actual del dólar en Córdoba es de $${cotizacionActual}`;
  }
  return null;
}

function escribirTexto(el, texto, velocidadMs, alTerminar) {
  el.textContent = "";
  el.style.transform = "translateX(0)";
  el.classList.remove("marquesina");
  let i = 0;
  const intervalo = setInterval(() => {
    i++;
    el.textContent = texto.slice(0, i);
    if (i >= texto.length) {
      clearInterval(intervalo);
      if (alTerminar) pausarYSeguir(el, alTerminar);
    }
  }, velocidadMs);
}

// Si el titular no entra en el ancho disponible, lo desliza como marquesina
// (en vez de dejarlo cortado con "..."), sin nunca forzar el ancho del header.
function pausarYSeguir(el, alTerminar) {
  setTimeout(() => {
    const desborde = el.scrollWidth - el.clientWidth;
    if (desborde <= 0) {
      setTimeout(alTerminar, 2000);
      return;
    }
    el.classList.add("marquesina");
    const duracionSeg = Math.max(2, desborde / 60);
    el.style.transition = `transform ${duracionSeg}s linear`;
    requestAnimationFrame(() => {
      el.style.transform = `translateX(-${desborde}px)`;
    });
    setTimeout(() => {
      el.style.transition = "none";
      el.style.transform = "translateX(0)";
      el.classList.remove("marquesina");
      setTimeout(alTerminar, 900);
    }, duracionSeg * 1000 + 900);
  }, 300);
}

function narrarSiguienteNoticia() {
  const el = document.getElementById("noticiero-texto");
  if (!el) return;
  cicloNoticiero++;
  const fraseEspecial = cicloNoticiero % 4 === 0 ? siguienteFraseEspecial() : null;
  let texto;
  if (fraseEspecial) {
    texto = `- ${fraseEspecial}`;
  } else {
    if (titularesNoticias.length === 0) return;
    const noticia = titularesNoticias[indiceNoticia % titularesNoticias.length];
    indiceNoticia++;
    texto = noticia.fuente ? `- ${noticia.titulo} (${noticia.fuente})` : `- ${noticia.titulo}`;
  }
  escribirTexto(el, texto, 35, narrarSiguienteNoticia);
}

async function iniciarNoticiero() {
  await Promise.all([cargarNoticias(), cargarCotizacion()]);
  narrarSiguienteNoticia();
  setInterval(cargarNoticias, 10 * 60 * 1000);
  setInterval(cargarCotizacion, 10 * 60 * 1000);
}

iniciarNoticiero();
iniciarUbicacionYClima();
setInterval(iniciarUbicacionYClima, 15 * 60 * 1000);

pintarCarrousel();
renderCarrito();
cargarCatalogo();
