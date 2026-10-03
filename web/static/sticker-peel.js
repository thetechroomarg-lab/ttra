// Sticker "Hola soy Vlad": se despega desde la esquina doblada (arriba a la
// derecha) arrastrando con el dedo o el mouse. La solapa sigue el puntero en
// ida y vuelta; si no se despega del todo, vuelve a su lugar. Atrás aparece
// la caricatura. Despegado del todo, un toque lo vuelve a pegar.
(function () {
  const sticker = document.querySelector(".ttra-personal-intro");
  if (!sticker || sticker.closest(".ttra-sticker-peel")) return;

  const wrap = document.createElement("div");
  wrap.className = "ttra-sticker-peel";
  sticker.parentNode.insertBefore(wrap, sticker);
  const foto = document.createElement("img");
  foto.className = "ttra-sticker-foto";
  foto.src = "/vlad-caricatura.webp";
  foto.alt = "Caricatura de Vlad";
  foto.decoding = "async";
  const solapa = document.createElement("div");
  solapa.className = "ttra-sticker-solapa";
  solapa.setAttribute("aria-hidden", "true");
  const esquina = document.createElement("button");
  esquina.type = "button";
  esquina.className = "ttra-sticker-esquina";
  esquina.setAttribute("aria-label", "Despegar el sticker");
  wrap.append(foto, sticker, solapa, esquina);

  const ANGULO = (-2 * Math.PI) / 180; // la rotación del wrapper en CSS
  let W = 0, H = 0, P = null, arrastrando = false, despegado = false, anim = 0;

  function medir() { W = sticker.offsetWidth; H = sticker.offsetHeight; }

  // Puntero de pantalla -> coordenadas locales del sticker (sin rotación).
  function local(ev) {
    const r = wrap.getBoundingClientRect();
    const dx = ev.clientX - (r.left + r.width / 2), dy = ev.clientY - (r.top + r.height / 2);
    const c = Math.cos(-ANGULO), s = Math.sin(-ANGULO);
    return { x: dx * c - dy * s + W / 2, y: dx * s + dy * c + H / 2 };
  }

  // Recorta el polígono contra el semiplano f(X) <= 0 (Sutherland–Hodgman).
  function recortar(poli, f) {
    const out = [];
    for (let i = 0; i < poli.length; i++) {
      const a = poli[i], b = poli[(i + 1) % poli.length], fa = f(a), fb = f(b);
      if (fa <= 0) out.push(a);
      if ((fa <= 0) !== (fb <= 0)) {
        const t = fa / (fa - fb);
        out.push({ x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t });
      }
    }
    return out;
  }
  const css = (poli, off = 0) => poli.length ? `polygon(${poli.map((p) => `${p.x + off}px ${p.y + off}px`).join(",")})` : "polygon(0 0)";
  const MARGEN_SOLAPA = 600; // la solapa es más grande que el sticker: el reflejo cae afuera

  function pintar() {
    const C = { x: W, y: 0 };
    if (!P || Math.hypot(P.x - C.x, P.y - C.y) < 2) {
      wrap.classList.remove("despegando");
      sticker.style.clipPath = solapa.style.clipPath = "";
      return;
    }
    wrap.classList.add("despegando");
    const M = { x: (C.x + P.x) / 2, y: (C.y + P.y) / 2 };
    const len = Math.hypot(C.x - P.x, C.y - P.y), n = { x: (C.x - P.x) / len, y: (C.y - P.y) / len };
    const d = (X) => (X.x - M.x) * n.x + (X.y - M.y) * n.y; // > 0: lado que se levanta
    const rect = [{ x: 0, y: 0 }, { x: W, y: 0 }, { x: W, y: H }, { x: 0, y: H }];
    sticker.style.clipPath = css(recortar(rect, d));
    const levantado = recortar(rect, (X) => -d(X));
    const reflejo = levantado.map((X) => { const k = 2 * d(X); return { x: X.x - k * n.x, y: X.y - k * n.y }; });
    solapa.style.clipPath = css(reflejo, MARGEN_SOLAPA);
    // Sombra de la solapa orientada hacia el doblez.
    solapa.style.setProperty("--peel-ang", `${Math.atan2(n.y, n.x) + Math.PI}rad`);
  }

  function animarHasta(destino, alTerminar) {
    cancelAnimationFrame(anim);
    const desde = P || { x: W, y: 0 }, t0 = performance.now(), dur = 380;
    const paso = (t) => {
      const k = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      P = { x: desde.x + (destino.x - desde.x) * e, y: desde.y + (destino.y - desde.y) * e };
      pintar();
      if (k < 1) anim = requestAnimationFrame(paso); else alTerminar && alTerminar();
    };
    anim = requestAnimationFrame(paso);
  }
  const DESPEGADO = () => ({ x: -W * 1.15, y: H * 2.2 });

  esquina.addEventListener("pointerdown", (ev) => {
    if (despegado) return;
    ev.preventDefault();
    cancelAnimationFrame(anim);
    medir();
    arrastrando = true;
    esquina.setPointerCapture(ev.pointerId);
    P = local(ev);
    pintar();
  });
  esquina.addEventListener("pointermove", (ev) => {
    if (!arrastrando) return;
    P = local(ev);
    pintar();
  });
  const soltar = () => {
    if (!arrastrando) return;
    arrastrando = false;
    // Despegado si el doblez ya pasó más de la mitad del sticker.
    const avance = Math.hypot(P.x - W, P.y) / Math.hypot(W, H);
    if (avance > 0.85) {
      animarHasta(DESPEGADO(), () => { despegado = true; wrap.classList.add("despegado"); });
    } else {
      animarHasta({ x: W, y: 0 }, () => { P = null; pintar(); });
    }
  };
  esquina.addEventListener("pointerup", soltar);
  esquina.addEventListener("pointercancel", soltar);

  // Despegado del todo: tocar la foto vuelve a pegar el sticker.
  foto.addEventListener("click", () => {
    if (!despegado) return;
    despegado = false;
    wrap.classList.remove("despegado");
    medir();
    animarHasta({ x: W, y: 0 }, () => { P = null; pintar(); });
  });
  window.addEventListener("resize", () => { medir(); if (despegado) { P = DESPEGADO(); pintar(); } });
  medir();
})();
