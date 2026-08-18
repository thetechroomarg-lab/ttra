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

          setTimeout(() => {
            reproducirEstaticaTV(() => overlay.classList.add("rc-boot-oculto"));
          }, 3200);
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

  // Estática breve estilo TV de tubo, solo en esta transición puntual
  // (boot -> landing), en ningún otro lado del sitio.
  function reproducirEstaticaTV(alTerminar) {
    const canvas = document.createElement("canvas");
    canvas.style.position = "fixed";
    canvas.style.inset = "0";
    canvas.style.zIndex = "10001";
    canvas.style.pointerEvents = "none";
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
    document.body.appendChild(canvas);
    const ctx = canvas.getContext("2d");

    const chico = document.createElement("canvas");
    chico.width = 160;
    chico.height = 90;
    const ctxChico = chico.getContext("2d");

    const duracionMs = 260;
    const inicio = performance.now();

    function cuadro(ahora) {
      const imagen = ctxChico.createImageData(chico.width, chico.height);
      for (let i2 = 0; i2 < imagen.data.length; i2 += 4) {
        const v = Math.random() * 255;
        imagen.data[i2] = 0;
        imagen.data[i2 + 1] = v;
        imagen.data[i2 + 2] = v * 0.3;
        imagen.data[i2 + 3] = 255;
      }
      ctxChico.putImageData(imagen, 0, 0);
      ctx.imageSmoothingEnabled = false;
      ctx.drawImage(chico, 0, 0, canvas.width, canvas.height);
      if (ahora - inicio < duracionMs) {
        requestAnimationFrame(cuadro);
      } else {
        canvas.remove();
        alTerminar();
      }
    }
    requestAnimationFrame(cuadro);
  }

  siguienteLinea();
})();
