// Panel flotante de perfil (#panel-perfil en index.html). No carga nada
// hasta que se llama a window.abrirPanelPerfil(), para no pegarle a /api/me
// en cada carga de la home. En otras páginas se abre dentro del <dialog> de
// cart-drawer.js, con la home embebida en un iframe.
const panelPerfilEmbebido = document.getElementById("panel-perfil");
const btnCerrarPanelPerfil = document.getElementById("btn-cerrar-panel-perfil");
const overlayPerfilEmbebido = document.getElementById("overlay-perfil");
const domicilioDireccionInput = document.getElementById("domicilio-direccion");
const domicilioAliasInput = document.getElementById("domicilio-alias");
const domicilioPisoInput = document.getElementById("domicilio-piso");
const domicilioDeptoInput = document.getElementById("domicilio-depto");
function textoPisoDepto(domicilio) {
  return [domicilio.piso && `Piso ${domicilio.piso}`, domicilio.depto && `Depto ${domicilio.depto}`].filter(Boolean).join(" · ");
}
const perfilSugerenciasDireccion = document.getElementById("perfil-sugerencias-direccion");
const listaDomicilios = document.getElementById("lista-domicilios");
const btnGuardarDomicilio = document.getElementById("btn-guardar-domicilio");
const btnCancelarEdicionDomicilio = document.getElementById("btn-cancelar-edicion-domicilio");
let apiPlacesPerfil;
let domicilioEnEdicionId = null;
let domicilioPrincipalActual = null;
// Coordenadas del domicilio en el formulario: salen del autocompletado y el
// pin del mapa las ajusta. Se mandan al guardar para que el cadete llegue a la puerta.
let coordsDomicilioActual = null;
const mapaDomicilio = window.TTRAMapaPin.crear(document.getElementById("domicilio-mapa"), (coords) => {
  coordsDomicilioActual = coords;
});

// Sesión vencida con un panel abierto (p. ej. el celular quedó horas en
// pausa): se pide el login en el modal y se vuelve al mismo panel, nunca a
// una pantalla completa.
function pedirLoginDesdePanel(panel) {
  if (document.documentElement.classList.contains("ttra-cart-embedded")) {
    parent.postMessage({ type: "ttra:panel-login", panel }, location.origin);
    return;
  }
  cerrarPanelPerfil();
  if (typeof cerrarPanelPedidos === "function") cerrarPanelPedidos();
  const disparador = document.getElementById("btn-perfil-toggle") || document.body;
  import("/login-drawer.js").then(({ abrirLoginEnPagina }) => {
    abrirLoginEnPagina(disparador, () => {
      const url = new URL(location.href);
      url.searchParams.set("panel", panel);
      location.href = url.toString();
    });
  });
}

function cerrarPanelPerfil() {
  if (!panelPerfilEmbebido) return;
  panelPerfilEmbebido.classList.add("oculto");
  if (overlayPerfilEmbebido) overlayPerfilEmbebido.classList.add("oculto");
}

if (btnCerrarPanelPerfil) {
  btnCerrarPanelPerfil.addEventListener("click", cerrarPanelPerfil);
}
// Tocar el fondo blureado no cierra el perfil: se perdían datos a medio
// editar. Se cierra solo con la ✕.

function ocultarSugerenciasPerfilDireccion(lista = perfilSugerenciasDireccion) {
  lista.replaceChildren();
  lista.hidden = true;
}

async function cargarApiPlacesPerfil() {
  if (apiPlacesPerfil !== undefined) return apiPlacesPerfil;
  apiPlacesPerfil = fetch("/api/configuracion-publica")
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
  return apiPlacesPerfil;
}

// Sugerencias de Google Places bajo un campo de dirección. Se usa en el
// formulario de domicilios y en el domicilio principal del perfil.
async function mostrarSugerenciasPerfilDireccion(texto, input, lista, alElegir) {
  const places = await cargarApiPlacesPerfil();
  if (!places || texto !== input.value.trim()) return;
  const { AutocompleteSuggestion } = places;
  const { suggestions } = await AutocompleteSuggestion.fetchAutocompleteSuggestions({
    input: texto,
    includedRegionCodes: ["ar"],
  });
  if (texto !== input.value.trim() || !suggestions?.length) {
    ocultarSugerenciasPerfilDireccion(lista);
    return;
  }
  lista.replaceChildren(...suggestions.slice(0, 5).map(({ placePrediction }) => {
    const item = document.createElement("li");
    const boton = document.createElement("button");
    boton.type = "button";
    boton.textContent = placePrediction.text.text;
    boton.addEventListener("click", async () => {
      const place = placePrediction.toPlace();
      await place.fetchFields({ fields: ["formattedAddress", "location"] });
      input.value = place.formattedAddress || placePrediction.text.text;
      ocultarSugerenciasPerfilDireccion(lista);
      alElegir(place.location ? { lat: place.location.lat(), lng: place.location.lng() } : null);
    });
    item.append(boton);
    return item;
  }));
  lista.hidden = false;
}

function conectarAutocompletadoDireccion(input, lista, alEscribir, alElegir) {
  let temporizador;
  input.addEventListener("input", () => {
    clearTimeout(temporizador);
    alEscribir();
    const texto = input.value.trim();
    if (texto.length < 3) {
      ocultarSugerenciasPerfilDireccion(lista);
      return;
    }
    temporizador = setTimeout(() => {
      mostrarSugerenciasPerfilDireccion(texto, input, lista, alElegir).catch(() => ocultarSugerenciasPerfilDireccion(lista));
    }, 250);
  });
}

conectarAutocompletadoDireccion(
  domicilioDireccionInput,
  perfilSugerenciasDireccion,
  () => { coordsDomicilioActual = null; mapaDomicilio.ocultar(); },
  (coords) => {
    coordsDomicilioActual = coords;
    if (coords) mapaDomicilio.mostrar(coords.lat, coords.lng);
  },
);

// Domicilio principal editado desde los datos del perfil: si se elige una
// sugerencia de Google se guardan sus coordenadas; escrito a mano, no.
let coordsPerfilDomicilio = null;
conectarAutocompletadoDireccion(
  document.getElementById("perfil-domicilio"),
  document.getElementById("perfil-domicilio-sugerencias"),
  () => { coordsPerfilDomicilio = null; },
  (coords) => { coordsPerfilDomicilio = coords; },
);

const seccionCondicionesMayorista = document.getElementById("seccion-condiciones-mayorista");
const condicionesMayoristaFecha = document.getElementById("condiciones-mayorista-fecha");
const btnVerCondicionesMayorista = document.getElementById("btn-ver-condiciones-mayorista");
// Sufijo "Local": embebido en index.html, landing.js ya declara sus propias
// const con estos mismos nombres (ambos scripts corren en el scope global)
// — sin el sufijo, cargar los dos en la misma página tira
// "Identifier ... has already been declared" y perfil.js entero deja de
// ejecutarse. Solo se usan acá como fallback para /perfil.html standalone
// (ver los "typeof mostrarModalTerminosMayorista" más abajo).
const overlayTerminosMayoristaLocal = document.getElementById("rc-terminos-mayorista");
const contenidoTerminosMayoristaLocal = document.getElementById("rc-terminos-contenido");
const btnTerminosCerrarLocal = document.getElementById("btn-terminos-cerrar");
let fragmentoTerminosMayoristaCacheLocal = null;

function mostrarSeccionCondicionesMayorista(datos) {
  if (!seccionCondicionesMayorista) return;
  const esMayorista = datos.tipo_cliente === "mayorista";
  seccionCondicionesMayorista.classList.toggle("oculto", !esMayorista);
  if (esMayorista && condicionesMayoristaFecha) {
    condicionesMayoristaFecha.textContent = datos.condiciones_mayorista_aceptadas_en
      ? `Aceptadas el ${new Date(datos.condiciones_mayorista_aceptadas_en).toLocaleString("es-AR")}`
      : "";
  }
  // El modo Fallout no está disponible para cuentas mayoristas — si llegó
  // acá con ?modo=fallout en la URL (ej. un link viejo guardado), se lo
  // saca a Classic apenas se sabe que la cuenta es mayorista. Embebido en
  // index.html usamos la función de landing.js (mantiene sincronizado su
  // propio estado interno de modo); en /perfil.html standalone no existe,
  // así que se cae al atributo directo de siempre.
  if (esMayorista && document.documentElement.getAttribute("data-modo") === "fallout") {
    if (typeof aplicarModoVisual === "function") {
      aplicarModoVisual("classic");
    } else {
      document.documentElement.setAttribute("data-modo", "classic");
    }
  }
}

// Sello de goma "LEALTAD": borde dentado, anillo, cinta cruzada y tinta gastada.
// Se define una sola vez por página y cada sello lo reusa con <use>.
function asegurarDibujoSello() {
  if (document.getElementById("ttra-sello-lealtad")) return;
  const defs = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  defs.setAttribute("aria-hidden", "true");
  defs.setAttribute("class", "fidelidad-defs");
  defs.innerHTML =
    '<defs><filter id="ttra-sello-tinta" x="0" y="0" width="100%" height="100%">' +
    '<feTurbulence type="fractalNoise" baseFrequency=".75" numOctaves="2" seed="11" result="ruido"/>' +
    '<feColorMatrix in="ruido" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  -22 0 0 0 15.6" result="gastado"/>' +
    '<feComposite in="SourceGraphic" in2="gastado" operator="in"/></filter>' +
    '<symbol id="ttra-sello-lealtad" viewBox="0 0 100 100"><g filter="url(#ttra-sello-tinta)">' +
    '<path fill-rule="evenodd" style="fill:var(--sello-tinta)" d="M50 2L55.12 7.81L61.49 3.39L65.07 10.26L72.31 7.5L74.14 15.02L81.83 14.07L81.81 21.82L89.5 22.73L87.63 30.25L94.88 32.98L91.27 39.83L97.65 44.21L92.5 50L97.65 55.79L91.27 60.17L94.88 67.02L87.63 69.75L89.5 77.27L81.81 78.18L81.83 85.93L74.14 84.98L72.31 92.5L65.07 89.74L61.49 96.61L55.12 92.19L50 98L44.88 92.19L38.51 96.61L34.93 89.74L27.69 92.5L25.86 84.98L18.17 85.93L18.19 78.18L10.5 77.27L12.37 69.75L5.12 67.02L8.73 60.17L2.35 55.79L7.5 50L2.35 44.21L8.73 39.83L5.12 32.98L12.37 30.25L10.5 22.73L18.19 21.82L18.17 14.07L25.86 15.02L27.69 7.5L34.93 10.26L38.51 3.39L44.88 7.81ZM13 50a37 37 0 1 0 74 0a37 37 0 1 0-74 0ZM19 50a31 31 0 1 0 62 0a31 31 0 1 0-62 0Z"/>' +
    '<g style="fill:var(--sello-papel)"><path d="M50 26l1.8 3.7 4 .6-2.9 2.8.7 4-3.6-1.9-3.6 1.9.7-4-2.9-2.8 4-.6z"/>' +
    '<path d="M50 64l1.8 3.7 4 .6-2.9 2.8.7 4-3.6-1.9-3.6 1.9.7-4-2.9-2.8 4-.6z"/></g>' +
    '<g transform="rotate(-14 50 50)"><path style="fill:var(--sello-cinta)" d="M-2 40.5H102L96 50L102 59.5H-2L4 50Z"/>' +
    '<text x="50" y="54.6" text-anchor="middle" style="fill:var(--sello-papel);font:900 13px/1 Arial Black,Arial,sans-serif;letter-spacing:.5px">LEALTAD</text></g>' +
    '</g></symbol></defs>';
  document.body.append(defs);
}

function mostrarTarjetaFidelidad(datos) {
  const contenedorSellos = document.getElementById("fidelidad-sellos");
  const mensajePremio = document.getElementById("fidelidad-premio");
  const seccion = document.getElementById("seccion-fidelidad");
  if (!contenedorSellos || !mensajePremio || !seccion) return;
  // Los mayoristas no participan: su precio ya es especial.
  seccion.classList.toggle("oculto", datos.tipo_cliente === "mayorista");
  contenedorSellos.replaceChildren();
  // Con un premio pendiente el contador queda congelado en 5.
  const conPremio = Boolean(datos.fidelidad_ultimo_codigo);
  mensajePremio.textContent = datos.descuento_reservado_usd > 0
    ? "Tu descuento ya está aplicado en tu pedido en curso: se descuenta cuando se concreta la venta."
    : "¡Ganaste US$20 de descuento por tus 5 compras! Se aplica solo en tu 6ta compra.";
  mensajePremio.classList.toggle("oculto", !conPremio);
  const sellos = conPremio ? 5 : Math.min(Number(datos.sellos_fidelidad) || 0, 5);
  asegurarDibujoSello();
  const fila = document.createElement("div");
  fila.className = "fidelidad-fila";
  fila.setAttribute("role", "img");
  fila.setAttribute("aria-label", `${sellos} de 5 sellos`);
  for (let i = 0; i < 5; i++) {
    const sello = document.createElement("span");
    // El último sello ganado entra "estampado" y queda girando.
    sello.className = "fidelidad-sello" + (i < sellos ? " lleno" : "") + (i === sellos - 1 ? " nuevo" : "");
    if (i < sellos) {
      // Dos caras iguales: al girar en 3D se lee derecho de ambos lados.
      sello.innerHTML =
        '<span class="fidelidad-sello-giro"><svg class="cara" viewBox="0 0 100 100"><use href="#ttra-sello-lealtad"/></svg>' +
        '<svg class="dorso" viewBox="0 0 100 100"><use href="#ttra-sello-lealtad"/></svg></span>';
    } else {
      sello.textContent = String(i + 1);
    }
    fila.append(sello);
  }
  contenedorSellos.append(fila);
  const ayuda = document.createElement("p");
  ayuda.className = "fidelidad-ayuda";
  ayuda.textContent = conPremio
    ? "Completaste tus 5 compras."
    : `${sellos} de 5 compras. A la quinta te regalo US$20 de descuento.`;
  contenedorSellos.append(ayuda);
}

function formatoUsd(monto) {
  const n = Number(monto) || 0;
  if (n > 0 && n < 0.01) return "menos de US$0,01";
  return `US$${n.toLocaleString("es-AR", { minimumFractionDigits: n % 1 ? 2 : 0, maximumFractionDigits: 2 })}`;
}

function nodoArbolRed(nodo) {
  const item = document.createElement("li");
  const nombre = document.createElement("span");
  nombre.className = "red-nodo";
  const texto = document.createElement("span");
  texto.className = "red-nodo-nombre";
  texto.textContent = nodo.nombre;
  nombre.append(texto);
  // Los que compraron (y le generaron una ganancia) van en verde con el monto;
  // los que solo se crearon la cuenta quedan sin resaltar.
  if (nodo.compro) {
    nombre.classList.add("red-nodo-compro");
    const ganancia = document.createElement("span");
    ganancia.className = "red-nodo-ganancia";
    ganancia.textContent = `¡Compró! Ganaste ${formatoUsd(nodo.ganado_usd)}`;
    texto.append(ganancia);
  }
  item.append(nombre);
  // Cuántos se sumaron debajo de esta persona (sus invitados y los de ellos).
  if (nodo.debajo > 0) {
    const debajo = document.createElement("span");
    debajo.className = "red-nodo-debajo";
    debajo.textContent = `+${nodo.debajo}`;
    debajo.title = `${nodo.debajo} ${nodo.debajo === 1 ? "persona se sumó" : "personas se sumaron"} a través de ${nodo.nombre}`;
    nombre.append(debajo);
  }
  if (nodo.hijos?.length) {
    const lista = document.createElement("ul");
    nodo.hijos.forEach((hijo) => lista.append(nodoArbolRed(hijo)));
    item.append(lista);
  }
  return item;
}

// Cartel sorpresa: lo que la red generó desde la última vez que el cliente
// abrió su perfil en este navegador.
function cartelSorpresaRed(r) {
  const clave = "ttra_red_visto_hasta";
  let vistoHasta = "";
  try { vistoHasta = localStorage.getItem(clave) || ""; } catch {}
  const nuevas = (r.ultimas_ganancias || []).filter((g) => g.fecha && g.fecha > vistoHasta);
  const masReciente = (r.ultimas_ganancias || [])[0]?.fecha;
  if (masReciente) {
    try { localStorage.setItem(clave, masReciente); } catch {}
  }
  if (!vistoHasta || !nuevas.length) return null;
  const total = nuevas.reduce((suma, g) => suma + Number(g.monto_usd || 0), 0);
  const cartel = document.createElement("p");
  cartel.className = "red-sorpresa";
  cartel.textContent = `🎉 ¡Tu red te hizo ganar ${formatoUsd(total)} desde tu última visita!`;
  return cartel;
}

// "Ver mi red": todos los que se sumaron debajo del cliente, a cualquier
// profundidad, compren o no. Se arma con lo último que trajo el perfil.
let redCompletaActual = null;

function arbolRedHtml(red) {
  const lista = document.createElement("ul");
  lista.className = "red-arbol";
  const raiz = document.createElement("li");
  const vos = document.createElement("span");
  vos.className = "red-nodo red-nodo-vos";
  vos.textContent = "Vos";
  const hijos = document.createElement("ul");
  red.arbol.forEach((nodo) => hijos.append(nodoArbolRed(nodo)));
  raiz.append(vos, hijos);
  lista.append(raiz);
  // Si la red crece mucho, el árbol scrollea dentro de su caja (arriba/abajo
  // y de costado) en lugar de estirar el panel.
  const caja = document.createElement("div");
  caja.className = "red-arbol-caja";
  caja.append(lista);
  return caja;
}

function abrirMiRed() {
  const red = redCompletaActual || { arbol: [], personas: 0, niveles: 0 };
  if (!red.personas) {
    window.TTRAAviso({
      etiqueta: "Tu semilla",
      titulo: "Todavía no se sumó nadie",
      texto: "Compartí tu link: cada persona que se cree la cuenta con él aparece acá, y también las que invite después.",
      boton: "Cerrar",
    });
    return;
  }
  const contenido = document.createElement("div");
  contenido.className = "red-panel";
  const cifras = document.createElement("div");
  cifras.className = "red-cifras";
  [
    [red.personas, red.personas === 1 ? "persona en tu red" : "personas en tu red"],
    [red.niveles, red.niveles === 1 ? "nivel de profundidad" : "niveles de profundidad"],
  ].forEach(([numero, etiqueta]) => {
    const cifra = document.createElement("p");
    const n = document.createElement("strong");
    n.textContent = String(numero);
    const e = document.createElement("span");
    e.textContent = etiqueta;
    cifra.append(n, e);
    cifras.append(cifra);
  });
  contenido.append(cifras, arbolRedHtml(red));
  window.TTRAAviso({ etiqueta: "Tu semilla", titulo: "Mi red", contenido, clase: "ttra-red-dialogo", boton: "Cerrar" });
}
document.getElementById("btn-ver-mi-red")?.addEventListener("click", abrirMiRed);

function mostrarReferidos(datos) {
  const seccion = document.getElementById("seccion-referidos");
  const seccionAmigos = document.getElementById("seccion-amigos-referidos");
  const estado = document.getElementById("referidos-estado");
  if (!seccion || !seccionAmigos || !estado) return;
  // Igual que fidelidad: el cupón no aplica sobre precio mayorista.
  const esMayorista = datos.tipo_cliente === "mayorista";
  seccion.classList.toggle("oculto", esMayorista);
  estado.replaceChildren();
  const r = datos.referidos;
  redCompletaActual = r?.red || null;
  const arbol = r?.arbol || [];
  // La sección aparece recién cuando alguien de la red compró.
  seccionAmigos.classList.toggle("oculto", esMayorista || !arbol.length);
  if (!arbol.length) return;

  const sorpresa = cartelSorpresaRed(r);
  if (sorpresa) estado.append(sorpresa);

  const resumen = document.createElement("div");
  resumen.className = "red-resumen";
  const filas = [
    ["Compraron en tu red", String(r.personas_en_red)],
    ["Ganaste en total", formatoUsd(r.ganado_total_usd)],
    ["Bolsa de tu red", formatoUsd(r.red_saldo_usd)],
  ];
  for (const [etiqueta, valor] of filas) {
    const fila = document.createElement("div");
    const e = document.createElement("span");
    e.textContent = etiqueta;
    const v = document.createElement("strong");
    v.textContent = valor;
    fila.append(e, v);
    resumen.append(fila);
  }
  estado.append(resumen);
  const ayudaTope = document.createElement("p");
  ayudaTope.className = "referidos-ayuda";
  ayudaTope.textContent = `De la bolsa de tu red se aplican hasta ${formatoUsd(r.red_tope_por_compra_usd)} por compra; el resto queda guardado para las siguientes.`;
  estado.append(ayudaTope);

  if (datos.descuento_reservado_usd > 0) {
    const reservado = document.createElement("p");
    reservado.className = "referidos-ayuda";
    reservado.textContent = `${formatoUsd(datos.descuento_reservado_usd)} ya aplicados en tu pedido en curso: se descuentan cuando se concreta la venta.`;
    estado.append(reservado);
  } else if (r.saldo_usd > 0) {
    const total = document.createElement("p");
    total.className = "referidos-total";
    const d = r.desglose || {};
    const partes = [
      d.fidelidad > 0 ? `sellos ${formatoUsd(d.fidelidad)}` : "",
      d.directos > 0 ? `amigos ${formatoUsd(d.directos)}` : "",
      d.red > 0 ? `red ${formatoUsd(d.red)}` : "",
    ].filter(Boolean);
    total.textContent = `Total en tu próxima compra: ${formatoUsd(r.saldo_usd)}${partes.length > 1 ? ` (${partes.join(" + ")})` : ""}. Se aplica solo.`;
    estado.append(total);
  }
}

async function compartirLinkReferido() {
  const boton = document.getElementById("btn-compartir-referido");
  const linkEl = document.getElementById("referidos-link");
  if (!boton || !linkEl) return;
  boton.disabled = true;
  try {
    const r = await fetch("/api/me/referido", { method: "POST" });
    const datos = await r.json().catch(() => ({}));
    if (!r.ok || !datos.url) throw new Error(datos.error || "No se pudo generar tu link.");
    const texto = "Te invito a The Tech Room Arg: creá tu cuenta con mi link.";
    // En el celular se abre el menú de compartir (WhatsApp, etc.). En la
    // computadora ese menú no deja nada en el portapapeles, así que se copia
    // el link y además se muestra, por si el navegador no deja copiar.
    const esCelular = window.matchMedia("(pointer: coarse)").matches;
    if (esCelular && typeof navigator.share === "function") {
      try {
        await navigator.share({ title: "The Tech Room Arg", text: texto, url: datos.url });
        return;
      } catch (e) {
        if (e?.name === "AbortError") return;
      }
    }
    let copiado = false;
    try {
      await navigator.clipboard.writeText(datos.url);
      copiado = true;
    } catch {}
    linkEl.textContent = copiado ? `Link copiado: ${datos.url}` : `Copiá tu link: ${datos.url}`;
    linkEl.classList.remove("oculto");
  } catch (e) {
    linkEl.textContent = e.message || "No se pudo generar tu link.";
    linkEl.classList.remove("oculto");
  } finally {
    boton.disabled = false;
  }
}

document.getElementById("btn-compartir-referido")?.addEventListener("click", compartirLinkReferido);

async function cargarFragmentoTerminosMayorista() {
  if (fragmentoTerminosMayoristaCacheLocal) return fragmentoTerminosMayoristaCacheLocal;
  try {
    const r = await fetch("/condiciones-mayorista.html");
    fragmentoTerminosMayoristaCacheLocal = r.ok
      ? await r.text()
      : "<p>No pude cargar las condiciones mayoristas. Probá de nuevo.</p>";
  } catch {
    fragmentoTerminosMayoristaCacheLocal = "<p>No pude cargar las condiciones mayoristas. Probá de nuevo.</p>";
  }
  return fragmentoTerminosMayoristaCacheLocal;
}

if (btnVerCondicionesMayorista) {
  btnVerCondicionesMayorista.addEventListener("click", async () => {
    // Embebido en index.html: reusa el modal + overlay que landing.js ya
    // maneja (mismos #rc-terminos-mayorista/#rc-terminos-contenido) —
    // así respeta el toggle Acepto/Cerrar en vez de dejar el overlay con
    // el estado de una apertura previa. Standalone en /perfil.html cae a
    // la copia local de acá abajo (esos elementos no existen en esa página).
    if (typeof mostrarModalTerminosMayorista === "function") {
      mostrarModalTerminosMayorista("ver");
      return;
    }
    if (!overlayTerminosMayoristaLocal || !contenidoTerminosMayoristaLocal) return;
    contenidoTerminosMayoristaLocal.innerHTML = await cargarFragmentoTerminosMayorista();
    contenidoTerminosMayoristaLocal.scrollTop = 0;
    overlayTerminosMayoristaLocal.classList.add("visible");
  });
}

// Embebido en index.html, landing.js ya le pone su propio listener a este
// mismo botón (ver btnTerminosCerrar ahí) — evita duplicarlo acá.
if (btnTerminosCerrarLocal && typeof mostrarModalTerminosMayorista !== "function") {
  btnTerminosCerrarLocal.addEventListener("click", () => {
    if (overlayTerminosMayoristaLocal) overlayTerminosMayoristaLocal.classList.remove("visible");
  });
}

async function cargarPerfil() {
  const errorEl = document.getElementById("perfil-error");
  try {
    const r = await fetch("/api/me");
    if (r.status === 401) {
      pedirLoginDesdePanel("perfil");
      return;
    }
    const datos = await r.json();
    if (!r.ok) {
      errorEl.textContent = datos.error || "No pude cargar tu perfil";
      return;
    }
    document.getElementById("perfil-nombre").value = datos.nombre || "";
    document.getElementById("perfil-apellido").value = datos.apellido || "";
    document.getElementById("perfil-email").value = datos.email || "";
    document.getElementById("perfil-celular").value = datos.celular || "";
    modoEdicionPerfil(false);
    mostrarSeccionCondicionesMayorista(datos);
    mostrarTarjetaFidelidad(datos);
    mostrarReferidos(datos);
  } catch {
    errorEl.textContent = "No pude conectar, probá de nuevo en un momento";
  }
}

const btnAbrirFormDomicilio = document.getElementById("btn-abrir-form-domicilio");
function abrirFormDomicilio() {
  document.getElementById("form-domicilio").classList.remove("oculto");
  btnAbrirFormDomicilio.classList.add("oculto");
}

function cancelarEdicionDomicilio() {
  document.getElementById("form-domicilio").classList.add("oculto");
  btnAbrirFormDomicilio.classList.remove("oculto");
  domicilioEnEdicionId = null;
  domicilioAliasInput.value = "";
  domicilioDireccionInput.value = "";
  domicilioPisoInput.value = "";
  domicilioDeptoInput.value = "";
  coordsDomicilioActual = null;
  mapaDomicilio.ocultar();
  btnGuardarDomicilio.textContent = "Guardar domicilio";
}

// Botón-fila de un domicilio (nombre arriba, dirección abajo). Lo comparte
// el selector del carrito (landing.js) vía window.opcionDomicilioHtml.
function opcionDomicilioHtml(domicilio, elegido) {
  const opcion = document.createElement("button");
  opcion.type = "button";
  opcion.className = "domicilio-opcion";
  opcion.setAttribute("role", "radio");
  opcion.setAttribute("aria-checked", String(Boolean(elegido)));
  const marca = document.createElement("span");
  marca.className = "domicilio-opcion-marca";
  marca.setAttribute("aria-hidden", "true");
  const texto = document.createElement("span");
  texto.className = "domicilio-opcion-texto";
  const nombre = document.createElement("span");
  nombre.className = "domicilio-opcion-nombre";
  nombre.textContent = domicilio.alias;
  const direccion = document.createElement("span");
  direccion.className = "domicilio-opcion-direccion";
  const pisoDepto = textoPisoDepto(domicilio);
  direccion.textContent = `${domicilio.direccion}${pisoDepto ? ` · ${pisoDepto}` : ""}`;
  texto.append(nombre, direccion);
  opcion.append(marca, texto);
  if (elegido) {
    const etiqueta = document.createElement("span");
    etiqueta.className = "domicilio-opcion-etiqueta";
    etiqueta.textContent = "Entrega";
    opcion.append(etiqueta);
  }
  return opcion;
}
window.opcionDomicilioHtml = opcionDomicilioHtml;

async function marcarDomicilioPrincipal(domicilio) {
  const r = await fetch(`/api/domicilios/${domicilio.id}/predeterminado`, { method: "POST" }).catch(() => null);
  return Boolean(r?.ok);
}

// Elegir otro domicilio pide confirmación en el panel flotante; cancelar lo deja como estaba.
async function proponerDomicilioPrincipal(domicilio) {
  const acepta = await window.TTRAConfirmar({
    titulo: "¿Establecer como domicilio de entrega?",
    texto: `${domicilio.alias} — ${domicilio.direccion}`,
    aceptar: "Establecer",
    cancelar: "Cancelar",
  });
  if (acepta && await marcarDomicilioPrincipal(domicilio)) {
    if (typeof usarDomicilioEnCarrito === "function") usarDomicilioEnCarrito(domicilio);
  }
  cargarDomicilios();
}

function itemDomicilioHtml(domicilio) {
  const item = document.createElement("div");
  item.className = "item-domicilio";
  const opcion = opcionDomicilioHtml(domicilio, domicilio.predeterminado);
  if (!domicilio.predeterminado) opcion.addEventListener("click", () => proponerDomicilioPrincipal(domicilio));
  item.append(opcion);

  const acciones = document.createElement("div");
  acciones.className = "item-domicilio-acciones";

  const btnEditar = document.createElement("button");
  btnEditar.type = "button";
  btnEditar.textContent = "Editar";
  btnEditar.addEventListener("click", () => {
    domicilioEnEdicionId = domicilio.id;
    domicilioAliasInput.value = domicilio.alias;
    domicilioDireccionInput.value = domicilio.direccion;
    domicilioPisoInput.value = domicilio.piso || "";
    domicilioDeptoInput.value = domicilio.depto || "";
    coordsDomicilioActual = (domicilio.lat != null && domicilio.lng != null) ? { lat: domicilio.lat, lng: domicilio.lng } : null;
    if (coordsDomicilioActual) {
      cargarApiPlacesPerfil().then(() => mapaDomicilio.mostrar(coordsDomicilioActual.lat, coordsDomicilioActual.lng)).catch(() => {});
    } else {
      mapaDomicilio.ocultar();
    }
    btnGuardarDomicilio.textContent = "Guardar cambios";
    abrirFormDomicilio();
    domicilioAliasInput.focus();
  });
  acciones.append(btnEditar);

  const btnEliminar = document.createElement("button");
  btnEliminar.type = "button";
  btnEliminar.textContent = "Eliminar";
  btnEliminar.addEventListener("click", async () => {
    const acepta = await window.TTRAConfirmar({
      titulo: "¿Eliminar este domicilio?",
      texto: `${domicilio.alias} — ${domicilio.direccion}`,
      aceptar: "Eliminar",
    });
    if (!acepta) return;
    await fetch(`/api/domicilios/${domicilio.id}`, { method: "DELETE" });
    if (domicilioEnEdicionId === domicilio.id) cancelarEdicionDomicilio();
    cargarDomicilios();
  });
  acciones.append(btnEliminar);

  item.append(acciones);
  return item;
}

async function cargarDomicilios() {
  try {
    const r = await fetch("/api/domicilios");
    const domicilios = await r.json();
    if (!r.ok) return;
    listaDomicilios.replaceChildren();
    const principal = domicilios.find((d) => d.predeterminado) || domicilios[0];
    domicilioPrincipalActual = principal || null;
    const campoDomicilio = document.getElementById("perfil-domicilio");
    if (campoDomicilio && campoDomicilio.disabled) campoDomicilio.value = textoDomicilioPrincipal(true);
    btnAbrirFormDomicilio.disabled = domicilios.length >= 5;
    btnAbrirFormDomicilio.title = domicilios.length >= 5 ? "Llegaste al máximo de 5 domicilios" : "";
    listaDomicilios.setAttribute("role", "radiogroup");
    listaDomicilios.setAttribute("aria-label", "Domicilio de entrega");
    if (!domicilios.length) {
      const vacio = document.createElement("p");
      vacio.className = "carrito-nota";
      vacio.textContent = "Todavía no tenés domicilios guardados.";
      listaDomicilios.append(vacio);
      return;
    }
    // El principal va siempre primero; el resto mantiene su orden.
    [...domicilios]
      .sort((a, b) => Number(Boolean(b.predeterminado)) - Number(Boolean(a.predeterminado)))
      .forEach((domicilio) => listaDomicilios.append(itemDomicilioHtml(domicilio)));
    btnGuardarDomicilio.disabled = domicilios.length >= 5 && !domicilioEnEdicionId;
  } catch {
    // Si falla, la lista simplemente queda vacía — el resto del perfil sigue usable.
  }
}

if (panelPerfilEmbebido) {
  window.abrirPanelPerfil = function abrirPanelPerfil() {
    // Cierra el carrito si estaba abierto: los dos comparten la franja
    // "flotante sobre la home blureada" y no tiene sentido ver ambos
    // superpuestos a la vez.
    if (typeof cerrarCarrito === "function") cerrarCarrito();
    if (typeof cerrarPanelPedidos === "function") cerrarPanelPedidos();
    // Mismo cálculo que el carrito (separación real del footer, no un
    // valor fijo) — sincronizarLimiteCarrito ya deja el resultado en la
    // variable CSS compartida --rc-carrito-separacion-footer.
    if (typeof sincronizarLimiteCarrito === "function") sincronizarLimiteCarrito();
    panelPerfilEmbebido.classList.remove("oculto");
    if (overlayPerfilEmbebido) overlayPerfilEmbebido.classList.remove("oculto");
    cargarPerfil();
    cargarDomicilios();
  };
}

// Los datos del perfil arrancan bloqueados: "Editar" habilita nombre,
// apellido, teléfono y la dirección del domicilio principal, y recién ahí se
// puede tocar "Guardar cambios". El mail queda siempre en gris. El campo de
// domicilio muestra el que esté marcado como principal en la lista.
const CAMPOS_PERFIL_EDITABLES = ["perfil-nombre", "perfil-apellido", "perfil-celular", "perfil-domicilio"];
function textoDomicilioPrincipal(conPisoDepto) {
  const d = domicilioPrincipalActual;
  if (!d) return "";
  const pisoDepto = conPisoDepto ? textoPisoDepto(d) : "";
  return `${d.direccion}${pisoDepto ? ` (${pisoDepto})` : ""}`;
}
const btnEditarPerfil = document.getElementById("btn-editar-perfil");
const btnGuardarPerfil = document.getElementById("btn-guardar-perfil");
function modoEdicionPerfil(editando) {
  CAMPOS_PERFIL_EDITABLES.forEach((id) => { document.getElementById(id).disabled = !editando; });
  btnGuardarPerfil.disabled = !editando;
  btnEditarPerfil.disabled = editando;
  // Editando se ve solo la dirección (piso y depto se cambian desde la lista).
  const campoDomicilio = document.getElementById("perfil-domicilio");
  campoDomicilio.value = textoDomicilioPrincipal(!editando);
  coordsPerfilDomicilio = null;
  ocultarSugerenciasPerfilDireccion(document.getElementById("perfil-domicilio-sugerencias"));
  if (editando) document.getElementById("perfil-nombre").focus();
}
btnEditarPerfil.addEventListener("click", () => modoEdicionPerfil(true));

const formPerfil = document.getElementById("form-perfil");
formPerfil.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("perfil-error");
  const okEl = document.getElementById("perfil-ok");
  errorEl.textContent = "";
  okEl.textContent = "";
  try {
    const r = await fetch("/api/me", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        nombre: document.getElementById("perfil-nombre").value,
        apellido: document.getElementById("perfil-apellido").value,
        celular: document.getElementById("perfil-celular").value,
      }),
    });
    const datos = await r.json();
    if (!r.ok) {
      errorEl.textContent = datos.error || datos.detail || "No pude guardar los cambios";
      return;
    }
    const direccionNueva = document.getElementById("perfil-domicilio").value.trim();
    const principal = domicilioPrincipalActual;
    if (direccionNueva && direccionNueva !== (principal?.direccion || "")) {
      // Dirección cambiada: el pin anterior ya no vale. Si vino de una
      // sugerencia de Google, se guardan sus coordenadas.
      const rDom = principal
        ? await fetch(`/api/domicilios/${principal.id}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              alias: principal.alias, direccion: direccionNueva,
              piso: principal.piso || null, depto: principal.depto || null,
              lat: coordsPerfilDomicilio?.lat ?? null, lng: coordsPerfilDomicilio?.lng ?? null,
            }),
          })
        : await fetch("/api/domicilios", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              alias: "Casa", direccion: direccionNueva,
              lat: coordsPerfilDomicilio?.lat ?? null, lng: coordsPerfilDomicilio?.lng ?? null,
            }),
          });
      const datosDom = await rDom.json().catch(() => ({}));
      if (!rDom.ok) {
        errorEl.textContent = datosDom.error || datosDom.detail || "Guardé tus datos, pero no pude actualizar el domicilio";
        return;
      }
    }
    okEl.textContent = "Datos guardados";
    modoEdicionPerfil(false);
    await cargarDomicilios();
  } catch {
    errorEl.textContent = "No pude conectar, probá de nuevo en un momento";
  }
});

const formDomicilio = document.getElementById("form-domicilio");
formDomicilio.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("domicilio-error");
  const okEl = document.getElementById("domicilio-ok");
  errorEl.textContent = "";
  okEl.textContent = "";
  const cuerpo = {
    alias: domicilioAliasInput.value, direccion: domicilioDireccionInput.value,
    piso: domicilioPisoInput.value, depto: domicilioDeptoInput.value,
    lat: coordsDomicilioActual?.lat ?? null, lng: coordsDomicilioActual?.lng ?? null,
  };
  try {
    const r = domicilioEnEdicionId
      ? await fetch(`/api/domicilios/${domicilioEnEdicionId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cuerpo),
        })
      : await fetch("/api/domicilios", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(cuerpo),
        });
    const datos = await r.json();
    if (!r.ok) {
      errorEl.textContent = datos.error || datos.detail || "No pude guardar el domicilio";
      return;
    }
    const eraNuevo = !domicilioEnEdicionId;
    okEl.textContent = "Domicilio guardado";
    cancelarEdicionDomicilio();
    await cargarDomicilios();
    // Recién agregado y no quedó solo de entrega (el primero ya lo es): se ofrece.
    if (eraNuevo && !datos.predeterminado) await proponerDomicilioPrincipal(datos);
  } catch {
    errorEl.textContent = "No pude conectar, probá de nuevo en un momento";
  }
});

btnAbrirFormDomicilio.addEventListener("click", () => {
  cancelarEdicionDomicilio();
  abrirFormDomicilio();
  domicilioAliasInput.focus();
});

btnCancelarEdicionDomicilio.addEventListener("click", () => {
  cancelarEdicionDomicilio();
  document.getElementById("domicilio-error").textContent = "";
  document.getElementById("domicilio-ok").textContent = "";
});

const formPassword = document.getElementById("form-password");
formPassword.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("password-error");
  const okEl = document.getElementById("password-ok");
  errorEl.textContent = "";
  okEl.textContent = "";
  const nueva = document.getElementById("password-nueva").value;
  const repetir = document.getElementById("password-nueva-repetir").value;
  if (nueva !== repetir) {
    errorEl.textContent = "Las contraseñas nuevas no coinciden";
    return;
  }
  try {
    const r = await fetch("/api/me/password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        password_actual: document.getElementById("password-actual").value,
        password_nueva: nueva,
      }),
    });
    const datos = await r.json();
    if (!r.ok) {
      errorEl.textContent = datos.error || datos.detail || "No pude cambiar la contraseña";
      return;
    }
    okEl.textContent = "Contraseña actualizada";
    formPassword.reset();
  } catch {
    errorEl.textContent = "No pude conectar, probá de nuevo en un momento";
  }
});

// Celular: solo números (también al pegar "+54 351-123 4567").
function soloNumerosEnCelular(input) {
  if (!input) return;
  input.addEventListener("input", () => {
    const limpio = input.value.replace(/\D+/g, "");
    if (limpio !== input.value) input.value = limpio;
  });
}
soloNumerosEnCelular(document.getElementById("perfil-celular"));
