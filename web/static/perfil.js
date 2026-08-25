const linkVolver = document.getElementById("link-volver");
const perfilDireccionInput = document.getElementById("perfil-direccion");
const perfilSugerenciasDireccion = document.getElementById("perfil-sugerencias-direccion");
let temporizadorPerfilDireccion;
let apiPlacesPerfil;
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
  if (!places || texto !== perfilDireccionInput.value.trim()) return;
  const { AutocompleteSuggestion } = places;
  const { suggestions } = await AutocompleteSuggestion.fetchAutocompleteSuggestions({
    input: texto,
    includedRegionCodes: ["ar"],
  });
  if (texto !== perfilDireccionInput.value.trim() || !suggestions?.length) {
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
      perfilDireccionInput.value = place.formattedAddress || placePrediction.text.text;
      ocultarSugerenciasPerfilDireccion();
    });
    item.append(boton);
    return item;
  }));
  perfilSugerenciasDireccion.hidden = false;
}

perfilDireccionInput.addEventListener("input", () => {
  clearTimeout(temporizadorPerfilDireccion);
  const texto = perfilDireccionInput.value.trim();
  if (texto.length < 3) {
    ocultarSugerenciasPerfilDireccion();
    return;
  }
  temporizadorPerfilDireccion = setTimeout(() => {
    mostrarSugerenciasPerfilDireccion(texto).catch(ocultarSugerenciasPerfilDireccion);
  }, 250);
});

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
    perfilDireccionInput.value = datos.direccion || "";
  } catch {
    errorEl.textContent = "No pudimos conectar, probá de nuevo en un momento";
  }
}

cargarPerfil();

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
        direccion: perfilDireccionInput.value,
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
