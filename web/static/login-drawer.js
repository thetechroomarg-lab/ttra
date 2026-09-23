// Host the login/registro form without navigating away from the current page.
let dialog;
export function abrirLoginEnPagina(trigger, onDone) {
  if (dialog?.open) return;
  dialog = document.createElement('dialog');
  dialog.className = 'ttra-login-dialog';
  dialog.setAttribute('aria-label', 'Ingresar');
  const status = document.createElement('div');
  status.className = 'ttra-login-loading';
  status.innerHTML = '<p role="status">Estoy cargando el ingreso…</p><button type="button">Cerrar</button>';
  const frame = document.createElement('iframe');
  frame.title = 'Ingresar a tu cuenta';
  const volver = new URLSearchParams({ volver: location.pathname + location.search, embed: 'login' });
  frame.src = `/login.html?${volver}`;
  dialog.append(frame, status);
  document.body.append(dialog);
  const timeout = setTimeout(() => {
    status.querySelector('p').textContent = 'No pude cargar el ingreso. Cerralo y probá de nuevo.';
  }, 15000);
  let logueado = false;
  function close() { dialog.close(); }
  function message(event) {
    if (event.origin !== location.origin || event.source !== frame.contentWindow) return;
    if (event.data?.type === 'ttra:login-done') { logueado = true; close(); }
    if (event.data?.type === 'ttra:login-close') close();
  }
  status.querySelector('button').addEventListener('click', close);
  window.addEventListener('message', message);
  dialog.addEventListener('load', () => {
    clearTimeout(timeout);
    status.hidden = true;
  }, { once: true, capture: true });
  frame.addEventListener('load', () => {
    clearTimeout(timeout);
    status.hidden = true;
    frame.focus();
  });
  dialog.addEventListener('close', () => {
    clearTimeout(timeout);
    window.removeEventListener('message', message);
    dialog.remove();
    trigger.focus({ preventScroll: true });
    if (logueado) onDone?.();
  }, { once: true });
  // Lock before native dialog autofocus can move the document's scroll.
  dialog.dataset.opening = '';
  document.dispatchEvent(new Event('ttra:overlay-change'));
  dialog.showModal();
  delete dialog.dataset.opening;
}
