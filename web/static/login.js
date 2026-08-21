const formLogin = document.getElementById("form-login");
const formRegistro = document.getElementById("form-registro");
const formCambiarObligatorio = document.getElementById("form-cambiar-obligatorio");
const linkIrARegistro = document.getElementById("link-ir-a-registro");
const linkIrALogin = document.getElementById("link-ir-a-login");
const tituloLogin = document.getElementById("titulo-login");

const TITULO_LOGIN = "Bienvenid@ a The Tech Room Arg";
const TITULO_REGISTRO = "Creación de cuenta";
const TITULO_CAMBIAR_OBLIGATORIO = "Elegí tu contraseña nueva";

// Link compartido de un producto (ver compartirProducto en landing.js): si
// alguien sin cuenta lo abre, cae acá con "?producto=..." en la URL. Hay
// que conservar ese query string al mandarlo de vuelta a "/" después de
// loguearse o registrarse, así landing.js puede abrir el producto
// directamente en vez de perderlo en el camino.
const productoCompartido = new URLSearchParams(location.search).get("producto");
const destinoTrasIngresar = productoCompartido ? `/${location.search}` : "/";

const btnVerLoginPassword = document.getElementById("btn-ver-login-password");
const loginPasswordInput = document.getElementById("login-password");
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

function mostrarRegistro() {
  formLogin.classList.add("oculto");
  formRegistro.classList.remove("oculto");
  tituloLogin.textContent = TITULO_REGISTRO;
}

function mostrarLogin() {
  formRegistro.classList.add("oculto");
  formLogin.classList.remove("oculto");
  tituloLogin.textContent = TITULO_LOGIN;
}

// Quien abre un link compartido probablemente no tenga cuenta todavía —
// arranca directo en el form de registro (puede pasarse a login con el
// link de siempre si ya tiene una).
if (productoCompartido) mostrarRegistro();

linkIrARegistro.addEventListener("click", (e) => {
  e.preventDefault();
  mostrarRegistro();
});

linkIrALogin.addEventListener("click", (e) => {
  e.preventDefault();
  mostrarLogin();
});

async function enviar(url, body, errorEl) {
  errorEl.textContent = "";
  const r = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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
  const errorEl = document.getElementById("registro-error");
  const password = document.getElementById("registro-password").value;
  const repetir = document.getElementById("registro-password-repetir").value;
  if (password !== repetir) {
    errorEl.textContent = "Las contraseñas no coinciden.";
    return;
  }
  const datos = await enviar(
    "/registro",
    {
      username: document.getElementById("registro-username").value,
      nombre: document.getElementById("registro-nombre").value,
      apellido: document.getElementById("registro-apellido").value,
      celular: document.getElementById("registro-celular").value,
      email: document.getElementById("registro-email").value,
      password,
    },
    errorEl,
  );
  if (!datos) return;
  window.location.href = destinoTrasIngresar;
});
