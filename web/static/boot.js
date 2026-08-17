// web/static/boot.js — secuencia de arranque estilo terminal RobCo.
// Se muestra en cada carga de página (F5 incluido).
(function () {
  const overlay = document.getElementById("rc-boot");
  if (!overlay) return;

  const LINEAS = [
    "THE TECH ROOM ARG",
    "UNIFIED TECHNOLOGY SYSTEM",
    "COPYRIGHT 2009-2026",
    "",
    "INITIALIZING TERMINAL...",
    "LOADING SYSTEM............. OK",
    "CHECKING MEMORY............ OK",
    "ESTABLISHING CONNECTION.... OK",
    "LOADING DATABASE........... OK",
    "VERIFYING INVENTORY........ OK",
    "SYSTEM STATUS.............. OPERATIONAL",
    "",
    "ACCESS GRANTED",
    "WELCOME, USER.",
  ];

  // Beeps estilo computadora vieja (onda cuadrada sintetizada, sin archivos de
  // audio). Los navegadores bloquean audio autoplay sin gesto del usuario: si
  // el contexto queda suspendido, el beep simplemente no suena, sin romper nada.
  let audioCtx;
  function beep(frecuencia, duracionMs) {
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === "suspended") audioCtx.resume();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "square";
      osc.frequency.value = frecuencia;
      gain.gain.setValueAtTime(0.05, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + duracionMs / 1000);
      osc.connect(gain).connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + duracionMs / 1000);
    } catch {
      // Web Audio no disponible: seguimos sin sonido, no es crítico.
    }
  }

  overlay.textContent = "";
  let i = 0;

  function siguienteLinea() {
    if (i >= LINEAS.length) {
      const listo = document.createElement("div");
      listo.innerHTML = '&gt; SYSTEM READY <span class="rc-cursor">█</span>';
      overlay.appendChild(listo);
      beep(880, 90);

      setTimeout(() => {
        overlay.textContent = ""; // pantallazo negro breve

        setTimeout(() => {
          const bloqueCara = document.createElement("div");
          bloqueCara.className = "rc-boot-cara";
          const cara = document.createElement("p");
          cara.className = "rc-boot-cara-emoji";
          cara.textContent = ":)";
          bloqueCara.appendChild(cara);
          const frase = document.createElement("p");
          frase.className = "rc-boot-frase";
          frase.textContent = "Estas conectad@ con The Tech Room Arg.";
          bloqueCara.appendChild(frase);
          overlay.appendChild(bloqueCara);
          beep(660, 130);

          setTimeout(() => overlay.classList.add("rc-boot-oculto"), 3200);
        }, 500);
      }, 500);
      return;
    }
    const linea = document.createElement("div");
    linea.textContent = LINEAS[i];
    overlay.appendChild(linea);
    if (LINEAS[i] !== "") beep(620, 70);
    i++;
    setTimeout(siguienteLinea, LINEAS[i - 1] === "" ? 260 : 420);
  }

  siguienteLinea();
})();
