const linkVolver = document.getElementById("link-volver");
const domicilioDireccionInput = document.getElementById("domicilio-direccion");
const domicilioAliasInput = document.getElementById("domicilio-alias");
const perfilSugerenciasDireccion = document.getElementById("perfil-sugerencias-direccion");
const listaDomicilios = document.getElementById("lista-domicilios");
const btnGuardarDomicilio = document.getElementById("btn-guardar-domicilio");
const btnCancelarEdicionDomicilio = document.getElementById("btn-cancelar-edicion-domicilio");
let temporizadorPerfilDireccion;
let apiPlacesPerfil;
let domicilioEnEdicionId = null;
if (document.documentElement.getAttribute("data-modo") === "fallout") {
  linkVolver.href = "/?modo=fallout";
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
const overlayTerminosMayorista = document.getElementById("rc-terminos-mayorista");
const contenidoTerminosMayorista = document.getElementById("rc-terminos-contenido");
const btnTerminosCerrar = document.getElementById("btn-terminos-cerrar");
let fragmentoTerminosMayoristaCache = null;

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
  // saca a Classic apenas se sabe que la cuenta es mayorista.
  if (esMayorista && document.documentElement.getAttribute("data-modo") === "fallout") {
    document.documentElement.setAttribute("data-modo", "classic");
  }
}

async function cargarFragmentoTerminosMayorista() {
  if (fragmentoTerminosMayoristaCache) return fragmentoTerminosMayoristaCache;
  try {
    const r = await fetch("/condiciones-mayorista.html");
    fragmentoTerminosMayoristaCache = r.ok
      ? await r.text()
      : "<p>No pudimos cargar las condiciones mayoristas. Probá de nuevo.</p>";
  } catch {
    fragmentoTerminosMayoristaCache = "<p>No pudimos cargar las condiciones mayoristas. Probá de nuevo.</p>";
  }
  return fragmentoTerminosMayoristaCache;
}

if (btnVerCondicionesMayorista) {
  btnVerCondicionesMayorista.addEventListener("click", async () => {
    if (!overlayTerminosMayorista || !contenidoTerminosMayorista) return;
    contenidoTerminosMayorista.innerHTML = await cargarFragmentoTerminosMayorista();
    contenidoTerminosMayorista.scrollTop = 0;
    overlayTerminosMayorista.classList.add("visible");
  });
}

if (btnTerminosCerrar) {
  btnTerminosCerrar.addEventListener("click", () => {
    if (overlayTerminosMayorista) overlayTerminosMayorista.classList.remove("visible");
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
      errorEl.textContent = datos.error || "No pudimos cargar tu perfil";
      return;
    }
    document.getElementById("perfil-nombre").value = datos.nombre || "";
    document.getElementById("perfil-apellido").value = datos.apellido || "";
    document.getElementById("perfil-email").value = datos.email || "";
    document.getElementById("perfil-celular").value = datos.celular || "";
    mostrarSeccionCondicionesMayorista(datos);
  } catch {
    errorEl.textContent = "No pudimos conectar, probá de nuevo en un momento";
  }
}

function cancelarEdicionDomicilio() {
  domicilioEnEdicionId = null;
  domicilioAliasInput.value = "";
  domicilioDireccionInput.value = "";
  btnGuardarDomicilio.textContent = "Agregar domicilio";
  btnCancelarEdicionDomicilio.classList.add("oculto");
}

function itemDomicilioHtml(domicilio) {
  const item = document.createElement("div");
  item.className = "item-domicilio";
  const info = document.createElement("p");
  info.textContent = `${domicilio.alias}${domicilio.predeterminado ? " · Predeterminado" : ""} — ${domicilio.direccion}`;
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

cargarPerfil();
cargarDomicilios();

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
      errorEl.textContent = datos.error || datos.detail || "No pudimos guardar los cambios";
      return;
    }
    okEl.textContent = "Datos guardados";
  } catch {
    errorEl.textContent = "No pudimos conectar, probá de nuevo en un momento";
  }
});

const formDomicilio = document.getElementById("form-domicilio");
formDomicilio.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("domicilio-error");
  const okEl = document.getElementById("domicilio-ok");
  errorEl.textContent = "";
  okEl.textContent = "";
  const cuerpo = { alias: domicilioAliasInput.value, direccion: domicilioDireccionInput.value };
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
      errorEl.textContent = datos.error || datos.detail || "No pudimos guardar el domicilio";
      return;
    }
    okEl.textContent = "Domicilio guardado";
    cancelarEdicionDomicilio();
    cargarDomicilios();
  } catch {
    errorEl.textContent = "No pudimos conectar, probá de nuevo en un momento";
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
      errorEl.textContent = datos.error || datos.detail || "No pudimos cambiar la contraseña";
      return;
    }
    okEl.textContent = "Contraseña actualizada";
    formPassword.reset();
  } catch {
    errorEl.textContent = "No pudimos conectar, probá de nuevo en un momento";
  }
});
