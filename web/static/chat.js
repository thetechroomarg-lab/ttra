// web/static/chat.js
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const entrada = document.getElementById("entrada");
const mic = document.getElementById("mic");
const historial = [];
const sesion = (crypto.randomUUID && crypto.randomUUID()) ||
               (Date.now() + "-" + Math.random().toString(16).slice(2));
let avatarCliente = "avatar-hombre.svg";  // hombre por defecto; cambia a mujer si corresponde

function aplicarAvatarCliente(genero) {
  if (genero === "mujer") avatarCliente = "avatar-mujer.svg";
  else if (genero === "hombre") avatarCliente = "avatar-hombre.svg";
  else return;
  document.querySelectorAll(".row.user img.avatar").forEach((img) => {
    img.src = avatarCliente;
    img.style.display = "";
  });
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function conLinks(texto) {
  // convierte URLs en enlaces clickeables (abren en pestaña nueva).
  // Los links de WhatsApp (largos, con el pedido adentro) se muestran como botón corto.
  return escapeHtml(texto).replace(/(https?:\/\/[^\s]+)/g, (url) => {
    if (url.includes("wa.me")) {
      return '<a href="' + url + '" target="_blank" rel="noopener" class="wa-btn">' +
             '📲 Enviar mi pedido por WhatsApp</a>';
    }
    return '<a href="' + url + '" target="_blank" rel="noopener">' + url + '</a>';
  });
}

function burbuja(texto, quien) {
  const row = document.createElement("div");
  row.className = "row " + quien;
  const av = document.createElement("img");
  av.className = "avatar";
  av.src = quien === "bot" ? "avatar-vlad.svg" : avatarCliente;
  av.alt = quien === "bot" ? "Vlad" : "Cliente";
  av.onerror = () => { av.style.display = "none"; };
  row.appendChild(av);
  const div = document.createElement("div");
  div.className = "msg " + quien;
  div.innerHTML = conLinks(texto);
  row.appendChild(div);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function setTexto(div, texto) {
  div.innerHTML = conLinks(texto);
  chat.scrollTop = chat.scrollHeight;
}

async function enviar(mensaje) {
  burbuja(mensaje, "user");
  historial.push({ role: "user", content: mensaje });
  const cargando = burbuja("…", "bot");
  try {
    const r = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mensaje, historial: historial.slice(0, -1), sesion }),
    });
    const data = await r.json();
    setTexto(cargando, data.respuesta);
    historial.push({ role: "assistant", content: data.respuesta });
    aplicarAvatarCliente(data.genero);
  } catch (e) {
    setTexto(cargando, "Error de conexión. Probá de nuevo 🙏");
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const t = entrada.value.trim();
  if (!t) return;
  entrada.value = "";
  enviar(t);
});

// --- Voz (Web Speech API) ---
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SR) {
  const rec = new SR();
  rec.lang = "es-AR";
  rec.interimResults = false;
  mic.addEventListener("click", () => { mic.classList.add("grabando"); rec.start(); });
  rec.addEventListener("result", (ev) => { entrada.value = ev.results[0][0].transcript; });
  rec.addEventListener("end", () => { mic.classList.remove("grabando"); });
} else {
  mic.style.display = "none";  // navegador sin soporte de voz
}

burbuja("Hola, soy Vlad, pero en versión digital. Llegaste a THE TECH ROOM ARG; " +
        "ahora podés buscar a cualquier hora.\n\nAntes de continuar, decime tu nombre " +
        "por favor. 🙂", "bot");
