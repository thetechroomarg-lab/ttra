/* Sección Garantías de la home: cada card abre el detalle en un <dialog>.
   scroll-lock.js detecta el dialog abierto, bloquea el scroll y oculta las
   barras de navegación. El panel se cierra solo con su ✕ (ni Escape ni el
   fondo lo cierran), igual que el resto de los paneles flotantes.
   El contenido se arma por bloques a partir de garantias.json. */
(() => {
  'use strict';

  // Los textos viven en garantias.json: es la misma fuente que usa el PDF
  // del recibo (web/garantias.py), así la web y el recibo dicen lo mismo.
  let GARANTIAS = null;
  const carga = fetch('/garantias.json')
    .then(r => (r.ok ? r.json() : null))
    .then(datos => { GARANTIAS = datos; })
    .catch(() => {});

  const SVG = 'http://www.w3.org/2000/svg';
  const ICONOS = {
    cubre: 'M7 12.5l3.2 3.2L17 9',
    noCubre: 'M8.5 8.5l7 7M15.5 8.5l-7 7',
    requisito: 'M7 12.5l3.2 3.2L17 9',
  };

  function el(tag, clase, texto) {
    const nodo = document.createElement(tag);
    if (clase) nodo.className = clase;
    if (texto != null) nodo.textContent = texto;
    return nodo;
  }
  function icono(tipo) {
    const svg = document.createElementNS(SVG, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    svg.setAttribute('focusable', 'false');
    svg.classList.add('ttra-gp-icono', `ttra-gp-icono-${tipo}`);
    const circulo = document.createElementNS(SVG, 'circle');
    circulo.setAttribute('cx', '12'); circulo.setAttribute('cy', '12'); circulo.setAttribute('r', '10.5');
    const trazo = document.createElementNS(SVG, 'path');
    trazo.setAttribute('d', ICONOS[tipo]);
    svg.append(circulo, trazo);
    return svg;
  }
  function itemConIcono(texto, tipo) {
    const li = el('li');
    li.append(icono(tipo), el('span', null, texto));
    return li;
  }
  function enlace(texto, href, clase) {
    const a = el('a', clase || 'ttra-gp-link', texto);
    a.href = href;
    a.target = '_blank';
    a.rel = 'noopener';
    return a;
  }
  function cifra([numero, unidad], clase) {
    const p = el('p', clase);
    p.append(el('strong', null, numero), el('span', null, unidad));
    return p;
  }

  const RENDER = {
    lista: b => {
      const ul = el('ul', 'ttra-gp-lista');
      b.items.forEach(t => ul.append(el('li', null, t)));
      return ul;
    },
    cobertura: b => {
      const grid = el('div', 'ttra-gp-cobertura');
      for (const [tipo, etiqueta, items] of [['cubre', 'Cubre', b.cubre], ['noCubre', 'No cubre', b.noCubre]]) {
        if (!items?.length) { grid.classList.add('ttra-gp-cobertura-simple'); continue; }
        const col = el('div', `ttra-gp-col ttra-gp-col-${tipo}`);
        const ul = el('ul');
        items.forEach(t => ul.append(itemConIcono(t, tipo)));
        col.append(el('p', 'ttra-gp-etiqueta', etiqueta), ul);
        grid.append(col);
      }
      return grid;
    },
    destacado: b => {
      const box = el('div', 'ttra-gp-destacado');
      box.append(cifra(b.cifra, 'ttra-gp-cifra'), el('p', 'ttra-gp-destacado-texto', b.texto));
      return box;
    },
    requisitos: b => {
      const ul = el('ul', 'ttra-gp-requisitos');
      b.items.forEach(t => ul.append(itemConIcono(t, 'requisito')));
      return ul;
    },
    proceso: b => {
      const ol = el('ol', 'ttra-gp-proceso');
      b.pasos.forEach(paso => {
        const li = el('li');
        li.append(cifra(paso.cifra, 'ttra-gp-cifra'), el('p', 'ttra-gp-paso-titulo', paso.titulo), el('p', 'ttra-gp-paso-texto', paso.texto));
        ol.append(li);
      });
      return ol;
    },
    opciones: b => {
      const ol = el('ol', 'ttra-gp-opciones');
      b.opciones.forEach(o => {
        const li = el('li');
        li.append(el('p', 'ttra-gp-paso-titulo', o.titulo), el('p', 'ttra-gp-paso-texto', o.texto));
        ol.append(li);
      });
      return ol;
    },
    aviso: b => el('p', 'ttra-gp-aviso', b.texto),
    servicios: b => {
      const box = el('div', 'ttra-gp-servicios');
      const lista = el('ul', 'ttra-gp-lugares');
      b.lugares.forEach(l => {
        const li = el('li', 'ttra-gp-lugar');
        const links = el('p', 'ttra-gp-lugar-links');
        l.links.forEach(([texto, href]) => links.append(enlace(texto, href)));
        li.append(el('p', 'ttra-gp-lugar-nombre', l.nombre), el('p', 'ttra-gp-lugar-donde', l.lugar), links);
        lista.append(li);
      });
      box.append(lista);
      if (b.turnos) box.append(enlace(b.turnos[0], b.turnos[1], 'ttra-gp-turnos'));
      return box;
    },
    excepciones: b => {
      const box = el('div', 'ttra-gp-excepciones');
      const cifraBox = el('div', 'ttra-gp-exc-cifra');
      cifraBox.append(cifra(b.cifra, 'ttra-gp-cifra'), el('p', 'ttra-gp-exc-cifra-nota', b.cifraNota));
      const ul = el('ul', 'ttra-gp-lista');
      b.items.forEach(t => ul.append(el('li', null, t)));
      box.append(cifraBox, ul);
      return box;
    },
    importante: b => {
      const box = el('div', 'ttra-gp-importante');
      b.parrafos.forEach(t => box.append(el('p', null, t)));
      if (b.cierre) box.append(el('p', 'ttra-gp-cierre', b.cierre));
      return box;
    },
  };

  function armarCuerpo(g) {
    const nodos = g.alcance ? [el('p', 'ttra-gp-alcance', g.alcance)] : [];
    let n = 0;
    for (const b of g.bloques) {
      if (b.tipo === 'firma') {
        if (b.cierre) nodos.push(el('p', 'ttra-gp-cierre-final', b.cierre));
        nodos.push(el('p', 'ttra-gp-firma', b.firma));
        continue;
      }
      const seccion = el('section', `ttra-gp-bloque ttra-gp-bloque-${b.tipo}`);
      const cabecera = el('h3', 'ttra-gp-titulo');
      cabecera.append(el('span', 'ttra-gp-indice', String(++n).padStart(2, '0')), document.createTextNode(b.titulo));
      if (b.etiqueta) cabecera.append(el('span', 'ttra-gp-etiqueta-tag', b.etiqueta));
      seccion.append(cabecera, RENDER[b.tipo](b));
      if (b.nota) seccion.append(el('p', 'ttra-gp-nota', b.nota));
      nodos.push(seccion);
      if (b.firma) nodos.push(el('p', 'ttra-gp-firma', b.firma));
    }
    return nodos;
  }

  const panel = document.getElementById('ttra-garantia-panel');
  const grid = document.querySelector('.ttra-garantias-grid');
  if (!panel || !grid || typeof panel.showModal !== 'function') return;
  const scroll = panel.querySelector('.ttra-garantia-panel-scroll');
  const titulo = panel.querySelector('#ttra-garantia-panel-titulo');
  const [numero, unidad] = panel.querySelectorAll('.ttra-garantia-panel-plazo > *');
  const desde = panel.querySelector('.ttra-garantia-panel-desde');
  const cuerpo = panel.querySelector('.ttra-garantia-panel-cuerpo');
  const cerrar = panel.querySelector('.ttra-garantia-cerrar');
  let origen = null;

  function abrir(card) {
    if (!GARANTIAS) { carga.then(() => GARANTIAS && abrir(card)); return; }
    const g = GARANTIAS[card.dataset.garantia];
    if (!g || panel.open) return;
    origen = card;
    panel.dataset.garantia = card.dataset.garantia;
    titulo.textContent = g.titulo;
    numero.textContent = g.plazo[0];
    unidad.textContent = g.plazo[1];
    unidad.hidden = !g.plazo[1];
    desde.textContent = g.desde;
    cuerpo.replaceChildren(...armarCuerpo(g));
    panel.showModal();
    scroll.scrollTop = 0;
    cerrar.focus({preventScroll: true});
  }

  grid.addEventListener('click', event => {
    const card = event.target.closest('.ttra-garantia');
    if (card) abrir(card);
  });
  cerrar.addEventListener('click', () => panel.close());
  // Escape no cierra: el panel se cierra solo con la ✕.
  panel.addEventListener('cancel', event => event.preventDefault());
  panel.addEventListener('close', () => {
    origen?.focus({preventScroll: true});
    origen = null;
  });
})();
