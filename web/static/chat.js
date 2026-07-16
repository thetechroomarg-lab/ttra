// web/static/chat.js
const chat = document.getElementById("chat");
const form = document.getElementById("form");
const entrada = document.getElementById("entrada");
const mic = document.getElementById("mic");
const historial = [];

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function conLinks(texto) {
  // convierte URLs en enlaces clickeables (abren en pestaña nueva)
  return escapeHtml(texto).replace(/(https?:\/\/[^\s]+)/g,
    '<a href="$1" target="_blank" rel="noopener">$1</a>');
}

function burbuja(texto, quien) {
  const div = document.createElement("div");
  div.className = "msg " + quien;
  div.innerHTML = conLinks(texto);
  chat.appendChild(div);
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
      body: JSON.stringify({ mensaje, historial: historial.slice(0, -1) }),
    });
    const data = await r.json();
    setTexto(cargando, data.respuesta);
    historial.push({ role: "assistant", content: data.respuesta });
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
        "ahora podés buscar todo a cualquier hora. 😊 ¿Qué estás buscando?", "bot");
