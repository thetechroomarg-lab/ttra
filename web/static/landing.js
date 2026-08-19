// --- Gate inicial: pide nombre + celular una vez por dispositivo, antes de
// dejar ver el sitio. Se guarda en localStorage para no volver a pedirlo, y
// se manda al servidor para sumarlo al registro de clientes (mismo archivo
// que ya usa el buscador vía web/leads.py). ---
(function () {
  const gate = document.getElementById("rc-gate");
  if (!gate) return;
  try {
    if (localStorage.getItem("ttra_cliente")) {
      gate.classList.add("oculto");
      return;
    }
  } catch {
    gate.classList.add("oculto"); // localStorage no disponible: no bloqueamos al usuario
    return;
  }
  const form = document.getElementById("form-gate");
  const error = document.getElementById("gate-error");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const nombre = document.getElementById("gate-nombre").value.trim();
    const celular = document.getElementById("gate-celular").value.trim();
    if (!nombre || !celular) {
      error.classList.add("visible");
      return;
    }
    error.classList.remove("visible");
    try {
      localStorage.setItem("ttra_cliente", JSON.stringify({ nombre, celular }));
    } catch {
      // Sin localStorage se le va a volver a pedir en la próxima visita: no es crítico.
    }
    gate.classList.add("oculto");
    fetch("/api/registro-cliente", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ nombre, celular }),
    }).catch(() => {});
  });
})();

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
let ordenPrecio = null; // null (sin orden) | "asc" | "desc"
// Classic es siempre el modo de arranque (ver boot.js); Fallout solo dura
// mientras no se recarga la página, no se persiste entre refrescos.
let modoVisual = "classic";

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

// --- Carrousel de productos recomendados (Modo Classic, reemplaza al Pip-Boy) ---

// Un producto es "usado" si su nombre o categoría lo indica (CPO también
// cuenta: son celulares con batería usada, ver disclaimer de usados).
function esProductoUsado(p) {
  const texto = `${p.nombre || ""} ${p.categoria || ""}`.toLowerCase();
  return texto.includes("usado") || texto.includes("cpo");
}

// Elige `n` productos distintos al azar (sin repetidos) de todo el catálogo,
// excluyendo siempre celulares usados/CPO.
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

function tarjetaRecomendadoHtml(p) {
  const tieneColores = Array.isArray(p.colores) && p.colores.length > 0;
  const listaColores = tieneColores ? p.colores : ["Color único"];
  const colorInicial = tieneColores ? "" : "Color único";
  return `
    <div class="tarjeta-recomendado" data-nombre="${escapeHtml(p.nombre)}">
      <div class="tarjeta-recomendado-etiqueta">✨ Recomendado para vos</div>
      <h3>${escapeHtml(p.nombre)}</h3>
      <p class="tarjeta-recomendado-precio">
        <strong>U$D ${p.usd ?? "-"}</strong>
        <span>$ ${formatearPesos(p.pesos)} contado</span>
        <span>$ ${formatearPesos(p.transferencia)} transferencia</span>
      </p>
      <div class="tarjeta-recomendado-acciones">
        <div class="dropdown-color">
          <button type="button" class="dropdown-color-boton" data-valor="${escapeHtml(colorInicial)}">
            ${escapeHtml(tieneColores ? "Elegir color" : colorInicial)}
          </button>
          <ul class="dropdown-color-lista oculto" role="listbox">
            ${listaColores.map((c) => `<li role="option" data-valor="${escapeHtml(c)}">${escapeHtml(c)}</li>`).join("")}
          </ul>
        </div>
        <button class="btn-agregar" type="button" data-color="${escapeHtml(colorInicial)}" ${tieneColores ? "disabled" : ""}>Agregar</button>
      </div>
    </div>
  `;
}

function tarjetasRecomendadosHtml() {
  const productos = productosAlAzar(3);
  if (!productos.length) {
    return `<div class="tarjeta-recomendado tarjeta-recomendado-vacia"><p>Cargando recomendaciones...</p></div>`;
  }
  return productos.map(tarjetaRecomendadoHtml).join("");
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
      btnAgregar.addEventListener("click", () => {
        agregarAlCarrito(producto, btnAgregar.dataset.color || null);
      });
    }
  });
}

function iniciarCicloRecomendados(el) {
  clearInterval(intervaloCiudad);
  intervaloCiudad = setInterval(() => {
    const grilla = el.querySelector(".carrousel-recomendados-grid");
    if (!grilla) return;
    grilla.classList.remove("visible");
    setTimeout(() => {
      grilla.innerHTML = tarjetasRecomendadosHtml();
      wireTarjetasRecomendadas(el);
      grilla.classList.add("visible");
    }, 250);
  }, 12000);
}

function pintarCarrouselRecomendados(el) {
  el.innerHTML = `
    <div class="carrousel-recomendados-wrap">
      <div class="carrousel-recomendados-grid visible">${tarjetasRecomendadosHtml()}</div>
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
  if (modoVisual === "classic") pintarCarrouselRecomendados(el);
  else pintarCarrouselCiudad(el);
}

// El favicon cambia junto con el modo: monograma navy/rojo en Classic,
// verde fósforo estilo Pip-Boy en Fallout.
function actualizarFavicon(modo) {
  const link = document.querySelector('link[rel="icon"]');
  if (!link) return;
  link.href = modo === "fallout" ? "favicon-fallout.svg" : "favicon.svg";
}

function aplicarModoVisual(modo, opciones) {
  const opts = opciones || {};
  modoVisual = modo;
  document.documentElement.setAttribute("data-modo", modo);
  document.querySelectorAll(".btn-modo").forEach((b) => {
    b.classList.toggle("activo", b.dataset.modo === modo);
  });
  actualizarFavicon(modo);
  if (opts.sinRepintar) return;
  // pintarFrasePie está definida más abajo en el archivo (function declaration,
  // hoisted) pero usa FRASES_FALLOUT/FRASES_LATINOAMERICANAS (const, con TDZ):
  // solo es seguro llamarla acá porque este tramo nunca corre durante la
  // ejecución inicial del script (esa pasa por sinRepintar:true y ya retornó
  // arriba), sino recién ante un click del usuario, bien después de que todo
  // el archivo terminó de ejecutarse.
  pintarFrasePie();
  const carrouselMarcasEl = document.getElementById("carrousel");
  if (carrouselMarcasEl) iniciarDesplazamientoCarrousel(carrouselMarcasEl);
  if (!seccionActiva && !filtroMarcaGlobal) {
    const productosEl = document.getElementById("productos");
    if (productosEl) {
      detenerCarrouselCiudad();
      pintarCarrouselSegunModo(productosEl);
    }
  }
}

document.getElementById("btn-modo-fallout").addEventListener("click", () => {
  aplicarModoVisual("fallout");
  if (typeof window.reproducirBootSequenceTTRA === "function") {
    window.reproducirBootSequenceTTRA();
  }
});
document.getElementById("btn-modo-classic").addEventListener("click", () => {
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

// --- Log out: borra el registro del cliente (nombre/celular guardados por
// el gate inicial) y muestra un mensaje de confirmación con el estilo del
// modo activo. Al cerrar el mensaje se recarga la página, así vuelve a
// aparecer el gate para volver a identificarse. ---
function cerrarSesionCliente() {
  try {
    localStorage.removeItem("ttra_cliente");
  } catch {
    // Sin localStorage no había nada que borrar: no es crítico.
  }
  const msg = document.getElementById("rc-logout-msg");
  if (msg) msg.classList.add("visible");
}

const btnLogoutClassic = document.getElementById("btn-logout-classic");
if (btnLogoutClassic) btnLogoutClassic.addEventListener("click", cerrarSesionCliente);

const btnLogoutFallout = document.getElementById("btn-logout-fallout");
if (btnLogoutFallout) {
  btnLogoutFallout.addEventListener("click", () => {
    btnLogoutFallout.classList.add("apagado");
    btnLogoutFallout.setAttribute("aria-pressed", "false");
    cerrarSesionCliente();
  });
}

const btnLogoutCerrar = document.getElementById("btn-logout-cerrar");
if (btnLogoutCerrar) {
  btnLogoutCerrar.addEventListener("click", () => location.reload());
}

// Al pasar el mouse sobre "Modo Fallout" suena el tema de radio de Fallout;
// se corta apenas el cursor se va del botón.
const btnModoFallout = document.getElementById("btn-modo-fallout");
const audioModoFallout = document.getElementById("audio-modo-fallout");
if (btnModoFallout && audioModoFallout) {
  btnModoFallout.addEventListener("mouseenter", () => {
    audioModoFallout.currentTime = 0;
    audioModoFallout.play().catch(() => {
      // Autoplay bloqueado hasta el primer gesto del usuario: no es crítico.
    });
  });
  btnModoFallout.addEventListener("mouseleave", () => {
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
const btnModoClassic = document.getElementById("btn-modo-classic");
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

  const primeraTanda = el.querySelector(".carrousel-tanda");
  let posicion = 0;
  let anchoTanda = 0;

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
    if (intervaloMarcas) clearInterval(intervaloMarcas);
    intervaloMarcas = setInterval(paso, 60);
  }

  const listoParaMedir = document.fonts && document.fonts.ready
    ? document.fonts.ready
    : Promise.resolve();
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

// Cierra cualquier dropdown de color que haya quedado abierto (se llama al
// abrir otro, o al hacer click en cualquier otro lado de la página).
function cerrarDropdownsColor() {
  document.querySelectorAll(".dropdown-color-lista").forEach((l) => l.classList.add("oculto"));
}
document.addEventListener("click", cerrarDropdownsColor);

function tarjetaProducto(p) {
  const tieneColores = Array.isArray(p.colores) && p.colores.length > 0;
  const listaColores = tieneColores ? p.colores : ["Color único"];
  const colorInicial = tieneColores ? "" : "Color único";
  const colores = `
    <div class="selector-colores">
      <strong>Color:</strong>
      <div class="dropdown-color">
        <button type="button" class="dropdown-color-boton" data-valor="${escapeHtml(colorInicial)}">
          ${escapeHtml(tieneColores ? "Elegir color" : colorInicial)}
        </button>
        <ul class="dropdown-color-lista oculto" role="listbox">
          ${listaColores.map((c) => `<li role="option" data-valor="${escapeHtml(c)}">${escapeHtml(c)}</li>`).join("")}
        </ul>
      </div>
    </div>
  `;
  return `
    <div class="card">
      <h3>${escapeHtml(p.nombre)}</h3>
      ${colores}
      <p class="precios">
        <strong>U$D ${p.usd ?? "-"}</strong><br>
        $ ${formatearPesos(p.pesos)} contado<br>
        $ ${formatearPesos(p.transferencia)} transferencia
      </p>
      <button class="btn-agregar" data-nombre="${escapeHtml(p.nombre)}" data-color="${escapeHtml(colorInicial)}" type="button" ${tieneColores ? "disabled" : ""}>Agregar al carrito</button>
    </div>
  `;
}

// Etiqueta y flecha del botón de orden, según el estado actual.
function etiquetaOrdenPrecio() {
  if (ordenPrecio === "asc") return 'Precio <span class="flecha-orden">↑</span>';
  if (ordenPrecio === "desc") return 'Precio <span class="flecha-orden">↓</span>';
  return "Ordenar precio";
}

function controlVistaHtml() {
  return `
    <div class="control-vista">
      <button type="button" class="btn-vista ${modoVista === "cards" ? "activo" : ""}" data-modo="cards">Cards</button>
      <button type="button" class="btn-vista ${modoVista === "lista" ? "activo" : ""}" data-modo="lista">Lista</button>
      <button type="button" class="btn-vista btn-orden-precio ${ordenPrecio ? "activo" : ""}" id="btn-orden-precio">${etiquetaOrdenPrecio()}</button>
    </div>
  `;
}

// Ciclo: sin orden -> ascendente -> descendente -> sin orden.
function siguienteOrdenPrecio() {
  if (ordenPrecio === null) return "asc";
  if (ordenPrecio === "asc") return "desc";
  return null;
}

function ordenarPorPrecio(productos) {
  if (!ordenPrecio) return productos;
  const signo = ordenPrecio === "asc" ? 1 : -1;
  return [...productos].sort((a, b) => signo * ((a.usd ?? 0) - (b.usd ?? 0)));
}

function pintarGrilla(el, productos, mensajeVacio) {
  if (!productos || productos.length === 0) {
    el.innerHTML = `<p class="mensaje-vacio">${mensajeVacio}</p>`;
    return;
  }
  productos = ordenarPorPrecio(productos);
  const claseModo = modoVista === "lista" ? "lista" : "";
  el.innerHTML = `${controlVistaHtml()}<div class="grilla ${claseModo}">${productos.map(tarjetaProducto).join("")}</div>`;
  el.querySelectorAll(".card").forEach((card) => {
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
    btnAgregar.addEventListener("click", () => {
      const producto = productos.find((p) => p.nombre === btnAgregar.dataset.nombre);
      if (producto) agregarAlCarrito(producto, btnAgregar.dataset.color || null);
    });
  });
  el.querySelectorAll(".btn-vista[data-modo]").forEach((btn) => {
    btn.addEventListener("click", () => {
      modoVista = btn.dataset.modo;
      actualizarVista();
    });
  });
  const btnOrden = el.querySelector("#btn-orden-precio");
  if (btnOrden) {
    btnOrden.addEventListener("click", () => {
      ordenPrecio = siguienteOrdenPrecio();
      actualizarVista();
    });
  }
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
  // El switch de log out (Modo Fallout) solo tiene sentido en el home: al
  // entrar a una sección los botones de categoría desaparecen y quedaba
  // como el único control visible en la barra lateral.
  const switchWrap = document.getElementById("rc-switch-fallout-wrap");
  if (switchWrap) switchWrap.classList.toggle("oculto", !enInicio);

  detenerCarrouselCiudad();

  if (enInicio) {
    pintarCarrouselSegunModo(productosEl);
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

// --- Frase del pie: Fallout en Modo Fallout, figuras históricas
// latinoamericanas en Modo Classic ---

const FRASES_FALLOUT = [
  { texto: "La guerra. La guerra nunca cambia.", autor: "El Narrador", fuente: "Fallout" },
  { texto: "¡La libertad prevalecerá!", autor: "Liberty Prime", fuente: "Fallout 3" },
  { texto: "Ad Victoriam.", autor: "Hermandad del Acero", fuente: "Fallout 4" },
  { texto: "Prepárate para el futuro... ¡hoy!", autor: "Vault-Tec", fuente: "Fallout" },
  { texto: "¡Habla Three Dog, estás escuchando Radio Galaxia!", autor: "Three Dog", fuente: "Fallout 3" },
  { texto: "¡Por la República!", autor: "Soldado de la NCR", fuente: "Fallout: New Vegas" },
];

const FRASES_LATINOAMERICANAS = [
  { texto: "Un pueblo ignorante es un instrumento ciego de su propia destrucción.", autor: "Simón Bolívar", fuente: "Venezuela" },
  { texto: "Patria es humanidad.", autor: "José Martí", fuente: "Cuba" },
  { texto: "Hasta la victoria siempre.", autor: "Ernesto Che Guevara", fuente: "Argentina" },
  { texto: "Seamos libres, lo demás no importa nada.", autor: "José de San Martín", fuente: "Argentina" },
  { texto: "¡Tierra y Libertad!", autor: "Emiliano Zapata", fuente: "México" },
  { texto: "La libertad no se mendiga, se conquista con el filo de la espada.", autor: "Simón Bolívar", fuente: "Venezuela" },
  { texto: "No hay libertad pequeña ni tirano grande.", autor: "Simón Bolívar", fuente: "Venezuela" },
  { texto: "Yo no vine a la Revolución a hacerme rico, vine a luchar por mis ideales.", autor: "Francisco Villa", fuente: "México" },
];

function pintarFrasePie() {
  const el = document.getElementById("pie-frase");
  if (!el) return;
  const lista = modoVisual === "classic" ? FRASES_LATINOAMERICANAS : FRASES_FALLOUT;
  const horaBucket = Math.floor(Date.now() / (60 * 60 * 1000));
  const frase = lista[horaBucket % lista.length];
  el.textContent = `"${frase.texto}" -- ${frase.autor} (${frase.fuente})`;
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

pintarCarrousel();
renderCarrito();
cargarCatalogo();
