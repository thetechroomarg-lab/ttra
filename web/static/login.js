const formLogin = document.getElementById("form-login");
const formRegistro = document.getElementById("form-registro");
const formCambiarObligatorio = document.getElementById("form-cambiar-obligatorio");
const linkIrARegistro = document.getElementById("link-ir-a-registro");
const linkIrALogin = document.getElementById("link-ir-a-login");
const tituloLogin = document.getElementById("titulo-login");

const TITULO_LOGIN = "Bienvenid@ de nuevo";
const TITULO_REGISTRO = "Creación de cuenta";
const TITULO_CAMBIAR_OBLIGATORIO = "Elegí tu contraseña nueva";

// Link compartido de un producto (ver compartirProducto en landing.js): si
// alguien sin cuenta lo abre, cae acá con "?producto=..." en la URL. Hay
// que conservar ese query string al mandarlo de vuelta a "/" después de
// loguearse o registrarse, así landing.js puede abrir el producto
// directamente en vez de perderlo en el camino.
const paramsPantalla = new URLSearchParams(location.search);
const productoCompartido = paramsPantalla.get("producto");
const forzarRegistro = paramsPantalla.get("registro") === "1";
const modoFallout = paramsPantalla.get("modo") === "fallout";
const volverTrasIngresar = paramsPantalla.get("volver");
const destinoTrasIngresar = volverTrasIngresar || (productoCompartido ? `/${location.search}` : (modoFallout ? "/?modo=fallout" : "/"));

if (modoFallout) {
  document.documentElement.setAttribute("data-modo", "fallout");
}

const btnVerLoginPassword = document.getElementById("btn-ver-login-password");
const loginPasswordInput = document.getElementById("login-password");
const loginErrorEl = document.getElementById("login-error");
const loginOkEl = document.getElementById("login-ok");
const registroErrorEl = document.getElementById("registro-error");
const registroOkEl = document.getElementById("registro-ok");
const CLAVE_ANON_ID = "ttra_anon_id";
const registroDireccionInput = document.getElementById("registro-direccion");
const registroSugerenciasDireccion = document.getElementById("registro-sugerencias-direccion");
let temporizadorRegistroDireccion;
let apiPlacesRegistro;

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

function limpiarMensajes() {
  [loginErrorEl, loginOkEl, registroErrorEl, registroOkEl, document.getElementById("cambiar-error")]
    .filter(Boolean)
    .forEach((el) => { el.textContent = ""; });
}

function paramsHashSupabase() {
  const hash = location.hash.startsWith("#") ? location.hash.slice(1) : location.hash;
  const params = new URLSearchParams(hash);
  return {
    accessToken: params.get("access_token"),
    refreshToken: params.get("refresh_token"),
    type: params.get("type"),
  };
}

function limpiarCallbackSupabaseDeUrl() {
  const query = new URLSearchParams(location.search);
  query.delete("token_hash");
  query.delete("type");
  query.delete("code");
  const queryStr = query.toString();
  history.replaceState({}, "", `${location.pathname}${queryStr ? `?${queryStr}` : ""}`);
  if (location.hash) history.replaceState({}, "", `${location.pathname}${queryStr ? `?${queryStr}` : ""}`);
}

if (btnVerLoginPassword && loginPasswordInput) {
  btnVerLoginPassword.addEventListener("click", () => {
    const visible = loginPasswordInput.type === "text";
    loginPasswordInput.type = visible ? "password" : "text";
    btnVerLoginPassword.setAttribute("aria-pressed", String(!visible));
    btnVerLoginPassword.setAttribute("aria-label", visible ? "Mostrar contraseña" : "Ocultar contraseña");
  });
}

function mostrarCambioObligatorio() {
  formLogin.classList.add("oculto");
  formRegistro.classList.add("oculto");
  formCambiarObligatorio.classList.remove("oculto");
  tituloLogin.textContent = TITULO_CAMBIAR_OBLIGATORIO;
}

// Si ya hay una sesión activa pendiente de cambio de contraseña (por ej. el
// usuario cerró la pestaña a mitad del flujo y volvió), mostramos el form
// obligatorio directo en vez del login — /api/me solo responde 200 con
// sesión activa, así que un 401 simplemente deja el login normal.
fetch("/api/me")
  .then((r) => (r.ok ? r.json() : null))
  .then((datos) => {
    if (datos && datos.debe_cambiar_password) mostrarCambioObligatorio();
  })
  .catch(() => {});

async function completarSignupVerificado() {
  const query = new URLSearchParams(location.search);
  const tokenHash = query.get("token_hash");
  const queryType = query.get("type");
  const { accessToken, type: hashType } = paramsHashSupabase();
  if (!accessToken && !tokenHash) return false;

  limpiarMensajes();
  loginOkEl.textContent = "Confirmando tu cuenta...";
  const r = await fetch("/auth/completar-signup", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-TTRA-ANON-ID": obtenerAnonId(),
    },
    body: JSON.stringify({
      access_token: accessToken,
      token_hash: tokenHash,
      type: queryType || hashType,
    }),
  });
  const datos = await r.json().catch(() => ({}));
  if (!r.ok) {
    loginOkEl.textContent = "";
    loginErrorEl.textContent = datos.error || "No se pudo completar la verificación.";
    return false;
  }
  limpiarCallbackSupabaseDeUrl();
  window.location.href = destinoTrasIngresar;
  return true;
}

function mostrarRegistro() {
  limpiarMensajes();
  formLogin.classList.add("oculto");
  formRegistro.classList.remove("oculto");
  formCambiarObligatorio.classList.add("oculto");
  tituloLogin.textContent = TITULO_REGISTRO;
}

function mostrarLogin() {
  limpiarMensajes();
  formRegistro.classList.add("oculto");
  formLogin.classList.remove("oculto");
  formCambiarObligatorio.classList.add("oculto");
  tituloLogin.textContent = TITULO_LOGIN;
}

// Quien abre un link compartido probablemente no tenga cuenta todavía —
// arranca directo en el form de registro (puede pasarse a login con el
// link de siempre si ya tiene una).
if (productoCompartido || forzarRegistro) mostrarRegistro();

completarSignupVerificado().catch(() => {
  loginOkEl.textContent = "";
  loginErrorEl.textContent = "No se pudo completar la verificación.";
});

linkIrARegistro.addEventListener("click", (e) => {
  e.preventDefault();
  mostrarRegistro();
});

linkIrALogin.addEventListener("click", (e) => {
  e.preventDefault();
  mostrarLogin();
});

function ocultarSugerenciasRegistroDireccion() {
  registroSugerenciasDireccion.replaceChildren();
  registroSugerenciasDireccion.hidden = true;
}

let scriptGoogleMapsRegistroCargado;

// Igual que en landing.js: el script se carga una sola vez, sin importar
// cuántas librerías (places, geocoding) se pidan después con importLibrary.
async function cargarScriptGoogleMapsRegistro() {
  if (scriptGoogleMapsRegistroCargado !== undefined) return scriptGoogleMapsRegistroCargado;
  scriptGoogleMapsRegistroCargado = fetch("/api/configuracion-publica")
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
  return scriptGoogleMapsRegistroCargado;
}

async function cargarApiPlacesRegistro() {
  if (apiPlacesRegistro !== undefined) return apiPlacesRegistro;
  apiPlacesRegistro = cargarScriptGoogleMapsRegistro()
    .then((ok) => ok ? google.maps.importLibrary("places") : null)
    .catch(() => null);
  return apiPlacesRegistro;
}

let apiGeocodingRegistro;
async function cargarApiGeocodingRegistro() {
  if (apiGeocodingRegistro !== undefined) return apiGeocodingRegistro;
  apiGeocodingRegistro = cargarScriptGoogleMapsRegistro()
    .then((ok) => ok ? google.maps.importLibrary("geocoding") : null)
    .catch(() => null);
  return apiGeocodingRegistro;
}

function obtenerUbicacionActualRegistro() {
  return new Promise((resolver) => {
    if (!navigator.geolocation) { resolver(null); return; }
    navigator.geolocation.getCurrentPosition(
      (posicion) => resolver({ lat: posicion.coords.latitude, lng: posicion.coords.longitude }),
      () => resolver(null),
      { enableHighAccuracy: true, timeout: 10000 },
    );
  });
}

// Coordenadas exactas asociadas al texto que hay AHORA en registroDireccionInput.
let coordsRegistroDireccionActual = null;

async function direccionRegistroUsandoMiUbicacion() {
  const coords = await obtenerUbicacionActualRegistro();
  if (!coords) return null;
  const geocoding = await cargarApiGeocodingRegistro();
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

async function mostrarSugerenciasRegistroDireccion(texto) {
  const places = await cargarApiPlacesRegistro();
  if (!places || texto !== registroDireccionInput.value.trim()) return;
  const { AutocompleteSuggestion } = places;
  const { suggestions } = await AutocompleteSuggestion.fetchAutocompleteSuggestions({
    input: texto,
    includedRegionCodes: ["ar"],
  });
  if (texto !== registroDireccionInput.value.trim() || !suggestions?.length) {
    ocultarSugerenciasRegistroDireccion();
    return;
  }
  registroSugerenciasDireccion.replaceChildren(...suggestions.slice(0, 5).map(({ placePrediction }) => {
    const item = document.createElement("li");
    const boton = document.createElement("button");
    boton.type = "button";
    boton.textContent = placePrediction.text.text;
    boton.addEventListener("click", async () => {
      const place = placePrediction.toPlace();
      await place.fetchFields({ fields: ["formattedAddress", "location"] });
      registroDireccionInput.value = place.formattedAddress || placePrediction.text.text;
      coordsRegistroDireccionActual = place.location
        ? { lat: place.location.lat(), lng: place.location.lng() }
        : null;
      ocultarSugerenciasRegistroDireccion();
    });
    item.append(boton);
    return item;
  }));
  registroSugerenciasDireccion.hidden = false;
}

const btnRegistroUsarUbicacion = document.getElementById("btn-registro-usar-ubicacion");
if (btnRegistroUsarUbicacion) {
  btnRegistroUsarUbicacion.addEventListener("click", async () => {
    const textoOriginal = btnRegistroUsarUbicacion.textContent;
    btnRegistroUsarUbicacion.disabled = true;
    btnRegistroUsarUbicacion.textContent = "Buscando ubicación...";
    const resultado = await direccionRegistroUsandoMiUbicacion();
    btnRegistroUsarUbicacion.disabled = false;
    btnRegistroUsarUbicacion.textContent = textoOriginal;
    if (!resultado) {
      registroErrorEl.textContent = "No pudimos obtener tu ubicación. Revisá el permiso de ubicación del navegador.";
      return;
    }
    registroDireccionInput.value = resultado.direccion;
    coordsRegistroDireccionActual = { lat: resultado.lat, lng: resultado.lng };
    ocultarSugerenciasRegistroDireccion();
  });
}

registroDireccionInput.addEventListener("input", () => {
  clearTimeout(temporizadorRegistroDireccion);
  coordsRegistroDireccionActual = null;
  const texto = registroDireccionInput.value.trim();
  if (texto.length < 3) {
    ocultarSugerenciasRegistroDireccion();
    return;
  }
  temporizadorRegistroDireccion = setTimeout(() => {
    mostrarSugerenciasRegistroDireccion(texto).catch(ocultarSugerenciasRegistroDireccion);
  }, 250);
});

async function enviar(url, body, errorEl) {
  limpiarMensajes();
  errorEl.textContent = "";
  const r = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-TTRA-ANON-ID": obtenerAnonId(),
    },
    body: JSON.stringify(body),
  });
  const datos = await r.json();
  if (!r.ok) {
    errorEl.textContent = datos.error || "Ocurrió un error, probá de nuevo.";
    return null;
  }
  return datos;
}

formLogin.addEventListener("submit", async (e) => {
  e.preventDefault();
  const datos = await enviar(
    "/login",
    {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    },
    document.getElementById("login-error"),
  );
  if (!datos) return;
  if (datos.debe_cambiar_password) {
    mostrarCambioObligatorio();
    return;
  }
  window.location.href = destinoTrasIngresar;
});

formCambiarObligatorio.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("cambiar-error");
  const password = document.getElementById("cambiar-password").value;
  const repetir = document.getElementById("cambiar-password-repetir").value;
  if (password !== repetir) {
    errorEl.textContent = "Las contraseñas no coinciden.";
    return;
  }
  const datos = await enviar("/cambiar-password-obligatorio", { password }, errorEl);
  if (!datos) return;
  window.location.href = destinoTrasIngresar;
});

formRegistro.addEventListener("submit", async (e) => {
  e.preventDefault();
  const password = document.getElementById("registro-password").value;
  const repetir = document.getElementById("registro-password-repetir").value;
  const email = document.getElementById("registro-email").value;
  if (password.length < 8) {
    registroErrorEl.textContent = "La contraseña tiene que tener al menos 8 caracteres.";
    return;
  }
  if (password !== repetir) {
    registroErrorEl.textContent = "Las contraseñas no coinciden.";
    return;
  }
  const datos = await enviar(
    modoFallout ? "/registro?modo=fallout" : "/registro",
    {
      nombre: document.getElementById("registro-nombre").value,
      apellido: document.getElementById("registro-apellido").value,
      celular: document.getElementById("registro-celular").value,
      email,
      password,
      provincia: document.getElementById("registro-provincia").value,
      direccion: registroDireccionInput.value,
      lat: coordsRegistroDireccionActual?.lat ?? null,
      lng: coordsRegistroDireccionActual?.lng ?? null,
    },
    registroErrorEl,
  );
  if (!datos) return;
  if (datos.requiere_confirmacion_email) {
    formRegistro.reset();
    mostrarLogin();
    document.getElementById("login-email").value = email;
    loginOkEl.textContent = "Te mandamos un mail para verificar tu cuenta. Confirmalo antes de ingresar.";
    return;
  }
  window.location.href = destinoTrasIngresar;
});
