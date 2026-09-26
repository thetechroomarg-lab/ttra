// Host the home's floating panels (carrito, perfil, pedidos) without leaving the current page.
const PANELES = {
  carrito: { etiqueta: 'Tu pedido', titulo: 'Carrito de compras', cargando: 'Estoy cargando tu carrito…', cerrar: 'Cerrar carrito', error: 'No pude cargar el carrito. Cerralo y probá de nuevo.' },
  perfil: { etiqueta: 'Mi perfil', titulo: 'Mi perfil', cargando: 'Estoy cargando tu perfil…', cerrar: 'Cerrar perfil', error: 'No pude cargar tu perfil. Cerralo y probá de nuevo.' },
  pedidos: { etiqueta: 'Mis pedidos', titulo: 'Mis pedidos', cargando: 'Estoy cargando tus pedidos…', cerrar: 'Cerrar pedidos', error: 'No pude cargar tus pedidos. Cerralo y probá de nuevo.' },
};
let dialog;
export function abrirCarritoEnPagina(trigger) {
  abrirPanelEnPagina(trigger, 'carrito');
}
export function abrirPanelEnPagina(trigger, panel) {
  if (dialog?.open) return;
  const textos = PANELES[panel];
  dialog = document.createElement('dialog');
  dialog.className = 'ttra-cart-dialog';
  dialog.dataset.ttraCart = '';
  dialog.setAttribute('aria-label', textos.etiqueta);
  const status = document.createElement('div');
  status.className = 'ttra-cart-loading';
  status.innerHTML = `<p role="status">${textos.cargando}</p><button type="button">${textos.cerrar}</button>`;
  const frame = document.createElement('iframe');
  frame.title = textos.titulo;
  frame.src = `/?panel=${panel}&embed=${panel}`;
  dialog.append(frame, status);
  document.body.append(dialog);
  const timeout = setTimeout(() => {
    status.querySelector('p').textContent = textos.error;
  }, 15000);
  let pedirLogin = false;
  function close() { dialog.close(); }
  function message(event) {
    if (event.origin !== location.origin || event.source !== frame.contentWindow) return;
    if (event.data?.type === 'ttra:cart-ready') {
      clearTimeout(timeout);
      status.hidden = true;
      frame.focus();
    }
    if (event.data?.type === 'ttra:cart-close') close();
    // Sesión vencida: login en su modal y, al entrar, el mismo panel de nuevo.
    if (event.data?.type === 'ttra:panel-login') { pedirLogin = true; close(); }
  }
  status.querySelector('button').addEventListener('click', close);
  window.addEventListener('message', message);
  dialog.addEventListener('close', () => {
    clearTimeout(timeout);
    window.removeEventListener('message', message);
    dialog.remove();
    trigger.focus({preventScroll:true});
    window.dispatchEvent(new Event('ttra:cart-change'));
    if (pedirLogin) {
      import('/login-drawer.js').then(({ abrirLoginEnPagina }) => {
        abrirLoginEnPagina(trigger, () => {
          window.dispatchEvent(new Event('ttra:session-change'));
          abrirPanelEnPagina(trigger, panel);
        });
      });
    }
  }, {once:true});
  // Lock before native dialog autofocus can move the document's scroll.
  dialog.dataset.opening = '';
  document.dispatchEvent(new Event('ttra:overlay-change'));
  dialog.showModal();
  delete dialog.dataset.opening;
}
