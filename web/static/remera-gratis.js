// Pop-up de felicitaciones por la remera gratis (ver web/remeras.py).
// Mismo formato que los demás paneles flotantes: <dialog> modal con el fondo
// blureado, sin cerrar con Escape ni tocando afuera. Un solo botón, OK: guarda
// el talle elegido y vuelve al carrito.
(function () {
  const COLORES = ["#ffb21a", "#d52f27", "#ecebe4", "#ffb21a", "#fffdf5"];

  function el(tag, clase, texto) {
    const nodo = document.createElement(tag);
    if (clase) nodo.className = clase;
    if (texto) nodo.textContent = texto;
    return nodo;
  }

  function camiseta() {
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("viewBox", "0 0 160 140");
    svg.setAttribute("class", "ttra-remera-dibujo");
    svg.setAttribute("aria-hidden", "true");
    const cuerpo = document.createElementNS(ns, "path");
    cuerpo.setAttribute("d", "M56 8 L8 30 L22 64 L38 57 V132 H122 V57 L138 64 L152 30 L104 8 C98 22 62 22 56 8 Z");
    cuerpo.setAttribute("class", "ttra-remera-tela");
    svg.append(cuerpo);
    const cuello = document.createElementNS(ns, "path");
    cuello.setAttribute("d", "M56 8 C62 22 98 22 104 8");
    cuello.setAttribute("class", "ttra-remera-cuello");
    svg.append(cuello);
    [["THE", 58], ["TECH", 72], ["ROOM", 86], ["ARG.", 100]].forEach(([texto, y]) => {
      const t = document.createElementNS(ns, "text");
      t.setAttribute("x", "80"); t.setAttribute("y", String(y));
      t.setAttribute("text-anchor", "middle");
      t.setAttribute("class", "ttra-remera-logo");
      t.textContent = texto;
      svg.append(t);
    });
    return svg;
  }

  function confeti() {
    const capa = el("div", "ttra-confeti");
    capa.setAttribute("aria-hidden", "true");
    for (let i = 0; i < 44; i++) {
      const p = el("i");
      p.style.setProperty("--x", `${Math.round(Math.random() * 100)}%`);
      p.style.setProperty("--d", `${(Math.random() * 0.7).toFixed(2)}s`);
      p.style.setProperty("--t", `${(1.9 + Math.random() * 1.3).toFixed(2)}s`);
      p.style.setProperty("--g", `${Math.round(-360 + Math.random() * 720)}deg`);
      p.style.setProperty("--s", `${Math.round(-26 + Math.random() * 52)}px`);
      p.style.background = COLORES[i % COLORES.length];
      capa.append(p);
    }
    setTimeout(() => capa.remove(), 4200);
    return capa;
  }

  // oferta: { pedido_id, talles: [{ talle, disponible }] }. Resuelve true si
  // la remera quedó guardada en el pedido.
  window.TTRARemeraGratis = function TTRARemeraGratis(oferta) {
    return new Promise((resolver) => {
      const dialog = el("dialog", "ttra-oferta-cargador ttra-dialogo ttra-remera");
      dialog.setAttribute("aria-labelledby", "ttra-remera-titulo");
      dialog.setAttribute("aria-describedby", "ttra-remera-texto");
      if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) dialog.append(confeti());
      dialog.append(camiseta());
      const h = el("h2", "", "¡Te ganaste una remera gratis!");
      h.id = "ttra-remera-titulo";
      dialog.append(h);
      const texto = el("p", "ttra-dialogo-texto", "Por tu compra te regalo una remera de The Tech Room Argentina. Elegí tu talle.");
      texto.id = "ttra-remera-texto";
      dialog.append(texto);

      const grupo = el("div", "ttra-remera-talles");
      grupo.setAttribute("role", "radiogroup");
      grupo.setAttribute("aria-label", "Talle de la remera");
      let elegido = null;
      const estado = el("p", "ttra-remera-estado", "Elegí un talle para seguir.");
      estado.setAttribute("role", "status");
      const ok = el("button", "", "OK");
      ok.type = "button";
      ok.value = "aceptar";
      ok.disabled = true;
      oferta.talles.forEach(({ talle, disponible }) => {
        const etiqueta = el("label", "ttra-remera-talle");
        const radio = el("input");
        radio.type = "radio"; radio.name = "talle-remera"; radio.value = talle;
        radio.disabled = !disponible;
        radio.addEventListener("change", () => {
          elegido = talle;
          ok.disabled = false;
          estado.textContent = `Talle ${talle}. La sumo a tu pedido.`;
        });
        etiqueta.append(radio, el("strong", "", talle));
        if (!disponible) etiqueta.append(el("small", "", "Sin stock"));
        grupo.append(etiqueta);
      });
      dialog.append(grupo, estado);

      const acciones = el("div", "ttra-oferta-cargador-acciones ttra-dialogo-un-boton");
      acciones.append(ok);
      dialog.append(acciones);

      ok.addEventListener("click", async () => {
        if (!elegido) return;
        ok.disabled = true;
        ok.textContent = "Guardando…";
        try {
          const r = await fetch(`/api/pedidos/${encodeURIComponent(oferta.pedido_id)}/remera`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ talle: elegido }),
          });
          const cuerpo = await r.json().catch(() => ({}));
          if (!r.ok) {
            estado.textContent = cuerpo.error || "No pude guardar tu talle. Probá de nuevo.";
            ok.disabled = false;
            ok.textContent = "OK";
            return;
          }
          dialog.dataset.guardada = "1";
          dialog.close("aceptar");
        } catch {
          estado.textContent = "No pude guardar tu talle. Revisá tu conexión y probá de nuevo.";
          ok.disabled = false;
          ok.textContent = "OK";
        }
      });
      dialog.addEventListener("cancel", (evento) => evento.preventDefault());
      const foco = document.activeElement;
      dialog.addEventListener("close", () => {
        const guardada = dialog.dataset.guardada === "1";
        dialog.remove();
        if (foco && typeof foco.focus === "function") foco.focus();
        resolver(guardada);
      });
      document.body.append(dialog);
      dialog.showModal();
      dialog.querySelector("input:not(:disabled)")?.focus();
    });
  };
})();
