// Host the existing checkout without navigating or replacing the current page.
let dialog;
export function abrirCarritoEnPagina(trigger) {
  if (dialog?.open) return;
  dialog = document.createElement('dialog');
  dialog.className = 'ttra-cart-dialog';
  dialog.dataset.ttraCart = '';
  dialog.setAttribute('aria-label', 'Tu pedido');
  const status = document.createElement('div');
  status.className = 'ttra-cart-loading';
  status.innerHTML = '<p role="status">Estoy cargando tu carrito…</p><button type="button">Cerrar carrito</button>';
  const frame = document.createElement('iframe');
  frame.title = 'Carrito de compras';
  frame.src = '/?panel=carrito&embed=carrito';
  dialog.append(frame, status);
  document.body.append(dialog);
  const timeout = setTimeout(() => {
    status.querySelector('p').textContent = 'No pude cargar el carrito. Cerralo y probá de nuevo.';
  }, 15000);
  function close() { dialog.close(); }
  function message(event) {
    if (event.origin !== location.origin || event.source !== frame.contentWindow) return;
    if (event.data?.type === 'ttra:cart-ready') {
      clearTimeout(timeout);
      status.hidden = true;
      frame.focus();
    }
    if (event.data?.type === 'ttra:cart-close') close();
  }
  status.querySelector('button').addEventListener('click', close);
  window.addEventListener('message', message);
  dialog.addEventListener('close', () => {
    clearTimeout(timeout);
    window.removeEventListener('message', message);
    dialog.remove();
    trigger.focus({preventScroll:true});
    window.dispatchEvent(new Event('ttra:cart-change'));
  }, {once:true});
  // Lock before native dialog autofocus can move the document's scroll.
  dialog.dataset.opening = '';
  document.dispatchEvent(new Event('ttra:overlay-change'));
  dialog.showModal();
  delete dialog.dataset.opening;
}
