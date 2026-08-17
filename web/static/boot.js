// web/static/boot.js — secuencia de arranque estilo terminal RobCo.
// Se muestra una sola vez por sesión de navegador (sessionStorage).
(function () {
  const YA_MOSTRADO = sessionStorage.getItem("rc_boot_visto") === "1";

  const overlay = document.getElementById("rc-boot");
  if (!overlay) return;

  if (YA_MOSTRADO) {
    overlay.classList.add("rc-boot-oculto");
    return;
  }

  const LINEAS = [
    "THE TECH ROOM ARG",
    "UNIFIED TECHNOLOGY SYSTEM",
    "COPYRIGHT 2009-2077",
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
      sessionStorage.setItem("rc_boot_visto", "1");
      setTimeout(() => overlay.classList.add("rc-boot-oculto"), 1000);
      return;
    }
    const linea = document.createElement("div");
    linea.textContent = LINEAS[i];
    overlay.appendChild(linea);
    i++;
    setTimeout(siguienteLinea, LINEAS[i - 1] === "" ? 130 : 220);
  }

  siguienteLinea();
})();
