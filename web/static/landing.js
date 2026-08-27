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
  if (modoVisual === "classic") return; // Modo Classic: sin beeps en ninguna interacción
  if (e.target.closest("button, a, [role='button']")) beepInteraccion();
});

// Sonido de "click" mecánico (más seco y grave que el beep genérico de
// arriba): para el power switch del Pip-Boy, como un interruptor real.
function sonidoClickSwitch() {
  try {
    audioCtxInteraccion = audioCtxInteraccion
      || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtxInteraccion.state === "suspended") audioCtxInteraccion.resume();
    const osc = audioCtxInteraccion.createOscillator();
    const gain = audioCtxInteraccion.createGain();
    osc.type = "square";
    osc.frequency.value = 140;
    gain.gain.setValueAtTime(0.12, audioCtxInteraccion.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtxInteraccion.currentTime + 0.03);
    osc.connect(gain).connect(audioCtxInteraccion.destination);
    osc.start();
    osc.stop(audioCtxInteraccion.currentTime + 0.03);
  } catch {
    // Web Audio no disponible: seguimos sin sonido, no es crítico.
  }
}

const MARCAS = [
  "Apple", "Samsung", "Xiaomi", "Motorola", "Realme", "Oppo", "Honor",
  "Infinix", "Nokia", "PlayStation", "Nintendo", "JBL", "Logitech",
];

// Logo real de cada marca (solo se muestra en Modo Classic, ver classic.css).
// "Otras marcas" e Itel no tienen logo oficial disponible: usan una
// insignia genérica con la inicial, mismo tamaño que el resto.
const MARCA_LOGO = {
  "Apple": "apple", "Samsung": "samsung", "Xiaomi": "xiaomi",
  "Motorola": "motorola", "Realme": "realme", "Oppo": "oppo",
  "Honor": "honor", "Infinix": "infinix", "Nokia": "nokia",
  "PlayStation": "sony", "Nintendo": "nintendo", "JBL": "jbl",
  "Logitech": "logitech", "Itel": "itel", "Otras marcas": "otras-marcas",
};

// El catálogo clasifica las consolas bajo la marca "PlayStation" (viene así
// del pipeline de datos), pero la marca real del fabricante es Sony: en
// toda la app (Classic y Fallout) se MUESTRA "Sony", aunque el filtrado y
// el dataset internamente sigan usando "PlayStation" para no romper el
// matching contra los productos del catálogo.
const MARCA_ETIQUETA = { "PlayStation": "Sony" };
function etiquetaMarca(marca) {
  return MARCA_ETIQUETA[marca] || marca;
}

function marcaLogoHtml(marca, clase) {
  const slug = MARCA_LOGO[marca];
  if (!slug) return "";
  return `<img class="${clase}" src="/logos/${slug}.svg" alt="" />`;
}

function productoSeccion(producto) {
  for (const [seccion, productos] of Object.entries(SECCIONES_DATA)) {
    if ((productos || []).some((p) => p.nombre === producto.nombre)) return seccion;
  }
  return producto.categoria || null;
}

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
const CLAVE_CARRITO_PENDIENTE = "ttra_carrito_pendiente";
const CLAVE_CHECKOUT_PENDIENTE = "ttra_checkout_pendiente";
const CLAVE_DESCUENTO_MAILING = "ttra_descuento_mailing";
const CLAVE_ANON_ID = "ttra_anon_id";
const CLAVE_TEMA_CLASSIC = "ttra_classic_theme";
const WHATSAPP_NUMERO = "543512145217";

// Un descuento de mailing solo es válido al entrar desde su enlace. Esto
// elimina códigos viejos que quedaron persistidos en visitas normales.
if (!new URLSearchParams(location.search).get("codigo")) {
  localStorage.removeItem(CLAVE_DESCUENTO_MAILING);
}

let SECCIONES_DATA = {};
let RECOMENDADOS_DATA = [];
let modoPrecioActual = "minorista";
let catalogoListo = false;
let cotizacionActual = null; // U$D actual, usado en el reloj del header y en el narrador de noticias
let pronosticoManana = null; // texto del pronóstico del día siguiente, para el narrador
let pronosticoConsejo = null; // consejo práctico según ese pronóstico (paraguas, abrigo, etc.)
let seccionActiva = null; // clave de sección elegida en la pantalla principal, o null
let subFiltrosActivos = new Set(); // marcas (o "Notebooks"/"Macbooks") elegidas, acumulables
let filtroMarcaGlobal = null; // marca elegida desde el carrousel o "Búsqueda por Marca", busca en TODO el catálogo
let modoVista = "cards"; // "cards" | "lista"
let criterioOrden = "default"; // default | nombre-asc | nombre-desc | precio-asc | precio-desc
let ultimoEventoVista = "";
let ultimoTerminoBuscado = "";
let timeoutBusquedaTrack = null;

function generarIdLocal() {
  if (window.crypto && typeof window.crypto.randomUUID === "function") {
    return window.crypto.randomUUID();
  }
  return `ttra-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function obtenerAnonId() {
  try {
    let anonId = localStorage.getItem(CLAVE_ANON_ID);
    if (!anonId) {
      anonId = generarIdLocal();
      localStorage.setItem(CLAVE_ANON_ID, anonId);
    }
    return anonId;
  } catch {
    return generarIdLocal();
  }
}

function registrarInteraccion(tipoEvento, datos = {}) {
  if (tipoEvento !== "view_item") return;
  const anonId = obtenerAnonId();
  const payload = {
    tipo_evento: tipoEvento,
    producto_nombre: datos.producto_nombre || null,
    categoria: datos.categoria || null,
    marca: datos.marca || null,
    session_id: anonId,
    metadata: datos.metadata || {},
  };
  fetch("/api/interacciones", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-TTRA-ANON-ID": anonId,
    },
    body: JSON.stringify(payload),
  }).catch(() => {});
}
let estadoSesionCliente = null;
// Classic es siempre el modo de arranque (ver boot.js); Fallout solo dura
// mientras no se recarga la página, no se persiste entre refrescos.
// Atajo de desarrollo: ?modo=fallout en la URL arranca directo en Fallout
// SIN el boot sequence (aplicarModoVisual no lo dispara por sí solo, solo
// el click en el botón lo envuelve con la animación), para poder iterar
// sobre cambios de Fallout sin pasar por Classic cada vez.
let modoVisual = new URLSearchParams(location.search).get("modo") === "fallout" ? "fallout" : "classic";

function temaClassicGuardado() {
  try {
    return localStorage.getItem(CLAVE_TEMA_CLASSIC) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

function aplicarTemaClassic(tema, persistir = false) {
  const temaNormalizado = tema === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-classic-theme", temaNormalizado);
  if (persistir) {
    try {
      localStorage.setItem(CLAVE_TEMA_CLASSIC, temaNormalizado);
    } catch {
      // Sin storage, el tema se conserva durante esta visita.
    }
  }
  const botonTema = document.getElementById("btn-classic-theme");
  if (botonTema) {
    const siguienteTema = temaNormalizado === "light" ? "dark" : "light";
    botonTema.textContent = siguienteTema === "light" ? "Modo Light ☼" : "Modo Oscuro ☾";
    botonTema.setAttribute("aria-label", `Cambiar a modo ${siguienteTema}`);
  }
}

aplicarTemaClassic(temaClassicGuardado());

// Fotos decorativas de la ciudad, solo visibles en la pantalla principal.
// Cada archivo se muestra dentro de una "tarjeta" tipo terminal (ver
// tarjetaLugarHtml): el nombre del punto de interés sale del nombre de
// archivo, y los datos descriptivos salen de DATOS_LUGARES (misma clave,
// sin extensión). Agregar una foto nueva = agregar el archivo acá y su
// entrada en DATOS_LUGARES.
const IMAGENES_CORDOBA_CAPITAL = [
  "ciudad/catedral.jpg",
  "ciudad/plaza-san-martin.jpg",
  "ciudad/plaza-colon.jpg",
  "ciudad/arco.jpeg",
  "ciudad/dique-san-roque.jpg",
  "ciudad/paseo-del-buen-pastor.jpeg",
  "ciudad/patio-olmos.jpeg",
  "ciudad/puente-cosquin.jpg",
  "ciudad/teatro-san-martin.jpg",
  "ciudad/capuchinos.jpg",
  "ciudad/manzana-jesuitica.jpg",
  "ciudad/canada.jpg",
  "ciudad/cabildo.jpg",
];

// Fotos por provincia argentina (3 por provincia, Wikimedia Commons), usadas
// para mostrarle al visitante el paisaje de SU provincia según geolocalización.
// La entrada "cordoba" incluye también las fotos de la capital (arriba).
const IMAGENES_POR_PROVINCIA = {
  "buenos-aires": [
    "ciudad/provincias/buenos-aires/catedral-de-la-plata.jpg",
    "ciudad/provincias/buenos-aires/piedra-movediza-tandil.jpg",
    "ciudad/provincias/buenos-aires/delta-del-tigre.jpg",
  ],
  caba: [
    "ciudad/provincias/caba/obelisco.jpg",
    "ciudad/provincias/caba/teatro-colon.jpg",
    "ciudad/provincias/caba/puente-de-la-mujer.jpg",
  ],
  catamarca: [
    "ciudad/provincias/catamarca/ruinas-del-shincal.jpg",
    "ciudad/provincias/catamarca/campo-de-piedra-pomez.jpg",
    "ciudad/provincias/catamarca/termas-de-fiambala.jpg",
  ],
  chaco: [
    "ciudad/provincias/chaco/parque-nacional-chaco.jpg",
    "ciudad/provincias/chaco/ciudad-de-las-esculturas-resistencia.jpg",
    "ciudad/provincias/chaco/isla-del-cerrito.jpg",
  ],
  chubut: [
    "ciudad/provincias/chubut/peninsula-valdes.jpg",
    "ciudad/provincias/chubut/la-trochita.jpg",
    "ciudad/provincias/chubut/punta-tombo.jpg",
  ],
  cordoba: [
    ...IMAGENES_CORDOBA_CAPITAL,
    "ciudad/provincias/cordoba-provincia/la-cumbrecita.jpg",
    "ciudad/provincias/cordoba-provincia/reloj-cucu-la-falda.jpg",
    "ciudad/provincias/cordoba-provincia/cerro-uritorco.jpg",
  ],
  corrientes: [
    "ciudad/provincias/corrientes/esteros-del-ibera.jpg",
    "ciudad/provincias/corrientes/puente-general-belgrano.jpg",
    "ciudad/provincias/corrientes/costanera-correntina.jpg",
  ],
  "entre-rios": [
    "ciudad/provincias/entre-rios/palacio-san-jose.jpg",
    "ciudad/provincias/entre-rios/parque-nacional-el-palmar.jpg",
    "ciudad/provincias/entre-rios/costanera-de-concordia.jpg",
  ],
  formosa: [
    "ciudad/provincias/formosa/plaza-san-martin-formosa.jpg",
    "ciudad/provincias/formosa/banado-la-estrella.jpg",
    "ciudad/provincias/formosa/parque-nacional-rio-pilcomayo.jpg",
  ],
  jujuy: [
    "ciudad/provincias/jujuy/cerro-de-los-siete-colores-purmamarca.jpg",
    "ciudad/provincias/jujuy/quebrada-de-humahuaca.jpg",
    "ciudad/provincias/jujuy/salinas-grandes.jpg",
  ],
  "la-pampa": [
    "ciudad/provincias/la-pampa/parque-nacional-lihue-calel.jpg",
    "ciudad/provincias/la-pampa/santa-rosa-capital.jpg",
    "ciudad/provincias/la-pampa/parque-luro.jpg",
  ],
  "la-rioja": [
    "ciudad/provincias/la-rioja/parque-nacional-talampaya.jpg",
    "ciudad/provincias/la-rioja/cable-carril-la-mejicana-chilecito.jpg",
    "ciudad/provincias/la-rioja/casa-de-gobierno-la-rioja.jpg",
  ],
  mendoza: [
    "ciudad/provincias/mendoza/cerro-aconcagua.jpg",
    "ciudad/provincias/mendoza/puente-del-inca.jpg",
    "ciudad/provincias/mendoza/vinedo-valle-de-uco.jpg",
  ],
  misiones: [
    "ciudad/provincias/misiones/cataratas-del-iguazu.jpg",
    "ciudad/provincias/misiones/ruinas-san-ignacio-mini.jpg",
    "ciudad/provincias/misiones/salto-encantado.jpg",
  ],
  neuquen: [
    "ciudad/provincias/neuquen/volcan-lanin.jpg",
    "ciudad/provincias/neuquen/lago-lacar.jpg",
    "ciudad/provincias/neuquen/lago-correntoso.jpg",
  ],
  "rio-negro": [
    "ciudad/provincias/rio-negro/centro-civico-bariloche.jpg",
    "ciudad/provincias/rio-negro/cerro-catedral.jpg",
    "ciudad/provincias/rio-negro/lago-nahuel-huapi.jpg",
  ],
  salta: [
    "ciudad/provincias/salta/viaducto-la-polvorilla.jpg",
    "ciudad/provincias/salta/quebrada-de-las-conchas.jpg",
    "ciudad/provincias/salta/catedral-de-salta.jpg",
  ],
  "san-juan": [
    "ciudad/provincias/san-juan/valle-de-la-luna.jpg",
    "ciudad/provincias/san-juan/dique-ullum.jpg",
    "ciudad/provincias/san-juan/santuario-difunta-correa.jpg",
  ],
  "san-luis": [
    "ciudad/provincias/san-luis/sierra-de-las-quijadas.jpg",
    "ciudad/provincias/san-luis/antigua-casa-potrero-de-los-funes.jpg",
    "ciudad/provincias/san-luis/mirador-del-sol-merlo.jpg",
  ],
  "santa-cruz": [
    "ciudad/provincias/santa-cruz/glaciar-perito-moreno.jpg",
    "ciudad/provincias/santa-cruz/cueva-de-las-manos.jpg",
    "ciudad/provincias/santa-cruz/monte-fitz-roy-el-chalten.jpg",
  ],
  "santa-fe": [
    "ciudad/provincias/santa-fe/monumento-a-la-bandera-rosario.jpg",
    "ciudad/provincias/santa-fe/catedral-de-santa-fe.jpg",
    "ciudad/provincias/santa-fe/laguna-setubal.jpg",
  ],
  "santiago-del-estero": [
    "ciudad/provincias/santiago-del-estero/catedral-basilica.jpg",
    "ciudad/provincias/santiago-del-estero/termas-de-rio-hondo.jpg",
    "ciudad/provincias/santiago-del-estero/convento-santo-domingo.jpg",
  ],
  "tierra-del-fuego": [
    "ciudad/provincias/tierra-del-fuego/panoramica-ushuaia.jpg",
    "ciudad/provincias/tierra-del-fuego/bahia-lapataia-parque-nacional.jpg",
    "ciudad/provincias/tierra-del-fuego/faro-les-eclaireurs.jpg",
  ],
  tucuman: [
    "ciudad/provincias/tucuman/casa-historica-independencia.jpg",
    "ciudad/provincias/tucuman/ruinas-de-quilmes.jpg",
    "ciudad/provincias/tucuman/cerro-san-javier.jpg",
  ],
};

// Mapeo de código ISO 3166-2:AR (que devuelve la reverse-geocode de
// BigDataCloud como "principalSubdivisionCode") a la clave usada en
// IMAGENES_POR_PROVINCIA.
const PROVINCIA_POR_CODIGO_ISO = {
  "AR-B": "buenos-aires",
  "AR-C": "caba",
  "AR-K": "catamarca",
  "AR-H": "chaco",
  "AR-U": "chubut",
  "AR-X": "cordoba",
  "AR-W": "corrientes",
  "AR-E": "entre-rios",
  "AR-P": "formosa",
  "AR-Y": "jujuy",
  "AR-L": "la-pampa",
  "AR-F": "la-rioja",
  "AR-M": "mendoza",
  "AR-N": "misiones",
  "AR-Q": "neuquen",
  "AR-R": "rio-negro",
  "AR-A": "salta",
  "AR-J": "san-juan",
  "AR-D": "san-luis",
  "AR-Z": "santa-cruz",
  "AR-S": "santa-fe",
  "AR-G": "santiago-del-estero",
  "AR-V": "tierra-del-fuego",
  "AR-T": "tucuman",
};

// Fotos que se muestran mientras se resuelve la geolocalización, y como base
// de la provincia de Córdoba (capital + interior).
let IMAGENES_CIUDAD = IMAGENES_CORDOBA_CAPITAL;

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
  capuchinos: {
    ubicacion: "NUEVA CÓRDOBA",
    construccion: "1926 — INCONCLUSA",
    estilo: "NEOGÓTICO / HORMIGÓN ARMADO",
    coordenadas: "31°25'S 64°11'O (APROX.)",
    estado: "ACTIVA",
    importancia: "PRIMERA IGLESIA DE HORMIGÓN ARMADO DEL PAÍS",
    log: "LOG DE ARCHIVO: iniciada en 1926, fue la primera iglesia de Argentina construida en hormigón armado. Sus dos torres quedaron deliberadamente sin terminar, como recordatorio de que solo la obra divina puede considerarse completa. Foto: Lcsrns, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "manzana-jesuitica": {
    ubicacion: "CENTRO HISTÓRICO",
    construccion: "1613",
    estilo: "COLONIAL JESUÍTICO",
    coordenadas: "31°25'S 64°11'O (APROX.)",
    estado: "ACTIVA — MUSEO HISTÓRICO",
    importancia: "PATRIMONIO UNESCO (2000)",
    log: "LOG DE ARCHIVO: núcleo original de lo que hoy es la Universidad Nacional de Córdoba, fundada en 1613 como Colegio Máximo — la más antigua del país. Integra la Manzana Jesuítica, Patrimonio de la Humanidad. Foto: Lcsrns, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  canada: {
    ubicacion: "CENTRO / NUEVA CÓRDOBA",
    construccion: "CANALIZADA EN 1944",
    estilo: "OBRA HIDRÁULICA URBANA",
    coordenadas: "31°25'S 64°11'O (APROX.)",
    estado: "ACTIVA",
    importancia: "ÍCONO PAISAJÍSTICO DE LA CIUDAD",
    log: "LOG DE ARCHIVO: canalización del arroyo La Cañada, habilitada en 1944 para controlar las inundaciones que afectaban a la ciudad. Sus puentes de piedra y tipas centenarias son hoy una de las postales más reconocibles de Córdoba. Foto: Lcsrns, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  cabildo: {
    ubicacion: "PLAZA SAN MARTÍN",
    construccion: "1783 — 1786",
    estilo: "COLONIAL / ARCADA DE 15 ARCOS",
    coordenadas: "31°25'S 64°11'O (APROX.)",
    estado: "ACTIVA — MUSEO DE LA CIUDAD",
    importancia: "MONUMENTO HISTÓRICO NACIONAL",
    log: "LOG DE ARCHIVO: sede del gobierno colonial hasta el siglo XIX, remodelado entre 1783 y 1786 con su característica galería de 15 arcos. Hoy funciona como Museo de la Ciudad, frente a la Catedral. Foto: Pablo D. Flores, CC BY-SA 2.5 (Wikimedia Commons).",
  },

  // --- Puntos de interés por provincia argentina (geolocalización) ---
  "catedral-de-la-plata": {
    ubicacion: "LA PLATA, BUENOS AIRES",
    construccion: "1884 — 1932",
    estilo: "NEOGÓTICO",
    coordenadas: "34°55'S 57°57'O (APROX.)",
    estado: "ACTIVA",
    importancia: "MAYOR BASÍLICA NEOGÓTICA DEL HEMISFERIO SUR",
    log: "LOG DE ARCHIVO: construida como parte del trazado fundacional de La Plata, con torres de casi 120 metros y ascensor panorámico. Foto: MartinPutz (Martinp1), CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "piedra-movediza-tandil": {
    ubicacion: "TANDIL, BUENOS AIRES",
    construccion: "RÉPLICA INSTALADA EN 2007",
    estilo: "FORMACIÓN GRANÍTICA / RÉPLICA",
    coordenadas: "37°19'S 59°08'O (APROX.)",
    estado: "ACTIVA — PARQUE LÍTICO",
    importancia: "ÍCONO GEOLÓGICO DE TANDIL",
    log: "LOG DE ARCHIVO: la piedra original, de unas 300 toneladas, se mecía en equilibrio hasta caer y romperse en 1912. La réplica actual recrea ese ícono en el Parque Lítico La Movediza. Foto: Leopogonza, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "delta-del-tigre": {
    ubicacion: "TIGRE, BUENOS AIRES",
    construccion: "FORMACIÓN NATURAL",
    estilo: "DELTA FLUVIAL / HUMEDAL",
    coordenadas: "34°25'S 58°34'O (APROX.)",
    estado: "ACTIVO",
    importancia: "DESTINO NATURAL MÁS VISITADO CERCA DE BUENOS AIRES",
    log: "LOG DE ARCHIVO: red de arroyos e islas del Delta del Paraná, recorrida tradicionalmente en lancha colectiva. Ecosistema de humedales con identidad cultural propia de 'isleños'. Foto: Vlasta x, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  obelisco: {
    ubicacion: "PLAZA DE LA REPÚBLICA, CABA",
    construccion: "1936",
    estilo: "MONUMENTO CONMEMORATIVO",
    coordenadas: "34°36'S 58°22'O (APROX.)",
    estado: "ACTIVA",
    importancia: "MONUMENTO MÁS RECONOCIBLE DE ARGENTINA",
    log: "LOG DE ARCHIVO: erigido en 1936 para el cuarto centenario de la primera fundación de la ciudad. Con 67 metros de altura, escenario tradicional de festejos populares y deportivos. Foto: Jorge Láscar, CC BY 2.0 (Wikimedia Commons).",
  },
  "teatro-colon": {
    ubicacion: "CABA",
    construccion: "1908",
    estilo: "ACADEMICISTA / BEAUX-ARTS",
    coordenadas: "34°36'S 58°23'O (APROX.)",
    estado: "ACTIVA",
    importancia: "UNO DE LOS TEATROS DE ÓPERA MÁS IMPORTANTES DEL MUNDO",
    log: "LOG DE ARCHIVO: inaugurado en 1908, reconocido por su acústica excepcional. Escenario de las mayores figuras de la música clásica y la ópera internacional. Foto: EEJCC, dominio público CC0 1.0 (Wikimedia Commons).",
  },
  "puente-de-la-mujer": {
    ubicacion: "PUERTO MADERO, CABA",
    construccion: "2001",
    estilo: "CONTEMPORÁNEO / PASARELA ROTATORIA",
    coordenadas: "34°36'S 58°21'O (APROX.)",
    estado: "ACTIVA",
    importancia: "SÍMBOLO DE LA RENOVACIÓN DE PUERTO MADERO",
    log: "LOG DE ARCHIVO: diseñado por Santiago Calatrava, inaugurado en 2001. Sus calles llevan nombres de mujeres, de ahí su denominación. Foto: Jorge Lascar, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "ruinas-del-shincal": {
    ubicacion: "LONDRES, DEPTO. BELÉN, CATAMARCA",
    construccion: "SIGLO XV",
    estilo: "ARQUITECTURA INCAICA",
    coordenadas: "27°38'S 67°06'O (APROX.)",
    estado: "SITIO ARQUEOLÓGICO — EN VALOR",
    importancia: "UNO DE LOS SITIOS INCAICOS MEJOR CONSERVADOS DE ARGENTINA",
    log: "LOG DE ARCHIVO: ciudad administrativa y ceremonial del Imperio Inca, centro de control del extremo austral del Qhapaq Ñan. Terrazas, ushnu y edificios de piedra puestos en valor entre 2013 y 2015. Foto: Reinaldo A. Moralejo, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "campo-de-piedra-pomez": {
    ubicacion: "ANTOFAGASTA DE LA SIERRA, CATAMARCA",
    construccion: "FORMACIÓN VOLCÁNICA",
    estilo: "PAISAJE LUNAR DE YARDANGS",
    coordenadas: "26°30'S 67°30'O (APROX.)",
    estado: "ÁREA NATURAL PROTEGIDA",
    importancia: "CURIOSIDAD GEOLÓGICA ÚNICA A +3.300 MSNM",
    log: "LOG DE ARCHIVO: depósitos volcánicos que crearon formaciones de piedra pómez de varios metros de altura en plena Puna catamarqueña. Foto: Rodolfo Pace, CC BY 2.0 (Wikimedia Commons).",
  },
  "termas-de-fiambala": {
    ubicacion: "FIAMBALÁ, DEPTO. TINOGASTA, CATAMARCA",
    construccion: "FUENTES TERMALES NATURALES",
    estilo: "PILETAS ESCALONADAS DE MONTAÑA",
    coordenadas: "27°41'S 67°37'O (APROX.)",
    estado: "ACTIVA — DESTINO TURÍSTICO",
    importancia: "TERMAS TRADICIONALES DEL OESTE CATAMARQUEÑO",
    log: "LOG DE ARCHIVO: aguas termales naturales en la precordillera, con piletas de distintas temperaturas rodeadas de paisaje serrano. Foto: CarlosA.Barrio, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "parque-nacional-chaco": {
    ubicacion: "CAPITÁN SOLARI, CHACO",
    construccion: "PARQUE NACIONAL DESDE 1954",
    estilo: "BOSQUE CHAQUEÑO ORIENTAL",
    coordenadas: "26°48'S 59°37'O (APROX.)",
    estado: "ACTIVO",
    importancia: "RESERVA DE FLORA Y FAUNA CHAQUEÑA",
    log: "LOG DE ARCHIVO: protege quebrachales, algarrobos y numerosas lagunas como la del Carpincho. Refugio de yacarés, carpinchos y aves autóctonas. Foto: Pertile, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "ciudad-de-las-esculturas-resistencia": {
    ubicacion: "PLAZA SAN MARTÍN, RESISTENCIA, CHACO",
    construccion: "TRADICIÓN INICIADA EN 1961",
    estilo: "ESCULTURA AL AIRE LIBRE",
    coordenadas: "27°27'S 58°59'O (APROX.)",
    estado: "ACTIVA — BIENAL DE ESCULTURAS",
    importancia: "RESISTENCIA, 'CIUDAD DE LAS ESCULTURAS'",
    log: "LOG DE ARCHIVO: tradición impulsada por el Fogón de los Arrieros, origen de la Bienal Internacional de Esculturas. Cientos de obras al aire libre en plazas y calles. Foto: Pertile, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "isla-del-cerrito": {
    ubicacion: "ISLA DEL CERRITO, CHACO",
    construccion: "PUEBLO RIBEREÑO HISTÓRICO",
    estilo: "PAISAJE FLUVIAL",
    coordenadas: "27°08'S 58°49'O (APROX.)",
    estado: "ACTIVO — CENTRO TURÍSTICO",
    importancia: "PRINCIPAL DESTINO DE PESCA DEL CHACO",
    log: "LOG DE ARCHIVO: ubicada en la confluencia de los ríos Paraná y Paraguay. Playas de agua dulce y antiguo casco urbano. Foto: Pertile, CC BY 3.0 (Wikimedia Commons).",
  },
  "peninsula-valdes": {
    ubicacion: "PENÍNSULA VALDÉS, CHUBUT",
    construccion: "FORMACIÓN NATURAL",
    estilo: "RESERVA DE FAUNA MARINA",
    coordenadas: "42°30'S 64°00'O (APROX.)",
    estado: "PATRIMONIO UNESCO (1999)",
    importancia: "SANTUARIO DE BALLENAS FRANCAS AUSTRALES",
    log: "LOG DE ARCHIVO: hogar de ballenas francas australes, elefantes marinos, lobos marinos y orcas. Caleta Valdés es una de sus bahías más emblemáticas. Foto: .vxctoria, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "la-trochita": {
    ubicacion: "EL MAITÉN / ESQUEL, CHUBUT",
    construccion: "1922",
    estilo: "FERROCARRIL DE TROCHA ANGOSTA",
    coordenadas: "42°56'S 71°10'O (APROX.)",
    estado: "ACTIVA — ATRACTIVO TURÍSTICO",
    importancia: "'THE OLD PATAGONIAN EXPRESS'",
    log: "LOG DE ARCHIVO: histórico ferrocarril patagónico popularizado por el libro de Paul Theroux. Sus locomotoras a vapor siguen operando entre Esquel y El Maitén. Foto: Pablo Bruno D'Amico, CC BY-SA 2.0 (Wikimedia Commons).",
  },
  "punta-tombo": {
    ubicacion: "PUNTA TOMBO, CHUBUT",
    construccion: "RESERVA PROTEGIDA DESDE 1979",
    estilo: "ESTEPA COSTERA",
    coordenadas: "44°02'S 65°11'O (APROX.)",
    estado: "ACTIVA",
    importancia: "MAYOR COLONIA DE PINGÜINOS MAGALLÁNICOS DE ARGENTINA",
    log: "LOG DE ARCHIVO: cientos de miles de pingüinos magallánicos nidifican cada primavera en la estepa costera. Uno de los destinos de avistaje de fauna más visitados de la Patagonia. Foto: littletroll, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "la-cumbrecita": {
    ubicacion: "VALLE DE CALAMUCHITA, CÓRDOBA",
    construccion: "1934",
    estilo: "PUEBLO PEATONAL ALPINO",
    coordenadas: "31°54'S 64°48'O (APROX.)",
    estado: "ACTIVA — DESTINO TURÍSTICO",
    importancia: "PUEBLO ALPINO A 1450 MSNM",
    log: "LOG DE ARCHIVO: fundado por inmigrantes centroeuropeos en las Altas Sierras cordobesas. Calles de piedra, arroyos y bosques de pinos. Foto: Banfield, CC BY-SA 2.5 AR (Wikimedia Commons).",
  },
  "reloj-cucu-la-falda": {
    ubicacion: "LA FALDA, VALLE DE PUNILLA, CÓRDOBA",
    construccion: "SIGLO XX",
    estilo: "INSPIRADO EN LA SELVA NEGRA",
    coordenadas: "31°05'S 64°29'O (APROX.)",
    estado: "ACTIVA",
    importancia: "MONUMENTO EMBLEMÁTICO DE ENTRADA A LA FALDA",
    log: "LOG DE ARCHIVO: símbolo identitario de La Falda, ciudad serrana que alojó al mítico Hotel Edén. Estructura inspirada en los relojes de cuco de la Selva Negra. Foto: Lanacabu, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "cerro-uritorco": {
    ubicacion: "CAPILLA DEL MONTE, VALLE DE PUNILLA, CÓRDOBA",
    construccion: "1979 METROS DE ALTURA",
    estilo: "ELEVACIÓN SERRANA",
    coordenadas: "30°58'S 64°49'O (APROX.)",
    estado: "ACTIVA",
    importancia: "ELEVACIÓN MÁS ALTA DEL VALLE DE PUNILLA",
    log: "LOG DE ARCHIVO: famoso por relatos de avistamientos OVNI y fenómenos paranormales que atraen turismo esotérico desde los años 80. Foto: Pablo D. Flores, CC BY-SA 2.5 (Wikimedia Commons).",
  },
  "esteros-del-ibera": {
    ubicacion: "CORRIENTES",
    construccion: "HUMEDAL NATURAL",
    estilo: "ESTEROS Y LAGUNAS",
    coordenadas: "28°30'S 57°30'O (APROX.)",
    estado: "ACTIVO — RESERVA NATURAL",
    importancia: "UNO DE LOS HUMEDALES MÁS GRANDES DEL MUNDO",
    log: "LOG DE ARCHIVO: paisaje de esteros y lagunas con gran biodiversidad de fauna autóctona, incluyendo yacarés y ciervos de los pantanos. Foto: Delfor Hernán Castro (Entrerrianitox), CC BY 4.0 (Wikimedia Commons).",
  },
  "puente-general-belgrano": {
    ubicacion: "CORRIENTES / CHACO",
    construccion: "OBRA VIAL SOBRE EL RÍO PARANÁ",
    estilo: "PUENTE COLGANTE",
    coordenadas: "27°28'S 58°50'O (APROX.)",
    estado: "ACTIVO",
    importancia: "CONEXIÓN VIAL CORRIENTES-CHACO",
    log: "LOG DE ARCHIVO: conecta las ciudades de Corrientes y Resistencia sobre el río Paraná, vista desde la costanera correntina. Foto: Pertile, CC BY 3.0 (Wikimedia Commons).",
  },
  "costanera-correntina": {
    ubicacion: "CIUDAD DE CORRIENTES",
    construccion: "PASEO COSTERO",
    estilo: "COSTANERA URBANA",
    coordenadas: "27°28'S 58°50'O (APROX.)",
    estado: "ACTIVA",
    importancia: "PASEO EMBLEMÁTICO A ORILLAS DEL PARANÁ",
    log: "LOG DE ARCHIVO: recorrido costero tradicional de la capital correntina, con vista al río Paraná y al puente que la conecta con el Chaco. Foto: Carlos Bagliani, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "palacio-san-jose": {
    ubicacion: "CERCA DE CONCEPCIÓN DEL URUGUAY, ENTRE RÍOS",
    construccion: "1848 — 1858",
    estilo: "RESIDENCIAL HISTÓRICO",
    coordenadas: "32°16'S 58°28'O (APROX.)",
    estado: "ACTIVA — MUSEO Y MONUMENTO HISTÓRICO",
    importancia: "EX RESIDENCIA DE JUSTO JOSÉ DE URQUIZA",
    log: "LOG DE ARCHIVO: residencia personal del general Justo José de Urquiza, diseñada por el arquitecto Pedro Fossati. Foto: Puchita, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "parque-nacional-el-palmar": {
    ubicacion: "COLÓN, ENTRE RÍOS",
    construccion: "PARQUE NACIONAL DESDE 1966",
    estilo: "PALMAR DE YATAY",
    coordenadas: "31°52'S 58°15'O (APROX.)",
    estado: "ACTIVO",
    importancia: "ÚLTIMOS GRANDES PALMARES DE YATAY DEL LITORAL",
    log: "LOG DE ARCHIVO: creado en 1966 para preservar los bosques de palmera yatay (Syagrus/Butia yatay), característicos del litoral entrerriano. Foto: Piazzanto, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "costanera-de-concordia": {
    ubicacion: "CONCORDIA, ENTRE RÍOS",
    construccion: "PASEO COSTERO SOBRE EL RÍO URUGUAY",
    estilo: "COSTANERA URBANA",
    coordenadas: "31°24'S 58°00'O (APROX.)",
    estado: "ACTIVA",
    importancia: "MIRADOR SOBRE EL RÍO URUGUAY",
    log: "LOG DE ARCHIVO: paseo costero de la segunda ciudad de Entre Ríos, con miradores sobre el río Uruguay. Foto: Agencia Oka, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "plaza-san-martin-formosa": {
    ubicacion: "CIUDAD DE FORMOSA",
    construccion: "PLAZA CENTRAL",
    estilo: "PLAZA URBANA",
    coordenadas: "26°11'S 58°10'O (APROX.)",
    estado: "ACTIVA",
    importancia: "PLAZA PRINCIPAL DE LA CAPITAL FORMOSEÑA",
    log: "LOG DE ARCHIVO: plaza General San Martín, ubicada en la ciudad de Formosa, capital de la provincia. Foto: Iro Bosero, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "banado-la-estrella": {
    ubicacion: "LAS LOMITAS, FORMOSA",
    construccion: "HUMEDAL NATURAL",
    estilo: "BAÑADO / HUMEDAL",
    coordenadas: "24°43'S 60°35'O (APROX.)",
    estado: "ACTIVO",
    importancia: "SEGUNDO HUMEDAL MÁS GRANDE DE ARGENTINA",
    log: "LOG DE ARCHIVO: paisaje natural de unas 400 mil hectáreas, hogar de más de 300 especies de aves. Foto: Iro Bosero, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "parque-nacional-rio-pilcomayo": {
    ubicacion: "FORMOSA",
    construccion: "PARQUE NACIONAL DESDE 1951",
    estilo: "HUMEDAL CHAQUEÑO",
    coordenadas: "25°05'S 58°15'O (APROX.)",
    estado: "ACTIVO",
    importancia: "51.889 HECTÁREAS DE HUMEDALES PROTEGIDOS",
    log: "LOG DE ARCHIVO: protege el curso del río Pilcomayo y sus esteros, con gran diversidad de fauna chaqueña. Foto: Tencho, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "cerro-de-los-siete-colores-purmamarca": {
    ubicacion: "PURMAMARCA, JUJUY",
    construccion: "FORMACIÓN GEOLÓGICA",
    estilo: "SEDIMENTACIÓN MARINA Y VOLCÁNICA",
    coordenadas: "23°45'S 65°30'O (APROX.)",
    estado: "ACTIVA",
    importancia: "PATRIMONIO UNESCO — QUEBRADA DE HUMAHUACA",
    log: "LOG DE ARCHIVO: ícono visual de Purmamarca, con franjas de rojo, ocre, violeta y verde formadas por sedimentación a lo largo de millones de años. Foto: JuliSarki, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "quebrada-de-humahuaca": {
    ubicacion: "JUJUY",
    construccion: "VALLE ANDINO DE +150 KM",
    estilo: "PAISAJE ANDINO",
    coordenadas: "23°12'S 65°21'O (APROX.)",
    estado: "PATRIMONIO UNESCO (2003)",
    importancia: "ANTIGUA VÍA DEL CAMINO INCA",
    log: "LOG DE ARCHIVO: valle atravesado históricamente por el Camino Inca y hoy por la Ruta Nacional 9, vía de tránsito comercial y cultural desde tiempos prehispánicos. Foto: Diego Salgado, CC BY 2.0 (Wikimedia Commons).",
  },
  "salinas-grandes": {
    ubicacion: "FRONTERA JUJUY-SALTA",
    construccion: "ANTIGUO LAGO SECO",
    estilo: "DESIERTO DE SAL",
    coordenadas: "23°30'S 66°53'O (APROX.)",
    estado: "ACTIVO — EXPLOTACIÓN ARTESANAL",
    importancia: "UNO DE LOS MAYORES DESIERTOS DE SAL DE SUDAMÉRICA",
    log: "LOG DE ARCHIVO: superficie blanca y agrietada a más de 3.300 msnm, explotada artesanalmente para extracción de sal y litio. Foto: diametrik (Lian Chang), CC BY 2.0 (Wikimedia Commons).",
  },
  "parque-nacional-lihue-calel": {
    ubicacion: "DEPTO. LIHUEL CALEL, LA PAMPA",
    construccion: "SIERRA GRANÍTICA AISLADA",
    estilo: "MONTE PAMPEANO",
    coordenadas: "38°01'S 65°35'O (APROX.)",
    estado: "ACTIVO — PARQUE NACIONAL",
    importancia: "'SIERRA DE LA VIDA' (LENGUA RANQUEL)",
    log: "LOG DE ARCHIVO: sistema serrano aislado en la llanura pampeana, con pinturas rupestres ranqueles. Último refugio del cacique Baigorrita en la Conquista del Desierto. Foto: Claudio Elias, dominio público (Wikimedia Commons).",
  },
  "santa-rosa-capital": {
    ubicacion: "SANTA ROSA, LA PAMPA (CAPITAL)",
    construccion: "FUNDADA EN 1892",
    estilo: "TRAZA URBANA PLANIFICADA",
    coordenadas: "36°37'S 64°17'O (APROX.)",
    estado: "ACTIVA — CAPITAL PROVINCIAL",
    importancia: "CAPITAL DE LA PAMPA DESDE 1952",
    log: "LOG DE ARCHIVO: centro administrativo y comercial surgido en torno a la actividad agropecuaria y ferroviaria de la región pampeana. Foto: Claudio Elias, dominio público (Wikimedia Commons).",
  },
  "parque-luro": {
    ubicacion: "DEPTO. TOAY, CERCA DE SANTA ROSA, LA PAMPA",
    construccion: "SIGLO XIX",
    estilo: "RESERVA NATURAL / CASCO HISTÓRICO",
    coordenadas: "36°49'S 64°15'O (APROX.)",
    estado: "ACTIVA — RESERVA PROVINCIAL",
    importancia: "PRIMER COTO DE CAZA MAYOR DE SUDAMÉRICA",
    log: "LOG DE ARCHIVO: fundado por Pedro Luro sobre territorio ranquel. Bosques de caldén nativo y ciervos colorados introducidos en el siglo XIX. Foto: Juanedc (Juan Eduardo De Cristofaro), CC BY 2.0 (Wikimedia Commons).",
  },
  "parque-nacional-talampaya": {
    ubicacion: "DEPTO. INDEPENDENCIA, LA RIOJA",
    construccion: "CAÑÓN NATURAL",
    estilo: "PAREDONES ROJIZOS EROSIONADOS",
    coordenadas: "29°59'S 67°55'O (APROX.)",
    estado: "PATRIMONIO UNESCO (JUNTO A ISCHIGUALASTO)",
    importancia: "FORMACIONES 'LA CATEDRAL' Y 'EL MONJE'",
    log: "LOG DE ARCHIVO: cañón de paredones de hasta 150 metros tallados por el viento y el agua, con petroglifos de más de 10.000 años. Foto: Gino Lucas T., CC BY-SA 2.5 (Wikimedia Commons).",
  },
  "cable-carril-la-mejicana-chilecito": {
    ubicacion: "CHILECITO, LA RIOJA",
    construccion: "PRINCIPIOS DEL SIGLO XX",
    estilo: "INGENIERÍA MINERA (SISTEMA BLEICHERT)",
    coordenadas: "29°10'S 67°30'O (APROX.)",
    estado: "MONUMENTO HISTÓRICO NACIONAL",
    importancia: "SÍMBOLO DEL PASADO MINERO RIOJANO",
    log: "LOG DE ARCHIVO: sistema de transporte minero que salvaba más de 35 km y 3.000 metros de desnivel desde la mina La Mejicana. Foto: Abubea, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "casa-de-gobierno-la-rioja": {
    ubicacion: "CIUDAD DE LA RIOJA (CAPITAL)",
    construccion: "FUNDADA EN 1591",
    estilo: "FACHADA COLONIAL",
    coordenadas: "29°25'S 66°51'O (APROX.)",
    estado: "ACTIVA — SEDE DEL PODER EJECUTIVO",
    importancia: "CENTRO HISTÓRICO DE LA CAPITAL RIOJANA",
    log: "LOG DE ARCHIVO: sede del gobierno provincial en la ciudad fundada en 1591 por Juan Ramírez de Velasco. Foto: Federico Gomez Aghetta, dominio público (Wikimedia Commons).",
  },
  "cerro-aconcagua": {
    ubicacion: "PARQUE PROVINCIAL ACONCAGUA, MENDOZA",
    construccion: "6.961 METROS DE ALTURA",
    estilo: "MACIZO ANDINO",
    coordenadas: "32°39'S 70°00'O (APROX.)",
    estado: "ACTIVO — DESTINO DE MONTAÑISMO",
    importancia: "PUNTO MÁS ALTO DE AMÉRICA",
    log: "LOG DE ARCHIVO: cumbre más alta del continente americano y del hemisferio occidental. Destino clásico del andinismo internacional. Foto: Roland Baumschlager, dominio público (Wikimedia Commons).",
  },
  "puente-del-inca": {
    ubicacion: "PUENTE DEL INCA, MENDOZA",
    construccion: "FORMACIÓN NATURAL",
    estilo: "PUENTE NATURAL DE ROCA",
    coordenadas: "32°49'S 69°55'O (APROX.)",
    estado: "ACTIVO",
    importancia: "PUENTE NATURAL SOBRE EL RÍO LAS CUEVAS",
    log: "LOG DE ARCHIVO: villa andina a 2700 msnm, con un puente natural de roca formado sobre el río Las Cuevas. Foto: Havardtl, CC BY 4.0 (Wikimedia Commons).",
  },
  "vinedo-valle-de-uco": {
    ubicacion: "VALLE DE UCO, MENDOZA",
    construccion: "REGIÓN VITIVINÍCOLA",
    estilo: "VIÑEDOS DE ALTURA",
    coordenadas: "33°29'S 69°15'O (APROX.)",
    estado: "ACTIVO",
    importancia: "UNA DE LAS REGIONES VITIVINÍCOLAS MÁS RECONOCIDAS DE ARGENTINA",
    log: "LOG DE ARCHIVO: viñedo frente a la cordillera de los Andes, en una de las zonas vitivinícolas de mayor prestigio del país. Foto: David, CC BY 2.0 (Wikimedia Commons).",
  },
  "cataratas-del-iguazu": {
    ubicacion: "PUERTO IGUAZÚ, MISIONES",
    construccion: "FORMACIÓN NATURAL",
    estilo: "CATARATAS / SELVA SUBTROPICAL",
    coordenadas: "25°41'S 54°26'O (APROX.)",
    estado: "PATRIMONIO UNESCO (1984)",
    importancia: "MARAVILLA NATURAL DEL MUNDO",
    log: "LOG DE ARCHIVO: conjunto de saltos de agua en la frontera con Brasil, una de las mayores atracciones naturales del planeta. Foto: Martin Gardeazabal, dominio público (Wikimedia Commons).",
  },
  "ruinas-san-ignacio-mini": {
    ubicacion: "SAN IGNACIO, MISIONES",
    construccion: "SIGLO XVII",
    estilo: "COLONIAL JESUÍTICO-GUARANÍ",
    coordenadas: "27°15'S 55°32'O (APROX.)",
    estado: "PATRIMONIO UNESCO",
    importancia: "MONUMENTO HISTÓRICO NACIONAL",
    log: "LOG DE ARCHIVO: ruinas de una de las reducciones jesuíticas mejor conservadas de Sudamérica, ejemplo del arte jesuítico-guaraní. Foto: Miguel Vieira, CC BY 2.0 (Wikimedia Commons).",
  },
  "salto-encantado": {
    ubicacion: "ARISTÓBULO DEL VALLE, MISIONES",
    construccion: "FORMACIÓN NATURAL",
    estilo: "CASCADA DE SELVA MISIONERA",
    coordenadas: "27°04'S 54°50'O (APROX.)",
    estado: "ACTIVO — PARQUE PROVINCIAL",
    importancia: "ÍCONO DEL VALLE DEL CUÑÁ PIRÚ",
    log: "LOG DE ARCHIVO: cascada dentro del Parque Provincial Salto Encantado del Valle de Cuñá Pirú, rodeada de selva misionera. Foto: Leandro Kibisz (Loco085), CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "volcan-lanin": {
    ubicacion: "PARQUE NACIONAL LANÍN, NEUQUÉN",
    construccion: "3.747 METROS DE ALTURA",
    estilo: "ESTRATOVOLCÁN NEVADO",
    coordenadas: "39°38'S 71°30'O (APROX.)",
    estado: "DORMIDO",
    importancia: "SÍMBOLO DE LA PROVINCIA DE NEUQUÉN",
    log: "LOG DE ARCHIVO: cono nevado en la frontera con Chile, visto desde el Lago Huechulafquen. Forma parte del escudo y la bandera de Neuquén. Foto: Viajando por la mía, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "lago-lacar": {
    ubicacion: "SAN MARTÍN DE LOS ANDES, NEUQUÉN",
    construccion: "LAGO GLACIAR",
    estilo: "LAGO ANDINO-PATAGÓNICO",
    coordenadas: "40°10'S 71°25'O (APROX.)",
    estado: "ACTIVO",
    importancia: "CENTRO DEL DEPARTAMENTO LÁCAR",
    log: "LOG DE ARCHIVO: lago glaciar enclavado en la cordillera, junto a la ciudad de San Martín de los Andes. Foto: Marco Antonio Correa Flores, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "lago-correntoso": {
    ubicacion: "VILLA LA ANGOSTURA, NEUQUÉN",
    construccion: "LAGO ANDINO",
    estilo: "PAISAJE PATAGÓNICO",
    coordenadas: "40°46'S 71°38'O (APROX.)",
    estado: "ACTIVO",
    importancia: "'JARDÍN DE LA PATAGONIA'",
    log: "LOG DE ARCHIVO: lago junto a Villa La Angostura, en el norte del Parque Nacional Nahuel Huapi. Foto: Luna929e9, CC BY 4.0 (Wikimedia Commons).",
  },
  "centro-civico-bariloche": {
    ubicacion: "SAN CARLOS DE BARILOCHE, RÍO NEGRO",
    construccion: "DÉCADA DE 1930-1940",
    estilo: "ARQUITECTURA ALPINA (PIEDRA Y MADERA)",
    coordenadas: "41°08'S 71°18'O (APROX.)",
    estado: "ACTIVO",
    importancia: "SEDE MUNICIPAL E ÍCONO ARQUITECTÓNICO DE BARILOCHE",
    log: "LOG DE ARCHIVO: conjunto edilicio diseñado por el arquitecto Ezequiel Bustillo, frente al Lago Nahuel Huapi, sede de la administración local. Foto: Rodriguez Rosela, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "cerro-catedral": {
    ubicacion: "SAN CARLOS DE BARILOCHE, RÍO NEGRO",
    construccion: "2.100 METROS DE ALTURA",
    estilo: "CENTRO DE ESQUÍ ANDINO",
    coordenadas: "41°10'S 71°26'O (APROX.)",
    estado: "ACTIVO",
    importancia: "UNO DE LOS CENTROS DE ESQUÍ MÁS IMPORTANTES DE ARGENTINA",
    log: "LOG DE ARCHIVO: base del cerro que da nombre a uno de los complejos de esquí más grandes de Sudamérica, a 19 km de Bariloche. Foto: Diego Gabriel, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "lago-nahuel-huapi": {
    ubicacion: "SAN CARLOS DE BARILOCHE, RÍO NEGRO",
    construccion: "LAGO GLACIAR",
    estilo: "LAGO ANDINO-PATAGÓNICO",
    coordenadas: "41°08'S 71°18'O (APROX.)",
    estado: "ACTIVO",
    importancia: "PARQUE NACIONAL MÁS ANTIGUO DE ARGENTINA (1922)",
    log: "LOG DE ARCHIVO: lago de 530 km² dentro del Parque Nacional Nahuel Huapi, junto a la ciudad de Bariloche. Foto: Pepe Robles, dominio público (Wikimedia Commons).",
  },
  "viaducto-la-polvorilla": {
    ubicacion: "PUNA SALTEÑA, SALTA",
    construccion: "1932",
    estilo: "VIADUCTO FERROVIARIO",
    coordenadas: "24°09'S 66°29'O (APROX.)",
    estado: "ACTIVO — ATRACTIVO TURÍSTICO",
    importancia: "PUNTO FINAL DEL 'TREN A LAS NUBES'",
    log: "LOG DE ARCHIVO: viaducto a 4.220 metros de altura, destino final del histórico Tren a las Nubes que conecta con la ciudad de Salta. Foto: Nestor Galina, CC BY 2.0 (Wikimedia Commons).",
  },
  "quebrada-de-las-conchas": {
    ubicacion: "CAFAYATE, SALTA",
    construccion: "FORMACIÓN GEOLÓGICA",
    estilo: "VALLES CALCHAQUÍES",
    coordenadas: "26°05'S 65°58'O (APROX.)",
    estado: "ACTIVA",
    importancia: "FORMACIONES ROJIZAS DE LOS VALLES CALCHAQUÍES",
    log: "LOG DE ARCHIVO: también llamada Quebrada de Cafayate, con formaciones rocosas rojizas como la Garganta del Diablo. Foto: Bachelot Pierre J-P, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "catedral-de-salta": {
    ubicacion: "CIUDAD DE SALTA",
    construccion: "SIGLO XIX",
    estilo: "NEOBARROCO COLONIAL",
    coordenadas: "24°47'S 65°25'O (APROX.)",
    estado: "MONUMENTO HISTÓRICO NACIONAL",
    importancia: "SANTUARIO DEL SEÑOR Y LA VIRGEN DEL MILAGRO",
    log: "LOG DE ARCHIVO: catedral basílica en el centro histórico de Salta, edificio colonial declarado monumento histórico nacional. Foto: Marianocecowski, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "valle-de-la-luna": {
    ubicacion: "PARQUE PROVINCIAL ISCHIGUALASTO, SAN JUAN",
    construccion: "FORMACIÓN GEOLÓGICA (TRIÁSICO)",
    estilo: "PAISAJE LUNAR EROSIONADO",
    coordenadas: "30°10'S 67°55'O (APROX.)",
    estado: "PATRIMONIO UNESCO",
    importancia: "SITIO PALEONTOLÓGICO CLAVE PARA EL ORIGEN DE LOS DINOSAURIOS",
    log: "LOG DE ARCHIVO: paisaje formado hace más de 200 millones de años, con formaciones como 'El Hongo'. Área protegida desde 1971. Foto: Littletroll, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "dique-ullum": {
    ubicacion: "ULLUM, SAN JUAN",
    construccion: "OBRA HIDRÁULICA",
    estilo: "EMBALSE ARTIFICIAL",
    coordenadas: "31°26'S 68°37'O (APROX.)",
    estado: "ACTIVO",
    importancia: "PRINCIPAL ESPEJO DE AGUA CERCANO A LA CAPITAL SANJUANINA",
    log: "LOG DE ARCHIVO: embalse sobre el río San Juan, destino de deportes náuticos y esparcimiento cercano a la ciudad capital. Foto: Enrique Guardia, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "santuario-difunta-correa": {
    ubicacion: "VALLECITO, SAN JUAN",
    construccion: "DESDE 1840",
    estilo: "SANTUARIO POPULAR",
    coordenadas: "31°38'S 68°09'O (APROX.)",
    estado: "ACTIVO — SITIO DE PEREGRINACIÓN",
    importancia: "FIGURA DE DEVOCIÓN POPULAR MÁS VISITADA DE CUYO",
    log: "LOG DE ARCHIVO: santuario dedicado a la Difunta Correa, figura de la religiosidad popular argentina, visitado por miles de promesantes cada año. Foto: EagLau, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "sierra-de-las-quijadas": {
    ubicacion: "DEPTO. AYACUCHO, SAN LUIS",
    construccion: "PARQUE NACIONAL",
    estilo: "CAÑONES Y ARENISCAS ROJIZAS",
    coordenadas: "32°30'S 67°00'O (APROX.)",
    estado: "ACTIVO",
    importancia: "HUELLAS DE DINOSAURIOS FOSILIZADAS",
    log: "LOG DE ARCHIVO: cañones erosionados por viento y agua, con el Potrero de la Aguada como cuenca natural rodeada de paredones. Foto: Piero Teardo, CC BY-SA 2.0 (Wikimedia Commons).",
  },
  "antigua-casa-potrero-de-los-funes": {
    ubicacion: "POTRERO DE LOS FUNES, SAN LUIS",
    construccion: "ORIGEN RURAL HISTÓRICO",
    estilo: "CONSTRUCCIÓN TRADICIONAL PUNTANA",
    coordenadas: "33°09'S 66°14'O (APROX.)",
    estado: "ACTIVA",
    importancia: "TESTIMONIO DEL ORIGEN RURAL DE LA VILLA",
    log: "LOG DE ARCHIVO: villa turística junto a un dique y lago artificial rodeado de sierras, hoy polo de turismo y deportes acuáticos. Foto: Dhmastan, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "mirador-del-sol-merlo": {
    ubicacion: "VILLA DE MERLO, SAN LUIS",
    construccion: "MIRADOR PANORÁMICO",
    estilo: "LADERA SERRANA",
    coordenadas: "32°20'S 65°10'O (APROX.)",
    estado: "ACTIVO",
    importancia: "VISTA PANORÁMICA DEL VALLE DE CONLARA",
    log: "LOG DE ARCHIVO: Villa de Merlo es famosa por su microclima con alta concentración de iones negativos en el aire, sobre las Sierras de los Comechingones. Foto: Merlo San Luis, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "glaciar-perito-moreno": {
    ubicacion: "PARQUE NACIONAL LOS GLACIARES, SANTA CRUZ",
    construccion: "GLACIAR EN EQUILIBRIO",
    estilo: "HIELO CONTINENTAL PATAGÓNICO",
    coordenadas: "50°28'S 73°03'O (APROX.)",
    estado: "PATRIMONIO UNESCO",
    importancia: "UNO DE LOS POCOS GLACIARES DEL MUNDO EN EQUILIBRIO",
    log: "LOG DE ARCHIVO: avanza sobre el Lago Argentino generando espectaculares rupturas de hielo. Ícono turístico de la Patagonia argentina. Foto: quimpg, CC BY 2.0 (Wikimedia Commons).",
  },
  "cueva-de-las-manos": {
    ubicacion: "CAÑÓN DEL RÍO PINTURAS, SANTA CRUZ",
    construccion: "MÁS DE 9.000 AÑOS DE ANTIGÜEDAD",
    estilo: "ARTE RUPESTRE",
    coordenadas: "47°09'S 70°33'O (APROX.)",
    estado: "PATRIMONIO UNESCO (1999)",
    importancia: "UNO DE LOS CONJUNTOS DE ARTE RUPESTRE MÁS IMPORTANTES DE SUDAMÉRICA",
    log: "LOG DE ARCHIVO: cientos de estarcidos de manos realizados por pueblos cazadores-recolectores hace miles de años. Foto: Mariano (Marianocecowski), CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "monte-fitz-roy-el-chalten": {
    ubicacion: "EL CHALTÉN, SANTA CRUZ",
    construccion: "3.405 METROS DE ALTURA",
    estilo: "MACIZO GRANÍTICO",
    coordenadas: "49°16'S 73°02'O (APROX.)",
    estado: "ACTIVO — DESTINO DE TREKKING",
    importancia: "SÍMBOLO DE LA PATAGONIA ARGENTINA",
    log: "LOG DE ARCHIVO: también llamado Cerro Chaltén, domina el paisaje cerca de El Chaltén, capital nacional del trekking. Foto: Alejandro Dau (Avd74), CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "monumento-a-la-bandera-rosario": {
    ubicacion: "ROSARIO, SANTA FE",
    construccion: "INAUGURADO EN 1957",
    estilo: "MONUMENTALISTA",
    coordenadas: "32°57'S 60°38'O (APROX.)",
    estado: "ACTIVO",
    importancia: "LUGAR DONDE BELGRANO IZÓ POR PRIMERA VEZ LA BANDERA (1812)",
    log: "LOG DE ARCHIVO: mástil de 70 metros a orillas del Paraná, combina arquitectura monumentalista con una gran plaza cívica. Foto: AmethystK, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "catedral-de-santa-fe": {
    ubicacion: "CIUDAD DE SANTA FE",
    construccion: "ESTILO NEOCLÁSICO",
    estilo: "NEOCLÁSICO ITALIANIZANTE",
    coordenadas: "31°38'S 60°42'O (APROX.)",
    estado: "MONUMENTO HISTÓRICO NACIONAL",
    importancia: "SEDE DEL ARZOBISPADO DE SANTA FE",
    log: "LOG DE ARCHIVO: catedral metropolitana frente a la Plaza 25 de Mayo, uno de los edificios históricos más representativos de la capital provincial. Foto: Biruma, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "laguna-setubal": {
    ubicacion: "CIUDAD DE SANTA FE",
    construccion: "ESPEJO DE AGUA NATURAL",
    estilo: "LAGUNA URBANA",
    coordenadas: "31°36'S 60°41'O (APROX.)",
    estado: "ACTIVA",
    importancia: "PUNTO CENTRAL DE ESPARCIMIENTO DE LA CAPITAL SANTAFESINA",
    log: "LOG DE ARCHIVO: espejo de agua de unos 32 km² conectado al sistema del río Paraná, bordea la costanera este de la ciudad. Foto: Maria Celeste Rios, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "catedral-basilica": {
    ubicacion: "SANTIAGO DEL ESTERO (CAPITAL)",
    construccion: "TERMINADA EN 1877",
    estilo: "COLONIAL / BASÍLICA",
    coordenadas: "27°47'S 64°16'O (APROX.)",
    estado: "MONUMENTO HISTÓRICO NACIONAL",
    importancia: "QUINTA CONSTRUCCIÓN EN EL MISMO SOLAR DESDE 1553",
    log: "LOG DE ARCHIVO: catedral basílica de la ciudad más antigua de Argentina aún existente, erigida en basílica menor en 1937. Foto: Diazmerce, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "termas-de-rio-hondo": {
    ubicacion: "TERMAS DE RÍO HONDO, SANTIAGO DEL ESTERO",
    construccion: "CIUDAD BALNEARIA",
    estilo: "AGUAS TERMALES MEDICINALES",
    coordenadas: "27°29'S 64°51'O (APROX.)",
    estado: "ACTIVA",
    importancia: "SEDE DEL AUTÓDROMO INTERNACIONAL (MOTOGP)",
    log: "LOG DE ARCHIVO: ciudad balnearia a orillas del río Dulce, reconocida por sus aguas termales medicinales desde principios del siglo XX. Foto: Antonellamainero, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "convento-santo-domingo": {
    ubicacion: "SANTIAGO DEL ESTERO (CAPITAL)",
    construccion: "ORÍGENES EN EL SIGLO XVI — RECONSTRUIDO EN 1881",
    estilo: "COLONIAL RELIGIOSO",
    coordenadas: "27°47'S 64°16'O (APROX.)",
    estado: "ACTIVA",
    importancia: "UNA DE LAS EDIFICACIONES RELIGIOSAS MÁS ANTIGUAS DEL NOA",
    log: "LOG DE ARCHIVO: convento dominico con imaginería colonial, escenario de hechos históricos ligados a la autonomía provincial santiagueña. Foto: Gergas, CC BY 4.0 (Wikimedia Commons).",
  },
  "panoramica-ushuaia": {
    ubicacion: "USHUAIA, TIERRA DEL FUEGO",
    construccion: "FUNDADA EN 1884",
    estilo: "CIUDAD PORTUARIA AUSTRAL",
    coordenadas: "54°48'S 68°18'O (APROX.)",
    estado: "ACTIVA — CAPITAL PROVINCIAL",
    importancia: "CIUDAD MÁS AUSTRAL DEL MUNDO",
    log: "LOG DE ARCHIVO: enclavada entre el Canal de Beagle y los Andes fueguinos, punto de partida de expediciones antárticas. 'Fin del mundo, principio de todo'. Foto: Balou46, CC BY-SA 4.0 (Wikimedia Commons).",
  },
  "bahia-lapataia-parque-nacional": {
    ubicacion: "PARQUE NACIONAL TIERRA DEL FUEGO",
    construccion: "PARQUE NACIONAL DESDE 1960",
    estilo: "BOSQUE SUBANTÁRTICO Y COSTA",
    coordenadas: "54°51'S 68°33'O (APROX.)",
    estado: "ACTIVO",
    importancia: "FIN DE LA RUTA NACIONAL 3 (KM 3079)",
    log: "LOG DE ARCHIVO: punto donde termina la Panamericana en el extremo sur del continente, dentro del Parque Nacional Tierra del Fuego. Foto: Anabela plos, CC BY 4.0 (Wikimedia Commons).",
  },
  "faro-les-eclaireurs": {
    ubicacion: "CANAL DE BEAGLE, TIERRA DEL FUEGO",
    construccion: "1920",
    estilo: "FARO MARÍTIMO",
    coordenadas: "54°52'S 68°00'O (APROX.)",
    estado: "ACTIVO",
    importancia: "CONOCIDO COMO EL 'FARO DEL FIN DEL MUNDO'",
    log: "LOG DE ARCHIVO: faro sobre un islote rocoso a 9 km de Ushuaia, infaltable en las excursiones náuticas por el Canal de Beagle. Foto: Leandro Neumann Ciuffo, CC BY 2.0 (Wikimedia Commons).",
  },
  "casa-historica-independencia": {
    ubicacion: "SAN MIGUEL DE TUCUMÁN",
    construccion: "CASONA COLONIAL",
    estilo: "COLONIAL",
    coordenadas: "26°49'S 65°12'O (APROX.)",
    estado: "MONUMENTO HISTÓRICO NACIONAL — MUSEO",
    importancia: "DECLARACIÓN DE LA INDEPENDENCIA (9 DE JULIO DE 1816)",
    log: "LOG DE ARCHIVO: en esta casona se reunió el Congreso de Tucumán que declaró la independencia de las Provincias Unidas del Río de la Plata. Foto: Marcelo Ois Lagarde (ChelOis), CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "ruinas-de-quilmes": {
    ubicacion: "VALLES CALCHAQUÍES, TUCUMÁN",
    construccion: "PREHISPÁNICA — DEPORTACIÓN EN 1667",
    estilo: "ARQUITECTURA DIAGUITA",
    coordenadas: "26°30'S 66°01'O (APROX.)",
    estado: "SITIO ARQUEOLÓGICO",
    importancia: "MAYOR ASENTAMIENTO PREHISPÁNICO CONSERVADO DE ARGENTINA",
    log: "LOG DE ARCHIVO: hogar del pueblo diaguita quilmes hasta su deportación forzada por los españoles. Terrazas de cultivo y sistema defensivo en ladera. Foto: Ruarte, CC BY-SA 3.0 (Wikimedia Commons).",
  },
  "cerro-san-javier": {
    ubicacion: "YERBA BUENA / SAN MIGUEL DE TUCUMÁN, TUCUMÁN",
    construccion: "1.361 METROS DE ALTURA",
    estilo: "SIERRA SUBANDINA CON SELVA DE YUNGAS",
    coordenadas: "26°45'S 65°22'O (APROX.)",
    estado: "ACTIVO — DESTINO DE TREKKING",
    importancia: "CRISTO REDENTOR VISIBLE DESDE EL VALLE",
    log: "LOG DE ARCHIVO: cordón serrano cubierto de selva de yungas al oeste de la capital tucumana, destino clásico de trekking y turismo religioso. Foto: Aibdescalzo, dominio público (Wikimedia Commons).",
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

// Excusas de por qué el Pip-Boy no logra triangular bien: siempre la culpa
// es de un espía ruso que hackeó los satélites de la NASA. Rotan al azar en
// cada pintura del Pip-Boy (misma cadencia que el cambio de foto). Cortas
// a propósito: nunca más de 2 líneas, para no romper la UI.
const FRASES_TRIANGULANDO = [
  "SEÑAL PERDIDA...<br>RUSIA HACKEÓ SATÉLITE NASA",
  "RUTA DESVIADA...<br>ESPÍA DEL KREMLIN EN EL GPS",
  "COORDENADAS CORRUPTAS...<br>AGENTE RUSO VULNERÓ LA NASA",
  "TRIANGULANDO...<br>SABOTAJE RUSO EN ÓRBITA",
  "SEÑAL INESTABLE...<br>TOPO RUSO EN CONTROL NASA",
  "GPS DESVIADO...<br>CIBERESPÍA RUSO EN RED NASA",
  "ERROR DE ENLACE...<br>MOSCÚ HACKEÓ EL SATÉLITE",
  "COORDENADAS FALSAS...<br>INFILTRADO RUSO EN LA NASA",
  "CIFRADO ROTO...<br>ESPIONAJE RUSO DETECTADO",
  "REINTENTANDO ENLACE...<br>AGENCIA RUSA HACKEÓ NASA",
];

function fraseTriangulandoAlAzar() {
  return FRASES_TRIANGULANDO[Math.floor(Math.random() * FRASES_TRIANGULANDO.length)];
}

// Convierte "31°25'18\"S 64°11'42\"O" (grados/minutos/segundos, con o sin
// segundos, y el "(APROX.)" que algunas entradas tienen al final) a
// {lat, lng} decimal. Devuelve null si el texto no matchea el formato (ej.
// "PENDIENTE DE TRIANGULACIÓN" del default), para no ofrecer un link roto.
function parseCoordenadasDMS(texto) {
  const regex = /(\d+)\s*°\s*(\d+)'(?:\s*(\d+(?:\.\d+)?)")?\s*([NSEOnseo])/g;
  const matches = [...texto.matchAll(regex)];
  if (matches.length < 2) return null;
  const aDecimal = ([, gStr, mStr, sStr, hemisferio]) => {
    const decimal = Number(gStr) + Number(mStr) / 60 + (sStr ? Number(sStr) / 3600 : 0);
    return /[SOso]/.test(hemisferio) ? -decimal : decimal;
  };
  return { lat: aDecimal(matches[0]), lng: aDecimal(matches[1]) };
}

// Coordenadas interactivas: un click en el texto lleva a ese punto exacto
// en Google Maps. Vale para cualquier imagen de cualquier lugar del país,
// no hace falta tocar nada por ciudad: sale de parsear datos.coordenadas.
function coordenadasHtml(coordenadasTexto) {
  const coords = parseCoordenadasDMS(coordenadasTexto);
  if (!coords) return escapeHtml(coordenadasTexto);
  const url = `https://www.google.com/maps?q=${coords.lat.toFixed(6)},${coords.lng.toFixed(6)}`;
  return `<a class="pipboy-coordenadas-link" href="${escapeHtml(url)}" target="_blank" rel="noopener" title="Ver ubicación en el mapa">${escapeHtml(coordenadasTexto)}</a>`;
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
          <div><b>COORDENADAS:</b> ${coordenadasHtml(datos.coordenadas)}</div>
          <div><b>ESTADO:</b> ${escapeHtml(datos.estado)}</div>
          <div><b>IMPORTANCIA:</b> ${escapeHtml(datos.importancia)}</div>
        </div>
        <hr class="pipboy-linea">
        <div class="pipboy-log">${escapeHtml(datos.log)}</div>
        <div class="pipboy-globo-wrap">
          <div class="pipboy-globo"></div>
          <div class="pipboy-globo-texto">${fraseTriangulandoAlAzar()}</div>
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
  // "auto" explícito (no "", vacío) porque #productos ahora también tiene
  // una regla CSS de height:100% (ver el media query "no scroll" en
  // landing.css): con "" la cascada caía en esa regla en vez de en el alto
  // natural, y la medición de acá abajo quedaba corta — cortando los puntos
  // del selector de fotos por debajo del borde del Pip-Boy.
  el.style.height = "auto";
  el.innerHTML = `
    <div class="carrousel-ciudad-wrap">
      <div class="carrousel-ciudad">
        <div class="carrousel-ciudad-tarjeta visible">${tarjetaLugarHtml(IMAGENES_CIUDAD[indiceCiudad])}</div>
      </div>
      <div class="carrousel-ciudad-puntos"></div>
    </div>
  `;
  pintarPuntosCiudad(el);
  requestAnimationFrame(() => {
    alturaPipboyHomePx = el.getBoundingClientRect().height;
    el.style.height = `${alturaPipboyHomePx}px`;
  });
  if (IMAGENES_CIUDAD.length <= 1) return;
  intervaloCiudad = setInterval(() => avanzarFotoCiudadAlAzar(el), 20000);
}

// --- Carrousel de productos recomendados (Modo Classic, reemplaza al Pip-Boy) ---

// Un producto es "usado" si su nombre o categoría lo indica (CPO también
// cuenta: son celulares con batería usada, ver disclaimer de usados).
function esProductoUsado(p) {
  const texto = `${p.nombre || ""} ${p.categoria || ""}`.toLowerCase();
  return texto.includes("usado") || texto.includes("cpo");
}

// REGLA ABSOLUTA: el carrousel de recomendados de Modo Classic JAMAS
// muestra iPhones usados/CPO (ni ningún otro producto usado).
function productosAlAzar(n) {
  const todos = Object.values(SECCIONES_DATA).flat().filter((p) => !esProductoUsado(p));
  const copia = todos.slice();
  const elegidos = [];
  while (elegidos.length < n && copia.length > 0) {
    const indice = Math.floor(Math.random() * copia.length);
    elegidos.push(copia.splice(indice, 1)[0]);
  }
  return elegidos;
}

// Marcado compartido por tarjetaRecomendadoHtml y tarjetaProducto: ambos
// contenedores (.tarjeta-recomendado-precio y .card .precios) son
// flex-column, así que cada <strong>/<span> ya cae en su propia fila sin
// necesitar <br>.
function bloquePreciosHtml(p) {
  const pr = preciosDe(p);
  return `
    <strong>Dólares: $${formatearPesos(pr.dolares)}</strong>
    <span>Dólar banco USA: $${formatearPesos(pr.bancoUsa)}</span>
    <span>USDT: $${formatearPesos(pr.usdt)}</span>
    <span>Pesos: $${formatearPesos(pr.pesos)}</span>
    <span>Pesos transf: $${formatearPesos(pr.pesosTransf)}</span>
  `;
}

function tarjetaRecomendadoHtml(p) {
  const tieneColores = Array.isArray(p.colores) && p.colores.length > 0;
  const listaColores = tieneColores ? p.colores : ["Color único"];
  // Mismo criterio que tarjetaProducto: siempre "Elegir color" sin nada
  // preseleccionado, Agregar inactivo hasta elegir explícitamente.
  return `
    <div class="tarjeta-recomendado" data-nombre="${escapeHtml(p.nombre)}">
      <h3>${marcaLogoHtml(p.marca, "marca-logo-card")}${escapeHtml(p.nombre)}</h3>
      <p class="tarjeta-recomendado-precio">
        ${bloquePreciosHtml(p)}
        <span class="tarjeta-recomendado-iconos">${botonFotoHtml(p)}${botonEspecificacionesHtml(p)}${botonCompartirHtml()}</span>
      </p>
      <div class="tarjeta-recomendado-acciones">
        <div class="dropdown-color">
          <button type="button" class="dropdown-color-boton" data-valor="">
            Elegir color
          </button>
          <ul class="dropdown-color-lista oculto" role="listbox">
            ${listaColores.map((c) => `<li role="option" data-valor="${escapeHtml(c)}">${escapeHtml(c)}</li>`).join("")}
          </ul>
        </div>
        <button class="btn-agregar" type="button" data-color="" disabled>Agregar</button>
      </div>
    </div>
  `;
}

function esClassicDesktopActivo() {
  return modoVisual === "classic" && window.innerWidth > 700;
}

function productosRecomendados(cantidad, personalizados = false) {
  const pool = personalizados && RECOMENDADOS_DATA.length
    ? barajar(RECOMENDADOS_DATA)
    : productosAlAzar(cantidad);
  const elegidos = pool.slice(0, cantidad);
  // Mandatorio: la grilla siempre debe completar `cantidad` cards. Si el pool
  // personalizado/al azar quedó corto (pocas recomendaciones para el
  // visitante, o pocos productos sin repetir), se rellena con productos al
  // azar del catálogo completo, sin repetir los ya elegidos.
  if (elegidos.length < cantidad) {
    const nombresElegidos = new Set(elegidos.map((p) => p.nombre));
    const relleno = productosAlAzar(cantidad).filter((p) => !nombresElegidos.has(p.nombre));
    for (const p of relleno) {
      if (elegidos.length >= cantidad) break;
      elegidos.push(p);
      nombresElegidos.add(p.nombre);
    }
  }
  return elegidos;
}

function tarjetasRecomendadosHtml(cantidad = 6, personalizados = false) {
  const productos = productosRecomendados(cantidad, personalizados);
  if (!productos.length) {
    return `<div class="tarjeta-recomendado tarjeta-recomendado-vacia"><p>Cargando recomendaciones...</p></div>`;
  }
  return productos.map(tarjetaRecomendadoHtml).join("");
}

function renovarLoteRecomendadosMobile() {
  recomendacionesMobileLote = productosRecomendados(6, false);
  recomendacionesMobileIndice = 0;
}

function tarjetaRecomendadoMobileHtml() {
  if (!recomendacionesMobileLote.length) {
    return `<div class="tarjeta-recomendado tarjeta-recomendado-vacia"><p>Cargando recomendaciones...</p></div>`;
  }
  return tarjetaRecomendadoHtml(recomendacionesMobileLote[recomendacionesMobileIndice]);
}

// Engancha el dropdown de color y "Agregar al carrito" de cada card
// recomendada (mismo patrón que las cards del catálogo normal).
function wireTarjetasRecomendadas(el) {
  const grilla = el.querySelector(".carrousel-recomendados-grid");
  if (!grilla) return;
  const catalogoPlano = Object.values(SECCIONES_DATA).flat();
  grilla.querySelectorAll(".tarjeta-recomendado[data-nombre]").forEach((card) => {
    const producto = catalogoPlano.find((p) => p.nombre === card.dataset.nombre);
    if (!producto) return;
    const btnAgregar = card.querySelector(".btn-agregar");
    const botonColor = card.querySelector(".dropdown-color-boton");
    const listaColor = card.querySelector(".dropdown-color-lista");
    if (botonColor && listaColor) {
      botonColor.addEventListener("click", (e) => {
        e.stopPropagation();
        const yaAbierto = !listaColor.classList.contains("oculto");
        cerrarDropdownsColor();
        if (!yaAbierto) listaColor.classList.remove("oculto");
      });
      listaColor.querySelectorAll("li").forEach((li) => {
        li.addEventListener("click", () => {
          botonColor.textContent = li.dataset.valor;
          botonColor.dataset.valor = li.dataset.valor;
          listaColor.classList.add("oculto");
          btnAgregar.dataset.color = li.dataset.valor;
          btnAgregar.disabled = false;
        });
      });
    }
    if (btnAgregar) {
      btnAgregar.addEventListener("click", async () => {
        await agregarAlCarritoProtegido(producto, btnAgregar.dataset.color || null);
      });
    }
    const btnCompartir = card.querySelector(".btn-compartir");
    if (btnCompartir) {
      btnCompartir.addEventListener("click", (e) => {
        e.stopPropagation();
        compartirProducto(card.dataset.nombre);
      });
    }
    card.addEventListener("click", (e) => {
      if (e.target.closest("button, a, .dropdown-color, li")) return;
      registrarInteraccion("view_item", {
        producto_nombre: producto.nombre,
        categoria: productoSeccion(producto),
        marca: producto.marca || "Otras marcas",
        metadata: { vista: "recomendado" },
      });
    });
  });
}

function iniciarCicloRecomendados(el) {
  clearInterval(intervaloCiudad);
  intervaloCiudad = setInterval(() => {
    const grilla = el.querySelector(".carrousel-recomendados-grid");
    if (!grilla) return;
    grilla.classList.remove("visible");
    setTimeout(() => {
      // Mismos cantidad/personalizados que la pintura inicial (ver
      // pintarCarrouselRecomendados): si no, cada refresco de 12s volvía a
      // una grilla de 6 sin personalizar y dejaba celdas vacías en la
      // grilla de 8 columnas del modo Classic desktop.
      grilla.innerHTML = tarjetasRecomendadosHtml(8, esClassicDesktopActivo());
      wireTarjetasRecomendadas(el);
      grilla.classList.add("visible");
    }, 250);
  }, 12000);
}

function esHomeMobileClassicActivo() {
  const inputBusquedaEl = document.getElementById("input-busqueda");
  const termino = inputBusquedaEl ? inputBusquedaEl.value.trim() : "";
  return modoVisual === "classic" &&
    window.innerWidth <= 700 &&
    !seccionActiva &&
    !filtroMarcaGlobal &&
    termino === "";
}

function ajustarAlturaRecomendadosMobile() {
  const productosEl = document.getElementById("productos");
  if (!productosEl) return;
  if (!esHomeMobileClassicActivo()) {
    productosEl.style.removeProperty("height");
    return;
  }
  // En mobile Classic el alto útil se resuelve por layout CSS: body/fila/main
  // reparten el viewport y el footer queda al final del flujo. Acá solo
  // limpiamos cualquier altura inline vieja para no pelear contra ese layout.
  productosEl.style.removeProperty("height");
}

function avanzarCarrouselRecomendadosMobile(el, direccion = 1) {
  if (!recomendacionesMobileLote.length) renovarLoteRecomendadosMobile();
  if (!recomendacionesMobileLote.length) return;

  if (direccion > 0) {
    if (recomendacionesMobileIndice >= recomendacionesMobileLote.length - 1) {
      renovarLoteRecomendadosMobile();
    } else {
      recomendacionesMobileIndice += 1;
    }
  } else {
    recomendacionesMobileIndice = recomendacionesMobileIndice === 0
      ? recomendacionesMobileLote.length - 1
      : recomendacionesMobileIndice - 1;
  }

  pintarCarrouselRecomendadosMobile(el);
}

function iniciarCicloRecomendadosMobile(el) {
  clearInterval(intervaloCiudad);
  intervaloCiudad = setInterval(() => {
    avanzarCarrouselRecomendadosMobile(el, 1);
  }, 6000);
}

function pintarCarrouselRecomendadosMobile(el) {
  if (!recomendacionesMobileLote.length) renovarLoteRecomendadosMobile();
  ajustarAlturaRecomendadosMobile();
  el.innerHTML = `
    <div class="carrousel-recomendados-wrap carrousel-recomendados-wrap-mobile">
      <div class="carrousel-recomendados-mobile-viewport">
        <div class="carrousel-recomendados-grid carrousel-recomendados-grid-mobile visible">
          <div class="carrousel-recomendados-mobile-card">
            <div class="carrousel-recomendados-mobile-contador">${recomendacionesMobileIndice + 1} / ${recomendacionesMobileLote.length}</div>
            ${tarjetaRecomendadoMobileHtml()}
          </div>
        </div>
      </div>
    </div>
  `;
  wireTarjetasRecomendadas(el);
  const viewport = el.querySelector(".carrousel-recomendados-mobile-viewport");
  if (viewport) {
    let touchInicioX = 0;
    let touchFinX = 0;
    viewport.addEventListener("mouseenter", () => clearInterval(intervaloCiudad));
    viewport.addEventListener("mouseleave", () => iniciarCicloRecomendadosMobile(el));
    viewport.addEventListener("touchstart", (e) => {
      clearInterval(intervaloCiudad);
      touchInicioX = e.changedTouches[0]?.clientX || 0;
      touchFinX = touchInicioX;
    }, { passive: true });
    viewport.addEventListener("touchmove", (e) => {
      touchFinX = e.changedTouches[0]?.clientX || touchFinX;
    }, { passive: true });
    viewport.addEventListener("touchend", () => {
      const deltaX = touchFinX - touchInicioX;
      if (Math.abs(deltaX) > 36) {
        avanzarCarrouselRecomendadosMobile(el, deltaX < 0 ? 1 : -1);
        return;
      }
      iniciarCicloRecomendadosMobile(el);
    }, { passive: true });
  }
  iniciarCicloRecomendadosMobile(el);
  requestAnimationFrame(ajustarAlturaRecomendadosMobile);
}

function pintarCarrouselRecomendados(el) {
  if (modoVisual === "classic" && window.innerWidth <= 700) {
    pintarCarrouselRecomendadosMobile(el);
    return;
  }
  if (modoVisual === "fallout" && alturaPipboyHomePx) {
    // Fallout con el Pip-Boy apagado: mismo alto que tenía prendido (ver
    // alturaPipboyHomePx), así apagarlo no mueve nada de la columna
    // izquierda (switches/reproductor).
    el.style.height = `${alturaPipboyHomePx}px`;
  } else {
    // Con la navegación arriba y sin carrusel de marcas, el main ya ocupa
    // el viewport útil por flujo natural; fijarle altura contra la vieja
    // columna lateral sólo volvería a introducir un límite artificial.
    el.style.height = "";
  }
  const esClassicDesktop = esClassicDesktopActivo();
  // Mandatorio: siempre 8 recomendados en la landing, sin importar el modo.
  const cantidad = 8;
  const personalizados = esClassicDesktop;
  el.innerHTML = `
    <div class="carrousel-recomendados-wrap">
      <div class="carrousel-recomendados-grid visible">${tarjetasRecomendadosHtml(cantidad, personalizados)}</div>
    </div>
  `;
  wireTarjetasRecomendadas(el);
  // Pausa el refresco automático mientras el mouse esté sobre alguna de las
  // 3 cards (dropdown de color, botón agregar), así no cambian de golpe;
  // al salir, retoma el ciclo de 12s. Se engancha una sola vez por pintura
  // completa del carrousel (el nodo .carrousel-recomendados-grid persiste
  // entre refrescos, solo cambia su innerHTML).
  const grilla = el.querySelector(".carrousel-recomendados-grid");
  if (grilla) {
    grilla.addEventListener("mouseenter", () => clearInterval(intervaloCiudad));
    grilla.addEventListener("mouseleave", () => iniciarCicloRecomendados(el));
  }
  iniciarCicloRecomendados(el);
}

// --- Modo visual: Fallout (default) / Classic ---

function pintarCarrouselSegunModo(el) {
  if (modoVisual === "classic" || pipboyApagado) pintarCarrouselRecomendados(el);
  else pintarCarrouselCiudad(el);
}

// Main Switch (barra lateral, arriba del Power Switch): apaga/enciende el
// Pip-Boy. Apagado, la foto se reemplaza por el mismo carrousel de
// recomendados que Modo Classic, con la temática Fallout. Al apagar, el
// Pip-Boy (no toda la pantalla) hace la animación de TV vieja apagándose,
// con un click de interruptor real; al encender, la animación inversa.
let pipboyEnTransicion = false;
const btnPipboySwitch = document.getElementById("btn-pipboy-switch");
if (btnPipboySwitch) {
  btnPipboySwitch.addEventListener("click", () => {
    const productosEl = document.getElementById("productos");
    if (!productosEl || pipboyEnTransicion) return;
    sonidoClickSwitch();
    if (!pipboyApagado) {
      const pipboyEl = productosEl.querySelector(".pipboy");
      btnPipboySwitch.classList.add("apagado");
      btnPipboySwitch.setAttribute("aria-pressed", "false");
      detenerCarrouselCiudad();
      if (!pipboyEl) {
        pipboyApagado = true;
        pintarCarrouselRecomendados(productosEl);
        return;
      }
      pipboyEnTransicion = true;
      pipboyEl.classList.add("rc-tv-apagando");
      setTimeout(() => {
        pipboyApagado = true;
        pintarCarrouselRecomendados(productosEl);
        pipboyEnTransicion = false;
      }, 520);
    } else {
      btnPipboySwitch.classList.remove("apagado");
      btnPipboySwitch.setAttribute("aria-pressed", "true");
      pipboyApagado = false;
      pintarCarrouselCiudad(productosEl);
      const nuevoPipboy = productosEl.querySelector(".pipboy");
      if (nuevoPipboy) {
        nuevoPipboy.classList.add("rc-tv-prendiendo");
        setTimeout(() => nuevoPipboy.classList.remove("rc-tv-prendiendo"), 450);
      }
    }
  });
}

// Botón "Play Music": sin panel visible, controlado por la IFrame API
// oficial de Spotify (developer.spotify.com/documentation/embeds), que sí
// soporta .play()/.pause() por código ante un click real — a mano, armando
// la URL con "?autoplay=1", Spotify simplemente lo ignora y no suena.
//
// Ojo con el gesto del usuario: el navegador solo deja sonar audio si
// .play() se llama DENTRO del propio click (mismo tick). Si el usuario
// clickeaba antes de que el script async de Spotify terminara de cargar,
// quedaba pendiente y el .play() se disparaba después, ya sin el gesto
// activo — el navegador lo bloqueaba en silencio. Por eso el botón arranca
// deshabilitado y solo se habilita con el evento "ready" del controller
// (no alcanza con que exista el controller: el player interno todavía
// puede no estar listo), garantizando que el click siempre dispare
// .play() de una, con el gesto todavía válido.
// La API oficial de Spotify no tiene salto de pista (solo
// play/pause/resume/togglePlay/restart/seek(segundos)/loadUri — confirmado
// contra developer.spotify.com/documentation/embeds/references/iframe-api).
// FF/RW simulan "siguiente/anterior" cargando a mano el track puntual (con
// loadUri) de esta lista fija, en el mismo orden de la playlist de Spotify.
const SPOTIFY_PLAYLIST_URI = "spotify:playlist:5RI1Q9tVzZkQInxpYmrARl";
const TRACKS_PLAYLIST = [
  "spotify:track:777zXDJpBufzttU4AJ2dGO",
  "spotify:track:5RLzsVW6UNiV2YrOlKwzNN",
  "spotify:track:6njnfScNr2pZuIdl0NcpEr",
  "spotify:track:5DTOOkooKFUvWj1XQTFa09",
  "spotify:track:1VttkRYAvi1036Fz0aOhWL",
  "spotify:track:0AQquaENerGps8BQmbPw14",
  "spotify:track:7coH7f2P7SiLxmo95b5QHX",
  "spotify:track:0wAtFj61WZQpKX3g79eyT2",
  "spotify:track:2xYlyywNgefLCRDG8hlxZq",
  "spotify:track:39tCr7Wn7yhgM15JUJmXWl",
  "spotify:track:0lWeRB7pSOZ6wIpqY1W4Uw",
];
const DOBLE_TOQUE_RW_MS = 500;
const btnPlayMusic = document.getElementById("btn-play-music");
const btnMusicaRw = document.getElementById("btn-musica-rw");
const btnMusicaFf = document.getElementById("btn-musica-ff");
let spotifyController = null;
let musicaSonando = false;
let posicionActualMs = 0;
let duracionActualMs = 0;
let indiceTrackActual = 0;
let ultimoToqueRwMs = 0;

[btnPlayMusic, btnMusicaRw, btnMusicaFf].forEach((b) => { if (b) b.disabled = true; });

window.onSpotifyIframeApiReady = (IFrameAPI) => {
  const elemento = document.getElementById("rc-musica-embed");
  if (!elemento) return;
  IFrameAPI.createController(elemento, { uri: SPOTIFY_PLAYLIST_URI }, (EmbedController) => {
    spotifyController = EmbedController;
    EmbedController.addListener("ready", () => {
      [btnPlayMusic, btnMusicaRw, btnMusicaFf].forEach((b) => { if (b) b.disabled = false; });
    });
    // Refleja el estado real de reproducción (en vez de asumirlo nosotros),
    // por si el usuario para/sigue la música desde otro lado, y guarda la
    // posición actual para que RW/FF puedan calcular el segundo destino.
    // playingURI, además, es lo único que nos deja mantener sincronizado
    // indiceTrackActual con el tema real (por si la playlist no arranca
    // por el primero de TRACKS_PLAYLIST).
    EmbedController.addListener("playback_update", (e) => {
      musicaSonando = !e.data.isPaused;
      posicionActualMs = e.data.position;
      duracionActualMs = e.data.duration;
      const idx = TRACKS_PLAYLIST.indexOf(e.data.playingURI);
      if (idx !== -1) indiceTrackActual = idx;
      if (btnPlayMusic) btnPlayMusic.classList.toggle("sonando", musicaSonando);
      const ecualizadorEl = document.querySelector(".rc-ecualizador");
      if (ecualizadorEl) ecualizadorEl.classList.toggle("sonando", musicaSonando);
    });
  });
};

if (btnPlayMusic) {
  btnPlayMusic.addEventListener("click", () => {
    if (!spotifyController) return;
    if (musicaSonando) spotifyController.pause();
    else spotifyController.play();
  });
}

function cargarTrack(indice) {
  indiceTrackActual = ((indice % TRACKS_PLAYLIST.length) + TRACKS_PLAYLIST.length) % TRACKS_PLAYLIST.length;
  spotifyController.loadUri(TRACKS_PLAYLIST[indiceTrackActual]);
  spotifyController.play();
}

// RW: un toque reinicia el tema actual (como el back de cualquier
// reproductor); un segundo toque rápido (antes de DOBLE_TOQUE_RW_MS) pasa
// al tema anterior en vez de reiniciar de nuevo.
if (btnMusicaRw) {
  btnMusicaRw.addEventListener("click", () => {
    if (!spotifyController) return;
    const ahora = Date.now();
    if (ahora - ultimoToqueRwMs < DOBLE_TOQUE_RW_MS) {
      cargarTrack(indiceTrackActual - 1);
    } else {
      spotifyController.restart();
    }
    ultimoToqueRwMs = ahora;
  });
}
if (btnMusicaFf) {
  btnMusicaFf.addEventListener("click", () => {
    if (!spotifyController) return;
    cargarTrack(indiceTrackActual + 1);
  });
}

// Visor del botón de música: no leemos el track real de Spotify (haría
// falta autenticar contra su API, fuera de alcance acá), así que es un
// detalle ambiente como el ecualizador — clásicos instrumentales de jazz,
// rotando cada tanto, en crawl continuo (2 copias del texto + loop -50%).
const CLASICOS_JAZZ_INSTRUMENTAL = [
  "Miles Davis — Blue in Green",
  "Bill Evans Trio — Waltz for Debby",
  "John Coltrane — Naima",
  "Dave Brubeck — Take Five",
  "Chet Baker — My Funny Valentine",
  "Thelonious Monk — Round Midnight",
  "Duke Ellington — In a Sentimental Mood",
  "Stan Getz & João Gilberto — Corcovado",
];

function pintarVisorMusica() {
  const visor = document.getElementById("rc-visor-texto");
  if (!visor) return;
  const texto = CLASICOS_JAZZ_INSTRUMENTAL[Math.floor(Math.random() * CLASICOS_JAZZ_INSTRUMENTAL.length)];
  visor.innerHTML = `<span>${escapeHtml(texto)}</span><span>${escapeHtml(texto)}</span>`;
}
pintarVisorMusica();
setInterval(pintarVisorMusica, 25000);

// El favicon cambia junto con el modo: monograma navy/rojo en Classic,
// verde fósforo estilo Pip-Boy en Fallout.
function actualizarFavicon(modo) {
  const link = document.querySelector('link[rel="icon"]');
  if (!link) return;
  link.href = modo === "fallout" ? "favicon-fallout.svg" : "favicon.svg";
}

function aplicarLayoutCatalogoPorModo(modo) {
  const header = document.querySelector("header");
  const headerCentro = document.querySelector(".rc-header-centro");
  const headerNav = document.querySelector(".rc-header-nav");
  const categoriasClassicWrap = document.getElementById("rc-categorias-classic-wrap");
  const columnaIzquierda = document.getElementById("columna-izquierda-layout");
  const buscador = document.querySelector(".rc-buscador-header");
  const switches = document.getElementById("rc-switches-fallout-wrap");
  if (!header || !headerCentro || !headerNav || !categoriasClassicWrap || !columnaIzquierda || !buscador || !switches) return;

  if (modo === "fallout") {
    if (buscador.parentElement !== columnaIzquierda) columnaIzquierda.prepend(buscador);
    if (headerNav.parentElement !== columnaIzquierda) columnaIzquierda.appendChild(headerNav);
    if (switches.parentElement !== columnaIzquierda) columnaIzquierda.appendChild(switches);
    return;
  }

  const noticiero = headerCentro.querySelector(".rc-noticiero");
  if (noticiero) {
    if (buscador.previousElementSibling !== null || buscador.parentElement !== headerCentro) {
      headerCentro.insertBefore(buscador, noticiero);
    }
  } else if (buscador.parentElement !== headerCentro) {
    headerCentro.appendChild(buscador);
  }
  if (headerNav.parentElement !== categoriasClassicWrap) categoriasClassicWrap.appendChild(headerNav);
  if (switches.parentElement !== header) header.appendChild(switches);
}

function aplicarModoVisual(modo, opciones) {
  const opts = opciones || {};
  modoVisual = modo;
  document.documentElement.setAttribute("data-modo", modo);
  document.querySelectorAll(".btn-modo").forEach((b) => {
    b.classList.toggle("activo", b.dataset.modo === modo);
  });
  actualizarFavicon(modo);
  aplicarLayoutCatalogoPorModo(modo);
  // La música (si estaba sonando) sigue de fondo al navegar por secciones
  // dentro de Fallout — el iframe de Spotify vive fuera de #productos, así
  // que no se toca al repintar la vista. Solo se corta acá, al pasar a
  // Classic (ese modo no tiene reproductor ni forma de controlarla).
  if (modo === "classic" && spotifyController && musicaSonando) spotifyController.pause();
  if (opts.sinRepintar) return;
  const carrouselMarcasEl = document.getElementById("carrousel");
  if (carrouselMarcasEl) iniciarDesplazamientoCarrousel(carrouselMarcasEl);
  // Cambiar de modo siempre vuelve al home: lo único que persiste entre
  // Classic y Fallout es el carrito (localStorage aparte, ajeno a esto).
  // Cualquier sección, filtro de marca, sub-filtro o búsqueda en curso se
  // descarta.
  seccionActiva = null;
  subFiltrosActivos = new Set();
  filtroMarcaGlobal = null;
  profundidadHistorial = 0;
  pipboyApagado = false;
  const btnPipboySwitchReset = document.getElementById("btn-pipboy-switch");
  if (btnPipboySwitchReset) {
    btnPipboySwitchReset.classList.remove("apagado");
    btnPipboySwitchReset.setAttribute("aria-pressed", "true");
  }
  const inputBusqueda = document.getElementById("input-busqueda");
  if (inputBusqueda) inputBusqueda.value = "";
  actualizarVista();
}

function entrarAModoFallout() {
  transicionandoAFallout = true;
  aplicarModoVisual("fallout");
  if (typeof window.reproducirBootSequenceTTRA === "function") {
    window.reproducirBootSequenceTTRA(() => {
      // Recién cuando el user llega al home de Fallout (boot terminado) se
      // corta la música, con un fade out suave en vez de un corte seco.
      desvanecerAudioModoFallout();
      transicionandoAFallout = false;
    });
  } else {
    transicionandoAFallout = false;
  }
}

const btnLogoFallout = document.getElementById("btn-logo-fallout");
if (btnLogoFallout) {
  btnLogoFallout.addEventListener("click", entrarAModoFallout);
}
const btnModoClassic = document.getElementById("btn-modo-classic");
if (btnModoClassic) btnModoClassic.addEventListener("click", () => {
  if (modoVisual !== "fallout") {
    aplicarModoVisual("classic");
    return;
  }
  // Viniendo de Fallout: efecto "apagado de TV vieja" (colapsa a una línea
  // y luego a un punto, todo a negro) antes de mostrar Classic, y un
  // "encendido" simétrico (crece desde el punto) al entrar.
  document.body.classList.add("rc-tv-apagando");
  setTimeout(() => {
    document.body.classList.remove("rc-tv-apagando");
    aplicarModoVisual("classic");
    document.body.classList.add("rc-tv-prendiendo");
    setTimeout(() => document.body.classList.remove("rc-tv-prendiendo"), 450);
  }, 520);
});
aplicarModoVisual(modoVisual, { sinRepintar: true });

// --- Log out: pedir "Cerrar sesión" (botón en Classic, switch "LOG OUT" en
// Fallout) SOLO abre un diálogo de confirmación — no cierra la sesión
// automáticamente. Recién si el usuario confirma se borra el registro del
// cliente (nombre/celular del gate inicial) y se muestra el mensaje final;
// si cancela, no cambia nada. Al cerrar el mensaje final se recarga la
// página, así vuelve a aparecer el gate para volver a identificarse. ---
function mostrarConfirmacionLogout() {
  const confirmar = document.getElementById("rc-logout-confirmar");
  if (confirmar) confirmar.classList.add("visible");
}

function ocultarConfirmacionLogout() {
  const confirmar = document.getElementById("rc-logout-confirmar");
  if (confirmar) confirmar.classList.remove("visible");
}

// --- Popup obligatorio de condiciones mayoristas: se muestra una sola vez,
// la primera vez que una cuenta mayorista entra a la landing (chequeado
// contra clientes.condiciones_mayorista_aceptadas_en en /api/me). No tiene
// forma de cerrarlo sin aceptar — ni botón cancelar ni click afuera — y el
// botón "Acepto" arranca deshabilitado hasta que se llega al final del
// scroll. Desde el perfil se reabre en modo solo lectura ("ver"), con botón
// "Cerrar" en vez de "Acepto". ---
const overlayTerminosMayorista = document.getElementById("rc-terminos-mayorista");
const contenidoTerminosMayorista = document.getElementById("rc-terminos-contenido");
const btnTerminosAceptar = document.getElementById("btn-terminos-aceptar");
const btnTerminosCerrar = document.getElementById("btn-terminos-cerrar");
let fragmentoTerminosMayoristaCache = null;

async function cargarFragmentoTerminosMayorista() {
  if (fragmentoTerminosMayoristaCache) return fragmentoTerminosMayoristaCache;
  try {
    const r = await fetch("/condiciones-mayorista.html");
    fragmentoTerminosMayoristaCache = r.ok
      ? await r.text()
      : "<p>No pudimos cargar las condiciones mayoristas. Recargá la página.</p>";
  } catch {
    fragmentoTerminosMayoristaCache = "<p>No pudimos cargar las condiciones mayoristas. Recargá la página.</p>";
  }
  return fragmentoTerminosMayoristaCache;
}

async function mostrarModalTerminosMayorista(modo) {
  if (!overlayTerminosMayorista || !contenidoTerminosMayorista) return;
  contenidoTerminosMayorista.innerHTML = await cargarFragmentoTerminosMayorista();
  contenidoTerminosMayorista.scrollTop = 0;
  const esAceptar = modo === "aceptar";
  if (btnTerminosAceptar) btnTerminosAceptar.classList.toggle("oculto", !esAceptar);
  if (btnTerminosCerrar) btnTerminosCerrar.classList.toggle("oculto", esAceptar);
  if (esAceptar && btnTerminosAceptar) {
    btnTerminosAceptar.disabled = true;
    btnTerminosAceptar.textContent = "Acepto";
    const alLlegarAlFinal = () => {
      const { scrollTop, clientHeight, scrollHeight } = contenidoTerminosMayorista;
      if (scrollTop + clientHeight >= scrollHeight - 4) {
        btnTerminosAceptar.disabled = false;
        contenidoTerminosMayorista.removeEventListener("scroll", alLlegarAlFinal);
      }
    };
    contenidoTerminosMayorista.addEventListener("scroll", alLlegarAlFinal);
    // Por si el contenido ya entra completo sin necesidad de scrollear.
    requestAnimationFrame(alLlegarAlFinal);
  }
  overlayTerminosMayorista.classList.add("visible");
}

function ocultarModalTerminosMayorista() {
  if (overlayTerminosMayorista) overlayTerminosMayorista.classList.remove("visible");
}

if (btnTerminosCerrar) {
  btnTerminosCerrar.addEventListener("click", ocultarModalTerminosMayorista);
}

if (btnTerminosAceptar) {
  btnTerminosAceptar.addEventListener("click", async () => {
    btnTerminosAceptar.disabled = true;
    btnTerminosAceptar.textContent = "Guardando...";
    try {
      const r = await fetch("/api/me/condiciones-mayorista", { method: "POST" });
      if (!r.ok) throw new Error("No se pudo guardar la aceptación");
      const datos = await r.json();
      if (estadoSesionCliente) {
        estadoSesionCliente.condiciones_mayorista_aceptadas_en = datos.condiciones_mayorista_aceptadas_en;
      }
      ocultarModalTerminosMayorista();
    } catch {
      alert("No pudimos guardar tu aceptación. Probá de nuevo.");
      btnTerminosAceptar.disabled = false;
      btnTerminosAceptar.textContent = "Acepto";
    }
  });
}

function verificarCondicionesMayoristaPendientes(sesion) {
  if (!sesion || sesion.tipo_cliente !== "mayorista" || sesion.condiciones_mayorista_aceptadas_en) return;
  mostrarModalTerminosMayorista("aceptar");
}

async function cerrarSesionCliente() {
  try {
    localStorage.removeItem("ttra_cliente");
  } catch {
    // Sin localStorage no había nada que borrar: no es crítico.
  }
  try {
    await fetch("/logout", { method: "POST" });
  } catch {
    // Si falla la llamada de red, igual redirigimos: la sesión del server
    // puede seguir viva, pero no tiene sentido bloquear al usuario acá.
  }
  estadoSesionCliente = null;
  cerrarMenuPerfil();
  window.location.href = "/";
}

// --- Menú de perfil del header: botón con nombre + ícono redondo que
// despliega "Ir a perfil" (los dos modos) y "Cerrar sesión" (solo Classic;
// en Fallout ese log out sigue siendo el interruptor de la barra lateral).
const menuPerfil = document.getElementById("rc-perfil-menu");
const btnPerfilToggle = document.getElementById("btn-perfil-toggle");
const dropdownPerfil = document.getElementById("rc-perfil-dropdown");
const linkIrAPerfil = document.getElementById("link-ir-a-perfil");
const btnClassicTheme = document.getElementById("btn-classic-theme");

function cerrarMenuPerfil() {
  if (!dropdownPerfil) return;
  dropdownPerfil.classList.add("oculto");
  if (btnPerfilToggle) btnPerfilToggle.setAttribute("aria-expanded", "false");
}

if (btnPerfilToggle && dropdownPerfil) {
  btnPerfilToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    const abierto = !dropdownPerfil.classList.contains("oculto");
    if (abierto) {
      cerrarMenuPerfil();
    } else {
      dropdownPerfil.classList.remove("oculto");
      btnPerfilToggle.setAttribute("aria-expanded", "true");
    }
  });
  document.addEventListener("click", (e) => {
    if (menuPerfil && !menuPerfil.contains(e.target)) cerrarMenuPerfil();
  });
}

if (linkIrAPerfil) {
  linkIrAPerfil.addEventListener("click", (e) => {
    e.preventDefault();
    const destinoPerfil = modoVisual === "fallout" ? "/perfil?modo=fallout" : "/perfil";
    const paramsLogin = new URLSearchParams({ volver: `${location.pathname}${location.search}` });
    if (modoVisual === "fallout") paramsLogin.set("modo", "fallout");
    const destinoLogin = `/login.html?${paramsLogin.toString()}`;
    window.location.href = estadoSesionCliente ? destinoPerfil : destinoLogin;
  });
}

if (btnClassicTheme) {
  btnClassicTheme.addEventListener("click", () => {
    const temaActual = document.documentElement.getAttribute("data-classic-theme");
    aplicarTemaClassic(temaActual === "light" ? "dark" : "light", true);
  });
}

function inicialesDe(nombre, apellido) {
  const inicial = (texto) => (texto || "").trim().charAt(0).toUpperCase();
  return `${inicial(nombre)}${inicial(apellido)}`;
}

async function cargarInicialesHeader() {
  const el = document.getElementById("perfil-primer-nombre");
  if (!el) return;
  try {
    const r = await fetch("/api/me");
    if (!r.ok) {
      el.textContent = "";
      return;
    }
    const datos = await r.json();
    el.textContent = inicialesDe(datos.nombre, datos.apellido);
  } catch {
    el.textContent = "";
  }
}

const btnLogoutClassic = document.getElementById("btn-logout-classic");
const btnLogoutFallout = document.getElementById("btn-logout-fallout");

async function sincronizarMenuPerfilSegunSesion(force = false) {
  const sesion = await obtenerEstadoSesionCliente(force);
  await cargarInicialesHeader();
  if (linkIrAPerfil) {
    linkIrAPerfil.textContent = sesion ? "Ir a perfil" : "Iniciar sesión";
  }
  if (btnLogoutClassic) {
    btnLogoutClassic.classList.toggle("oculto", !sesion);
  }
  if (btnLogoutFallout) {
    btnLogoutFallout.classList.toggle("oculto", !sesion);
  }
  return sesion;
}
sincronizarMenuPerfilSegunSesion(true).then(verificarCondicionesMayoristaPendientes);

if (btnLogoutClassic) {
  btnLogoutClassic.addEventListener("click", () => {
    cerrarMenuPerfil();
    mostrarConfirmacionLogout();
  });
}

if (btnLogoutFallout) {
  btnLogoutFallout.addEventListener("click", mostrarConfirmacionLogout);
}

const btnLogoutConfirmarSi = document.getElementById("btn-logout-confirmar-si");
if (btnLogoutConfirmarSi) {
  btnLogoutConfirmarSi.addEventListener("click", () => {
    ocultarConfirmacionLogout();
    if (btnLogoutFallout) {
      btnLogoutFallout.classList.add("apagado");
      btnLogoutFallout.setAttribute("aria-pressed", "false");
    }
    cerrarSesionCliente();
  });
}

const btnLogoutConfirmarNo = document.getElementById("btn-logout-confirmar-no");
if (btnLogoutConfirmarNo) {
  btnLogoutConfirmarNo.addEventListener("click", ocultarConfirmacionLogout);
}

const btnLogoutCerrar = document.getElementById("btn-logout-cerrar");
if (btnLogoutCerrar) {
  btnLogoutCerrar.addEventListener("click", () => location.reload());
}

// Al pasar el mouse sobre "Modo Fallout" suena el tema de radio de Fallout;
// se corta apenas el cursor se va del botón. Excepción: si el user ya hizo
// click para pasar a Fallout, la música sigue sonando durante todo el boot
// (el mouse se va del botón apenas aparece el overlay, pero no hay que
// cortarla ahí) y recién se desvanece cuando termina, en el home de Fallout.
let transicionandoAFallout = false;
const audioModoFallout = document.getElementById("audio-modo-fallout");

function desvanecerAudioModoFallout() {
  if (!audioModoFallout || audioModoFallout.paused) return;
  const pasoMs = 40;
  const duracionMs = 900;
  const decremento = 1 / (duracionMs / pasoMs);
  const intervalo = setInterval(() => {
    audioModoFallout.volume = Math.max(0, audioModoFallout.volume - decremento);
    if (audioModoFallout.volume <= 0) {
      clearInterval(intervalo);
      audioModoFallout.pause();
      audioModoFallout.currentTime = 0;
      audioModoFallout.volume = 1;
    }
  }, pasoMs);
}

if (btnLogoFallout && audioModoFallout) {
  btnLogoFallout.addEventListener("mouseenter", () => {
    if (transicionandoAFallout) return;
    audioModoFallout.currentTime = 0;
    audioModoFallout.volume = 1;
    audioModoFallout.play().catch(() => {
      // Autoplay bloqueado hasta el primer gesto del usuario: no es crítico.
    });
  });
  btnLogoFallout.addEventListener("mouseleave", () => {
    if (transicionandoAFallout) return;
    audioModoFallout.pause();
    audioModoFallout.currentTime = 0;
  });
}

// Estando en Fallout, pasar el mouse sobre "Modo Classic" (el único botón
// de modo visible ahí) suena un abucheo sintetizado, en tono de broma.
function reproducirAbucheo() {
  try {
    audioCtxInteraccion = audioCtxInteraccion
      || new (window.AudioContext || window.webkitAudioContext)();
    const ctx = audioCtxInteraccion;
    if (ctx.state === "suspended") ctx.resume();

    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    const lfo = ctx.createOscillator();
    const lfoGain = ctx.createGain();

    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(300, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(85, ctx.currentTime + 0.8);

    lfo.frequency.value = 7; // tremolo, para que suene a "abucheo" y no a sirena
    lfoGain.gain.value = 0.05;
    lfo.connect(lfoGain);

    gain.gain.setValueAtTime(0.0001, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.09, ctx.currentTime + 0.08);
    gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 0.85);
    lfoGain.connect(gain.gain);

    osc.connect(gain).connect(ctx.destination);
    osc.start();
    lfo.start();
    osc.stop(ctx.currentTime + 0.9);
    lfo.stop(ctx.currentTime + 0.9);
  } catch {
    // Web Audio no disponible: seguimos sin sonido, no es crítico.
  }
}
if (btnModoClassic) {
  btnModoClassic.addEventListener("mouseenter", () => {
    if (modoVisual === "fallout") reproducirAbucheo();
  });
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
  // Modo Classic: el glitch tipo CRT queda desactivado por CSS, así que en su
  // lugar hacemos un fade-out/fade-in del contenido para suavizar el salto de
  // layout entre el menú principal y una sub-sección.
  if (modoVisual === "classic") {
    contenedor.classList.add("rc-fade");
    setTimeout(() => {
      cambiarContenido();
      void contenedor.offsetWidth;
      contenedor.classList.remove("rc-fade");
    }, 180);
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
    (m) => `<span data-marca="${escapeHtml(m)}" tabindex="0" role="button">${marcaLogoHtml(m, "marca-logo-carrousel")}${escapeHtml(etiquetaMarca(m))}</span>`
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
let intervaloMarcas = null;
let resizeHandlerMarcas = null;

// Reutilizable: se vuelve a llamar al cambiar de Modo en vivo (Fallout <->
// Classic), así que primero limpia cualquier intervalo/listener de una
// llamada anterior antes de arrancar (o de quedarse fijo en Classic).
function iniciarDesplazamientoCarrousel(el) {
  if (intervaloMarcas) {
    clearInterval(intervaloMarcas);
    intervaloMarcas = null;
  }
  if (resizeHandlerMarcas) {
    window.removeEventListener("resize", resizeHandlerMarcas);
    resizeHandlerMarcas = null;
  }

  // En Modo Classic el carrousel de marcas queda fijo, sin desplazamiento.
  if (modoVisual === "classic") {
    el.style.transform = "translateX(0)";
    return;
  }

  const tandas = el.querySelectorAll(".carrousel-tanda");
  const primeraTanda = tandas[0];
  let posicion = 0;
  let anchoTanda = 0;

  // Ground truth: la distancia real entre el inicio de la 2da tanda y el de
  // la 1ra (offsetLeft, no depende de parsear "gap" por getComputedStyle,
  // que en algunos navegadores lo devuelve vacío para flex y desincroniza
  // el punto de reinicio — eso era el glitch/blanco después de la última
  // marca de cada tanda). Como las dos tandas son un copy-paste exacto del
  // mismo HTML, esa distancia es exactamente el período del loop.
  function medirAncho() {
    anchoTanda = tandas.length > 1
      ? tandas[1].offsetLeft - tandas[0].offsetLeft
      : primeraTanda.getBoundingClientRect().width;
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
    if (intervaloMarcas) clearInterval(intervaloMarcas);
    intervaloMarcas = setInterval(paso, 60);
  }

  // Espera tipografía Y logos (Modo Classic) antes de la primera medición:
  // un <img> de marca sin decodificar todavía puede rendir con otro ancho
  // y desalinear igual el punto de reinicio.
  const imagenesListas = Promise.all(
    Array.from(el.querySelectorAll("img")).map((img) =>
      img.decode ? img.decode().catch(() => {}) : Promise.resolve()
    )
  );
  const listoParaMedir = Promise.all([
    document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve(),
    imagenesListas,
  ]);
  listoParaMedir.then(iniciar);

  resizeHandlerMarcas = () => {
    posicion = 0;
    el.style.transform = "translateX(0)";
    iniciar();
  };
  window.addEventListener("resize", resizeHandlerMarcas);
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  // innerHTML escapa &/</> pero NO las comillas (no hace falta para texto
  // suelto) — acá SÍ hace falta, porque el resultado se usa también dentro
  // de atributos HTML entre comillas dobles (data-nombre="...", href="...").
  // Un nombre de producto con " literal (ej. notebooks/iPads con pulgadas,
  // "15.6""), sin este reemplazo, cerraba el atributo antes de tiempo y
  // rompía el HTML — el botón "Agregar al carrito" quedaba con un
  // data-nombre truncado que nunca matcheaba ningún producto real, así que
  // el click no hacía nada, en silencio.
  return div.innerHTML.replaceAll('"', "&quot;").replaceAll("'", "&#39;");
}

async function obtenerEstadoSesionCliente(force = false) {
  if (!force && estadoSesionCliente !== null) return estadoSesionCliente;
  try {
    const r = await fetch("/api/me");
    if (!r.ok) {
      estadoSesionCliente = null;
      return null;
    }
    estadoSesionCliente = await r.json();
    return estadoSesionCliente;
  } catch {
    estadoSesionCliente = null;
    return null;
  }
}

function guardarPendienteCarrito(producto, color) {
  sessionStorage.setItem(CLAVE_CARRITO_PENDIENTE, JSON.stringify({
    nombre: producto.nombre,
    color: color || null,
  }));
}

function leerPendienteCarrito() {
  try {
    return JSON.parse(sessionStorage.getItem(CLAVE_CARRITO_PENDIENTE) || "null");
  } catch {
    return null;
  }
}

function borrarPendienteCarrito() {
  sessionStorage.removeItem(CLAVE_CARRITO_PENDIENTE);
}

function guardarPendienteCheckout() {
  localStorage.setItem(CLAVE_CHECKOUT_PENDIENTE, "1");
}

function hayCheckoutPendiente() {
  return localStorage.getItem(CLAVE_CHECKOUT_PENDIENTE) === "1";
}

function borrarCheckoutPendiente() {
  localStorage.removeItem(CLAVE_CHECKOUT_PENDIENTE);
}

function paramsMailingActuales() {
  const params = new URLSearchParams(location.search);
  return {
    producto: params.get("producto"),
    codigo: (params.get("codigo") || "").trim().toUpperCase(),
    agregar: params.get("agregar") === "1",
    modo: params.get("modo"),
  };
}

function limpiarParametrosMailingProcesados() {
  const params = new URLSearchParams(location.search);
  params.delete("agregar");
  params.delete("codigo");
  const query = params.toString();
  history.replaceState({}, "", `${location.pathname}${query ? `?${query}` : ""}`);
}

function urlLoginParaCarrito() {
  const params = new URLSearchParams();
  params.set("registro", "1");
  params.set("volver", `${location.pathname}${location.search}`);
  if (modoVisual === "fallout") params.set("modo", "fallout");
  return `/login.html?${params.toString()}`;
}

async function asegurarSesionParaCarrito(producto, color) {
  const sesion = await obtenerEstadoSesionCliente(true);
  if (sesion && !sesion.debe_cambiar_password) return true;
  guardarPendienteCarrito(producto, color);
  window.location.href = urlLoginParaCarrito();
  return false;
}

// Ícono de cámara (SVG, no emoji): lleva a una búsqueda de Google Imágenes
// del producto en una pestaña nueva, mismo link_imagen que ya arma el
// catálogo por cada ítem.
const ICONO_CAMARA_SVG = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M4 8.5C4 7.67157 4.67157 7 5.5 7H7.5L8.5 5.5H15.5L16.5 7H18.5C19.3284 7 20 7.67157 20 8.5V17.5C20 18.3284 19.3284 19 18.5 19H5.5C4.67157 19 4 18.3284 4 17.5V8.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
  <circle cx="12" cy="13" r="3.4" stroke="currentColor" stroke-width="1.6"/>
</svg>`;

function botonFotoHtml(p) {
  if (!p.link_imagen) return "";
  return `<a class="btn-foto" href="${escapeHtml(p.link_imagen)}" target="_blank" rel="noopener" title="Ver fotos en Google Imágenes" aria-label="Ver fotos en Google Imágenes">${ICONO_CAMARA_SVG}</a>`;
}

// Ícono de especificaciones (SVG, no emoji): a la derecha del de cámara,
// misma fila. Busca el producto en Google agregando siempre la palabra
// "especificaciones", para ir directo a fichas técnicas en vez de una
// búsqueda genérica del nombre.
const ICONO_ESPECIFICACIONES_SVG = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect x="5" y="4" width="14" height="16" rx="1.5" stroke="currentColor" stroke-width="1.6"/>
  <line x1="8" y1="8.5" x2="16" y2="8.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="8" y1="12" x2="16" y2="12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="8" y1="15.5" x2="13" y2="15.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>`;

function botonEspecificacionesHtml(p) {
  const url = `https://www.google.com/search?q=${encodeURIComponent(`${p.nombre} especificaciones`)}`;
  return `<a class="btn-foto" href="${escapeHtml(url)}" target="_blank" rel="noopener" title="Ver especificaciones en Google" aria-label="Ver especificaciones en Google">${ICONO_ESPECIFICACIONES_SVG}</a>`;
}

// Ícono de compartir (SVG, no emoji): a la derecha del de especificaciones,
// misma fila. No es un link — dispara compartirProducto (copia el link al
// portapapeles), por eso es <button> y no <a> como los otros dos.
const ICONO_COMPARTIR_SVG = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="6" cy="12" r="2.6" stroke="currentColor" stroke-width="1.6"/>
  <circle cx="18" cy="6" r="2.6" stroke="currentColor" stroke-width="1.6"/>
  <circle cx="18" cy="18" r="2.6" stroke="currentColor" stroke-width="1.6"/>
  <line x1="8.3" y1="10.8" x2="15.7" y2="7.2" stroke="currentColor" stroke-width="1.6"/>
  <line x1="8.3" y1="13.2" x2="15.7" y2="16.8" stroke="currentColor" stroke-width="1.6"/>
</svg>`;

function botonCompartirHtml() {
  return `<button type="button" class="btn-foto btn-compartir" title="Compartir" aria-label="Compartir">${ICONO_COMPARTIR_SVG}</button>`;
}

// Aviso flotante genérico, abajo al centro, se oculta solo. Reutilizado por
// compartirProducto (ver más abajo).
let avisoFlotanteTimeout;
function mostrarAvisoFlotante(mensaje) {
  let aviso = document.getElementById("rc-aviso-flotante");
  if (!aviso) {
    aviso = document.createElement("div");
    aviso.id = "rc-aviso-flotante";
    document.body.appendChild(aviso);
  }
  aviso.textContent = mensaje;
  aviso.classList.add("visible");
  clearTimeout(avisoFlotanteTimeout);
  avisoFlotanteTimeout = setTimeout(() => aviso.classList.remove("visible"), 2600);
}

function abrirPanelCompartir(url, nombre) {
  let panel = document.getElementById("rc-panel-compartir");
  if (!panel) {
    panel = document.createElement("div");
    panel.id = "rc-panel-compartir";
    panel.hidden = true;
    panel.innerHTML = `
      <section class="rc-panel-compartir-contenido" role="dialog" aria-modal="true" aria-labelledby="rc-panel-compartir-titulo">
        <button type="button" class="rc-panel-compartir-cerrar" aria-label="Cerrar">×</button>
        <h2 id="rc-panel-compartir-titulo">Compartir producto</h2>
        <p class="rc-panel-compartir-nombre"></p>
        <input class="rc-panel-compartir-url" type="text" readonly aria-label="Link del producto">
        <div class="rc-panel-compartir-acciones">
          <button type="button" class="rc-panel-compartir-accion rc-panel-compartir-copiar">Copiar enlace</button>
          <button type="button" class="rc-panel-compartir-accion rc-panel-compartir-whatsapp">Compartir por WhatsApp</button>
        </div>
      </section>`;
    document.body.appendChild(panel);
    const cerrar = () => { panel.hidden = true; };
    panel.querySelector(".rc-panel-compartir-cerrar").addEventListener("click", cerrar);
    panel.addEventListener("click", (e) => { if (e.target === panel) cerrar(); });
    panel.querySelector(".rc-panel-compartir-copiar").addEventListener("click", async () => {
      const campo = panel.querySelector(".rc-panel-compartir-url");
      campo.focus();
      campo.select();
      try {
        if (!navigator.clipboard?.writeText) throw new Error("Clipboard unavailable");
        await navigator.clipboard.writeText(campo.value);
        mostrarAvisoFlotante("¡Link copiado!");
      } catch {
        document.execCommand("copy");
        mostrarAvisoFlotante("Link seleccionado: podés copiarlo manualmente.");
      }
    });
    panel.querySelector(".rc-panel-compartir-whatsapp").addEventListener("click", () => {
      window.open(panel.dataset.whatsappUrl, "_blank", "noopener,noreferrer");
    });
  }
  const campo = panel.querySelector(".rc-panel-compartir-url");
  panel.querySelector(".rc-panel-compartir-nombre").textContent = nombre;
  campo.value = url;
  panel.dataset.whatsappUrl = `https://wa.me/?text=${encodeURIComponent(`${nombre}\n${url}`)}`;
  panel.hidden = false;
  campo.focus();
  campo.select();
}

// Arma el link directo al producto (?producto=<nombre>, preserva el modo
// Fallout si corresponde) y abre el selector nativo de compartir. Quien lo abra: si
// está logueado, landing.js lo lleva directo a la sección y abre la card
// (ver abrirProductoCompartido); si no tiene cuenta, cae en login.html que
// lo manda al registro y, ya creada la cuenta, lo redirige acá mismo (ver
// login.js).
async function compartirProducto(nombre) {
  const producto = Object.values(SECCIONES_DATA).flat().find((p) => p.nombre === nombre);
  registrarInteraccion("share_product", {
    producto_nombre: nombre,
    categoria: producto ? productoSeccion(producto) : null,
    marca: producto ? (producto.marca || "Otras marcas") : null,
  });
  const params = new URLSearchParams();
  params.set("producto", nombre);
  if (modoVisual === "fallout") params.set("modo", "fallout");
  const url = `${location.origin}/?${params.toString()}`;
  abrirPanelCompartir(url, nombre);
}

// true mientras el usuario apagó el Pip-Boy manualmente (ver Main Switch,
// #btn-pipboy-switch). Se reinicia a false cada vez que se entra a Fallout
// (ver aplicarModoVisual), así siempre arranca encendido.
let pipboyApagado = false;
let recomendacionesMobileLote = [];
let recomendacionesMobileIndice = 0;

// Alto (px) que ocupa #productos con el Pip-Boy encendido, medido apenas se
// pinta. El carrousel de recomendados (6 cards, 2 filas) es naturalmente más
// alto que el Pip-Boy: si se lo deja crecer libremente, la fila entera crece
// con align-items:stretch y arrastra hacia abajo los switches/reproductor de
// la columna izquierda (que se centran en el espacio libre de esa columna).
// Fijando este alto en #productos en los dos estados, la fila nunca cambia
// de tamaño al apagar/prender, así los controles quedan siempre donde están
// con el Pip-Boy encendido.
let alturaPipboyHomePx = null;

function sincronizarAnchoBuscadorHeader() {
  const buscador = document.querySelector(".rc-buscador-header");
  const categoriasClassicWrap = document.getElementById("rc-categorias-classic-wrap");
  const headerNav = document.querySelector(".rc-header-nav");
  if (!buscador) return;
  buscador.style.removeProperty("--rc-header-buscador-width");

  if (!categoriasClassicWrap || !headerNav) return;

  const esMobileClassic = modoVisual === "classic" && window.innerWidth <= 700;
  if (!esMobileClassic) {
    categoriasClassicWrap.style.removeProperty("width");
    categoriasClassicWrap.style.removeProperty("max-width");
    headerNav.style.removeProperty("width");
    headerNav.style.removeProperty("max-width");
    return;
  }

  const anchoBuscador = Math.round(buscador.getBoundingClientRect().width);
  if (!anchoBuscador) return;

  const anchoPx = `${anchoBuscador}px`;
  categoriasClassicWrap.style.width = anchoPx;
  categoriasClassicWrap.style.maxWidth = anchoPx;
  headerNav.style.width = "100%";
  headerNav.style.maxWidth = "100%";
}

function pintarCategorias() {
  const el = document.getElementById("categorias");
  el.innerHTML = CATEGORIAS_BOTONES.map(
    (c) => `<button data-seccion="${escapeHtml(c.clave)}" class="btn-categoria" type="button">${escapeHtml(c.etiqueta)}</button>`
  ).join("");
  sincronizarAnchoBuscadorHeader();
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      seccionActiva = btn.dataset.seccion;
      registrarInteraccion("view_category", { categoria: seccionActiva });
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
  const sinOtrasMarcas = [...ordenadas, ...resto].filter((m) => m !== "Otras marcas");
  return [...sinOtrasMarcas, ...(presentes.has("Otras marcas") ? ["Otras marcas"] : [])];
}

function pintarSelectorMarcas(el) {
  const marcas = todasLasMarcasDelCatalogo();
  const selectorLogosClase = modoVisual === "classic" ? " selector-marcas-logos" : "";
  const botonMarcaHtml = (m) => modoVisual === "classic"
    ? `<button class="btn-categoria btn-marca-logo" data-marca="${escapeHtml(m)}" type="button" aria-label="Ver productos de ${escapeHtml(etiquetaMarca(m))}" title="${escapeHtml(etiquetaMarca(m))}">${marcaLogoHtml(m, "marca-logo-selector")}</button>`
    : `<button class="btn-categoria" data-marca="${escapeHtml(m)}" type="button">${escapeHtml(etiquetaMarca(m))}</button>`;
  el.innerHTML = `<div class="rc-catalogo-surface"><div class="selector-marcas${selectorLogosClase}">${marcas.map(
    botonMarcaHtml
  ).join("")}</div></div>`;
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => {
      filtroMarcaGlobal = btn.dataset.marca;
      registrarInteraccion("view_category", {
        categoria: "Búsqueda por Marca",
        marca: filtroMarcaGlobal,
      });
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
    return `<button data-clave="${escapeHtml(o)}" class="btn-categoria ${activo ? "activo" : ""}" type="button">${escapeHtml(etiquetaMarca(o))}</button>`;
  }).join("");
  sincronizarAnchoBuscadorHeader();
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
      registrarInteraccion("view_category", {
        categoria: seccionActiva,
        marca: clave === "Todos" ? null : clave,
      });
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

// Las 5 formas de precio que se muestran en cada card/list view (Classic y
// Fallout comparten esta misma función — cada modo solo cambia el CSS).
// Todo redondeado hacia arriba, nunca hacia abajo (a pedido).
function preciosDe(p) {
  const dolares = p.usd ?? null;
  const pesos = p.pesos ?? null;
  return {
    dolares,
    bancoUsa: dolares == null ? null : Math.ceil(dolares / 0.975),
    usdt: dolares == null ? null : Math.ceil(dolares / 0.99),
    pesos,
    pesosTransf: pesos == null ? null : Math.ceil(pesos / 0.97),
  };
}

function preciosCarritoHtml(precios, signo = "") {
  const monto = (valor) => `${signo}$${formatearPesos(valor)}`;
  return `
    <span>Dólares: ${monto(precios.dolares)}</span>
    <span>Dólar banco USA: ${monto(precios.bancoUsa)}</span>
    <span>USDT: ${monto(precios.usdt)}</span>
    <span>Pesos: ${monto(precios.pesos)}</span>
    <span>Pesos transf: ${monto(precios.pesosTransf)}</span>
  `;
}

function preciosWhatsapp(precios, signo = "") {
  const monto = (valor) => `${signo}$${formatearPesos(valor)}`;
  return [
    `Dólares: ${monto(precios.dolares)}`,
    `Dólar banco USA: ${monto(precios.bancoUsa)}`,
    `USDT: ${monto(precios.usdt)}`,
    `Pesos: ${monto(precios.pesos)}`,
    `Pesos transf: ${monto(precios.pesosTransf)}`,
  ].join(" · ");
}

// Cierra cualquier dropdown de color que haya quedado abierto (se llama al
// abrir otro, o al hacer click en cualquier otro lado de la página).
function cerrarDropdownsColor() {
  document.querySelectorAll(".dropdown-color-lista").forEach((l) => l.classList.add("oculto"));
}
document.addEventListener("click", cerrarDropdownsColor);

function tarjetaProducto(p) {
  const tieneColores = Array.isArray(p.colores) && p.colores.length > 0;
  const listaColores = tieneColores ? p.colores : ["Color único"];
  // Siempre arranca en "Elegir color" sin nada preseleccionado, tenga el
  // producto uno o varios colores: Agregar al carrito queda inactivo hasta
  // que el usuario elija explícitamente una opción de la lista.
  const colores = `
    <div class="selector-colores">
      <strong>Color:</strong>
      <div class="dropdown-color">
        <button type="button" class="dropdown-color-boton" data-valor="">
          Elegir color
        </button>
        <ul class="dropdown-color-lista oculto" role="listbox">
          ${listaColores.map((c) => `<li role="option" data-valor="${escapeHtml(c)}">${escapeHtml(c)}</li>`).join("")}
        </ul>
      </div>
    </div>
  `;
  return `
    <div class="card" data-nombre="${escapeHtml(p.nombre)}">
      <h3>${marcaLogoHtml(p.marca, "marca-logo-card")}${escapeHtml(p.nombre)}</h3>
      ${colores}
      <p class="precios">
        ${bloquePreciosHtml(p)}
      </p>
      <div class="card-acciones">
        <span class="tarjeta-recomendado-iconos">${botonFotoHtml(p)}${botonEspecificacionesHtml(p)}${botonCompartirHtml()}</span>
        <button class="btn-agregar" data-nombre="${escapeHtml(p.nombre)}" data-color="" type="button" disabled>Agregar al carrito</button>
      </div>
    </div>
  `;
}

function etiquetaOrdenActual() {
  if (criterioOrden === "nombre-asc") return "Nombre A-Z";
  if (criterioOrden === "nombre-desc") return "Nombre Z-A";
  if (criterioOrden === "precio-asc") return "Precio menor a mayor";
  if (criterioOrden === "precio-desc") return "Precio mayor a menor";
  return "Ordenar";
}

function controlVistaHtml() {
  return `
    <div class="control-vista">
      <button type="button" class="btn-vista ${modoVista === "cards" ? "activo" : ""}" data-modo="cards">Cards</button>
      <button type="button" class="btn-vista ${modoVista === "lista" ? "activo" : ""}" data-modo="lista">Lista</button>
      <label class="control-orden">
        <span class="control-orden-etiqueta">Ordenar</span>
        <select id="select-orden" class="btn-vista btn-select-orden ${criterioOrden !== "default" ? "activo" : ""}">
          <option value="default">Sin ordenar</option>
          <option value="nombre-asc" ${criterioOrden === "nombre-asc" ? "selected" : ""}>Nombre A-Z</option>
          <option value="nombre-desc" ${criterioOrden === "nombre-desc" ? "selected" : ""}>Nombre Z-A</option>
          <option value="precio-asc" ${criterioOrden === "precio-asc" ? "selected" : ""}>Precio menor a mayor</option>
          <option value="precio-desc" ${criterioOrden === "precio-desc" ? "selected" : ""}>Precio mayor a menor</option>
        </select>
      </label>
    </div>
  `;
}

function ordenarProductos(productos) {
  if (criterioOrden === "default") return productos;
  const ordenados = [...productos];
  if (criterioOrden === "nombre-asc") {
    return ordenados.sort((a, b) => (a.nombre || "").localeCompare(b.nombre || "", "es", { sensitivity: "base" }));
  }
  if (criterioOrden === "nombre-desc") {
    return ordenados.sort((a, b) => (b.nombre || "").localeCompare(a.nombre || "", "es", { sensitivity: "base" }));
  }
  if (criterioOrden === "precio-asc") {
    return ordenados.sort((a, b) => (a.usd ?? 0) - (b.usd ?? 0));
  }
  if (criterioOrden === "precio-desc") {
    return ordenados.sort((a, b) => (b.usd ?? 0) - (a.usd ?? 0));
  }
  return productos;
}

function pintarGrilla(el, productos, mensajeVacio) {
  const esMobileClassic = modoVisual === "classic" && window.innerWidth <= 700;
  if (!productos || productos.length === 0) {
    el.innerHTML = `<div class="rc-catalogo-surface"><p class="mensaje-vacio">${mensajeVacio}</p></div>`;
    return;
  }
  productos = ordenarProductos(productos);
  const claseModo = (modoVista === "lista" || esMobileClassic) ? "lista" : "";
  const controlesHtml = esMobileClassic ? "" : controlVistaHtml();
  el.innerHTML = `<div class="rc-catalogo-surface">${controlesHtml}<div class="grilla ${claseModo}">${productos.map(tarjetaProducto).join("")}</div></div>`;
  el.querySelectorAll(".card").forEach((card) => {
    const producto = productos.find((item) => item.nombre === card.dataset.nombre);
    if (!producto) return;
    const btnAgregar = card.querySelector(".btn-agregar");
    const botonColor = card.querySelector(".dropdown-color-boton");
    const listaColor = card.querySelector(".dropdown-color-lista");

    // El título se trunca por lo largo del nombre; seleccionar la card lo
    // expande para ver el nombre completo. No es acumulativo: solo una
    // card seleccionada a la vez, para que el user vea un ítem por vez en
    // su extensión completa. Elegir color y agregar al carrito solo tiene
    // sentido si la card ya está seleccionada; si no, el primer click la
    // selecciona nomás (no abre el dropdown ni agrega todavía).
    function seleccionarCard() {
      const yaExpandida = card.classList.contains("expandida");
      cerrarDropdownsColor();
      el.querySelectorAll(".card.expandida").forEach((c) => c.classList.remove("expandida"));
      if (!yaExpandida) card.classList.add("expandida");
      // La card no es un <button>, así que el beep global de Fallout (que
      // solo escucha button/a/[role=button]) no la alcanza: la disparamos acá.
      if (modoVisual === "fallout") beepInteraccion();
    }

    if (botonColor && listaColor) {
      botonColor.addEventListener("click", (e) => {
        e.stopPropagation();
        if (!card.classList.contains("expandida")) {
          seleccionarCard();
          return;
        }
        const yaAbierto = !listaColor.classList.contains("oculto");
        cerrarDropdownsColor();
        if (!yaAbierto) listaColor.classList.remove("oculto");
      });
      listaColor.querySelectorAll("li").forEach((li) => {
        li.addEventListener("click", () => {
          botonColor.textContent = li.dataset.valor;
          botonColor.dataset.valor = li.dataset.valor;
          listaColor.classList.add("oculto");
          btnAgregar.dataset.color = li.dataset.valor;
          btnAgregar.disabled = false;
        });
      });
    }
    btnAgregar.addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!card.classList.contains("expandida")) {
        seleccionarCard();
        return;
      }
      const producto = productos.find((p) => p.nombre === btnAgregar.dataset.nombre);
      if (producto) await agregarAlCarritoProtegido(producto, btnAgregar.dataset.color || null);
    });
    const btnCompartir = card.querySelector(".btn-compartir");
    if (btnCompartir) {
      btnCompartir.addEventListener("click", (e) => {
        e.stopPropagation();
        compartirProducto(card.dataset.nombre);
      });
    }
    card.addEventListener("click", (e) => {
      if (e.target.closest("button, a, .dropdown-color, li")) return;
      registrarInteraccion("view_item", {
        producto_nombre: producto.nombre,
        categoria: productoSeccion(producto),
        marca: producto.marca || "Otras marcas",
        metadata: { vista: modoVista },
      });
      seleccionarCard();
    });
  });
  el.querySelectorAll(".btn-vista[data-modo]").forEach((btn) => {
    btn.addEventListener("click", () => {
      modoVista = btn.dataset.modo;
      actualizarVista();
    });
  });
  const selectOrden = el.querySelector("#select-orden");
  if (selectOrden) {
    selectOrden.addEventListener("change", () => {
      criterioOrden = selectOrden.value;
      actualizarVista();
    });
  }
}

// Etiqueta del placeholder del buscador: aclara si la búsqueda va a correr
// sobre todo el catálogo, sobre una sección puntual, o sobre todas las marcas
// (Búsqueda por Marca busca igual que la general, solo cambia el universo).
function etiquetaPlaceholderBusqueda() {
  if (seccionActiva === BUSQUEDA_MARCA_CLAVE || filtroMarcaGlobal) return "Busca en todas las marcas";
  if (seccionActiva) {
    const cat = CATEGORIAS_BOTONES.find((c) => c.clave === seccionActiva);
    const nombre = (cat ? cat.etiqueta : seccionActiva).toLowerCase();
    return `Busca dentro de ${nombre}`;
  }
  return "Busca en todo The Tech Room Arg...";
}

// Decide qué mostrar según la sección elegida (si hay), el sub-filtro (marca
// o tipo) y el término de búsqueda, y pinta categorías/sub-nav/grilla/volver.
function actualizarVista() {
  const inputBusquedaEl = document.getElementById("input-busqueda");
  inputBusquedaEl.placeholder = etiquetaPlaceholderBusqueda();
  const termino = inputBusquedaEl.value.trim().toLowerCase();
  const esMobileClassic = modoVisual === "classic" && window.innerWidth <= 700;
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
  sincronizarAnchoBuscadorHeader();
  // Los switches (Main Switch / Power Switch, Modo Fallout) solo tienen
  // sentido en el home: al entrar a una sección los botones de categoría
  // desaparecen y quedaban como único control visible en la barra lateral.
  const switchesWrap = document.getElementById("rc-switches-fallout-wrap");
  if (switchesWrap) switchesWrap.classList.toggle("oculto", !enInicio);
  // Al entrar a una sección (no en el home): el menú de la izquierda queda
  // fijo y el listado de productos de la derecha scrollea solo si no entra
  // en la pantalla. En el home la página entera sigue scrolleando normal.
  document.body.classList.toggle("rc-vista-seccion", !enInicio);

  detenerCarrouselCiudad();

  if (enInicio) {
    if (ultimoEventoVista !== "home") {
      ultimoEventoVista = "home";
      registrarInteraccion("view_home");
    }
    pintarCarrouselSegunModo(productosEl);
    return;
  }
  // Fuera del home el alto fijo del Pip-Boy no aplica (acá va el listado de
  // productos, con su propio alto real).
  productosEl.style.height = "";

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
    mensajeVacioSinFiltro = `Todavía no hay productos de ${etiquetaMarca(filtroMarcaGlobal)} cargados.`;
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

  const claveVista = [
    seccionActiva || "",
    filtroMarcaGlobal || "",
    [...subFiltrosActivos].sort().join("|"),
  ].join("::");
  if (ultimoEventoVista !== claveVista) {
    ultimoEventoVista = claveVista;
    registrarInteraccion("view_category", {
      categoria: seccionActiva || "General",
      marca: filtroMarcaGlobal || null,
    });
  }

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
  catalogoListo = false;
  renderCarrito();
  let datos;
  try {
    const anonId = obtenerAnonId();
    const headers = { "X-TTRA-ANON-ID": anonId };
    const [catalogoR, recomendadosR] = await Promise.all([
      fetch("/api/catalogo", { headers }),
      fetch("/api/recomendados?limit=24", { headers }),
    ]);
    if (!catalogoR.ok) throw new Error(`HTTP ${catalogoR.status}`);
    datos = await catalogoR.json();
    RECOMENDADOS_DATA = recomendadosR.ok
      ? ((await recomendadosR.json()).productos || [])
      : [];
  } catch {
    ocultarNavegacionCatalogo();
    document.getElementById("productos").innerHTML =
      '<p class="mensaje-vacio">No pudimos cargar el catálogo. Escribinos por WhatsApp: ' +
      '<a href="https://wa.me/543512145217" target="_blank" rel="noopener">wa.me/543512145217</a></p>';
    return false;
  }
  modoPrecioActual = datos.modo_precio === "mayorista" ? "mayorista" : "minorista";
  SECCIONES_DATA = datos.secciones || {};
  RECOMENDADOS_DATA = RECOMENDADOS_DATA
    .map((p) => ({ ...p, marca: p.marca || "Otras marcas" }))
    .filter((p) => p && p.nombre);
  actualizarModoPrecio();
  refrescarPreciosCarrito();
  catalogoListo = true;
  renderCarrito();
  if (datos.mensaje) {
    ocultarNavegacionCatalogo();
    document.getElementById("productos").innerHTML = `<p class="mensaje-vacio">${datos.mensaje}</p>`;
    return true;
  }
  pintarCategorias();
  actualizarVista();
  return true;
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

function cargarDescuentoMailing() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_DESCUENTO_MAILING) || "null");
  } catch {
    return null;
  }
}

function guardarDescuentoMailing(descuento) {
  localStorage.setItem(CLAVE_DESCUENTO_MAILING, JSON.stringify(descuento));
  renderCarrito();
}

function borrarDescuentoMailing() {
  localStorage.removeItem(CLAVE_DESCUENTO_MAILING);
  renderCarrito();
}

function actualizarModoPrecio() {
  const esMayorista = modoPrecioActual === "mayorista";
  const indicador = document.getElementById("indicador-mayorista");
  const botonCodigo = document.getElementById("btn-abrir-codigo");
  const panelCodigo = document.getElementById("modal-codigo");

  if (indicador) indicador.hidden = !esMayorista;
  if (botonCodigo) botonCodigo.hidden = esMayorista;
  if (panelCodigo) {
    panelCodigo.hidden = esMayorista;
    if (esMayorista) panelCodigo.classList.add("oculto");
  }
  if (esMayorista) borrarDescuentoMailing();
}

function itemsCarritoParaDescuento(carrito) {
  return carrito.map((it) => ({ nombre: it.nombre, cantidad: it.cantidad }));
}

const CLAVE_REGALO_PROMO = "ttra_regalo_promo";

function cargarRegaloPromo() {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_REGALO_PROMO) || "null");
  } catch {
    return null;
  }
}

function guardarRegaloPromo(regalo) {
  localStorage.setItem(CLAVE_REGALO_PROMO, JSON.stringify(regalo));
  renderCarrito();
}

function borrarRegaloPromo() {
  localStorage.removeItem(CLAVE_REGALO_PROMO);
  renderCarrito();
}

function setEstadoCodigoMailing(mensaje, tipo = "") {
  const el = document.getElementById("estado-codigo-mailing");
  if (!el) return;
  el.textContent = mensaje || "";
  el.className = `descuento-mailing-estado${tipo ? ` ${tipo}` : ""}`;
}

function descuentoMailingAplicado(carrito) {
  if (!catalogoListo) return null;
  if (modoPrecioActual === "mayorista") return null;
  const descuento = cargarDescuentoMailing();
  if (!descuento || !Array.isArray(descuento.productos) || !descuento.productos.length) return null;

  const productosElegibles = new Set(descuento.productos);
  let cantidad = 0;
  let usd = 0;
  let pesos = 0;
  let transferencia = 0;

  carrito.forEach((it) => {
    if (!productosElegibles.has(it.nombre) || !it.usd) return;
    const descuentoUsdUnit = Math.min(Number(descuento.descuento_usd_por_item) || 0, Number(it.usd) || 0);
    if (descuentoUsdUnit <= 0) return;
    cantidad += it.cantidad;
    usd += descuentoUsdUnit * it.cantidad;
    pesos += Math.round(descuentoUsdUnit * ((it.pesos || 0) / it.usd)) * it.cantidad;
    transferencia += Math.round(descuentoUsdUnit * ((it.transferencia || 0) / it.usd)) * it.cantidad;
  });

  if (!cantidad) return null;
  return { codigo: descuento.codigo, cantidad, usd, pesos, transferencia, productos: descuento.productos };
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
  registrarInteraccion("add_to_cart", {
    producto_nombre: producto.nombre,
    categoria: productoSeccion(producto),
    marca: producto.marca || "Otras marcas",
    metadata: { color: color || "", cantidad: 1 },
  });
  abrirCarrito();
}

async function agregarAlCarritoProtegido(producto, color) {
  agregarAlCarrito(producto, color);
}

async function procesarPendienteCarrito() {
  const pendiente = leerPendienteCarrito();
  if (!pendiente) return;
  const sesion = await obtenerEstadoSesionCliente();
  if (!sesion || sesion.debe_cambiar_password) return;

  const catalogoPlano = {};
  Object.values(SECCIONES_DATA).forEach((productos) => {
    (productos || []).forEach((p) => {
      catalogoPlano[p.nombre] = p;
    });
  });

  const producto = catalogoPlano[pendiente.nombre];
  borrarPendienteCarrito();
  if (producto) agregarAlCarrito(producto, pendiente.color || null);
}

async function procesarCheckoutPendiente() {
  if (!catalogoListo) return false;
  if (!hayCheckoutPendiente()) return false;
  const sesion = await obtenerEstadoSesionCliente(true);
  if (!sesion || sesion.debe_cambiar_password) return false;
  const carrito = cargarCarrito();
  if (carrito.length === 0) {
    borrarCheckoutPendiente();
    return false;
  }
  await derivarCheckoutAWhatsapp(carrito);
  return true;
}

async function asegurarSesionParaCheckout() {
  if (!catalogoListo) return false;
  const sesion = await obtenerEstadoSesionCliente(true);
  if (sesion && !sesion.debe_cambiar_password) return true;
  guardarPendienteCheckout();
  window.location.href = urlLoginParaCarrito();
  return false;
}

function cambiarCantidad(nombre, color, delta) {
  if (!catalogoListo) return;
  const carrito = cargarCarrito();
  const item = carrito.find((it) => mismoItemCarrito(it, nombre, color));
  if (!item) return;
  item.cantidad += delta;
  const nuevo = item.cantidad > 0 ? carrito : carrito.filter((it) => !mismoItemCarrito(it, nombre, color));
  guardarCarrito(nuevo);
}

function quitarDelCarrito(nombre, color) {
  if (!catalogoListo) return;
  const catalogoPlano = {};
  Object.values(SECCIONES_DATA).forEach((productos) => {
    (productos || []).forEach((p) => {
      catalogoPlano[p.nombre] = p;
    });
  });
  const producto = catalogoPlano[nombre];
  registrarInteraccion("remove_from_cart", {
    producto_nombre: nombre,
    categoria: producto ? productoSeccion(producto) : null,
    marca: producto ? (producto.marca || "Otras marcas") : null,
    metadata: { color: color || "" },
  });
  guardarCarrito(cargarCarrito().filter((it) => !mismoItemCarrito(it, nombre, color)));
}

function vaciarCarrito() {
  if (!catalogoListo) return;
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
  if (!catalogoListo) return null;
  return modoPrecioActual === "mayorista" ? null : calcularDescuentoMinorista(carrito);
}

function calcularDescuentoMinorista(carrito) {
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
  const totalUsd = (it.usd || 0) * it.cantidad;
  const totalPesos = (it.pesos || 0) * it.cantidad;
  const precios = preciosDe({ usd: totalUsd, pesos: totalPesos });
  return `
    <div class="item-carrito">
      <p class="item-nombre">${escapeHtml(it.nombre)}${colorTexto}</p>
      <p class="item-precios">${preciosCarritoHtml(precios)}</p>
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
      <p class="item-descuento-valor">${preciosCarritoHtml(preciosDe(descuento), "-")}</p>
    </div>
  `;
}

function itemDescuentoMailingHtml(descuento) {
  return `
    <div class="item-carrito item-descuento">
      <p class="item-nombre">✉️ Código ${escapeHtml(descuento.codigo)} aplicado a ${descuento.cantidad} ítem(s)</p>
      <p class="item-descuento-valor">${preciosCarritoHtml(preciosDe(descuento), "-")}</p>
    </div>
  `;
}

function itemRegaloPromoHtml(regalo) {
  return `
    <div class="item-carrito item-descuento">
      <p class="item-nombre">🎁 ${escapeHtml(regalo.producto_regalo)} — Regalo (código ${escapeHtml(regalo.codigo)})</p>
      <p class="item-descuento-valor">Gratis</p>
    </div>
  `;
}

function renderCarrito() {
  const contadorEl = document.getElementById("carrito-contador");
  const el = document.getElementById("items-carrito");
  const totalEl = document.getElementById("total-carrito");
  if (!catalogoListo) {
    contadorEl.textContent = "0";
    el.innerHTML = '<p class="mensaje-vacio">Actualizando carrito...</p>';
    totalEl.textContent = "";
    return;
  }

  const carrito = cargarCarrito();
  const cantidadTotal = carrito.reduce((n, it) => n + it.cantidad, 0);
  contadorEl.textContent = cantidadTotal;

  const descuento = calcularDescuento(carrito);
  const descuentoMailing = descuentoMailingAplicado(carrito);
  const regaloPromo = carrito.length ? cargarRegaloPromo() : null;
  el.innerHTML = carrito.length === 0
    ? '<p class="mensaje-vacio">Tu carrito está vacío.</p>'
    : carrito.map(itemCarritoHtml).join("")
      + (descuento ? itemDescuentoHtml(descuento) : "")
      + (descuentoMailing ? itemDescuentoMailingHtml(descuentoMailing) : "")
      + (regaloPromo ? itemRegaloPromoHtml(regaloPromo) : "");

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
  const inputCodigo = document.getElementById("input-codigo-mailing");
  const descuentoGuardado = cargarDescuentoMailing();
  if (inputCodigo && document.activeElement !== inputCodigo) {
    inputCodigo.value = descuentoGuardado?.codigo || "";
  }
  if (descuentoGuardado && descuentoMailing) {
    setEstadoCodigoMailing(`Código ${descuentoMailing.codigo} aplicado sobre ${descuentoMailing.cantidad} ítem(s).`, "ok");
  } else if (descuentoGuardado) {
    setEstadoCodigoMailing("El código está cargado, pero hoy no aplica a los productos actuales del carrito.", "error");
  } else {
    setEstadoCodigoMailing("");
  }

  const descuentoUsd = (descuento?.usd || 0) + (descuentoMailing?.usd || 0);
  const descuentoPesos = (descuento?.pesos || 0) + (descuentoMailing?.pesos || 0);
  const totalNeto = {
    usd: t.usd - descuentoUsd,
    pesos: t.pesos - descuentoPesos,
  };
  if (carrito.length === 0) {
    totalEl.textContent = "";
  } else {
    totalEl.innerHTML = `<strong>Total:</strong>${preciosCarritoHtml(preciosDe(totalNeto))}`;
  }
}

function sincronizarLimiteCarrito() {
  const pie = document.querySelector(".rc-pie");
  const separacion = pie ? Math.ceil(pie.getBoundingClientRect().height) + 16 : 24;
  document.documentElement.style.setProperty("--rc-carrito-separacion-footer", `${separacion}px`);
}

function abrirCarrito() {
  if (!catalogoListo) return;
  cargarOpcionesEntrega().catch(() => {});
  sincronizarLimiteCarrito();
  document.getElementById("panel-carrito").classList.remove("oculto");
  document.getElementById("overlay-carrito").classList.remove("oculto");
}

function cerrarCarrito() {
  document.getElementById("panel-carrito").classList.add("oculto");
  document.getElementById("overlay-carrito").classList.add("oculto");
}

function armarMensajeWhatsapp(carrito, fechaEntrega) {
  if (!catalogoListo) return null;
  const lineas = carrito.map((it) => {
    const color = it.color ? ` (${it.color})` : "";
    const totalUsd = (it.usd || 0) * it.cantidad;
    const totalPesos = (it.pesos || 0) * it.cantidad;
    return `- ${it.nombre}${color} x${it.cantidad}\n  ${preciosWhatsapp(preciosDe({ usd: totalUsd, pesos: totalPesos }))}`;
  });
  const descuento = calcularDescuento(carrito);
  const descuentoMailing = descuentoMailingAplicado(carrito);
  const regaloPromo = cargarRegaloPromo();
  if (descuento) {
    lineas.push(`- 🎉 Descuento por ${descuento.cantidadTotal} unidades\n  ${preciosWhatsapp(preciosDe(descuento), "-")}`);
  }
  if (descuentoMailing) {
    lineas.push(`- ✉️ Código ${descuentoMailing.codigo}\n  ${preciosWhatsapp(preciosDe(descuentoMailing), "-")}`);
  }
  if (regaloPromo) {
    lineas.push(`- 🎁 ${regaloPromo.producto_regalo} — Regalo (código ${regaloPromo.codigo})\n  Gratis`);
  }
  const t = totales(carrito);
  const totalUsd = t.usd - (descuento?.usd || 0) - (descuentoMailing?.usd || 0);
  const totalPesos = t.pesos - (descuento?.pesos || 0) - (descuentoMailing?.pesos || 0);
  const total = `Total:\n${preciosWhatsapp(preciosDe({ usd: totalUsd, pesos: totalPesos }))}`;
  return `Hola! Quiero encargar:\n${lineas.join("\n")}\n\nEntrega solicitada: ${fechaEntrega}\n${total}`;
}

async function cargarOpcionesEntrega() {
  const select = document.getElementById("fecha-entrega");
  const nota = document.getElementById("nota-entrega");
  const r = await fetch("/api/entregas-disponibles");
  const datos = await r.json();
  select.innerHTML = (datos.opciones || []).map((opcion) => {
    return `<option value="${opcion.fecha}">${opcion.etiqueta}</option>`;
  }).join("");
  nota.textContent = datos.opciones?.[0]?.requiere_confirmacion ? "El pedido se entrega el lunes. Confirmá si querés continuar." : "Elegí tu fecha de entrega.";
}

async function aplicarCodigoMailing() {
  if (!catalogoListo) return;
  if (modoPrecioActual === "mayorista") {
    borrarDescuentoMailing();
    return;
  }
  const carrito = cargarCarrito();
  if (!carrito.length) {
    setEstadoCodigoMailing("Agregá productos al carrito antes de aplicar un código.", "error");
    return;
  }
  const input = document.getElementById("input-codigo-mailing");
  const codigo = (input?.value || "").trim().toUpperCase();
  if (!codigo) {
    borrarDescuentoMailing();
    setEstadoCodigoMailing("");
    return;
  }
  setEstadoCodigoMailing("Validando código...");
  const r = await fetch("/api/descuentos/validar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codigo, items: itemsCarritoParaDescuento(carrito) }),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    setEstadoCodigoMailing(body.error || "No se pudo validar el código.", "error");
    return;
  }
  guardarDescuentoMailing(body);
}

async function aplicarCodigoMailingPorValor(codigo) {
  if (!catalogoListo) return false;
  if (modoPrecioActual === "mayorista") {
    borrarDescuentoMailing();
    return false;
  }
  const input = document.getElementById("input-codigo-mailing");
  if (input) input.value = codigo;
  const carrito = cargarCarrito();
  if (!carrito.length || !codigo) return false;
  setEstadoCodigoMailing("Validando código...");
  const r = await fetch("/api/descuentos/validar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codigo, items: itemsCarritoParaDescuento(carrito) }),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    setEstadoCodigoMailing(body.error || "No se pudo validar el código.", "error");
    return false;
  }
  guardarDescuentoMailing(body);
  return true;
}

async function derivarCheckoutAWhatsapp(carrito) {
  if (!catalogoListo) return false;
  registrarInteraccion("complete_checkout", {
    metadata: { cantidad: carrito.reduce((n, it) => n + it.cantidad, 0) },
  });
  const fechaEntrega = document.getElementById("fecha-entrega").value;
  const direccionEntrega = document.getElementById("direccion-entrega").value.trim();
  if (!direccionEntrega) { alert("Especificá dirección de entrega."); return; }
  const mensaje = armarMensajeWhatsapp(carrito, fechaEntrega);
  if (!mensaje) return false;
  try {
    if (!(await registrarPedidoEnClientes(carrito, fechaEntrega, direccionEntrega))) return false;
  } catch (error) {
    console.error("No se pudo guardar el pedido", error);
    alert("No pudimos guardar tu pedido. Probá nuevamente antes de abrir WhatsApp.");
    return;
  }
  borrarCheckoutPendiente();
  vaciarCarrito();
  borrarDescuentoMailing();
  borrarRegaloPromo();
  cerrarCarrito();
  window.location.href = `https://wa.me/${WHATSAPP_NUMERO}?text=${encodeURIComponent(mensaje)}`;
  return true;
}

document.getElementById("btn-carrito").addEventListener("click", abrirCarrito);
document.getElementById("btn-cerrar-carrito").addEventListener("click", cerrarCarrito);
document.getElementById("overlay-carrito").addEventListener("click", cerrarCarrito);
window.addEventListener("resize", sincronizarLimiteCarrito);
document.getElementById("btn-vaciar-carrito").addEventListener("click", () => {
  vaciarCarrito();
  borrarDescuentoMailing();
  borrarRegaloPromo();
});

const panelDireccionEntrega = document.getElementById("direccion-entrega-wrap");
const panelSelectorDomicilio = document.getElementById("selector-domicilio-entrega");
const panelCodigoPromocional = document.getElementById("modal-codigo");
const inputDireccionEntrega = document.getElementById("direccion-entrega");
const inputDireccionAlias = document.getElementById("direccion-alias");
const sugerenciasDireccion = document.getElementById("sugerencias-direccion");
const listaDomiciliosEntrega = document.getElementById("lista-domicilios-entrega");
let temporizadorSugerenciasDireccion;
let apiPlacesCargada;
let domiciliosCliente = [];

function ocultarSugerenciasDireccion() {
  sugerenciasDireccion.replaceChildren();
  sugerenciasDireccion.classList.add("oculto");
}

async function cargarApiPlaces() {
  if (apiPlacesCargada !== undefined) return apiPlacesCargada;
  apiPlacesCargada = fetch("/api/configuracion-publica")
    .then((respuesta) => respuesta.ok ? respuesta.json() : {})
    .then(async ({ google_maps_api_key: clave }) => {
      if (!clave) return null;
      await new Promise((resolver, rechazar) => {
        const script = document.createElement("script");
        script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(clave)}&libraries=places&v=weekly`;
        script.async = true;
        script.onload = resolver;
        script.onerror = rechazar;
        document.head.append(script);
      });
      return google.maps.importLibrary("places");
    })
    .catch(() => null);
  return apiPlacesCargada;
}

async function mostrarSugerenciasDireccion(texto) {
  const places = await cargarApiPlaces();
  if (!places || texto !== inputDireccionEntrega.value.trim()) return;
  const { AutocompleteSuggestion } = places;
  const { suggestions } = await AutocompleteSuggestion.fetchAutocompleteSuggestions({
    input: texto,
    includedRegionCodes: ["ar"],
  });
  if (texto !== inputDireccionEntrega.value.trim() || !suggestions?.length) {
    ocultarSugerenciasDireccion();
    return;
  }
  sugerenciasDireccion.replaceChildren(...suggestions.slice(0, 5).map(({ placePrediction }) => {
    const item = document.createElement("li");
    const boton = document.createElement("button");
    boton.type = "button";
    boton.textContent = placePrediction.text.text;
    boton.addEventListener("click", async () => {
      const place = placePrediction.toPlace();
      await place.fetchFields({ fields: ["formattedAddress"] });
      inputDireccionEntrega.value = place.formattedAddress || placePrediction.text.text;
      ocultarSugerenciasDireccion();
    });
    item.append(boton);
    return item;
  }));
  sugerenciasDireccion.classList.remove("oculto");
}

inputDireccionEntrega.addEventListener("input", () => {
  clearTimeout(temporizadorSugerenciasDireccion);
  const texto = inputDireccionEntrega.value.trim();
  if (texto.length < 3) {
    ocultarSugerenciasDireccion();
    return;
  }
  temporizadorSugerenciasDireccion = setTimeout(() => {
    mostrarSugerenciasDireccion(texto).catch(ocultarSugerenciasDireccion);
  }, 250);
});

function abrirPanelSecundario(idPanel) {
  panelSelectorDomicilio.classList.toggle("oculto", idPanel !== "selector-domicilio-entrega");
  panelDireccionEntrega.classList.toggle("oculto", idPanel !== "direccion-entrega-wrap");
  panelCodigoPromocional.classList.toggle("oculto", idPanel !== "modal-codigo");
}

function cerrarPanelSecundario() {
  panelSelectorDomicilio.classList.add("oculto");
  panelDireccionEntrega.classList.add("oculto");
  panelCodigoPromocional.classList.add("oculto");
  ocultarSugerenciasDireccion();
}

function abrirFormularioNuevaDireccion() {
  const puedeGuardar = Boolean(estadoSesionCliente) && domiciliosCliente.length < 5;
  inputDireccionAlias.classList.toggle("oculto", !puedeGuardar);
  inputDireccionAlias.value = "";
  inputDireccionEntrega.value = "";
  abrirPanelSecundario("direccion-entrega-wrap");
}

async function abrirSelectorDireccion() {
  const cliente = await obtenerEstadoSesionCliente(true);
  if (!cliente) {
    abrirFormularioNuevaDireccion();
    return;
  }
  const r = await fetch("/api/domicilios");
  domiciliosCliente = r.ok ? await r.json() : [];
  if (!domiciliosCliente.length) {
    abrirFormularioNuevaDireccion();
    return;
  }
  function itemDomicilioEntregaHtml(texto, alClickear) {
    const item = document.createElement("li");
    const boton = document.createElement("button");
    boton.type = "button";
    boton.textContent = texto;
    boton.addEventListener("click", alClickear);
    item.append(boton);
    return item;
  }
  listaDomiciliosEntrega.replaceChildren(
    ...domiciliosCliente.map((domicilio) => itemDomicilioEntregaHtml(`${domicilio.alias} — ${domicilio.direccion}`, () => {
      inputDireccionEntrega.value = domicilio.direccion;
      document.getElementById("btn-abrir-direccion").textContent = `Entrega: ${domicilio.alias}`;
      cerrarPanelSecundario();
    })),
    itemDomicilioEntregaHtml("+ Agregar nueva dirección", abrirFormularioNuevaDireccion),
  );
  abrirPanelSecundario("selector-domicilio-entrega");
}

document.getElementById("btn-abrir-direccion").addEventListener("click", () => {
  abrirSelectorDireccion().catch(abrirFormularioNuevaDireccion);
});
document.getElementById("btn-guardar-direccion").addEventListener("click", async () => {
  const direccion = inputDireccionEntrega.value.trim();
  if (!direccion) {
    inputDireccionEntrega.focus();
    return;
  }
  let aliasGuardado = null;
  if (!inputDireccionAlias.classList.contains("oculto")) {
    const alias = inputDireccionAlias.value.trim() || "Dirección";
    const respuesta = await fetch("/api/domicilios", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ alias, direccion }),
    });
    if (respuesta.ok) {
      const domicilio = await respuesta.json();
      domiciliosCliente.push(domicilio);
      aliasGuardado = domicilio.alias;
    }
  }
  document.getElementById("btn-abrir-direccion").textContent = aliasGuardado ? `Entrega: ${aliasGuardado}` : "Dirección de entrega";
  cerrarPanelSecundario();
});

document.getElementById("btn-abrir-codigo").addEventListener("click", () => {
  if (modoPrecioActual === "mayorista") return;
  abrirPanelSecundario("modal-codigo");
});
document.addEventListener("pointerdown", (evento) => {
  const panelSecundarioAbierto = [panelSelectorDomicilio, panelDireccionEntrega, panelCodigoPromocional]
    .find((panel) => !panel.classList.contains("oculto"));
  if (!panelSecundarioAbierto || panelSecundarioAbierto.contains(evento.target)) return;
  if (evento.target.closest("#btn-abrir-direccion, #btn-abrir-codigo")) return;
  cerrarPanelSecundario();
});

document.getElementById("btn-aplicar-codigo").addEventListener("click", async () => {
  if (!catalogoListo) return;
  if (modoPrecioActual === "mayorista") {
    borrarDescuentoMailing();
    return;
  }
  const carrito = cargarCarrito();
  if (!carrito.length) {
    alert("Agregá productos al carrito antes de aplicar un código.");
    return;
  }
  const input = document.getElementById("input-codigo-mailing");
  const codigo = (input?.value || "").trim().toUpperCase();
  if (!codigo) {
    alert("Ingresá un código.");
    return;
  }
  const r = await fetch("/api/codigos-promo/validar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ codigo }),
  });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) {
    alert(body.error || "No se pudo validar el código.");
    return;
  }
  guardarRegaloPromo(body);
  cerrarPanelSecundario();
  alert(`¡Código aplicado! Sumamos ${body.producto_regalo} de regalo a tu pedido.`);
});

// Al cerrar un pedido, suma los productos encargados al registro del
// cliente (mismo clientes.json/csv que ya alimentan el gate inicial y el
// buscador por chat) — así el panel /admin/clientes también refleja los
// pedidos hechos desde la web, no solo el alta inicial.
async function registrarPedidoEnClientes(carrito, fecha_entrega, direccion_entrega) {
  if (!catalogoListo) return false;
  const regaloPromo = cargarRegaloPromo();
  const productos = [...new Set(carrito.map((it) =>
    it.color && it.color !== "Color único" ? `${it.nombre} (${it.color})` : it.nombre
  ))];
  const descuento = calcularDescuento(carrito);
  const descuentoMailing = descuentoMailingAplicado(carrito);
  const total_usd = Math.max(
    totales(carrito).usd - (descuento?.usd || 0) - (descuentoMailing?.usd || 0),
    0,
  );
  const codigo_descuento = descuentoMailing?.codigo || null;
  const codigo_promo = regaloPromo?.codigo || null;
  const detalle = carrito.map((it) => ({
    nombre: it.nombre,
    color: it.color || null,
    cantidad: it.cantidad,
    usd_unitario: it.usd || 0,
    usd_subtotal: (it.usd || 0) * it.cantidad,
  }));
  const respuesta = await fetch("/api/pedidos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      productos, fecha_entrega, direccion_entrega, detalle, total_usd,
      codigo_descuento, codigo_promo,
    }),
  });
  const body = await respuesta.json().catch(() => ({}));
  if (respuesta.status === 409) {
    if (body.conflicto === "codigo_promo") borrarRegaloPromo();
    if (body.conflicto === "codigo_descuento") borrarDescuentoMailing();
    alert(body.error
      ? `${body.error}\n\nRevisá el carrito y confirmá nuevamente.`
      : "El catálogo cambió. Revisá el carrito y confirmá nuevamente.");
    const recargado = await cargarCatalogo();
    if (recargado) abrirCarrito();
    return false;
  }
  if (!respuesta.ok) {
    throw new Error(body.error || "No se pudo guardar el pedido");
  }
  return true;
}

document.getElementById("btn-whatsapp").addEventListener("click", async () => {
  if (!catalogoListo) return;
  const carrito = cargarCarrito();
  if (carrito.length === 0) return;
  registrarInteraccion("begin_checkout", {
    metadata: { cantidad: carrito.reduce((n, it) => n + it.cantidad, 0) },
  });
  if (!(await asegurarSesionParaCheckout())) return;
  await derivarCheckoutAWhatsapp(carrito);
});
document.getElementById("btn-volver").addEventListener("click", volverUnPaso);
document.getElementById("titulo-inicio").addEventListener("click", volverAPantallaPrincipal);
document.getElementById("input-busqueda").addEventListener("input", () => {
  actualizarVista();
  clearTimeout(timeoutBusquedaTrack);
  timeoutBusquedaTrack = setTimeout(() => {
    const termino = document.getElementById("input-busqueda").value.trim();
    if (!termino || termino === ultimoTerminoBuscado) return;
    ultimoTerminoBuscado = termino;
    registrarInteraccion("search", {
      categoria: seccionActiva || "General",
      marca: filtroMarcaGlobal || null,
      metadata: { termino },
    });
  }, 450);
});

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

// Baraja Fisher-Yates, sin mutar el array original.
function barajar(lista) {
  const copia = lista.slice();
  for (let i = copia.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copia[i], copia[j]] = [copia[j], copia[i]];
  }
  return copia;
}

// Se resuelve una sola vez por carga de página (no se vuelve a barajar en
// los refrescos de clima cada 15 min, para no reiniciar el carrousel si el
// visitante lo está mirando).
let provinciaImagenesResueltas = false;

function actualizarImagenesSegunProvincia(codigoIso) {
  if (provinciaImagenesResueltas) return;
  provinciaImagenesResueltas = true;

  const slug = codigoIso && PROVINCIA_POR_CODIGO_ISO[codigoIso];
  const fotosProvincia = slug && IMAGENES_POR_PROVINCIA[slug];

  if (fotosProvincia && fotosProvincia.length) {
    IMAGENES_CIUDAD = barajar(fotosProvincia);
  } else {
    // Geolocalización rechazada, fallida, o provincia sin fotos cargadas:
    // mostramos fotos al azar de todo el país.
    const todasLasFotos = Object.values(IMAGENES_POR_PROVINCIA).flat();
    IMAGENES_CIUDAD = barajar(todasLasFotos);
  }
  indiceCiudad = 0;

  // Si el visitante ya está viendo el carrousel en la pantalla principal
  // (y está en Modo Fallout, el único que usa estas fotos), lo repintamos
  // con las fotos recién resueltas.
  if (!seccionActiva && !filtroMarcaGlobal && modoVisual === "fallout") {
    const productosEl = document.getElementById("productos");
    if (productosEl) {
      detenerCarrouselCiudad();
      pintarCarrouselCiudad(productosEl);
    }
  }
}

async function cargarClimaYCiudad(lat, lon, ubicacionReal) {
  let codigoIso = null;
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
      codigoIso = datosCiudad.principalSubdivisionCode || null;
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
  // Solo confiamos en la provincia si la ubicación vino de geolocalización
  // real aceptada por el visitante; si no (permiso denegado, no soportado,
  // etc.), el default es Córdoba ("AR-X"), no fotos de todo el país.
  actualizarImagenesSegunProvincia(ubicacionReal ? codigoIso : "AR-X");
  pintarFechaHoraTemp();
}

function iniciarUbicacionYClima() {
  if (!("geolocation" in navigator)) {
    cargarClimaYCiudad(COORD_RESPALDO.lat, COORD_RESPALDO.lon, false);
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (posicion) => cargarClimaYCiudad(posicion.coords.latitude, posicion.coords.longitude, true),
    () => cargarClimaYCiudad(COORD_RESPALDO.lat, COORD_RESPALDO.lon, false),
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

  // El texto está anclado con bottom:0, así que para que entre totalmente
  // oculto abajo hay que arrancar en +scrollHeight (no +clientHeight), y para
  // que salga totalmente oculto arriba hay que llegar a -clientHeight (no
  // -scrollHeight) — si no, se queda a mitad de camino, todavía visible.
  let posicion = el.scrollHeight;
  const destino = -contenedor.clientHeight;
  el.style.transform = `translateY(${posicion}px)`;

  requestAnimationFrame(() => {
    const intervalo = setInterval(() => {
      posicion -= pxPorTick;
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
window.addEventListener("resize", sincronizarAnchoBuscadorHeader);
window.addEventListener("resize", ajustarAlturaRecomendadosMobile);

pintarCarrousel();
renderCarrito();

// Link compartido (ver compartirProducto): busca el producto en cualquier
// sección, navega ahí y lo deja "en modo pop" (misma clase .expandida que
// usa el click normal en la card). Corre después de que cargarCatalogo
// termina su propio pintado inicial (home/carrousel), así que pisa esa
// vista con la sección del producto compartido.
function buscarProductoYSeccion(nombre) {
  for (const [clave, productos] of Object.entries(SECCIONES_DATA)) {
    const encontrado = productos.find((p) => p.nombre === nombre);
    if (encontrado) return clave;
  }
  return null;
}

function abrirProductoCompartido() {
  const nombreObjetivo = paramsMailingActuales().producto;
  if (!nombreObjetivo) return;
  const clave = buscarProductoYSeccion(nombreObjetivo);
  if (!clave) return;
  seccionActiva = clave;
  subFiltrosActivos = new Set();
  filtroMarcaGlobal = null;
  pushEstadoNav();
  actualizarVista();
  requestAnimationFrame(() => {
    const card = [...document.querySelectorAll("#productos .card")]
      .find((c) => c.dataset.nombre === nombreObjetivo);
    if (!card) return;
    card.classList.add("expandida");
    card.scrollIntoView({ behavior: "smooth", block: "center" });
  });
}

async function procesarLinkMailing() {
  const { producto: nombreObjetivo, codigo, agregar } = paramsMailingActuales();
  if (!nombreObjetivo || !agregar) return;

  const clave = buscarProductoYSeccion(nombreObjetivo);
  if (!clave) return;
  const producto = (SECCIONES_DATA[clave] || []).find((p) => p.nombre === nombreObjetivo);
  if (!producto) return;

  if (!(await asegurarSesionParaCarrito(producto, null))) return;

  agregarAlCarrito(producto, null);
  if (codigo) {
    await aplicarCodigoMailingPorValor(codigo);
  }
  abrirCarrito();
  limpiarParametrosMailingProcesados();
}

cargarCatalogo().then(async () => {
  await procesarPendienteCarrito();
  if (await procesarCheckoutPendiente()) return;
  abrirProductoCompartido();
  await procesarLinkMailing();
});
