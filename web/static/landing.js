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
let cotizacionActual = null; // U$D actual, usado en el reloj del header y en el narrador de noticias
let pronosticoManana = null; // texto del pronóstico del día siguiente, para el narrador
let pronosticoConsejo = null; // consejo práctico según ese pronóstico (paraguas, abrigo, etc.)
let seccionActiva = null; // clave de sección elegida en la pantalla principal, o null
let subFiltrosActivos = new Set(); // marcas (o "Notebooks"/"Macbooks") elegidas, acumulables
let filtroMarcaGlobal = null; // marca elegida desde el carrousel o "Búsqueda por Marca", busca en TODO el catálogo
let modoVista = "cards"; // "cards" | "lista"

// Fotos decorativas de la ciudad, solo visibles en la pantalla principal.
// Cada archivo se muestra dentro de una "tarjeta" tipo terminal (ver
// tarjetaLugarHtml): el nombre del punto de interés sale del nombre de
// archivo, y los datos descriptivos salen de DATOS_LUGARES (misma clave,
// sin extensión). Agregar una foto nueva = agregar el archivo acá y su
// entrada en DATOS_LUGARES.
const IMAGENES_CIUDAD = [
  "ciudad/catedral.jpg",
  "ciudad/plaza-san-martin.jpg",
  "ciudad/plaza-colon.jpg",
  "ciudad/arco.jpeg",
  "ciudad/dique-san-roque.jpg",
  "ciudad/paseo-del-buen-pastor.jpeg",
  "ciudad/patio-olmos.jpeg",
  "ciudad/puente-cosquin.jpg",
  "ciudad/teatro-san-martin.jpg",
];

// Datos históricos/descriptivos por punto de interés, con tono de terminal
// retro. La clave es el nombre de archivo sin extensión, en minúsculas.
const DATOS_LUGARES = {
  catedral: {
    ubicacion: "CÓRDOBA CAPITAL",
    construccion: "1582 — 1758",
    estilo: "RENACENTISTA / BARROCO",
    coordenadas: "31°25'18\"S 64°11'42\"O",
    estado: "ACTIVA",
    importancia: "PATRIMONIO UNESCO (2000)",
    log: "LOG DE ARCHIVO RECUPERADO: obra iniciada en 1582, con más de siglo y medio de demoras y reconstrucciones antes de su finalización en 1758. Integra la Manzana Jesuítica, Patrimonio de la Humanidad. Estructura verificada: estable pese a más de 400 años de exposición.",
  },
  "plaza-san-martin": {
    ubicacion: "CENTRO HISTÓRICO",
    construccion: "1573 — FUNDACIONAL",
    estilo: "PLAZA FUNDACIONAL COLONIAL",
    coordenadas: "31°25'S 64°11'O (APROX.)",
    estado: "ACTIVA",
    importancia: "NÚCLEO FUNDACIONAL DE LA CIUDAD",
    log: "LOG DE ARCHIVO: plaza mayor trazada junto con la fundación de la ciudad en 1573. Rodeada por el Cabildo y la Catedral, sigue siendo el centro simbólico del casco histórico, 450 años después.",
  },
  "plaza-colon": {
    ubicacion: "NUEVA CÓRDOBA",
    construccion: "SIGLO XIX (FUENTE)",
    estilo: "PLAZA URBANA / FUENTE ORNAMENTAL",
    coordenadas: "31°25'S 64°11'O (APROX.)",
    estado: "ACTIVA",
    importancia: "PATRIMONIO URBANO",
    log: "LOG DE ARCHIVO: uno de los pulmones verdes históricos de Nueva Córdoba, organizado en torno a una fuente ornamental de estilo francés. Punto de encuentro tradicional del barrio universitario desde hace más de un siglo.",
  },
  arco: {
    ubicacion: "AV. SABATTINI",
    construccion: "1973",
    estilo: "CONMEMORATIVO / MAMPOSTERÍA DE PIEDRA",
    coordenadas: "31°22'S 64°11'O (APROX.)",
    estado: "ACTIVA",
    importancia: "MONUMENTO CONMEMORATIVO",
    log: "LOG DE ARCHIVO: erigido para el cuarto centenario de la fundación de la ciudad (1573-1973). Sus dos torres gemelas flanquean el ingreso norte, a modo de puerta simbólica hacia el casco urbano.",
  },
  "dique-san-roque": {
    ubicacion: "VILLA CARLOS PAZ / VALLE DE PUNILLA",
    construccion: "FINES S. XIX — RECONSTRUIDO S. XX",
    estilo: "OBRA HIDRÁULICA",
    coordenadas: "31°22'S 64°28'O (APROX.)",
    estado: "ACTIVA",
    importancia: "PRIMER GRAN EMBALSE DE ARGENTINA",
    log: "LOG DE ARCHIVO: uno de los primeros grandes diques de contención de Sudamérica. Su lago artificial abastece de agua a la ciudad y es hoy uno de los espejos de agua más visitados de las sierras cordobesas.",
  },
  "paseo-del-buen-pastor": {
    ubicacion: "NUEVA CÓRDOBA",
    construccion: "EX CONVENTO/CÁRCEL S. XIX — RECICLADO 2007",
    estilo: "ECLÉCTICO / RECICLAJE URBANO",
    coordenadas: "31°25'S 64°11'O (APROX.)",
    estado: "ACTIVA",
    importancia: "CENTRO CULTURAL",
    log: "LOG DE ARCHIVO: funcionó como convento y luego como cárcel de mujeres durante buena parte del siglo XX. Reconvertido en centro cultural y paseo comercial, conserva su torre-reloj como seña de identidad.",
  },
  "patio-olmos": {
    ubicacion: "NUEVA CÓRDOBA",
    construccion: "ANTIGUA RESIDENCIA S. XX — SHOPPING DESDE 1997",
    estilo: "ECLÉCTICO / RECICLAJE URBANO",
    coordenadas: "31°24'S 64°11'O (APROX.)",
    estado: "ACTIVA",
    importancia: "CENTRO COMERCIAL HISTÓRICO",
    log: "LOG DE ARCHIVO: antigua residencia reconvertida en una de las primeras grandes galerías comerciales de la ciudad. Su fachada original se mantiene integrada a la estructura moderna del shopping.",
  },
  "puente-cosquin": {
    ubicacion: "VALLE DE PUNILLA",
    construccion: "SIGLO XX",
    estilo: "PUENTE DE HORMIGÓN EN ARCO",
    coordenadas: "31°15'S 64°28'O (APROX.)",
    estado: "ACTIVA",
    importancia: "CONEXIÓN VIAL REGIONAL",
    log: "LOG DE ARCHIVO: cruce elevado sobre el espejo de agua del Valle de Punilla, en la ruta hacia Cosquín. Punto panorámico frecuente para quienes recorren las sierras.",
  },
  "teatro-san-martin": {
    ubicacion: "CENTRO HISTÓRICO",
    construccion: "1891",
    estilo: "NEOCLÁSICO / ITALIANIZANTE",
    coordenadas: "31°25'S 64°11'O (APROX.)",
    estado: "ACTIVA",
    importancia: "TEATRO HISTÓRICO PROVINCIAL",
    log: "LOG DE ARCHIVO: inaugurado en 1891, es uno de los teatros más antiguos en actividad de la provincia. Sede habitual de la programación oficial de artes escénicas de Córdoba.",
  },
};

// Se usa si se agrega una foto nueva antes de cargar sus datos reales.
const DATOS_LUGAR_DEFAULT = {
  ubicacion: "CÓRDOBA CAPITAL",
  construccion: "EN RELEVAMIENTO",
  estilo: "EN RELEVAMIENTO",
  coordenadas: "PENDIENTE DE TRIANGULACIÓN",
  estado: "ARCHIVO INCOMPLETO",
  importancia: "SIN CLASIFICAR",
  log: "LOG DE ARCHIVO PARCIAL: los datos de este punto de interés todavía no fueron cargados al sistema. Reintentando sincronización...",
};

function claveDesdeArchivo(src) {
  return src.split("/").pop().replace(/\.[a-z0-9]+$/i, "").toLowerCase();
}

function nombreDesdeArchivo(src) {
  return claveDesdeArchivo(src).replace(/[-_]/g, " ").toUpperCase();
}

function tarjetaLugarHtml(src) {
  const datos = DATOS_LUGARES[claveDesdeArchivo(src)] || DATOS_LUGAR_DEFAULT;
  const nombre = nombreDesdeArchivo(src);
  return `
    <div class="pipboy">
      <div class="pipboy-datos">
        <div class="pipboy-marca">THE TECH ROOM ARG</div>
        <div class="pipboy-sub">SISTEMA DE EXPLORACIÓN // TTRA-01</div>
        <div class="pipboy-ubicacion">&gt; UBICACIÓN: ${escapeHtml(datos.ubicacion)}</div>
        <div class="pipboy-etiqueta">PUNTO DE INTERÉS</div>
        <div class="pipboy-nombre">${escapeHtml(nombre)}</div>
        <hr class="pipboy-linea">
        <div class="pipboy-campos">
          <div><b>CONSTRUCCIÓN:</b> ${escapeHtml(datos.construccion)}</div>
          <div><b>ESTILO:</b> ${escapeHtml(datos.estilo)}</div>
          <div><b>COORDENADAS:</b> ${escapeHtml(datos.coordenadas)}</div>
          <div><b>ESTADO:</b> ${escapeHtml(datos.estado)}</div>
          <div><b>IMPORTANCIA:</b> ${escapeHtml(datos.importancia)}</div>
        </div>
        <hr class="pipboy-linea">
        <div class="pipboy-log">${escapeHtml(datos.log)}</div>
        <div class="pipboy-globo-wrap">
          <div class="pipboy-globo"></div>
          <div class="pipboy-globo-texto">TRIANGULANDO<br>COORDENADAS...</div>
        </div>
        <div class="pipboy-pie">
          <span class="pipboy-frase">TRANSMISIÓN ESTABLE // SEÑAL 98% // ARCHIVO TTRA-01<span class="rc-cursor">_</span></span>
        </div>
      </div>
      <div class="pipboy-imagen-wrap">
        <img src="${src}" alt="${escapeHtml(nombre)}">
        <span class="pipboy-esquina tl"></span>
        <span class="pipboy-esquina tr"></span>
        <span class="pipboy-esquina bl"></span>
        <span class="pipboy-esquina br"></span>
      </div>
    </div>
  `;
}

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

function pintarPuntosCiudad(el) {
  const wrap = el.querySelector(".carrousel-ciudad-puntos");
  if (!wrap) return;
  wrap.innerHTML = IMAGENES_CIUDAD.map((_, i) =>
    `<button type="button" class="punto-ciudad ${i === indiceCiudad ? "activo" : ""}" data-indice="${i}" aria-label="Foto ${i + 1}"></button>`
  ).join("");
  wrap.querySelectorAll(".punto-ciudad").forEach((btn) => {
    btn.addEventListener("click", () => irAFotoCiudad(el, Number(btn.dataset.indice)));
  });
}

// Cambia a una foto puntual (por click en los puntos) y reinicia el
// temporizador de 20s, para no cortar la navegación manual del usuario.
function irAFotoCiudad(el, indice) {
  if (indice === indiceCiudad) return;
  indiceCiudad = indice;
  mostrarFotoCiudad(el);
  detenerCarrouselCiudad();
  intervaloCiudad = setInterval(() => avanzarFotoCiudadAlAzar(el), 20000);
}

function avanzarFotoCiudadAlAzar(el) {
  indiceCiudad = siguienteIndiceCiudadAlAzar();
  mostrarFotoCiudad(el);
}

// Crossfade a la foto en `indiceCiudad`, con un glitch de interferencia
// sutil en la tarjeta nueva (solo ella, no la pantalla completa).
function mostrarFotoCiudad(el) {
  const contenedor = el.querySelector(".carrousel-ciudad");
  if (!contenedor) return;
  const actual = contenedor.querySelector(".carrousel-ciudad-tarjeta.visible");
  const siguiente = document.createElement("div");
  siguiente.className = "carrousel-ciudad-tarjeta pipboy-interferencia";
  siguiente.innerHTML = tarjetaLugarHtml(IMAGENES_CIUDAD[indiceCiudad]);
  contenedor.appendChild(siguiente);
  requestAnimationFrame(() => siguiente.classList.add("visible"));
  if (actual) {
    actual.classList.remove("visible");
    setTimeout(() => actual.remove(), 1400);
  }
  pintarPuntosCiudad(el);
}

function pintarCarrouselCiudad(el) {
  if (IMAGENES_CIUDAD.length === 0) {
    el.innerHTML = "";
    return;
  }
  el.innerHTML = `
    <div class="carrousel-ciudad-wrap">
      <div class="carrousel-ciudad">
        <div class="carrousel-ciudad-tarjeta visible">${tarjetaLugarHtml(IMAGENES_CIUDAD[indiceCiudad])}</div>
      </div>
      <div class="carrousel-ciudad-puntos"></div>
    </div>
  `;
  pintarPuntosCiudad(el);
  if (IMAGENES_CIUDAD.length <= 1) return;
  intervaloCiudad = setInterval(() => avanzarFotoCiudadAlAzar(el), 20000);
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

// Descuento por cantidad, calculado como un ítem aparte (no se resta del
// precio de cada producto): más de 5 unidades en total, U$D 7.5 por unidad;
// más de 1 unidad, U$D 5 por unidad; 1 sola unidad, sin descuento.
function descuentoPorUnidad(cantidadTotal) {
  if (cantidadTotal > 5) return 7.5;
  if (cantidadTotal > 1) return 5;
  return 0;
}

function calcularDescuento(carrito) {
  const cantidadTotal = carrito.reduce((n, it) => n + it.cantidad, 0);
  const porUnidad = descuentoPorUnidad(cantidadTotal);
  if (porUnidad === 0) return null;
  const subtotal = totales(carrito);
  if (subtotal.usd <= 0) return null;
  const usd = porUnidad * cantidadTotal;
  const pesos = Math.round(usd * (subtotal.pesos / subtotal.usd));
  const transferencia = Math.round(usd * (subtotal.transferencia / subtotal.usd));
  return { cantidadTotal, porUnidad, usd, pesos, transferencia };
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

function itemDescuentoHtml(descuento) {
  return `
    <div class="item-carrito item-descuento">
      <p class="item-nombre">🎉 Descuento por ${descuento.cantidadTotal} unidades (U$D ${descuento.porUnidad} c/u)</p>
      <p class="item-descuento-valor">
        -U$D ${descuento.usd} · -$ ${formatearPesos(descuento.pesos)} contado · -$ ${formatearPesos(descuento.transferencia)} transferencia
      </p>
    </div>
  `;
}

function renderCarrito() {
  const carrito = cargarCarrito();
  const cantidadTotal = carrito.reduce((n, it) => n + it.cantidad, 0);
  document.getElementById("carrito-contador").textContent = cantidadTotal;

  const descuento = calcularDescuento(carrito);
  const el = document.getElementById("items-carrito");
  el.innerHTML = carrito.length === 0
    ? '<p class="mensaje-vacio">Tu carrito está vacío.</p>'
    : carrito.map(itemCarritoHtml).join("") + (descuento ? itemDescuentoHtml(descuento) : "");

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
  const totalEl = document.getElementById("total-carrito");
  if (carrito.length === 0) {
    totalEl.textContent = "";
  } else if (descuento) {
    totalEl.textContent =
      `Total: U$D ${t.usd - descuento.usd} · $ ${formatearPesos(t.pesos - descuento.pesos)} contado · ` +
      `$ ${formatearPesos(t.transferencia - descuento.transferencia)} transferencia`;
  } else {
    totalEl.textContent = `Total: U$D ${t.usd} · $ ${formatearPesos(t.pesos)} contado · $ ${formatearPesos(t.transferencia)} transferencia`;
  }
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
  const descuento = calcularDescuento(carrito);
  if (descuento) {
    lineas.push(`- 🎉 Descuento por ${descuento.cantidadTotal} unidades — -U$D ${descuento.usd}`);
  }
  const t = totales(carrito);
  const totalUsd = descuento ? t.usd - descuento.usd : t.usd;
  const totalPesos = descuento ? t.pesos - descuento.pesos : t.pesos;
  const totalTransferencia = descuento ? t.transferencia - descuento.transferencia : t.transferencia;
  const total = `Total: U$D ${totalUsd} · $ ${formatearPesos(totalPesos)} contado · $ ${formatearPesos(totalTransferencia)} transferencia`;
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
  const elFechaHora = document.getElementById("fecha-hora");
  const elCiudadTemp = document.getElementById("ciudad-temp");
  const elDolar = document.getElementById("dolar-linea");
  if (!elFechaHora || !elCiudadTemp || !elDolar) return;
  elFechaHora.textContent = formatearFechaHora();
  const partesCiudadTemp = [];
  if (ciudadActual) partesCiudadTemp.push(ciudadActual);
  if (temperaturaActual !== null) partesCiudadTemp.push(`${temperaturaActual}°C`);
  elCiudadTemp.textContent = partesCiudadTemp.join(" · ");
  elDolar.textContent = cotizacionActual !== null ? `Dólar: $${cotizacionActual}` : "";
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

// Consejo práctico según el pronóstico del día siguiente.
function consejoClima(codigo, min, max) {
  if ([71, 73, 75, 77, 85, 86].includes(codigo)) return "🥶 Abrigate bien, puede nevar";
  if ([51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99].includes(codigo)) {
    return "🌂 Llevá paraguas, puede llover";
  }
  if (min <= 8) return "🧥 Abrigate, va a hacer frío";
  if (max >= 30) return "🥵 Usá ropa liviana, va a hacer calor";
  return "🙂 Buen día para salir";
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
      const codigo = datosPronostico.daily.weathercode[1];
      const desc = descripcionClima(codigo);
      pronosticoManana = `Mañana en ${ciudadActual || "Córdoba"}: máxima de ${max}°, mínima de ${min}°, ${desc}`;
      pronosticoConsejo = consejoClima(codigo, min, max);
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
// clima con su consejo), alternando entre las dos, en vez de una noticia real.
function siguienteFraseEspecial() {
  const usarClima = cicloNoticiero % 8 === 7;
  if (usarClima && pronosticoManana) {
    return { titulo: pronosticoManana, descripcion: pronosticoConsejo };
  }
  if (cotizacionActual !== null) {
    return { titulo: `La cotización actual del dólar en Córdoba es de $${cotizacionActual}`, descripcion: null };
  }
  return null;
}

// Título (línea 1, en negrita) + descripción opcional (línea 2). Entra desde
// abajo del recuadro y sube en crawl continuo, estilo Star Wars, hasta salir
// por completo arriba — siempre, tanto para noticias reales como para las
// frases especiales (cotización/clima).
function mostrarConCrawl(el, titulo, descripcion, link, alTerminar) {
  if (link) {
    el.href = link;
    el.classList.add("clickeable");
  } else {
    el.removeAttribute("href");
    el.classList.remove("clickeable");
  }
  el.innerHTML = `<strong>${escapeHtml(titulo)}</strong>${descripcion ? `<br>${escapeHtml(descripcion)}` : ""}`;
  el.style.transition = "none";

  const contenedor = el.parentElement;
  const distanciaTotal = contenedor.clientHeight + el.scrollHeight;

  // Movimiento a saltos de píxeles (no transición suave de CSS), igual estética
  // retro que el carrousel de marcas; ~25px/seg, con un piso de 6s de duración
  // para que las noticias cortas también se puedan leer con calma.
  const intervaloMs = 60;
  const pxPorTickBase = 1.5;
  const pasosMinimos = 100;
  const totalPasos = Math.max(pasosMinimos, Math.ceil(distanciaTotal / pxPorTickBase));
  const pxPorTick = distanciaTotal / totalPasos;

  let posicion = contenedor.clientHeight;
  el.style.transform = `translateY(${posicion}px)`;

  requestAnimationFrame(() => {
    const intervalo = setInterval(() => {
      posicion -= pxPorTick;
      const destino = -el.scrollHeight;
      if (posicion <= destino) {
        posicion = destino;
        el.style.transform = `translateY(${posicion}px)`;
        clearInterval(intervalo);
        setTimeout(alTerminar, 400);
        return;
      }
      el.style.transform = `translateY(${posicion}px)`;
    }, intervaloMs);
  });
}

function narrarSiguienteNoticia() {
  const el = document.getElementById("noticiero-texto");
  if (!el) return;
  cicloNoticiero++;
  const fraseEspecial = cicloNoticiero % 4 === 0 ? siguienteFraseEspecial() : null;
  if (fraseEspecial) {
    mostrarConCrawl(el, fraseEspecial.titulo, fraseEspecial.descripcion, null, narrarSiguienteNoticia);
    return;
  }
  if (titularesNoticias.length === 0) return;
  const noticia = titularesNoticias[indiceNoticia % titularesNoticias.length];
  indiceNoticia++;
  const descripcion = noticia.fuente ? `Fuente: ${noticia.fuente}` : null;
  mostrarConCrawl(el, noticia.titulo, descripcion, noticia.link, narrarSiguienteNoticia);
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

// El recuadro de noticias nace y termina exactamente a la altura del logo:
// misma altura, mismo tope y mismo pie. Se re-sincroniza si cambia la fuente
// (Archivo Black, que carga async) o el viewport (el logo usa clamp con vw).
function sincronizarAlturaNoticiero() {
  const logo = document.querySelector(".rc-logo");
  const noticiero = document.querySelector(".rc-noticiero");
  if (!logo || !noticiero) return;
  const altura = logo.getBoundingClientRect().height;
  if (altura > 0) noticiero.style.height = `${altura}px`;
}

sincronizarAlturaNoticiero();
(document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve())
  .then(sincronizarAlturaNoticiero);
window.addEventListener("resize", sincronizarAlturaNoticiero);

pintarCarrousel();
renderCarrito();
cargarCatalogo();
