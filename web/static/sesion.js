/* Sesión del cliente, consultada una sola vez por página. Los easter eggs
   (gatitos, puerta del header, pescador, sticker despegable, punto rojo) son
   solo para clientes logueados: esperan window.TTRASesion y, si no hay
   sesión, ni se cargan. Con sesión, <html> lleva la clase ttra-logueado. */
window.TTRASesion = fetch('/api/me', { cache: 'no-store' })
  .then((response) => {
    if (response.ok) document.documentElement.classList.add('ttra-logueado');
    return response.ok;
  })
  .catch(() => false);
