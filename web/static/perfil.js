const linkVolver = document.getElementById("link-volver");
if (document.documentElement.getAttribute("data-modo") === "fallout") {
  linkVolver.href = "/?modo=fallout";
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
    document.getElementById("perfil-username").value = datos.username || "";
    document.getElementById("perfil-email").value = datos.email || "";
    document.getElementById("perfil-celular").value = datos.celular || "";
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
        username: document.getElementById("perfil-username").value,
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
