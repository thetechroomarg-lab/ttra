// Parte 1 de la landing (se carga antes que el resto, ver index.html).
// Beep de interacción, helpers de producto/marca, tracking de interacciones
// y el tema del modo Classic.
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
  "Logitech": "logitech", "Itel": "itel", "HP": "hp", "Lenovo": "lenovo",
  "Asus": "asus", "Acer": "acer", "Dell": "dell", "MSI": "msi",
  "Gigabyte": "gigabyte", "Xtrem": "xtrem", "Otras marcas": "otras-marcas",
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
  // Marca sin logo mapeado (ej. una marca nueva que llegó en un catálogo
  // actualizado): usa la insignia genérica en vez de dejar el casillero
  // vacío, así la grilla de "Búsqueda por Marca" nunca queda rota.
  const slug = MARCA_LOGO[marca] || MARCA_LOGO["Otras marcas"];
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
// Modo Fallout deshabilitado (a pedido: sin acceso de usuario por ahora,
// solo Classic). Se comenta el atajo ?modo=fallout en vez de borrarlo, para
// poder restaurarlo fácilmente el día que se vuelva a habilitar.
// let modoVisual = new URLSearchParams(location.search).get("modo") === "fallout" ? "fallout" : "classic";
let modoVisual = "classic";

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
    "ciudad/provincias/buenos-aires/basilica-de-lujan.jpg",
    "ciudad/provincias/buenos-aires/sierra-de-la-ventana.jpg",
    "ciudad/provincias/buenos-aires/torreon-del-monje.jpg",
  ],
  caba: [
    "ciudad/provincias/caba/obelisco.jpg",
    "ciudad/provincias/caba/teatro-colon.jpg",
    "ciudad/provincias/caba/puente-de-la-mujer.jpg",
    "ciudad/provincias/caba/caminito.jpg",
    "ciudad/provincias/caba/cementerio-de-la-recoleta.jpg",
    "ciudad/provincias/caba/congreso-nacional.jpg",
  ],
  catamarca: [
    "ciudad/provincias/catamarca/ruinas-del-shincal.jpg",
    "ciudad/provincias/catamarca/campo-de-piedra-pomez.jpg",
    "ciudad/provincias/catamarca/termas-de-fiambala.jpg",
    "ciudad/provincias/catamarca/dique-las-pirquitas.jpg",
    "ciudad/provincias/catamarca/catedral-basilica-nuestra-senora-del-valle.jpg",
    "ciudad/provincias/catamarca/cuesta-del-portezuelo.jpg",
  ],
  chaco: [
    "ciudad/provincias/chaco/parque-nacional-chaco.jpg",
    "ciudad/provincias/chaco/ciudad-de-las-esculturas-resistencia.jpg",
    "ciudad/provincias/chaco/isla-del-cerrito.jpg",
    "ciudad/provincias/chaco/catedral-de-resistencia.jpg",
    "ciudad/provincias/chaco/puente-general-belgrano.jpg",
    "ciudad/provincias/chaco/casa-de-gobierno-del-chaco.jpg",
  ],
  chubut: [
    "ciudad/provincias/chubut/peninsula-valdes.jpg",
    "ciudad/provincias/chubut/la-trochita.jpg",
    "ciudad/provincias/chubut/punta-tombo.jpg",
    "ciudad/provincias/chubut/parque-nacional-los-alerces.jpg",
    "ciudad/provincias/chubut/cabo-dos-bahias.jpg",
    "ciudad/provincias/chubut/cabana-de-butch-cassidy-cholila.jpg",
  ],
  cordoba: [
    ...IMAGENES_CORDOBA_CAPITAL,
    "ciudad/provincias/cordoba-provincia/la-cumbrecita.jpg",
    "ciudad/provincias/cordoba-provincia/reloj-cucu-la-falda.jpg",
    "ciudad/provincias/cordoba-provincia/cerro-uritorco.jpg",
    "ciudad/provincias/cordoba-provincia/estancia-jesuitica-santa-catalina.jpg",
    "ciudad/provincias/cordoba-provincia/dique-san-roque.jpg",
    "ciudad/provincias/cordoba-provincia/villa-general-belgrano.jpg",
  ],
  corrientes: [
    "ciudad/provincias/corrientes/esteros-del-ibera.jpg",
    "ciudad/provincias/corrientes/puente-general-belgrano.jpg",
    "ciudad/provincias/corrientes/costanera-correntina.jpg",
    "ciudad/provincias/corrientes/casa-de-san-martin-yapeyu.jpg",
    "ciudad/provincias/corrientes/basilica-de-itati.jpg",
    "ciudad/provincias/corrientes/teatro-juan-de-vera.jpg",
  ],
  "entre-rios": [
    "ciudad/provincias/entre-rios/palacio-san-jose.jpg",
    "ciudad/provincias/entre-rios/parque-nacional-el-palmar.jpg",
    "ciudad/provincias/entre-rios/costanera-de-concordia.jpg",
    "ciudad/provincias/entre-rios/termas-de-federacion.jpg",
    "ciudad/provincias/entre-rios/basilica-inmaculada-concepcion.jpg",
    "ciudad/provincias/entre-rios/puente-general-artigas.jpg",
  ],
  formosa: [
    "ciudad/provincias/formosa/plaza-san-martin-formosa.jpg",
    "ciudad/provincias/formosa/banado-la-estrella.jpg",
    "ciudad/provincias/formosa/parque-nacional-rio-pilcomayo.jpg",
    "ciudad/provincias/formosa/costanera-de-formosa.jpg",
    "ciudad/provincias/formosa/catedral-nuestra-senora-del-carmen.jpg",
    "ciudad/provincias/formosa/laguna-oca.jpg",
  ],
  jujuy: [
    "ciudad/provincias/jujuy/cerro-de-los-siete-colores-purmamarca.jpg",
    "ciudad/provincias/jujuy/quebrada-de-humahuaca.jpg",
    "ciudad/provincias/jujuy/salinas-grandes.jpg",
    "ciudad/provincias/jujuy/pucara-de-tilcara.jpg",
    "ciudad/provincias/jujuy/laguna-de-los-pozuelos.jpg",
    "ciudad/provincias/jujuy/catedral-de-san-salvador-de-jujuy.jpg",
  ],
  "la-pampa": [
    "ciudad/provincias/la-pampa/parque-nacional-lihue-calel.jpg",
    "ciudad/provincias/la-pampa/santa-rosa-capital.jpg",
    "ciudad/provincias/la-pampa/parque-luro.jpg",
    "ciudad/provincias/la-pampa/laguna-don-tomas.jpg",
    "ciudad/provincias/la-pampa/embalse-casa-de-piedra.jpg",
    "ciudad/provincias/la-pampa/catedral-santa-rosa-de-lima.jpg",
  ],
  "la-rioja": [
    "ciudad/provincias/la-rioja/parque-nacional-talampaya.jpg",
    "ciudad/provincias/la-rioja/cable-carril-la-mejicana-chilecito.jpg",
    "ciudad/provincias/la-rioja/casa-de-gobierno-la-rioja.jpg",
    "ciudad/provincias/la-rioja/catedral-de-la-rioja.jpg",
    "ciudad/provincias/la-rioja/cuesta-de-miranda.jpg",
    "ciudad/provincias/la-rioja/dique-los-sauces.jpg",
  ],
  mendoza: [
    "ciudad/provincias/mendoza/cerro-aconcagua.jpg",
    "ciudad/provincias/mendoza/puente-del-inca.jpg",
    "ciudad/provincias/mendoza/vinedo-valle-de-uco.jpg",
    "ciudad/provincias/mendoza/canon-del-atuel.jpg",
    "ciudad/provincias/mendoza/reserva-villavicencio.jpg",
    "ciudad/provincias/mendoza/plaza-independencia.jpg",
  ],
  misiones: [
    "ciudad/provincias/misiones/cataratas-del-iguazu.jpg",
    "ciudad/provincias/misiones/ruinas-san-ignacio-mini.jpg",
    "ciudad/provincias/misiones/salto-encantado.jpg",
    "ciudad/provincias/misiones/saltos-del-mocona.jpg",
    "ciudad/provincias/misiones/ruinas-de-loreto.jpg",
    "ciudad/provincias/misiones/costanera-de-posadas.jpg",
  ],
  neuquen: [
    "ciudad/provincias/neuquen/volcan-lanin.jpg",
    "ciudad/provincias/neuquen/lago-lacar.jpg",
    "ciudad/provincias/neuquen/lago-correntoso.jpg",
    "ciudad/provincias/neuquen/san-martin-de-los-andes.jpg",
    "ciudad/provincias/neuquen/museo-carmen-funes.jpg",
    "ciudad/provincias/neuquen/lago-huechulafquen.jpg",
  ],
  "rio-negro": [
    "ciudad/provincias/rio-negro/centro-civico-bariloche.jpg",
    "ciudad/provincias/rio-negro/cerro-catedral.jpg",
    "ciudad/provincias/rio-negro/lago-nahuel-huapi.jpg",
    "ciudad/provincias/rio-negro/el-bolson.jpg",
    "ciudad/provincias/rio-negro/las-grutas.jpg",
    "ciudad/provincias/rio-negro/cerro-tronador.jpg",
  ],
  salta: [
    "ciudad/provincias/salta/viaducto-la-polvorilla.jpg",
    "ciudad/provincias/salta/quebrada-de-las-conchas.jpg",
    "ciudad/provincias/salta/catedral-de-salta.jpg",
    "ciudad/provincias/salta/cerro-san-bernardo.jpg",
    "ciudad/provincias/salta/cachi.jpg",
    "ciudad/provincias/salta/cuesta-del-obispo.jpg",
  ],
  "san-juan": [
    "ciudad/provincias/san-juan/valle-de-la-luna.jpg",
    "ciudad/provincias/san-juan/dique-ullum.jpg",
    "ciudad/provincias/san-juan/santuario-difunta-correa.jpg",
    "ciudad/provincias/san-juan/parque-nacional-el-leoncito.jpg",
    "ciudad/provincias/san-juan/barreal.jpg",
    "ciudad/provincias/san-juan/catedral-de-san-juan.jpg",
  ],
  "san-luis": [
    "ciudad/provincias/san-luis/sierra-de-las-quijadas.jpg",
    "ciudad/provincias/san-luis/antigua-casa-potrero-de-los-funes.jpg",
    "ciudad/provincias/san-luis/mirador-del-sol-merlo.jpg",
    "ciudad/provincias/san-luis/salinas-del-bebedero.jpg",
    "ciudad/provincias/san-luis/templo-historico-villa-de-merlo.jpg",
    "ciudad/provincias/san-luis/salto-del-tigre.jpg",
  ],
  "santa-cruz": [
    "ciudad/provincias/santa-cruz/glaciar-perito-moreno.jpg",
    "ciudad/provincias/santa-cruz/cueva-de-las-manos.jpg",
    "ciudad/provincias/santa-cruz/monte-fitz-roy-el-chalten.jpg",
    "ciudad/provincias/santa-cruz/puerto-deseado.jpg",
    "ciudad/provincias/santa-cruz/pinguinos-cabo-virgenes.jpg",
    "ciudad/provincias/santa-cruz/bahia-de-san-julian.jpg",
  ],
  "santa-fe": [
    "ciudad/provincias/santa-fe/monumento-a-la-bandera-rosario.jpg",
    "ciudad/provincias/santa-fe/catedral-de-santa-fe.jpg",
    "ciudad/provincias/santa-fe/laguna-setubal.jpg",
    "ciudad/provincias/santa-fe/puente-colgante-santa-fe.jpg",
    "ciudad/provincias/santa-fe/parque-de-la-independencia.jpg",
    "ciudad/provincias/santa-fe/basilica-de-guadalupe.jpg",
  ],
  "santiago-del-estero": [
    "ciudad/provincias/santiago-del-estero/catedral-basilica.jpg",
    "ciudad/provincias/santiago-del-estero/termas-de-rio-hondo.jpg",
    "ciudad/provincias/santiago-del-estero/convento-santo-domingo.jpg",
    "ciudad/provincias/santiago-del-estero/parque-aguirre.jpg",
    "ciudad/provincias/santiago-del-estero/dique-frontal-rio-hondo.jpg",
    "ciudad/provincias/santiago-del-estero/casa-de-gobierno.jpg",
  ],
  "tierra-del-fuego": [
    "ciudad/provincias/tierra-del-fuego/panoramica-ushuaia.jpg",
    "ciudad/provincias/tierra-del-fuego/bahia-lapataia-parque-nacional.jpg",
    "ciudad/provincias/tierra-del-fuego/faro-les-eclaireurs.jpg",
    "ciudad/provincias/tierra-del-fuego/glaciar-martial.jpg",
    "ciudad/provincias/tierra-del-fuego/tren-del-fin-del-mundo.jpg",
    "ciudad/provincias/tierra-del-fuego/estancia-harberton.jpg",
  ],
  tucuman: [
    "ciudad/provincias/tucuman/casa-historica-independencia.jpg",
    "ciudad/provincias/tucuman/ruinas-de-quilmes.jpg",
    "ciudad/provincias/tucuman/cerro-san-javier.jpg",
    "ciudad/provincias/tucuman/dique-el-cadillal.jpg",
    "ciudad/provincias/tucuman/iglesia-san-francisco.jpg",
    "ciudad/provincias/tucuman/parque-9-de-julio.jpg",
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
