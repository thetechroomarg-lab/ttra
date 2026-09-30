// One cart format for catalog cards and the existing checkout panel.
(() => {
  const key = 'ttra_carrito';
  let feedbackTimer;

  function leer() {
    const cart = JSON.parse(localStorage.getItem(key) || '[]');
    if (!Array.isArray(cart)) throw new Error('Carrito inválido');
    return cart;
  }

  function notificar(message, error = false) {
    let feedback = document.getElementById('ttra-cart-feedback');
    if (!feedback) {
      feedback = document.createElement('div');
      feedback.id = 'ttra-cart-feedback';
      feedback.className = 'ttra-cart-feedback';
      feedback.setAttribute('role', 'status');
      feedback.setAttribute('aria-live', 'polite');
      document.body.appendChild(feedback);
    }
    clearTimeout(feedbackTimer);
    feedback.textContent = message;
    feedback.classList.toggle('is-error', error);
    feedback.classList.add('is-visible');
    feedbackTimer = setTimeout(() => feedback.classList.remove('is-visible'), error ? 6000 : 2600);
  }

  function agregar(producto, color) {
    const cart = leer();
    const withoutVariants = !Array.isArray(producto.colores) || producto.colores.length === 0;
    const normalizeColor = (value) => withoutVariants && value === 'Color único' ? null : (value || null);
    const selectedColor = normalizeColor(color);
    const existing = cart.find((item) => item.nombre === producto.nombre && normalizeColor(item.color) === selectedColor);
    if (existing) {
      existing.cantidad = (Number(existing.cantidad) || 0) + 1;
      existing.color = selectedColor;
    } else {
      cart.push({
        nombre: producto.nombre,
        color: selectedColor,
        usd: producto.usd,
        pesos: producto.pesos,
        transferencia: producto.transferencia,
        cantidad: 1,
      });
    }
    // Persist first: no successful feedback or animation if storage fails.
    localStorage.setItem(key, JSON.stringify(cart));
    window.dispatchEvent(new Event('ttra:cart-change'));
    window.dispatchEvent(new Event('ttra:cart-added'));
    notificar(`${producto.nombre} agregado al carrito.`);
    return cart;
  }

  async function animar(source) {
    if (!source || document.documentElement.dataset.modo !== 'classic' ||
        window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const target = document.querySelector('.ttra-site-cart, #btn-carrito');
    if (!target || typeof source.animate !== 'function') return;
    const from = source.getBoundingClientRect();
    const to = (target.querySelector('svg') || target).getBoundingClientRect();
    if (!from.width || !from.height || !to.width) return;
    const x = to.left + to.width / 2;
    const y = to.top + to.height / 2;
    const dx = x - from.left - from.width / 2;
    const dy = y - from.top - from.height / 2;
    const ghost = source.cloneNode(true);
    ghost.removeAttribute('id');
    ghost.querySelectorAll('[id], [name]').forEach((element) => {
      element.removeAttribute('id');
      element.removeAttribute('name');
    });
    ghost.classList.add('ttra-cart-flight');
    ghost.setAttribute('aria-hidden', 'true');
    ghost.inert = true;
    Object.assign(ghost.style, {
      left: `${from.left}px`, top: `${from.top}px`,
      width: `${from.width}px`, height: `${from.height}px`,
    });
    const portal = document.createElement('div');
    portal.className = 'ttra-cart-portal';
    portal.setAttribute('aria-hidden', 'true');
    portal.style.left = `${x - 36}px`;
    portal.style.top = `${y - 36}px`;
    document.body.append(ghost, portal);
    source.classList.add('ttra-card-adding');
    try {
      const absorb = ghost.animate([
        { transform: 'translate(0, 0) rotate(0) scale(1)', opacity: 1, filter: 'blur(0)' },
        { transform: `translate(${dx * .18}px, ${dy * .35 - 35}px) rotate(-8deg) scale(.72)`, opacity: .95, offset: .35 },
        { transform: `translate(${dx * .84}px, ${dy * .9}px) rotate(14deg) scale(.17)`, opacity: .85, filter: 'blur(1px)', offset: .8 },
        { transform: `translate(${dx}px, ${dy}px) rotate(42deg) scale(.005)`, opacity: 0, filter: 'blur(3px)' },
      ], { duration: 760, easing: 'cubic-bezier(.4, 0, .65, 1)', fill: 'forwards' });
      const vortex = portal.animate([
        { transform: 'scale(.1) rotate(0deg)', opacity: 0 },
        { transform: 'scale(1) rotate(100deg)', opacity: .95, offset: .45 },
        { transform: 'scale(.95) rotate(220deg)', opacity: 1, offset: .8 },
        { transform: 'scale(0) rotate(300deg)', opacity: 0 },
      ], { duration: 900, easing: 'ease-in-out', fill: 'forwards' });
      await Promise.all([absorb.finished, vortex.finished]);
      target.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.12)' }, { transform: 'scale(1)' }], { duration: 220 });
    } catch {
      // Visual effects must never prevent an already-saved addition.
    } finally {
      ghost.remove();
      portal.remove();
      source.classList.remove('ttra-card-adding');
    }
  }

  window.TTRACarrito = { leer, agregar, animar, notificar };
})();
