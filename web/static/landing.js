// Parte 4 (y última) de la landing: modo visual Fallout/Classic, música,
// menú de perfil, pantallas, carrito, ubicación, clima y noticiero.
// Las partes 1 a 3 se cargan antes (ver index.html) y comparten scope global.
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

// Modo Fallout deshabilitado: el botón #btn-logo-fallout se comentó en
// index.html, así que esto ya no encuentra nada — se deja comentado en vez
// de borrado para restaurarlo fácil más adelante.
// const btnLogoFallout = document.getElementById("btn-logo-fallout");
// if (btnLogoFallout) {
//   btnLogoFallout.addEventListener("click", entrarAModoFallout);
// }
const btnLogoFallout = null;
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
      : "<p>No pude cargar las condiciones mayoristas. Recargá la página.</p>";
  } catch {
    fragmentoTerminosMayoristaCache = "<p>No pude cargar las condiciones mayoristas. Recargá la página.</p>";
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
      alert("No pude guardar tu aceptación. Probá de nuevo.");
      btnTerminosAceptar.disabled = false;
      btnTerminosAceptar.textContent = "Acepto";
    }
  });
}

function verificarCondicionesMayoristaPendientes(sesion) {
  if (!sesion || sesion.tipo_cliente !== "mayorista" || sesion.condiciones_mayorista_aceptadas_en) return;
  mostrarModalTerminosMayorista("aceptar");
}

// --- El modo Fallout es un "easter egg" visual, no algo que tenga sentido
// para una cuenta mayorista comprando al por mayor — se le desactiva el
// botón de entrada y, si ya estaba adentro (por ejemplo por un link viejo
// con ?modo=fallout, o porque un admin le dio mayorista mientras estaba en
// Fallout), se lo saca a Classic apenas se conoce el tipo de cuenta. ---
function restringirFalloutSegunSesion(sesion) {
  const esMayorista = Boolean(sesion && sesion.tipo_cliente === "mayorista");
  if (btnLogoFallout) {
    btnLogoFallout.disabled = esMayorista;
    btnLogoFallout.title = esMayorista ? "No disponible para cuentas mayoristas" : "";
  }
  if (esMayorista && modoVisual === "fallout") {
    aplicarModoVisual("classic");
  }
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
const overlayPerfil = document.getElementById("overlay-perfil");
const linkIrAPerfil = document.getElementById("link-ir-a-perfil");

function cerrarMenuPerfil() {
  if (!dropdownPerfil) return;
  dropdownPerfil.classList.add("oculto");
  if (btnPerfilToggle) btnPerfilToggle.setAttribute("aria-expanded", "false");
  // El fondo blureado (overlay-perfil) es un agregado solo de Classic (ver
  // classic.css) — sin CSS propia en Fallout, así que de todos modos no se
  // ve ahí, pero igual la ocultamos siempre para no dejarla "abierta" si el
  // usuario cambia de modo con el menú desplegado.
  if (overlayPerfil) overlayPerfil.classList.add("oculto");
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
      // Solo Classic pide el fondo blureado/sin interacción (pedido
      // explícito: no tocar el comportamiento de Fallout).
      if (overlayPerfil && document.documentElement.getAttribute("data-modo") === "classic") {
        overlayPerfil.classList.remove("oculto");
      }
    }
  });
  document.addEventListener("click", (e) => {
    if (menuPerfil && !menuPerfil.contains(e.target)) cerrarMenuPerfil();
  });
  if (overlayPerfil) overlayPerfil.addEventListener("click", cerrarMenuPerfil);
}

if (linkIrAPerfil) {
  linkIrAPerfil.addEventListener("click", (e) => {
    e.preventDefault();
    // Classic + con sesión: abre el panel embebido (ver perfil.js) en vez
    // de navegar a /perfil — así queda la home blureada detrás, igual que
    // el carrito. Fallout sigue navegando a la página completa de siempre
    // (pedido explícito: no tocar ese modo) y un invitado sigue yendo a
    // login, en los dos casos no hay panel que abrir.
    if (modoVisual !== "fallout" && estadoSesionCliente && typeof window.abrirPanelPerfil === "function") {
      cerrarMenuPerfil();
      window.abrirPanelPerfil();
      return;
    }
    const destinoPerfil = modoVisual === "fallout" ? "/perfil?modo=fallout" : "/perfil";
    const paramsLogin = new URLSearchParams({ volver: `${location.pathname}${location.search}` });
    if (modoVisual === "fallout") paramsLogin.set("modo", "fallout");
    const destinoLogin = `/login.html?${paramsLogin.toString()}`;
    window.location.href = estadoSesionCliente ? destinoPerfil : destinoLogin;
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
sincronizarMenuPerfilSegunSesion(true).then((sesion) => {
  verificarCondicionesMayoristaPendientes(sesion);
  restringirFalloutSegunSesion(sesion);
});

// --- Resincronizar sesión/precio al volver a una pestaña ya abierta:
// /api/me y /api/catalogo solo se piden una vez al cargar la página, así
// que si en el medio alguien cierra sesión en otra pestaña, o un admin le
// saca/da mayorista a la cuenta, el cartel "Cuenta mayorista" y los
// precios quedan con el estado viejo hasta que se refresca. Se dispara al
// volver a poner el foco en la pestaña (visibilitychange) y al restaurarse
// desde el bfcache del navegador (pageshow con persisted=true, típico al
// volver con el botón "atrás"). Solo recarga el catálogo completo (más
// pesado, reordena/repinta todo) si el modo de precio realmente cambió —
// evita repintar en cada cambio de pestaña sin necesidad. ---
async function resincronizarSesionAlVolver() {
  const sesion = await obtenerEstadoSesionCliente(true);
  const tipoVigente = sesion && sesion.tipo_cliente === "mayorista" ? "mayorista" : "minorista";
  if (tipoVigente !== modoPrecioActual) {
    await cargarCatalogo();
  }
  await sincronizarMenuPerfilSegunSesion(true);
  verificarCondicionesMayoristaPendientes(sesion);
  restringirFalloutSegunSesion(sesion);
}
window.addEventListener("pageshow", (e) => {
  if (e.persisted) resincronizarSesionAlVolver();
});
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") resincronizarSesionAlVolver();
});

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

// La carita animada (":)") solo se ve en modo Fallout (oculta por CSS en
// Classic) — al pasarle el mouse por encima suena boy.mp3.
const caritaFallout = document.querySelector(".rc-cara-wrap");
const audioCaritaFallout = document.getElementById("audio-carita-fallout");
if (caritaFallout && audioCaritaFallout) {
  caritaFallout.addEventListener("mouseenter", () => {
    if (modoVisual !== "fallout") return;
    audioCaritaFallout.currentTime = 0;
    audioCaritaFallout.play().catch(() => {
      // Autoplay bloqueado hasta el primer gesto del usuario: no es crítico.
    });
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
  navegarDesdeCarrito(urlLoginParaCarrito());
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

// Un toque fuera de las tarjetas y de los controles vuelve al catálogo sin
// ningún producto resaltado. El mismo click que selecciona una card no la
// deselecciona al propagarse hasta document.
document.addEventListener("click", (e) => {
  if (e.target.closest?.(".card, button, a, input, select, textarea, [role='button']")) return;
  document.querySelectorAll("#productos .card.expandida").forEach((card) => {
    card.classList.remove("expandida");
  });
});

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
      <p class="precios">
        ${bloquePreciosHtml(p)}
      </p>
      ${colores}
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
      const producto = productos.find((p) => p.nombre === btnAgregar.dataset.nombre);
      if (producto) await agregarAlCarritoProtegido(producto, btnAgregar.dataset.color || null, card);
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
      '<p class="mensaje-vacio">No pude cargar el catálogo. Escribime por WhatsApp: ' +
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

function agregarAlCarrito(producto, color, desdeCard = false) {
  if (!catalogoListo) return false;
  try {
    TTRACarrito.agregar(producto, color);
  } catch {
    TTRACarrito.notificar("No pude guardar el producto en el carrito. Probá de nuevo.", true);
    return false;
  }
  renderCarrito();
  registrarInteraccion("add_to_cart", {
    producto_nombre: producto.nombre,
    categoria: productoSeccion(producto),
    marca: producto.marca || "Otras marcas",
    metadata: { color: color || "", cantidad: 1 },
  });
  if (!desdeCard) abrirCarrito();
  return true;
}

async function agregarAlCarritoProtegido(producto, color, card = null) {
  const button = card?.querySelector('.btn-agregar');
  if (button?.disabled) return;
  if (button) button.disabled = true;
  const animarCard = modoVisual === 'classic' && card;
  try {
    if (agregarAlCarrito(producto, color, Boolean(animarCard)) && animarCard) await TTRACarrito.animar(card);
  } finally {
    if (button) button.disabled = false;
  }
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
  navegarDesdeCarrito(urlLoginParaCarrito());
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
  // Cierra el panel de perfil si estaba abierto: los dos comparten la
  // franja "flotante sobre la home blureada" y no tiene sentido ver ambos
  // superpuestos a la vez.
  if (typeof cerrarPanelPerfil === "function") cerrarPanelPerfil();
  cargarOpcionesEntrega().catch(() => {});
  sincronizarLimiteCarrito();
  document.getElementById("panel-carrito").classList.remove("oculto");
  document.getElementById("overlay-carrito").classList.remove("oculto");
}

function navegarDesdeCarrito(url) {
  const destino = document.documentElement.classList.contains('ttra-cart-embedded') ? window.parent : window;
  destino.location.href = url;
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
    if (!(await registrarPedidoEnClientes(carrito, fechaEntrega, direccionEntrega, coordsDireccionEntregaActual))) return false;
  } catch (error) {
    console.error("No se pudo guardar el pedido", error);
    alert("No pude guardar tu pedido. Probá nuevamente antes de abrir WhatsApp.");
    return;
  }
  borrarCheckoutPendiente();
  vaciarCarrito();
  borrarDescuentoMailing();
  borrarRegaloPromo();
  cerrarCarrito();
  navegarDesdeCarrito(`https://wa.me/${WHATSAPP_NUMERO}?text=${encodeURIComponent(mensaje)}`);
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
// Coordenadas exactas asociadas al texto que hay AHORA en inputDireccionEntrega
// (o null si no hay ninguna — texto tipeado a mano, sin elegir sugerencia).
let coordsDireccionEntregaActual = null;

function ocultarSugerenciasDireccion() {
  sugerenciasDireccion.replaceChildren();
  sugerenciasDireccion.classList.add("oculto");
}

let scriptGoogleMapsCargado;

// Carga el script de Google Maps una sola vez (memoizado), sin importar
// cuántas librerías (places, geocoding) se pidan después con importLibrary.
async function cargarScriptGoogleMaps() {
  if (scriptGoogleMapsCargado !== undefined) return scriptGoogleMapsCargado;
  scriptGoogleMapsCargado = fetch("/api/configuracion-publica")
    .then((respuesta) => respuesta.ok ? respuesta.json() : {})
    .then(async ({ google_maps_api_key: clave }) => {
      if (!clave) return false;
      await new Promise((resolver, rechazar) => {
        const script = document.createElement("script");
        script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(clave)}&libraries=places&v=weekly`;
        script.async = true;
        script.onload = resolver;
        script.onerror = rechazar;
        document.head.append(script);
      });
      return true;
    })
    .catch(() => false);
  return scriptGoogleMapsCargado;
}

async function cargarApiPlaces() {
  if (apiPlacesCargada !== undefined) return apiPlacesCargada;
  apiPlacesCargada = cargarScriptGoogleMaps()
    .then((ok) => ok ? google.maps.importLibrary("places") : null)
    .catch(() => null);
  return apiPlacesCargada;
}

let apiGeocodingCargada;
async function cargarApiGeocoding() {
  if (apiGeocodingCargada !== undefined) return apiGeocodingCargada;
  apiGeocodingCargada = cargarScriptGoogleMaps()
    .then((ok) => ok ? google.maps.importLibrary("geocoding") : null)
    .catch(() => null);
  return apiGeocodingCargada;
}

// --- "Usar mi ubicación": geolocalización del navegador + reverse geocoding
// para completar el texto de la dirección, con las coordenadas exactas
// (clave para barrios privados, donde el texto solo no alcanza). Devuelve
// {direccion, lat, lng} o null si el user no dio permiso / falló algo.
function obtenerUbicacionActual() {
  return new Promise((resolver) => {
    if (!navigator.geolocation) { resolver(null); return; }
    navigator.geolocation.getCurrentPosition(
      (posicion) => resolver({ lat: posicion.coords.latitude, lng: posicion.coords.longitude }),
      () => resolver(null),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  });
}

async function direccionUsandoMiUbicacion() {
  const coords = await obtenerUbicacionActual();
  if (!coords) return null;
  const geocoding = await cargarApiGeocoding();
  let direccion = `${coords.lat.toFixed(6)}, ${coords.lng.toFixed(6)}`;
  if (geocoding) {
    try {
      const { Geocoder } = geocoding;
      const { results } = await new Geocoder().geocode({ location: coords });
      if (results?.[0]?.formatted_address) direccion = results[0].formatted_address;
    } catch { /* si falla el reverse geocoding, se usan las coordenadas crudas */ }
  }
  return { direccion, lat: coords.lat, lng: coords.lng };
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
      await place.fetchFields({ fields: ["formattedAddress", "location"] });
      inputDireccionEntrega.value = place.formattedAddress || placePrediction.text.text;
      coordsDireccionEntregaActual = place.location
        ? { lat: place.location.lat(), lng: place.location.lng() }
        : null;
      ocultarSugerenciasDireccion();
    });
    item.append(boton);
    return item;
  }));
  sugerenciasDireccion.classList.remove("oculto");
}

inputDireccionEntrega.addEventListener("input", () => {
  clearTimeout(temporizadorSugerenciasDireccion);
  // El texto tipeado a mano ya no corresponde a las coordenadas que había
  // (si había): se pierde la precisión hasta elegir otra sugerencia, usar
  // la ubicación o seleccionar un domicilio guardado.
  coordsDireccionEntregaActual = null;
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
  coordsDireccionEntregaActual = null;
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
      coordsDireccionEntregaActual = (domicilio.lat != null && domicilio.lng != null)
        ? { lat: domicilio.lat, lng: domicilio.lng }
        : null;
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

const btnUsarUbicacion = document.getElementById("btn-usar-ubicacion");
if (btnUsarUbicacion) {
  btnUsarUbicacion.addEventListener("click", async () => {
    const textoOriginal = btnUsarUbicacion.textContent;
    btnUsarUbicacion.disabled = true;
    btnUsarUbicacion.textContent = "Buscando ubicación...";
    const resultado = await direccionUsandoMiUbicacion();
    btnUsarUbicacion.disabled = false;
    btnUsarUbicacion.textContent = textoOriginal;
    if (!resultado) {
      alert("No pude obtener tu ubicación. Revisá el permiso de ubicación del navegador.");
      return;
    }
    inputDireccionEntrega.value = resultado.direccion;
    coordsDireccionEntregaActual = { lat: resultado.lat, lng: resultado.lng };
    ocultarSugerenciasDireccion();
  });
}
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
      body: JSON.stringify({
        alias, direccion,
        lat: coordsDireccionEntregaActual?.lat ?? null,
        lng: coordsDireccionEntregaActual?.lng ?? null,
      }),
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
async function registrarPedidoEnClientes(carrito, fecha_entrega, direccion_entrega, coordsDireccion) {
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
      lat: coordsDireccion?.lat ?? null,
      lng: coordsDireccion?.lng ?? null,
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

// --- Compatibilidad con el reloj del header anterior, sin geolocalización ---
let temperaturaActual = null;
let ciudadActual = null;

function formatearFechaHora() {
  const ahora = new Date();
  const fecha = ahora.toLocaleDateString("es-AR");
  const hora = ahora.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  return `${fecha} ${hora}`;
}

// Últimos dígitos de la hora pintados en Classic (para animar -deslizar-
// solo el/los dígitos que cambiaron entre un tick y el siguiente, en vez de
// repintar/reanimar los 6 cada segundo). null = todavía no se armó la
// estructura de spans, o venimos de Fallout (que no la usa).
let digitosRelojClassicActual = null;

// Arma <span class="rc-reloj-fecha">/-digitos/-resto> una sola vez dentro de
// #fecha-hora, la primera vez que este tick corre en Classic.
function asegurarEstructuraRelojClassic(el) {
  if (el.querySelector(".rc-reloj-digitos")) return;
  el.innerHTML =
    '<span class="rc-reloj-fecha"></span> ' +
    '<span class="rc-reloj-digitos"></span>' +
    '<span class="rc-reloj-resto"></span>';
}

function pintarFechaHoraTemp() {
  const elFechaHora = document.getElementById("fecha-hora");
  const elCiudadTemp = document.getElementById("ciudad-temp");
  const elDolar = document.getElementById("dolar-linea");
  if (!elFechaHora || !elCiudadTemp || !elDolar) return;

  const ahora = new Date();
  const fecha = ahora.toLocaleDateString("es-AR");
  const hora = ahora.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  // Efecto "reloj slot" solo en Classic (pedido explícito: no tocar Fallout,
  // que sigue con el texto plano de siempre). match separa "05:55:10" (se
  // anima dígito por dígito) de " p. m." (casi no cambia, texto fijo).
  const esClassic = document.documentElement.getAttribute("data-modo") === "classic";
  const match = esClassic ? hora.match(/^(\d{2}:\d{2}:\d{2})\s*(.*)$/) : null;

  if (!match) {
    // Fallout, o formato de hora inesperado: texto plano, sin animación.
    elFechaHora.textContent = `${fecha} ${hora}`;
    digitosRelojClassicActual = null;
  } else {
    const [, digitos, resto] = match;
    asegurarEstructuraRelojClassic(elFechaHora);
    elFechaHora.querySelector(".rc-reloj-fecha").textContent = fecha;
    elFechaHora.querySelector(".rc-reloj-resto").textContent = resto ? ` ${resto}` : "";

    const contenedorDigitos = elFechaHora.querySelector(".rc-reloj-digitos");
    const nuevos = Array.from(digitos);
    if (!digitosRelojClassicActual || digitosRelojClassicActual.length !== nuevos.length) {
      // Primera pintada en Classic (o se acaba de volver de Fallout): arma
      // los 8 caracteres (6 dígitos animables + 2 ":" fijos).
      contenedorDigitos.innerHTML = nuevos
        .map((char) =>
          char === ":"
            ? ":"
            : `<span class="rc-reloj-digito"><span class="rc-reloj-digito-valor">${char}</span></span>`
        )
        .join("");
    } else {
      // Estructura ya armada: solo se toca (y anima) el dígito que cambió,
      // el resto queda quieto — así cada segundo solo "gira" el de segundos,
      // y minutos/hora solo cuando de verdad cambian.
      const valores = contenedorDigitos.querySelectorAll(".rc-reloj-digito-valor");
      let cursor = 0;
      nuevos.forEach((char, i) => {
        if (char === ":") return;
        const span = valores[cursor++];
        if (span && digitosRelojClassicActual[i] !== char) {
          span.textContent = char;
          span.classList.remove("rc-reloj-cambio");
          void span.offsetWidth; // fuerza reflow: permite re-disparar la misma animación
          span.classList.add("rc-reloj-cambio");
        }
      });
    }
    digitosRelojClassicActual = nuevos;
  }

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

// Se resuelve una sola vez por carga de página, sin consultar la ubicación.
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
// Legacy city artwork uses Córdoba without requesting the visitor’s location.
actualizarImagenesSegunProvincia("AR-X");

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
  const parametrosPanel = new URLSearchParams(location.search);
  if (parametrosPanel.get("panel") === "carrito") {
    abrirCarrito();
    parametrosPanel.delete("panel");
    const query = parametrosPanel.toString();
    history.replaceState(history.state, "", `${location.pathname}${query ? `?${query}` : ""}${location.hash}`);
  }
});
