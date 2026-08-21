const tabs = document.querySelectorAll(".tab");
const formLogin = document.getElementById("form-login");
const formRegistro = document.getElementById("form-registro");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((t) => t.classList.remove("activa"));
    tab.classList.add("activa");
    const esLogin = tab.dataset.tab === "login";
    formLogin.classList.toggle("oculto", !esLogin);
    formRegistro.classList.toggle("oculto", esLogin);
  });
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
  enviar(
    "/registro",
    {
      nombre: document.getElementById("registro-nombre").value,
      apellido: document.getElementById("registro-apellido").value,
      celular: document.getElementById("registro-celular").value,
      email: document.getElementById("registro-email").value,
      password: document.getElementById("registro-password").value,
    },
    document.getElementById("registro-error"),
  );
});
