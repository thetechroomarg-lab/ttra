// web/static/boot.js — secuencia de arranque estilo terminal RobCo.
// Se muestra en cada carga de página (F5 incluido).
(function () {
  const overlay = document.getElementById("rc-boot");
  if (!overlay) return;

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

  // Cara pixelada (anillo + ojos + sonrisa) generada por geometría, no a mano,
  // para asegurar que quede simétrica sin importar el tamaño de grilla elegido.
  function construirCaraPixel() {
    const COLS = 17;
    const FILAS = 17;
    const cx = 8;
    const cy = 8;
    const grid = document.createElement("div");
    grid.className = "rc-cara-pixel";
    grid.style.setProperty("--rc-cara-cols", COLS);
    for (let y = 0; y < FILAS; y++) {
      for (let x = 0; x < COLS; x++) {
        const dx = x - cx;
        const dy = y - cy;
        const dist = Math.sqrt(dx * dx + dy * dy);
        let on = dist >= 7.0 && dist <= 8.3; // anillo de la cara

        const esOjo = (x === 5 || x === 11) && y >= 6 && y <= 8;
        if (esOjo) on = true;

        const dxBoca = x - cx;
        const dyBoca = y - 10;
        const distBoca = Math.sqrt(dxBoca * dxBoca + dyBoca * dyBoca);
        const esBoca = y >= 10 && y <= 12 && distBoca >= 3.0 && distBoca <= 3.8;
        if (esBoca) on = true;

        const celda = document.createElement("span");
        if (on) celda.className = "on";
        grid.appendChild(celda);
      }
    }
    return grid;
  }

  overlay.textContent = "";
  let i = 0;

  function siguienteLinea() {
    if (i >= LINEAS.length) {
      const listo = document.createElement("div");
      listo.innerHTML = '&gt; SYSTEM READY <span class="rc-cursor">█</span>';
      overlay.appendChild(listo);

      const bloqueCara = document.createElement("div");
      bloqueCara.className = "rc-boot-cara";
      bloqueCara.appendChild(construirCaraPixel());
      const frase = document.createElement("p");
      frase.className = "rc-boot-frase";
      frase.textContent = "Estas conectad@ con The Tech Room Arg.";
      bloqueCara.appendChild(frase);
      overlay.appendChild(bloqueCara);

      setTimeout(() => overlay.classList.add("rc-boot-oculto"), 2400);
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
