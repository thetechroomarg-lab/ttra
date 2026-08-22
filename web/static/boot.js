// web/static/boot.js — secuencia de arranque estilo terminal RobCo.
// Cada carga/recarga de página entra siempre en Modo Classic (sin boot
// sequence); la animación solo se reproduce cuando el usuario cambia a
// Modo Fallout en vivo con el botón (ver window.reproducirBootSequenceTTRA,
// usado desde landing.js).

// Beeps estilo computadora vieja (onda cuadrada sintetizada, sin archivos de
// audio). Los navegadores bloquean audio autoplay sin gesto del usuario: si
// el contexto queda suspendido, el beep simplemente no suena, sin romper nada.
let audioCtxBoot;
function beepBoot(frecuencia, duracionMs) {
  try {
    audioCtxBoot = audioCtxBoot || new (window.AudioContext || window.webkitAudioContext)();
    if (audioCtxBoot.state === "suspended") audioCtxBoot.resume();
    const osc = audioCtxBoot.createOscillator();
    const gain = audioCtxBoot.createGain();
    osc.type = "square";
    osc.frequency.value = frecuencia;
    gain.gain.setValueAtTime(0.05, audioCtxBoot.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.0001, audioCtxBoot.currentTime + duracionMs / 1000);
    osc.connect(gain).connect(audioCtxBoot.destination);
    osc.start();
    osc.stop(audioCtxBoot.currentTime + duracionMs / 1000);
  } catch {
    // Web Audio no disponible: seguimos sin sonido, no es crítico.
  }
}

// Estática breve estilo TV de tubo, solo en la transición boot -> landing.
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

// Reproduce la secuencia de arranque completa sobre `overlay` y llama a
// `alTerminar` cuando termina (estática de TV incluida). Reutilizable tanto
// en la carga inicial de página como al cambiar a Modo Fallout en vivo.
function reproducirBootCompleto(overlay, alTerminar) {
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

  overlay.classList.remove("rc-boot-oculto");
  overlay.textContent = "";
  let i = 0;

  function siguienteLinea() {
    if (i >= LINEAS.length) {
      const listo = document.createElement("div");
      listo.innerHTML = '&gt; SYSTEM READY <span class="rc-cursor">█</span>';
      overlay.appendChild(listo);
      beepBoot(880, 90);

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
          beepBoot(660, 130);

          setTimeout(() => {
            reproducirEstaticaTV(() => {
              overlay.classList.add("rc-boot-oculto");
              alTerminar();
            });
          }, 3200);
        }, 500);
      }, 500);
      return;
    }
    const linea = document.createElement("div");
    linea.textContent = LINEAS[i];
    overlay.appendChild(linea);
    if (LINEAS[i] !== "") beepBoot(620, 70);
    i++;
    setTimeout(siguienteLinea, LINEAS[i - 1] === "" ? 260 : 420);
  }

  siguienteLinea();
}

// Punto de entrada usado por landing.js al cambiar a Modo Fallout en vivo.
window.reproducirBootSequenceTTRA = function (alTerminar) {
  const overlay = document.getElementById("rc-boot");
  const terminar = alTerminar || function () {};
  if (!overlay) {
    terminar();
    return;
  }
  reproducirBootCompleto(overlay, terminar);
};

// Registro del service worker (ver sw.js): habilita el cartel de "instalar
// como app" del navegador. Sin caché propia adentro, así nunca sirve
// precios/catálogo/JS viejos — solo existe para cumplir el requisito de
// instalación de una PWA.
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("/sw.js").catch(() => {
    // Si falla el registro, el sitio sigue funcionando igual sin ser
    // instalable: no es crítico.
  });
}

(function () {
  const overlay = document.getElementById("rc-boot");
  if (!overlay) return;

  // Classic es siempre el modo de arranque: cada carga/recarga de página
  // entra ahí, sin boot sequence, sin importar qué modo se haya elegido
  // antes. Fallout solo se activa en vivo con el botón, y dura hasta el
  // próximo refresh.
  document.documentElement.setAttribute("data-modo", "classic");
  overlay.classList.add("rc-boot-oculto");
  const portada = document.getElementById("rc-portada-ingreso");
  const btnPortada = document.getElementById("btn-portada-ingreso");
  const tituloPortada = portada ? portada.querySelector(".rc-portada-ingreso-titulo") : null;
  const ctaPortada = portada ? portada.querySelector(".rc-portada-ingreso-cta") : null;
  if (portada && btnPortada) {
    document.body.classList.add("rc-portada-activa");
    const mostrarTextoPortada = () => {
      window.setTimeout(() => {
        if (tituloPortada) tituloPortada.classList.add("visible");
        window.setTimeout(() => {
          if (ctaPortada) ctaPortada.classList.add("visible");
        }, 3400);
      }, 1500);
    };
    const imagenPortada = new Image();
    imagenPortada.onload = mostrarTextoPortada;
    imagenPortada.onerror = mostrarTextoPortada;
    imagenPortada.src = "/texturas/cordoba%20city.jpg";
    if (imagenPortada.complete) mostrarTextoPortada();
    btnPortada.addEventListener("click", () => {
      document.body.classList.add("rc-portada-saliendo");
      portada.classList.add("oculto");
      window.setTimeout(() => {
        document.body.classList.remove("rc-portada-activa");
        document.body.classList.remove("rc-portada-saliendo");
      }, 700);
    });
  }
  return;

  reproducirBootCompleto(overlay, () => {});
})();
