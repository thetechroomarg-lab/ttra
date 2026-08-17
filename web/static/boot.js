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

  overlay.textContent = "";
  let i = 0;

  function siguienteLinea() {
    if (i >= LINEAS.length) {
      const listo = document.createElement("div");
      listo.innerHTML = '&gt; SYSTEM READY <span class="rc-cursor">█</span>';
      overlay.appendChild(listo);

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

          setTimeout(() => overlay.classList.add("rc-boot-oculto"), 3200);
        }, 500);
      }, 500);
      return;
    }
    const linea = document.createElement("div");
    linea.textContent = LINEAS[i];
    overlay.appendChild(linea);
    i++;
    setTimeout(siguienteLinea, LINEAS[i - 1] === "" ? 260 : 420);
  }

  siguienteLinea();
})();
