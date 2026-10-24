// Panel flotante de confirmación con el look del diálogo de logout
// (.rc-logout-overlay/.rc-logout-tarjeta: fondo blureado y tarjeta con halo).
// No se descarta tocando afuera ni con Escape: solo se sale con sus dos
// botones. Devuelve una promesa que resuelve true (aceptar) o false (cancelar).
(function () {
  let abierto = null;

  function cerrar(resultado) {
    if (!abierto) return;
    const { panel, resolver, foco } = abierto;
    abierto = null;
    panel.remove();
    document.body.classList.remove("dialogo-confirmar-abierto");
    if (foco && typeof foco.focus === "function") foco.focus();
    resolver(resultado);
  }

  window.TTRAConfirmar = function TTRAConfirmar({ titulo, texto = "", aceptar = "Aceptar", cancelar = "Cancelar" }) {
    if (abierto) cerrar(false);
    return new Promise((resolver) => {
      const panel = document.createElement("div");
      panel.className = "rc-logout-overlay visible dialogo-confirmar";
      panel.setAttribute("role", "alertdialog");
      panel.setAttribute("aria-modal", "true");
      panel.setAttribute("aria-labelledby", "dialogo-confirmar-titulo");

      const tarjeta = document.createElement("div");
      tarjeta.className = "rc-logout-tarjeta dialogo-confirmar-tarjeta";
      const h = document.createElement("h2");
      h.id = "dialogo-confirmar-titulo";
      h.textContent = titulo;
      tarjeta.append(h);
      if (texto) {
        const p = document.createElement("p");
        p.className = "dialogo-confirmar-texto";
        p.textContent = texto;
        tarjeta.append(p);
      }
      const acciones = document.createElement("div");
      acciones.className = "rc-logout-acciones dialogo-confirmar-acciones";
      const btnAceptar = document.createElement("button");
      // type="submit": toma el estilo de CTA principal (rojo) de los diálogos.
      btnAceptar.type = "submit";
      btnAceptar.className = "dialogo-confirmar-aceptar";
      btnAceptar.textContent = aceptar;
      btnAceptar.addEventListener("click", () => cerrar(true));
      const btnCancelar = document.createElement("button");
      btnCancelar.type = "button";
      btnCancelar.className = "dialogo-confirmar-cancelar";
      btnCancelar.textContent = cancelar;
      btnCancelar.addEventListener("click", () => cerrar(false));
      acciones.append(btnAceptar, btnCancelar);
      tarjeta.append(acciones);
      panel.append(tarjeta);

      // El foco queda adentro: Tab alterna entre los dos botones.
      panel.addEventListener("keydown", (evento) => {
        if (evento.key === "Escape") evento.preventDefault();
        if (evento.key !== "Tab") return;
        evento.preventDefault();
        (document.activeElement === btnAceptar ? btnCancelar : btnAceptar).focus();
      });
      // Los toques al fondo no llegan a lo de atrás (carrito, perfil).
      panel.addEventListener("pointerdown", (evento) => evento.stopPropagation());

      abierto = { panel, resolver, foco: document.activeElement };
      document.body.append(panel);
      document.body.classList.add("dialogo-confirmar-abierto");
      btnAceptar.focus();
    });
  };
})();
