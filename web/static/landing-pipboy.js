// Parte 3 de la landing: el Pip-Boy — telemetría, barras de señal,
// tarjetas de lugar y el carrousel de recomendados del modo Classic.

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

// --- Línea de telemetría del Pip-Boy (pie de cada tarjeta de lugar) ---
// Idea tomada del "AI HUD summary" de God's Eye View (MIT) — un renglón que
// reporta el estado del sistema — pero sin IA: rota entre datos reales del
// dispositivo (hora local, batería si el navegador la expone) y un status
// fijo, dando la sensación de telemetría en vivo sin costo ni backend.
let bateriaPipboy = null;
if (typeof navigator !== "undefined" && navigator.getBattery) {
  navigator.getBattery().then((b) => {
    bateriaPipboy = b;
  }).catch(() => {});
}

function textoStatusPipboy() {
  const opciones = [
    "TRANSMISIÓN ESTABLE // SEÑAL 98% // ARCHIVO TTRA-01",
    `HORA LOCAL: ${new Date().toLocaleTimeString("es-AR", { hour12: false })} // SISTEMA: NOMINAL`,
  ];
  if (bateriaPipboy) {
    const nivel = Math.round(bateriaPipboy.level * 100);
    const cargando = bateriaPipboy.charging ? " // CARGANDO" : "";
    opciones.push(`BATERÍA DEL TERMINAL: ${nivel}%${cargando} // SISTEMA: NOMINAL`);
  }
  return opciones[Math.floor(Math.random() * opciones.length)];
}

// Refresca el texto de cada tarjeta visible sin recrear el DOM (no interfiere
// con el carrousel de fotos, que sí reemplaza el nodo cada 20s).
function actualizarStatusPipboyVisible() {
  document.querySelectorAll(".pipboy-frase-texto").forEach((el) => {
    el.textContent = textoStatusPipboy();
  });
}
setInterval(actualizarStatusPipboyVisible, 4000);

// --- Barras de señal del HUD fijo (esquina inferior izquierda) ---
// Varían al azar cada tanto, simulando interferencia leve de la señal.
// Puramente decorativo, no representa nada medido.
const BARRAS_SEÑAL = ["▮▮▮▮▮", "▮▮▮▮▯", "▮▮▮▯▯", "▮▮▮▮▯", "▮▮▮▮▮", "▮▮▮▮▯"];
function actualizarBarrasSeñal() {
  const el = document.getElementById("rc-hud-barras");
  if (!el) return;
  el.textContent = BARRAS_SEÑAL[Math.floor(Math.random() * BARRAS_SEÑAL.length)];
}
setInterval(actualizarBarrasSeñal, 2600);

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
          <span class="pipboy-frase"><span class="pipboy-frase-texto">${textoStatusPipboy()}</span><span class="rc-cursor">_</span></span>
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
        await agregarAlCarritoProtegido(producto, btnAgregar.dataset.color || null, card);
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
