const formLogin = document.getElementById("form-login");
const formRegistro = document.getElementById("form-registro");
const linkIrARegistro = document.getElementById("link-ir-a-registro");
const linkIrALogin = document.getElementById("link-ir-a-login");
const tituloLogin = document.getElementById("titulo-login");

const TITULO_LOGIN = "Bienvenid@ a The Tech Room Arg";
const TITULO_REGISTRO = "Creación de cuenta";

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
    return;
  }
  window.location.href = "/";
}

formLogin.addEventListener("submit", (e) => {
  e.preventDefault();
  enviar(
    "/login",
    {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    },
    document.getElementById("login-error"),
  );
});

formRegistro.addEventListener("submit", (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("registro-error");
  const password = document.getElementById("registro-password").value;
  const repetir = document.getElementById("registro-password-repetir").value;
  if (password !== repetir) {
    errorEl.textContent = "Las contraseñas no coinciden.";
    return;
  }
  enviar(
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
});
