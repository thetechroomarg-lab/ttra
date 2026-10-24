// Diálogos propios de la web, en el mismo formato que la promo del cargador
// (.ttra-oferta-cargador, ver carrito.css): <dialog> modal con el fondo
// blureado, etiqueta opcional, título, texto y botones. Reemplazan a
// alert()/confirm()/prompt() del navegador en todo el sitio.
// No se descartan con Escape ni tocando afuera: solo con sus botones.
(function () {
  function crearDialogo({ etiqueta, titulo, texto, botones, valor }) {
    const dialog = document.createElement("dialog");
    dialog.className = "ttra-oferta-cargador ttra-dialogo";
    dialog.setAttribute("aria-labelledby", "ttra-dialogo-titulo");
    if (etiqueta) {
      const p = document.createElement("p");
      p.className = "ttra-oferta-cargador-etiqueta";
      p.textContent = etiqueta;
      dialog.append(p);
    }
    const h = document.createElement("h2");
    h.id = "ttra-dialogo-titulo";
    h.textContent = titulo;
    dialog.append(h);
    if (texto) {
      const p = document.createElement("p");
      p.className = "ttra-dialogo-texto";
      p.id = "ttra-dialogo-texto";
      p.textContent = texto;
      dialog.setAttribute("aria-describedby", p.id);
      dialog.append(p);
    }
    if (valor !== undefined) {
      const input = document.createElement("input");
      input.className = "ttra-dialogo-valor";
      input.type = "text";
      input.readOnly = true;
      input.value = valor;
      input.setAttribute("aria-label", titulo);
      input.addEventListener("focus", () => input.select());
      dialog.append(input);
    }
    const acciones = document.createElement("div");
    acciones.className = "ttra-oferta-cargador-acciones";
    if (botones.length === 1) acciones.classList.add("ttra-dialogo-un-boton");
    botones.forEach(({ texto: rotulo, value }) => {
      const boton = document.createElement("button");
      boton.type = "button";
      boton.value = value;
      boton.textContent = rotulo;
      boton.addEventListener("click", () => dialog.close(value));
      acciones.append(boton);
    });
    dialog.append(acciones);
    // Escape no cierra: la decisión se toma con los botones.
    dialog.addEventListener("cancel", (evento) => evento.preventDefault());
    return dialog;
  }

  function mostrar(opciones) {
    return new Promise((resolver) => {
      const dialog = crearDialogo(opciones);
      const foco = document.activeElement;
      dialog.addEventListener("close", () => {
        dialog.remove();
        if (foco && typeof foco.focus === "function") foco.focus();
        resolver(dialog.returnValue);
      });
      document.body.append(dialog);
      dialog.showModal();
      dialog.querySelector('button[value="aceptar"]')?.focus();
    });
  }

  // Pregunta con Aceptar / Cancelar. Resuelve true si acepta.
  window.TTRAConfirmar = async function TTRAConfirmar({ etiqueta, titulo, texto, aceptar = "Aceptar", cancelar = "Cancelar" }) {
    const valor = await mostrar({
      etiqueta, titulo, texto,
      botones: [{ texto: cancelar, value: "cancelar" }, { texto: aceptar, value: "aceptar" }],
    });
    return valor === "aceptar";
  };

  // Aviso con un solo botón. Acepta un texto suelto o las mismas opciones.
  window.TTRAAviso = function TTRAAviso(opciones) {
    const { etiqueta, titulo, texto, boton = "Entendido", valor } =
      typeof opciones === "string" ? { titulo: opciones } : opciones;
    return mostrar({ etiqueta, titulo, texto, valor, botones: [{ texto: boton, value: "aceptar" }] });
  };
  window.avisar = window.TTRAAviso;
})();
