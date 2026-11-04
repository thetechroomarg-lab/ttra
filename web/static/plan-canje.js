// Plan Canje: el cliente elige su iPhone, sube las 4 fotos y me llega la
// solicitud (mail con las fotos + WhatsApp armado). Hace falta cuenta: sin
// sesión se abre el login en esta misma página y las fotos se conservan.
const ROTULOS = ['Frente', 'Reverso', 'Costado', 'Batería'];
const fotos = [null, null, null, null];
let enviando = false;

const $ = (id) => document.getElementById(id);
const dialogo = $('canje-dialog');
const selector = $('canje-equipo');
const error = $('canje-error');
const botonEnviar = $('canje-enviar');
let tabla = [];

function mostrarError(texto) { error.textContent = texto || ''; }

// Achica la foto en el teléfono: viaja rápido y entra en el mail.
async function comprimir(archivo) {
  const imagen = await createImageBitmap(archivo);
  const escala = Math.min(1, 1600 / Math.max(imagen.width, imagen.height));
  const lienzo = document.createElement('canvas');
  lienzo.width = Math.round(imagen.width * escala);
  lienzo.height = Math.round(imagen.height * escala);
  lienzo.getContext('2d').drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
  const blob = await new Promise((ok) => lienzo.toBlob(ok, 'image/jpeg', 0.8));
  if (!blob) throw new Error('sin blob');
  return new File([blob], 'foto.jpg', { type: 'image/jpeg' });
}

function pintar() {
  document.querySelectorAll('.canje-slot').forEach((boton) => {
    const i = Number(boton.dataset.slot);
    const foto = fotos[i];
    boton.classList.toggle('con-foto', Boolean(foto));
    boton.querySelector('img')?.remove();
    boton.querySelector('.canje-slot-vacio').hidden = Boolean(foto);
    if (foto) {
      const img = document.createElement('img');
      img.alt = `${ROTULOS[i]} de tu iPhone`;
      img.src = foto.vista;
      boton.prepend(img);
    }
    boton.setAttribute('aria-label', foto ? `Cambiar la foto: ${ROTULOS[i]}` : `Agregar la foto: ${ROTULOS[i]}`);
  });
  const equipo = tabla.find((fila) => fila.id === selector.value);
  $('canje-valor').textContent = equipo ? `Te lo tomo a US$ ${equipo.valor_usd.toLocaleString('es-AR')}` : '';
  botonEnviar.disabled = enviando || !equipo || fotos.some((f) => !f);
}

async function cargarFoto(i, archivo) {
  try {
    const comprimida = await comprimir(archivo);
    if (fotos[i]) URL.revokeObjectURL(fotos[i].vista);
    fotos[i] = { archivo: comprimida, vista: URL.createObjectURL(comprimida) };
    mostrarError('');
  } catch {
    mostrarError('No pude leer esa foto. Probá con otra.');
  }
}

async function cargarTabla() {
  if (tabla.length) return;
  try {
    const r = await fetch('/api/canje/tabla');
    tabla = r.ok ? await r.json() : [];
  } catch { tabla = []; }
  selector.append(...tabla.map((fila) => new Option(`${fila.modelo} · ${fila.capacidad}`, fila.id)));
}

async function abrirPanel() {
  await cargarTabla();
  $('canje-formulario').hidden = false;
  $('canje-listo').hidden = true;
  mostrarError('');
  pintar();
  if (!dialogo.open) dialogo.showModal();
}

// El botón de la página abre la cámara o la galería; las fotos elegidas se
// reparten en orden entre los huecos libres (frente, reverso, costado, batería).
$('canje-abrir').addEventListener('click', () => $('canje-archivos').click());
$('canje-archivos').addEventListener('change', async (evento) => {
  const elegidos = [...evento.target.files];
  evento.target.value = '';
  if (!elegidos.length) return;
  await abrirPanel();
  for (const archivo of elegidos) {
    const libre = fotos.findIndex((f) => !f);
    if (libre === -1) break;
    await cargarFoto(libre, archivo);
  }
  pintar();
});

let slotActivo = 0;
document.querySelectorAll('.canje-slot').forEach((boton) => boton.addEventListener('click', () => {
  slotActivo = Number(boton.dataset.slot);
  $('canje-archivo-uno').click();
}));
$('canje-archivo-uno').addEventListener('change', async (evento) => {
  const archivo = evento.target.files[0];
  evento.target.value = '';
  if (archivo) await cargarFoto(slotActivo, archivo);
  pintar();
});
selector.addEventListener('change', pintar);

function cerrarPanel() {
  dialogo.close();
}
$('canje-cancelar').addEventListener('click', cerrarPanel);
$('canje-cerrar').addEventListener('click', () => {
  fotos.forEach((f, i) => { if (f) URL.revokeObjectURL(f.vista); fotos[i] = null; });
  selector.value = '';
  cerrarPanel();
});

async function hayCuenta() {
  try { return (await fetch('/api/me', { cache: 'no-store' })).ok; } catch { return false; }
}

async function enviar() {
  if (enviando) return;
  mostrarError('');
  if (!(await hayCuenta())) {
    // Sin cuenta: login o registro sobre esta página y, al volver, se envía.
    const { abrirLoginEnPagina } = await import('/login-drawer.js');
    dialogo.close();
    abrirLoginEnPagina($('canje-abrir'), async () => { await abrirPanel(); enviar(); });
    return;
  }
  enviando = true;
  botonEnviar.textContent = 'Enviando…';
  pintar();
  const datos = new FormData();
  datos.append('equipo', selector.value);
  fotos.forEach((f, i) => datos.append('fotos', f.archivo, `${i + 1}.jpg`));
  try {
    const r = await fetch('/api/canje/solicitudes', { method: 'POST', body: datos });
    const cuerpo = await r.json().catch(() => ({}));
    if (r.status === 401) { enviando = false; botonEnviar.textContent = 'Enviar'; return enviar(); }
    if (!r.ok) throw new Error(cuerpo.error || cuerpo.detail || 'No pude enviar tu solicitud. Probá de nuevo.');
    $('canje-whatsapp').href = cuerpo.whatsapp_url;
    $('canje-formulario').hidden = true;
    $('canje-listo').hidden = false;
    // Igual que al confirmar un pedido: se abre WhatsApp con el mensaje armado.
    window.open(cuerpo.whatsapp_url, '_blank', 'noopener');
  } catch (e) {
    mostrarError(e.message || 'No pude enviar tu solicitud. Probá de nuevo.');
  } finally {
    enviando = false;
    botonEnviar.textContent = 'Enviar';
    pintar();
  }
}
botonEnviar.addEventListener('click', enviar);
