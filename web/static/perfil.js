// Este script sirve dos contextos:
// 1) /perfil.html standalone (link-volver existe): se comporta como
//    siempre, cargando el perfil apenas el script corre.
// 2) Panel embebido en index.html (panel-perfil existe, ver
//    #panel-perfil/landing.js): NO carga nada hasta que se llama a
//    window.abrirPanelPerfil() -evita pegarle a /api/me y redirigir a un
//    invitado a login.html solo porque este script está en la página-, y
//    "cerrar" oculta el panel en vez de navegar.
const panelPerfilEmbebido = document.getElementById("panel-perfil");
const linkVolver = document.getElementById("link-volver");
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
let temporizadorPerfilDireccion;
let apiPlacesPerfil;
let domicilioEnEdicionId = null;
if (linkVolver && document.documentElement.getAttribute("data-modo") === "fallout") {
  linkVolver.href = "/?modo=fallout";
}

function cerrarPanelPerfil() {
  if (!panelPerfilEmbebido) return;
  panelPerfilEmbebido.classList.add("oculto");
  if (overlayPerfilEmbebido) overlayPerfilEmbebido.classList.add("oculto");
}

if (btnCerrarPanelPerfil) {
  btnCerrarPanelPerfil.addEventListener("click", cerrarPanelPerfil);
}
if (overlayPerfilEmbebido) {
  overlayPerfilEmbebido.addEventListener("click", cerrarPanelPerfil);
}

function ocultarSugerenciasPerfilDireccion() {
  perfilSugerenciasDireccion.replaceChildren();
  perfilSugerenciasDireccion.hidden = true;
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

async function mostrarSugerenciasPerfilDireccion(texto) {
  const places = await cargarApiPlacesPerfil();
  if (!places || texto !== domicilioDireccionInput.value.trim()) return;
  const { AutocompleteSuggestion } = places;
  const { suggestions } = await AutocompleteSuggestion.fetchAutocompleteSuggestions({
    input: texto,
    includedRegionCodes: ["ar"],
  });
  if (texto !== domicilioDireccionInput.value.trim() || !suggestions?.length) {
    ocultarSugerenciasPerfilDireccion();
    return;
  }
  perfilSugerenciasDireccion.replaceChildren(...suggestions.slice(0, 5).map(({ placePrediction }) => {
    const item = document.createElement("li");
    const boton = document.createElement("button");
    boton.type = "button";
    boton.textContent = placePrediction.text.text;
    boton.addEventListener("click", async () => {
      const place = placePrediction.toPlace();
      await place.fetchFields({ fields: ["formattedAddress"] });
      domicilioDireccionInput.value = place.formattedAddress || placePrediction.text.text;
      ocultarSugerenciasPerfilDireccion();
    });
    item.append(boton);
    return item;
  }));
  perfilSugerenciasDireccion.hidden = false;
}

domicilioDireccionInput.addEventListener("input", () => {
  clearTimeout(temporizadorPerfilDireccion);
  const texto = domicilioDireccionInput.value.trim();
  if (texto.length < 3) {
    ocultarSugerenciasPerfilDireccion();
    return;
  }
  temporizadorPerfilDireccion = setTimeout(() => {
    mostrarSugerenciasPerfilDireccion(texto).catch(ocultarSugerenciasPerfilDireccion);
  }, 250);
});

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
  if (datos.fidelidad_ultimo_codigo) {
    mensajePremio.textContent =
      `¡Tenés un premio! Usá el código ${datos.fidelidad_ultimo_codigo} en tu próxima compra: US$20 de descuento.`;
    mensajePremio.classList.remove("oculto");
    return;
  }
  mensajePremio.classList.add("oculto");
  const sellos = Math.min(Number(datos.sellos_fidelidad) || 0, 5);
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
  ayuda.textContent = `${sellos} de 5 compras. A la quinta te regalo US$20 de descuento.`;
  contenedorSellos.append(ayuda);
}

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
      window.location.href = "/login.html";
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
    mostrarSeccionCondicionesMayorista(datos);
    mostrarTarjetaFidelidad(datos);
  } catch {
    errorEl.textContent = "No pude conectar, probá de nuevo en un momento";
  }
}

function cancelarEdicionDomicilio() {
  domicilioEnEdicionId = null;
  domicilioAliasInput.value = "";
  domicilioDireccionInput.value = "";
  domicilioPisoInput.value = "";
  domicilioDeptoInput.value = "";
  btnGuardarDomicilio.textContent = "Agregar domicilio";
  btnCancelarEdicionDomicilio.classList.add("oculto");
}

function itemDomicilioHtml(domicilio) {
  const item = document.createElement("div");
  item.className = "item-domicilio";
  const info = document.createElement("p");
  const pisoDepto = textoPisoDepto(domicilio);
  info.textContent = `${domicilio.alias}${domicilio.predeterminado ? " · Predeterminado" : ""} — ${domicilio.direccion}${pisoDepto ? ` (${pisoDepto})` : ""}`;
  item.append(info);

  const acciones = document.createElement("div");
  acciones.className = "item-domicilio-acciones";

  if (!domicilio.predeterminado) {
    const btnPredeterminado = document.createElement("button");
    btnPredeterminado.type = "button";
    btnPredeterminado.textContent = "Marcar predeterminado";
    btnPredeterminado.addEventListener("click", async () => {
      await fetch(`/api/domicilios/${domicilio.id}/predeterminado`, { method: "POST" });
      cargarDomicilios();
    });
    acciones.append(btnPredeterminado);
  }

  const btnEditar = document.createElement("button");
  btnEditar.type = "button";
  btnEditar.textContent = "Editar";
  btnEditar.addEventListener("click", () => {
    domicilioEnEdicionId = domicilio.id;
    domicilioAliasInput.value = domicilio.alias;
    domicilioDireccionInput.value = domicilio.direccion;
    domicilioPisoInput.value = domicilio.piso || "";
    domicilioDeptoInput.value = domicilio.depto || "";
    btnGuardarDomicilio.textContent = "Guardar cambios";
    btnCancelarEdicionDomicilio.classList.remove("oculto");
    domicilioAliasInput.focus();
  });
  acciones.append(btnEditar);

  const btnEliminar = document.createElement("button");
  btnEliminar.type = "button";
  btnEliminar.textContent = "Eliminar";
  btnEliminar.addEventListener("click", async () => {
    if (!confirm(`¿Eliminar el domicilio "${domicilio.alias}"?`)) return;
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
    if (!domicilios.length) {
      const vacio = document.createElement("p");
      vacio.className = "carrito-nota";
      vacio.textContent = "Todavía no tenés domicilios guardados.";
      listaDomicilios.append(vacio);
      return;
    }
    domicilios.forEach((domicilio) => listaDomicilios.append(itemDomicilioHtml(domicilio)));
    btnGuardarDomicilio.disabled = domicilios.length >= 5 && !domicilioEnEdicionId;
  } catch {
    // Si falla, la lista simplemente queda vacía — el resto del perfil sigue usable.
  }
}

if (panelPerfilEmbebido) {
  // Embebido: no se carga nada hasta que el usuario realmente abre el
  // panel (ver btn-perfil-toggle -> linkIrAPerfil en landing.js), para no
  // pegarle a /api/me -y de paso redirigir a un invitado a login.html- en
  // cada carga de la home solo porque este script está en la página.
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
} else {
  // Standalone (/perfil.html): comportamiento de siempre.
  cargarPerfil();
  cargarDomicilios();
}

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
    okEl.textContent = "Datos guardados";
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
    okEl.textContent = "Domicilio guardado";
    cancelarEdicionDomicilio();
    cargarDomicilios();
  } catch {
    errorEl.textContent = "No pude conectar, probá de nuevo en un momento";
  }
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
