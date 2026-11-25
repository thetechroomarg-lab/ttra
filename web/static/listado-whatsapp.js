// LISTADO WHATSAPP (solo mayoristas): arma tres listados listos para pegar en
// WhatsApp, a partir de los dólares que manda /api/listado-whatsapp. Los pesos
// se calculan acá, con el dólar de la página o con el que escriba el mayorista.
(function () {
  'use strict';

  // Misma regla que precios.js: la transferencia en pesos suma el 3% (pesos / 0,97).
  var DIVISOR_TRANSFERENCIA = 0.97;
  // WhatsApp acepta ~65.000 caracteres por mensaje; se corta antes, entre marcas.
  var MAX_CARACTERES = 55000;
  var DOLAR_MINIMO = 100;
  var DOLAR_MAXIMO = 100000;

  var COLUMNAS = [
    {
      id: 'mayorista', campo: 'a', titulo: 'Armá tu listado',
      detalle: 'Elegís cuánto querés ganar en cada rango de precio. Le sumo ese monto a tu precio mayorista y el listado se arma solo. Con US$ 0 queda tal cual tu catálogo.',
    },
    {
      id: 'publico', campo: 'b', titulo: 'Al precio que vendo yo',
      detalle: 'Mi precio de venta al público, sin cambios. Si vendés a este precio, tu ganancia es la diferencia con lo que me pagás a mí.',
    },
    {
      id: 'ganancia', campo: 'c', titulo: 'Un poco más caro que yo',
      detalle: 'Mi precio de venta más US$ 10 (productos de hasta US$ 499) o US$ 15 (desde US$ 500). Para vender por encima de mi precio con una ganancia ya incluida. Ideal para revender en el interior.',
    },
  ];

  var TRAMO_USD = 300;
  var GANANCIA_MAXIMA = 5000;

  // ---------- Lógica pura (se prueba con node) ----------

  var formatoEntero = new Intl.NumberFormat('es-AR', { maximumFractionDigits: 0 });

  function formatearPesos(valor) { return '$' + formatoEntero.format(valor); }
  function formatearUsd(valor) { return 'US$ ' + formatoEntero.format(valor); }

  // "1.800", "1800", "1800,50" o "$ 1.800" -> número; cualquier otra cosa -> null.
  function leerDolar(texto) {
    var limpio = String(texto == null ? '' : texto).replace(/[^\d.,]/g, '');
    if (!limpio) return null;
    if (limpio.indexOf(',') !== -1) limpio = limpio.replace(/\./g, '').replace(',', '.');
    else if (/^\d{1,3}(\.\d{3})+$/.test(limpio)) limpio = limpio.replace(/\./g, '');
    var valor = Number(limpio);
    return isFinite(valor) && valor > 0 ? valor : null;
  }

  function dolarEsPlausible(valor) {
    return valor >= DOLAR_MINIMO && valor <= DOLAR_MAXIMO;
  }

  // WhatsApp da formato a *, _, ~ y ` y a las líneas que arrancan con - * > o "1. ".
  function limpiarTexto(texto) {
    return String(texto)
      .replace(/[*_~`]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .replace(/^([-*>•]+|\d+[.)])\s*/, '');
  }

  function fechaLarga(fecha) {
    return new Intl.DateTimeFormat('es-AR', {
      timeZone: 'America/Argentina/Buenos_Aires', day: 'numeric', month: 'long', year: 'numeric',
    }).format(fecha);
  }

  function precios(usd, dolar) {
    var pesos = Math.round(usd * dolar);
    return { usd: usd, pesos: pesos, transferencia: Math.round(pesos / DIVISOR_TRANSFERENCIA) };
  }

  function encabezado(opciones) {
    var lineas = [];
    var nombre = limpiarTexto(opciones.nombre || '');
    if (nombre) lineas.push('*' + nombre.toUpperCase() + '*');
    lineas.push('📅 ' + fechaLarga(opciones.fecha));
    lineas.push('💵 Dólar: ' + formatearPesos(opciones.dolar) + ' (puede variar sin previo aviso)');
    lineas.push('📄 Precios en dólares, pesos contado y transferencia en pesos');
    lineas.push('🇺🇸 Dólar billete · 🇦🇷 Pesos contado · 🏦 Transferencia en pesos');
    return lineas.join('\n');
  }

  function bloqueProducto(item, campo, dolar) {
    var p = precios(item[campo], dolar);
    return limpiarTexto(item.n) + '\n' +
      '🇺🇸 ' + formatearUsd(p.usd) + ' · 🇦🇷 ' + formatearPesos(p.pesos) + ' · 🏦 ' + formatearPesos(p.transferencia);
  }

  // Cada bloque de marca arranca con su título en negrita; un bloque nunca se parte
  // salvo que por sí solo supere el máximo.
  function bloquesDeMarca(seccion, grupo, campo, dolar) {
    var titulo = '*⚫ ' + limpiarTexto(seccion.seccion) + ' · ' + limpiarTexto(grupo.titulo) + '*';
    var partes = [];
    var actual = [titulo];
    var largo = titulo.length;
    grupo.items.forEach(function (item) {
      var texto = bloqueProducto(item, campo, dolar);
      if (largo + texto.length + 2 > MAX_CARACTERES / 2 && actual.length > 1) {
        partes.push(actual.join('\n\n'));
        actual = [titulo];
        largo = titulo.length;
      }
      actual.push(texto);
      largo += texto.length + 2;
    });
    partes.push(actual.join('\n\n'));
    return partes;
  }

  // Devuelve la lista de mensajes (casi siempre uno) de una columna.
  function armarMensajes(secciones, campo, dolar, opciones) {
    var cabecera = encabezado({ nombre: opciones.nombre, dolar: dolar, fecha: opciones.fecha });
    var bloques = [];
    secciones.forEach(function (seccion) {
      seccion.grupos.forEach(function (grupo) {
        bloquesDeMarca(seccion, grupo, campo, dolar).forEach(function (b) { bloques.push(b); });
      });
    });
    var mensajes = [];
    var actual = [];
    var largo = 0;
    bloques.forEach(function (bloque) {
      if (largo + bloque.length + 2 > MAX_CARACTERES - cabecera.length - 40 && actual.length) {
        mensajes.push(actual);
        actual = [];
        largo = 0;
      }
      actual.push(bloque);
      largo += bloque.length + 2;
    });
    if (actual.length) mensajes.push(actual);
    var total = mensajes.length;
    return mensajes.map(function (cuerpo, i) {
      var parte = total > 1 ? '\n(parte ' + (i + 1) + ' de ' + total + ')' : '';
      return cabecera + parte + '\n\n' + cuerpo.join('\n\n');
    });
  }

  // Rangos de US$ 300 según el precio mayorista: 0 a 300, 301 a 600, etc.
  function rangoDe(usd) { return usd <= 0 ? 0 : Math.ceil(usd / TRAMO_USD) - 1; }

  function etiquetaRango(indice) {
    var desde = indice === 0 ? 0 : indice * TRAMO_USD + 1;
    return 'US$ ' + formatoEntero.format(desde) + ' a ' + formatoEntero.format((indice + 1) * TRAMO_USD);
  }

  // Solo los rangos que tienen productos, con cuántos son.
  function rangos(secciones) {
    var cuenta = {};
    secciones.forEach(function (s) {
      s.grupos.forEach(function (g) {
        g.items.forEach(function (item) {
          var i = rangoDe(item.a);
          cuenta[i] = (cuenta[i] || 0) + 1;
        });
      });
    });
    return Object.keys(cuenta).map(Number).sort(function (x, y) { return x - y; }).map(function (i) {
      return { indice: i, etiqueta: etiquetaRango(i), cantidad: cuenta[i] };
    });
  }

  // "150", "US$ 150" -> 150; vacío o basura -> 0; nunca negativo ni mayor al máximo.
  function leerGanancia(texto) {
    var digitos = String(texto == null ? '' : texto).replace(/\D/g, '');
    if (!digitos) return 0;
    return Math.min(Number(digitos), GANANCIA_MAXIMA);
  }

  // Copia del listado con la ganancia elegida sumada al precio mayorista (campo a).
  // El rango se decide por el precio mayorista original.
  function conGanancias(secciones, ganancias) {
    return secciones.map(function (s) {
      return {
        seccion: s.seccion,
        grupos: s.grupos.map(function (g) {
          return {
            titulo: g.titulo,
            items: g.items.map(function (item) {
              var extra = ganancias[rangoDe(item.a)] || 0;
              return { n: item.n, a: item.a + extra, b: item.b, c: item.c };
            }),
          };
        }),
      };
    });
  }

  function contarProductos(secciones) {
    return secciones.reduce(function (suma, s) {
      return suma + s.grupos.reduce(function (n, g) { return n + g.items.length; }, 0);
    }, 0);
  }

  var api = {
    COLUMNAS: COLUMNAS, MAX_CARACTERES: MAX_CARACTERES,
    leerDolar: leerDolar, dolarEsPlausible: dolarEsPlausible, limpiarTexto: limpiarTexto,
    precios: precios, encabezado: encabezado, armarMensajes: armarMensajes,
    contarProductos: contarProductos, formatearPesos: formatearPesos,
    rangoDe: rangoDe, rangos: rangos, etiquetaRango: etiquetaRango,
    leerGanancia: leerGanancia, conGanancias: conGanancias,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (typeof document === 'undefined') return;
  window.ListadoWhatsapp = api;

  // ---------- Página ----------

  var CLAVE_NOMBRE = 'ttra_listado_nombre';
  var estado = { secciones: [], dolarPagina: 0, nombre: '', dolarPropio: null, ganancias: {} };
  var guardado = { temporizador: 0, pendiente: false, elTexto: null };
  var temporizadores = new WeakMap();

  var $ = function (id) { return document.getElementById(id); };
  var elNombre = $('lw-nombre');
  var elDolar = $('lw-dolar');
  var elAyudaDolar = $('lw-dolar-ayuda');
  var elColumnas = $('lw-columnas');
  var elEstado = $('lw-estado');
  var elAnuncio = $('lw-anuncio');

  function leerAlmacen(clave) {
    try { return window.localStorage.getItem(clave) || ''; } catch (e) { return ''; }
  }
  function guardarAlmacen(clave, valor) {
    try { window.localStorage.setItem(clave, valor); } catch (e) { /* sin storage: no se recuerda */ }
  }

  function dolarVigente() { return estado.dolarPropio || estado.dolarPagina; }

  function mostrarEstado(texto, conReintento) {
    elEstado.hidden = false;
    elEstado.replaceChildren();
    var p = document.createElement('p');
    p.textContent = texto;
    elEstado.append(p);
    if (conReintento) {
      var boton = document.createElement('button');
      boton.type = 'button';
      boton.className = 'lw-boton lw-boton-claro';
      boton.textContent = 'Reintentar';
      boton.addEventListener('click', cargar);
      elEstado.append(boton);
    }
    elColumnas.hidden = true;
  }

  function ocultarEstado() { elEstado.hidden = true; elEstado.replaceChildren(); }

  function crear(tag, clase, texto) {
    var el = document.createElement(tag);
    if (clase) el.className = clase;
    if (texto != null) el.textContent = texto;
    return el;
  }

  // Las ganancias viven en la cuenta del mayorista: se guardan en el servidor poco
  // después del último cambio y vuelven a cargarse en cualquier visita o dispositivo.
  function mostrarGuardado(texto, error) {
    if (!guardado.elTexto) return;
    guardado.elTexto.textContent = texto;
    guardado.elTexto.classList.toggle('lw-error', Boolean(error));
  }

  function guardarGanancias() {
    window.clearTimeout(guardado.temporizador);
    guardado.pendiente = false;
    mostrarGuardado('Guardando…');
    return fetch('/api/listado-whatsapp/ganancias', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ganancias: estado.ganancias }),
      keepalive: true,
    }).then(function (r) {
      if (!r.ok) throw new Error('guardar');
      if (!guardado.pendiente) mostrarGuardado('Guardado en tu cuenta');
    }).catch(function () {
      mostrarGuardado('No se pudo guardar. Tus montos siguen acá, probá cambiar uno para reintentar.', true);
    });
  }

  function fijarGanancia(indice, valor) {
    if (valor > 0) estado.ganancias[indice] = valor;
    else delete estado.ganancias[indice];
    guardado.pendiente = true;
    mostrarGuardado('Guardando…');
    window.clearTimeout(guardado.temporizador);
    guardado.temporizador = window.setTimeout(guardarGanancias, 700);
  }

  window.addEventListener('pagehide', function () {
    if (guardado.pendiente) guardarGanancias();
  });

  function campoGanancia(etiquetaAccesible, valorInicial, alCambiar) {
    var envoltorio = crear('label', 'lw-ganancia');
    envoltorio.append(crear('span', 'lw-ganancia-prefijo', 'Ganás US$'));
    var input = crear('input', null);
    input.type = 'text';
    input.inputMode = 'numeric';
    input.autocomplete = 'off';
    input.maxLength = 4;
    input.placeholder = '0';
    input.value = valorInicial > 0 ? String(valorInicial) : '';
    input.setAttribute('aria-label', etiquetaAccesible);
    input.addEventListener('input', function () {
      var limpio = input.value.replace(/\D/g, '');
      if (limpio !== input.value) input.value = limpio;
      alCambiar(leerGanancia(limpio));
    });
    envoltorio.append(input);
    return envoltorio;
  }

  function construirRangos() {
    var cont = crear('div', 'lw-rangos');
    var tituloRangos = crear('h3', 'lw-rangos-titulo', 'Cuánto querés ganar por rango');
    tituloRangos.id = 'lw-rangos-titulo';
    cont.setAttribute('role', 'group');
    cont.setAttribute('aria-labelledby', 'lw-rangos-titulo');
    var textoGuardado = crear('p', 'lw-guardado', 'Se guardan en tu cuenta para la próxima vez.');
    textoGuardado.setAttribute('role', 'status');
    guardado.elTexto = textoGuardado;
    cont.append(tituloRangos, textoGuardado);

    var todos = crear('div', 'lw-rango lw-rango-todos');
    var textoTodos = crear('div', 'lw-rango-texto');
    textoTodos.append(crear('strong', null, 'Mismo monto para todos'), crear('span', null, 'Completa todos los rangos de una vez'));
    var entradas = [];
    todos.append(textoTodos, campoGanancia('Ganancia en dólares para todos los rangos', 0, function (valor) {
      rangos(estado.secciones).forEach(function (r) { fijarGanancia(r.indice, valor); });
      entradas.forEach(function (e) { e.input.value = valor > 0 ? String(valor) : ''; });
      pintar();
    }));
    cont.append(todos);

    rangos(estado.secciones).forEach(function (r) {
      var fila = crear('div', 'lw-rango');
      var texto = crear('div', 'lw-rango-texto');
      texto.append(crear('strong', null, r.etiqueta), crear('span', null, r.cantidad + (r.cantidad === 1 ? ' producto' : ' productos')));
      var campo = campoGanancia('Ganancia en dólares para productos de ' + r.etiqueta, estado.ganancias[r.indice] || 0, function (valor) {
        fijarGanancia(r.indice, valor);
        pintar();
      });
      entradas.push({ input: campo.querySelector('input') });
      fila.append(texto, campo);
      cont.append(fila);
    });
    return cont;
  }

  function construirColumnas() {
    elColumnas.replaceChildren();
    COLUMNAS.forEach(function (col, posicion) {
      var principal = posicion === 0;
      var panel = crear('article', principal ? 'lw-panel lw-panel-principal' : 'lw-panel');
      panel.dataset.columna = col.id;
      var tituloId = 'lw-titulo-' + col.id;
      panel.setAttribute('aria-labelledby', tituloId);

      var cabecera = crear('div', 'lw-panel-cabecera');
      var titulo = crear('h2', 'lw-placa', col.titulo);
      titulo.id = tituloId;
      cabecera.append(titulo, crear('p', 'lw-panel-detalle', col.detalle));

      var meta = crear('p', 'lw-panel-meta');
      meta.dataset.meta = col.id;

      var acciones = crear('div', 'lw-acciones');
      acciones.dataset.acciones = col.id;

      var vista = crear('pre', 'lw-vista');
      vista.tabIndex = 0;
      vista.dataset.vista = col.id;
      vista.setAttribute('aria-label', 'Vista previa de ' + col.titulo);

      if (principal) {
        var cuerpo = crear('div', 'lw-principal-cuerpo');
        var salida = crear('div', 'lw-salida');
        salida.append(acciones, meta, vista);
        cuerpo.append(construirRangos(), salida);
        panel.append(cabecera, cuerpo);
      } else {
        panel.append(cabecera, acciones, meta, vista);
      }
      elColumnas.append(panel);
    });
  }

  function marcarCopiado(boton, textoOriginal) {
    window.clearTimeout(temporizadores.get(boton));
    boton.textContent = 'Copiado';
    boton.classList.add('lw-copiado');
    elAnuncio.textContent = 'Listado copiado. Pegalo en WhatsApp.';
    temporizadores.set(boton, window.setTimeout(function () {
      boton.textContent = textoOriginal;
      boton.classList.remove('lw-copiado');
      elAnuncio.textContent = '';
    }, 2200));
  }

  function copiarTexto(texto) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(texto);
    }
    return new Promise(function (resolve, reject) {
      var area = document.createElement('textarea');
      area.value = texto;
      area.setAttribute('readonly', '');
      area.style.position = 'fixed';
      area.style.opacity = '0';
      document.body.append(area);
      area.select();
      var ok = false;
      try { ok = document.execCommand('copy'); } catch (e) { ok = false; }
      area.remove();
      return ok ? resolve() : reject(new Error('copy'));
    });
  }

  function avisarFalloCopia(boton, textoOriginal) {
    boton.textContent = 'No se pudo copiar';
    elAnuncio.textContent = 'No se pudo copiar. Seleccioná el texto y copialo a mano.';
    window.setTimeout(function () { boton.textContent = textoOriginal; }, 2600);
  }

  function pintar() {
    var dolar = dolarVigente();
    var fecha = new Date();
    COLUMNAS.forEach(function (col) {
      var origen = col.id === 'mayorista' ? conGanancias(estado.secciones, estado.ganancias) : estado.secciones;
      var mensajes = armarMensajes(origen, col.campo, dolar, { nombre: estado.nombre, fecha: fecha });
      var vista = elColumnas.querySelector('[data-vista="' + col.id + '"]');
      var acciones = elColumnas.querySelector('[data-acciones="' + col.id + '"]');
      var meta = elColumnas.querySelector('[data-meta="' + col.id + '"]');
      vista.textContent = mensajes.join('\n\n————————\n\n');
      var cantidad = contarProductos(estado.secciones);
      meta.textContent = cantidad + ' productos' + (mensajes.length > 1 ? ' · ' + mensajes.length + ' mensajes' : '');
      acciones.replaceChildren();
      mensajes.forEach(function (texto, i) {
        var etiqueta = mensajes.length > 1 ? 'Copiar parte ' + (i + 1) + ' de ' + mensajes.length : 'Copiar listado';
        var boton = crear('button', 'lw-boton', etiqueta);
        boton.type = 'button';
        boton.addEventListener('click', function () {
          copiarTexto(texto).then(function () { marcarCopiado(boton, etiqueta); },
            function () { avisarFalloCopia(boton, etiqueta); });
        });
        acciones.append(boton);
      });
    });
  }

  function actualizarAyudaDolar() {
    var pagina = estado.dolarPagina;
    var texto = elDolar.value.trim();
    elAyudaDolar.classList.remove('lw-error');
    if (!texto) {
      estado.dolarPropio = null;
      elAyudaDolar.textContent = 'Dólar de la página: ' + formatearPesos(pagina) + '. Dejalo vacío para usarlo.';
      return;
    }
    var valor = leerDolar(texto);
    if (valor === null || !dolarEsPlausible(valor)) {
      estado.dolarPropio = null;
      elAyudaDolar.classList.add('lw-error');
      elAyudaDolar.textContent = 'Revisá el número: escribí un dólar entre ' + formatearPesos(DOLAR_MINIMO) +
        ' y ' + formatearPesos(DOLAR_MAXIMO) + '. Mientras tanto uso el de la página (' + formatearPesos(pagina) + ').';
      return;
    }
    estado.dolarPropio = valor;
    elAyudaDolar.textContent = 'Usando tu dólar: ' + formatearPesos(valor) + '. El de la página es ' + formatearPesos(pagina) + '.';
  }

  function alCambiarNombre() {
    estado.nombre = elNombre.value;
    guardarAlmacen(CLAVE_NOMBRE, estado.nombre.trim());
    pintar();
  }

  function alCambiarDolar() {
    actualizarAyudaDolar();
    pintar();
  }

  async function cargar() {
    mostrarEstado('Armando tu listado…', false);
    var respuesta;
    try {
      respuesta = await fetch('/api/listado-whatsapp', { cache: 'no-store' });
    } catch (e) {
      mostrarEstado('No pude conectar. Revisá tu internet y probá de nuevo.', true);
      return;
    }
    if (respuesta.status === 401) { window.location.replace('/login.html'); return; }
    if (respuesta.status === 403) { window.location.replace('/'); return; }
    if (!respuesta.ok) {
      mostrarEstado('No pude armar el listado ahora. Probá de nuevo en un momento.', true);
      return;
    }
    var datos = await respuesta.json();
    estado.secciones = datos.secciones || [];
    estado.dolarPagina = Number(datos.cotizacion) || 0;
    estado.ganancias = {};
    Object.keys(datos.ganancias || {}).forEach(function (k) {
      var v = leerGanancia(datos.ganancias[k]);
      if (v > 0) estado.ganancias[k] = v;
    });
    if (!estado.secciones.length || !estado.dolarPagina) {
      mostrarEstado('Estoy actualizando los precios. Volvé en unos minutos.', true);
      return;
    }
    ocultarEstado();
    elColumnas.hidden = false;
    construirColumnas();
    actualizarAyudaDolar();
    pintar();
  }

  elNombre.value = leerAlmacen(CLAVE_NOMBRE);
  estado.nombre = elNombre.value;
  elNombre.addEventListener('input', alCambiarNombre);
  elDolar.addEventListener('input', alCambiarDolar);
  cargar();
})();
