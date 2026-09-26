const MARCAS = [
  "Apple", "Samsung", "Xiaomi", "Motorola", "Realme", "Oppo", "Honor",
  "Infinix", "Nokia", "PlayStation", "Nintendo", "JBL", "Logitech",
];

const SECCIONES = [
  "Celulares", "Accesorios Celulares", "Tablets", "Notebooks y Macbooks", "Gaming",
];

function pintarCarrousel() {
  const el = document.getElementById("carrousel");
  const marcas = [...MARCAS, ...MARCAS]; // duplicado para el loop visual
  el.innerHTML = marcas.map((m) => `<span>${m}</span>`).join("");
}

// Match the existing product-view history used by the administration panel.
const productosConsultados = new Set();
function registrarConsultaProducto(producto) {
  if (!producto?.nombre || productosConsultados.has(producto.nombre)) return;
  productosConsultados.add(producto.nombre);
  let anonId;
  try {
    anonId = localStorage.getItem('ttra_anon_id');
    if (!anonId) {
      anonId = crypto.randomUUID();
      localStorage.setItem('ttra_anon_id', anonId);
    }
  } catch {
    anonId = `ttra-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }
  fetch('/api/interacciones', {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-TTRA-ANON-ID': anonId},
    body: JSON.stringify({tipo_evento: 'view_item', producto_nombre: producto.nombre, session_id: anonId}),
    keepalive: true,
  }).catch(() => {});
}

let SECCIONES_DATA = {};
let categoriaActiva = "Todos";
let marcaActiva = "";
let condicionActiva = "";
// Solo en "Notebooks y Macbooks": "" (todos), "Notebook" o "Mac", igual que la categoría del producto.
let tipoActivo = "";

const SECCION_NOTEBOOKS = "Notebooks y Macbooks";

// Mismos logos que la "Búsqueda por Marca" de la landing (landing-base.js).
const MARCA_LOGO = {
  "Apple": "apple", "Samsung": "samsung", "Xiaomi": "xiaomi",
  "Motorola": "motorola", "Realme": "realme", "Oppo": "oppo",
  "Honor": "honor", "Infinix": "infinix", "Nokia": "nokia",
  "PlayStation": "sony", "Nintendo": "nintendo", "JBL": "jbl",
  "Logitech": "logitech", "Itel": "itel", "HP": "hp", "Lenovo": "lenovo",
  "Asus": "asus", "Acer": "acer", "Dell": "dell", "MSI": "msi",
  "Gigabyte": "gigabyte", "Xtrem": "xtrem", "Otras marcas": "otras-marcas",
};
const MARCA_ETIQUETA = { "PlayStation": "Sony" };
const etiquetaMarca = (marca) => MARCA_ETIQUETA[marca] || marca;
const marcaDe = (producto) => producto.marca || "Otras marcas";

// Marcas presentes en los productos, alfabéticas y con "Otras marcas" al final.
function marcasDe(productos) {
  const marcas = [...new Set(productos.map(marcaDe))].filter((m) => m !== "Otras marcas")
    .sort((a, b) => etiquetaMarca(a).localeCompare(etiquetaMarca(b), "es"));
  return productos.some((p) => marcaDe(p) === "Otras marcas") ? [...marcas, "Otras marcas"] : marcas;
}

function productosDeCategoria(nombre) {
  const base = nombre === "Todos"
    ? Object.values(SECCIONES_DATA).flat()
    : (SECCIONES_DATA[nombre] || []);
  return nombre === SECCION_NOTEBOOKS && tipoActivo
    ? base.filter((producto) => producto.categoria === tipoActivo)
    : base;
}

function permiteFiltroCondicion(categoria, marca) {
  return categoria === "Celulares" && marca.toLocaleLowerCase("es") === "apple";
}

function condicionProducto(producto) {
  const descripcion = [producto.nombre, ...(producto.colores || [])].join(" ");
  if (/\bcpo\b/i.test(descripcion)) return "cpo";
  return /\b(usad[oa]s?|reacondicionad[oa]s?|refurbished|renewed)\b|\d{1,3}\s*%/i.test(descripcion)
    ? "usado" : "nuevo";
}


// El dropdown solo ofrece las marcas de la sección (y del tipo, en notebooks).
function pintarMarcas(productos) {
  const selector = document.getElementById("marca-filter");
  const marcas = marcasDe(productos);
  if (!marcas.includes(marcaActiva)) marcaActiva = "";
  selector.replaceChildren(new Option("Todas las marcas", ""),
    ...marcas.map((marca) => new Option(etiquetaMarca(marca), marca)));
  selector.value = marcaActiva;
}

// En Notebooks y Macbooks primero se elige el tipo; la marca aparece solo para Notebooks.
function pintarFiltrosDeSeccion(nombre) {
  const esNotebooks = nombre === SECCION_NOTEBOOKS;
  if (!esNotebooks) tipoActivo = "";
  document.getElementById("tipo-filter-field").hidden = !esNotebooks;
  document.getElementById("tipo-filter").value = tipoActivo;
  const mostrarMarca = !esNotebooks || tipoActivo === "Notebook";
  document.getElementById("marca-filter-field").hidden = !mostrarMarca;
  if (!mostrarMarca) marcaActiva = "";
  const base = productosDeCategoria(nombre);
  pintarMarcas(base);
  return base;
}

// Mismos nombres que el menú de Categorías.
const TITULOS_SECCION = { "Todos": "Todo el catálogo", "Accesorios Celulares": "Accesorios" };

// El título refleja dónde está el cliente: la categoría, o la marca si vino
// desde "Búsqueda por marca" (catálogo completo filtrado por una marca).
function pintarTitulo(nombre) {
  const titulo = nombre === "Todos" && marcaActiva
    ? etiquetaMarca(marcaActiva)
    : nombre === SECCION_NOTEBOOKS && tipoActivo
      ? (tipoActivo === "Mac" ? "Macbooks" : "Notebooks")
      : (TITULOS_SECCION[nombre] || nombre);
  const h1 = document.getElementById("catalog-title");
  h1.textContent = titulo;
  const punto = document.createElement("span");
  punto.textContent = ".";
  h1.append(punto);
  document.title = `THE TECH ROOM ARG — ${titulo}`;
}

function pintarSeccion(nombre) {
  categoriaActiva = nombre;
  const base = pintarFiltrosDeSeccion(nombre);
  pintarTitulo(nombre);
  const filtrarCondicion = permiteFiltroCondicion(nombre, marcaActiva);
  document.getElementById("condition-filter-field").hidden = !filtrarCondicion;
  if (!filtrarCondicion) {
    condicionActiva = "";
    document.getElementById("condition-filter").value = "";
  }
  const el = document.getElementById("secciones");
  const porMarca = marcaActiva
    ? base.filter((producto) => (producto.marca || "Otras marcas") === marcaActiva)
    : base;
  // Saca emojis y s\u00edmbolos (quedan letras/n\u00fameros/espacios) para que pegar una l\u00ednea
  // de un listado (que arranca con un emoji por producto) no rompa la b\u00fasqueda.
  const normalizarBusqueda = (texto) => texto.toLocaleLowerCase('es').normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
  const palabrasBusqueda = normalizarBusqueda(document.getElementById('catalog-search').value.trim())
    .split(' ').filter(Boolean);
  const porCondicion = filtrarCondicion && condicionActiva
    ? porMarca.filter(producto => condicionProducto(producto) === condicionActiva)
    : porMarca;
  const productos = palabrasBusqueda.length
    ? porCondicion.filter(producto => {
        const texto = normalizarBusqueda(`${producto.nombre || ''} ${producto.marca || ''}`);
        return palabrasBusqueda.every(palabra => texto.includes(palabra));
      })
    : porCondicion;
  document.getElementById("contador-productos").textContent =
    `${productos.length} ${productos.length === 1 ? "producto" : "productos"}`;
  if (productos.length === 0) {
    const detalle = marcaActiva
      ? ` de ${escapeHtml(etiquetaMarca(marcaActiva))} en ${escapeHtml(nombre)}`
      : ` en ${escapeHtml(nombre)}`;
    el.innerHTML = palabrasBusqueda.length
      ? '<p class="mensaje-vacio">No encontré productos que coincidan con tu búsqueda.</p>'
      : `<p class="mensaje-vacio">Todavía no hay productos${detalle}.</p>`;
    return;
  }
  el.innerHTML = `<div class="grilla">${productos.map(tarjetaProducto).join("")}</div>`;
  window.TTRAComparar?.bind(el, productos, SECCIONES_DATA, () => ({
    categoria: categoriaActiva, marca: marcaActiva, condicion: condicionActiva, tipo: tipoActivo,
    query: document.getElementById('catalog-search').value,
    searchVisible: !document.querySelector('.catalog-search-wrap').hidden
  }));
  el.querySelectorAll('.card').forEach((card) => {
    const producto = productos[Number(card.dataset.productIndex)];
    card.addEventListener('click', () => registrarConsultaProducto(producto));
    card.addEventListener('focusin', () => registrarConsultaProducto(producto));
    card.querySelector('.btn-compartir').addEventListener('click', () => abrirCompartirCatalogo(producto));
    const select = card.querySelector('select');
    const button = card.querySelector('.btn-agregar');
    const status = card.querySelector('.catalog-card-status');
    select?.addEventListener('change', () => {
      registrarConsultaProducto(producto);
      button.disabled = !select.value;
      status.textContent = '';
    });
    button.addEventListener('click', async () => {
      const color = select ? select.value : (producto.colores?.[0] || null);
      if (select && !color) return;
      button.disabled = true;
      try {
        TTRACarrito.agregar(producto, color);
      } catch {
        status.textContent = 'No pude guardar el producto en el carrito. Probá de nuevo.';
        button.disabled = false;
        return;
      }
      status.textContent = 'Agregado al carrito.';
      try {
        await TTRACarrito.animar(card);
      } finally {
        button.disabled = Boolean(select && !select.value);
      }
    });
  });
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  return div.innerHTML;
}

const ICONO_CAMARA_SVG = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <path d="M4 8.5C4 7.67157 4.67157 7 5.5 7H7.5L8.5 5.5H15.5L16.5 7H18.5C19.3284 7 20 7.67157 20 8.5V17.5C20 18.3284 19.3284 19 18.5 19H5.5C4.67157 19 4 18.3284 4 17.5V8.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>
  <circle cx="12" cy="13" r="3.4" stroke="currentColor" stroke-width="1.6"/>
</svg>`;

function botonFotoHtml(p) {
  const url = `https://www.google.com/search?tbm=isch&q=${encodeURIComponent(p.nombre || "")}`;
  return `<a class="btn-foto" href="${escapeHtml(url)}" target="_blank" rel="noopener" title="Ver fotos en Google Imágenes" aria-label="Ver fotos en Google Imágenes">${ICONO_CAMARA_SVG}</a>`;
}

// Ícono de especificaciones (SVG, no emoji): a la derecha del de cámara,
// misma fila. Busca el producto en Google agregando siempre la palabra
// "especificaciones", para ir directo a fichas técnicas en vez de una
// búsqueda genérica del nombre.
const ICONO_ESPECIFICACIONES_SVG = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <rect x="5" y="4" width="14" height="16" rx="1.5" stroke="currentColor" stroke-width="1.6"/>
  <line x1="8" y1="8.5" x2="16" y2="8.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="8" y1="12" x2="16" y2="12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
  <line x1="8" y1="15.5" x2="13" y2="15.5" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/>
</svg>`;

function botonEspecificacionesHtml(p) {
  const url = `https://www.google.com/search?q=${encodeURIComponent(`${p.nombre || ""} especificaciones`)}`;
  return `<a class="btn-foto" href="${escapeHtml(url)}" target="_blank" rel="noopener" title="Ver especificaciones en Google" aria-label="Ver especificaciones en Google">${ICONO_ESPECIFICACIONES_SVG}</a>`;
}

// Compartir abre el panel con enlace directo y opciones para copiar o WhatsApp.
const ICONO_COMPARTIR_SVG = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <circle cx="6" cy="12" r="2.6" stroke="currentColor" stroke-width="1.6"/>
  <circle cx="18" cy="6" r="2.6" stroke="currentColor" stroke-width="1.6"/>
  <circle cx="18" cy="18" r="2.6" stroke="currentColor" stroke-width="1.6"/>
  <line x1="8.3" y1="10.8" x2="15.7" y2="7.2" stroke="currentColor" stroke-width="1.6"/>
  <line x1="8.3" y1="13.2" x2="15.7" y2="16.8" stroke="currentColor" stroke-width="1.6"/>
</svg>`;

function botonCompartirHtml() {
  return `<button type="button" class="btn-foto btn-compartir" title="Compartir producto" aria-label="Compartir producto">${ICONO_COMPARTIR_SVG}</button>`;
}


function abrirCompartirCatalogo(producto) {
  let panel = document.getElementById('catalog-share');
  if (!panel) {
    panel = document.createElement('dialog');
    panel.id = 'catalog-share';
    panel.setAttribute('aria-labelledby', 'catalog-share-title');
    panel.innerHTML = `<h2 id="catalog-share-title">Compartir producto</h2>
      <p class="catalog-share-name"></p>
      <input readonly aria-label="Link del producto">
      <div class="catalog-share-actions">
        <button type="button" class="catalog-share-copy">Copiar enlace</button>
        <a class="catalog-share-whatsapp" target="_blank" rel="noopener noreferrer">Compartir por WhatsApp</a>
        <button type="button" class="catalog-share-close">Cerrar</button>
      </div><p role="status"></p>`;
    document.body.append(panel);
    panel.querySelector('.catalog-share-close').addEventListener('click', () => panel.close());
    panel.addEventListener('click', event => {
      const bounds = panel.getBoundingClientRect();
      if (event.target === panel && (event.clientX < bounds.left || event.clientX > bounds.right ||
          event.clientY < bounds.top || event.clientY > bounds.bottom)) panel.close();
    });
    panel.querySelector('.catalog-share-copy').addEventListener('click', async () => {
      const input = panel.querySelector('input');
      try {
        await navigator.clipboard.writeText(input.value);
        panel.querySelector('[role="status"]').textContent = '¡Enlace copiado!';
      } catch {
        input.focus(); input.select();
        panel.querySelector('[role="status"]').textContent = 'Seleccioné el enlace para que puedas copiarlo.';
      }
    });
    panel.addEventListener('close', () => document.body.classList.remove('catalog-share-open'));
  }
  const url = new URL('/', location.origin);
  url.searchParams.set('producto', producto.nombre);
  panel.querySelector('.catalog-share-name').textContent = producto.nombre;
  panel.querySelector('input').value = url.href;
  panel.querySelector('.catalog-share-whatsapp').href = 'https://wa.me/?text=' +
    encodeURIComponent(producto.nombre + '\n' + url.href);
  panel.querySelector('[role="status"]').textContent = '';
  document.body.classList.add('catalog-share-open');
  panel.showModal();
}

function tarjetaProducto(p, indice = 0) {
  const precios = preciosDe(p);
  const monto = (valor) => valor == null ? "-" : Number(valor).toLocaleString("es-AR");
  const opciones = Array.isArray(p.colores) && p.colores.length ? p.colores : ["Color único"];
  const elegirColor = true;
  const etiqueta = condicionProducto(p) === "usado" ? "variante" : "color";
  const colores = opciones.length > 0
    ? `<label for="catalog-color-${indice}">${etiqueta === "variante" ? "Color y % de batería:" : "Colores disponibles:"}</label>
       <select id="catalog-color-${indice}" required>
         <option value="" disabled selected hidden>Elegí una opción de color</option>
         ${opciones.map((color) => `<option value="${escapeHtml(color).replaceAll('"', '&quot;')}">${escapeHtml(color)}</option>`).join('')}
       </select>`
    : `<p class="colores">${escapeHtml(opciones[0] || 'Color único')}</p>`;
  return `
    <div class="card" data-product-index="${indice}">
      <h3>${escapeHtml(p.nombre)}</h3>
      <p class="precios">
        <strong>U$D ${monto(precios.dolares)} (contado)</strong><br>
        U$D ${monto(precios.bancoUsa)} (Transf. USA)<br>
        USDT ${monto(precios.usdt)}<br>
        $ ${monto(p.pesos)} Pesos contado.<br>
        $ ${monto(p.transferencia)} Pesos transf.
      </p>
      <div class="catalog-card-actions">
        ${colores}
        <div class="catalog-product-links">${botonFotoHtml(p)}${botonEspecificacionesHtml(p)}${botonCompartirHtml()}${typeof TTRAComparar !== "undefined" ? TTRAComparar.buttonHtml() : ""}</div>
        <button class="btn-agregar" type="button" ${elegirColor ? 'disabled' : ''}>Agregar al carrito</button>
        <p class="catalog-card-status" role="status">${elegirColor ? (etiqueta === 'variante' ? 'Elegí una variante para agregar.' : 'Elegí un color para agregar.') : ''}</p>
      </div>
    </div>
  `;
}

async function cargarCatalogo() {
  try {
    const r = await fetch("/api/catalogo");
    if (r.status === 401) {
      window.location.href = "/login.html";
      return;
    }
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const datos = await r.json();
    SECCIONES_DATA = datos.secciones || {};
    if (datos.mensaje) {
      document.getElementById("secciones").innerHTML =
        `<p class="mensaje-vacio">${escapeHtml(datos.mensaje)}</p>`;
      document.getElementById("contador-productos").textContent = "0 productos";
      return;
    }
    const parametros = new URLSearchParams(window.location.search);
    const regreso = window.TTRAComparar?.readReturn()?.context;
    const categoriaSolicitada = regreso ? regreso.categoria : parametros.get("categoria");
    if (!regreso && parametros.get("filtro") === "marca" && !categoriaSolicitada && !parametros.get("marca")) {
      pintarLandingMarcas();
      return;
    }
    marcaActiva = (regreso ? regreso.marca : parametros.get("marca")) || "";
    tipoActivo = ["Notebook", "Mac"].includes(regreso?.tipo) ? regreso.tipo : "";
    document.getElementById("catalog-search").value = regreso ? regreso.query : parametros.get("q") || "";
    if (regreso) {
      condicionActiva = regreso.condicion || '';
      document.getElementById('condition-filter').value = condicionActiva;
    }
    pintarSeccion(SECCIONES.includes(categoriaSolicitada) ? categoriaSolicitada : "Todos");
    if (regreso ? regreso.searchVisible : parametros.get("buscar") === "1") {
      document.querySelector('.catalog-search-wrap').hidden = false;
      document.getElementById("catalog-search").focus();
    }
    window.TTRAComparar?.restorePosition();
  } catch {
    document.getElementById("secciones").innerHTML =
      '<p class="mensaje-vacio">No pude cargar el catálogo. Probá de nuevo en un momento.</p>';
    document.getElementById("contador-productos").textContent = "Catálogo no disponible";
  }
}

// "Búsqueda por marca": una grilla con el logo de cada marca del catálogo;
// cada logo abre el catálogo completo filtrado por esa marca.
function pintarLandingMarcas() {
  const marcas = marcasDe(Object.values(SECCIONES_DATA).flat());
  document.getElementById("catalog-title").innerHTML = "Búsqueda por marca<span>.</span>";
  document.querySelector(".catalog-intro > p").textContent = "Elegí una marca para ver todos sus productos.";
  document.getElementById("catalog-filters").hidden = true;
  document.getElementById("contador-productos").textContent =
    `${marcas.length} ${marcas.length === 1 ? "marca" : "marcas"}`;
  document.getElementById("secciones").innerHTML = `<nav class="catalog-brand-grid" aria-label="Marcas">${marcas.map((marca) => {
    const logo = MARCA_LOGO[marca] || MARCA_LOGO["Otras marcas"];
    return `<a class="catalog-brand-card" href="/catalogo?marca=${encodeURIComponent(marca)}">`
      + `<img class="marca-logo-selector" src="/logos/${logo}.svg" alt="">`
      + `<span>${escapeHtml(etiquetaMarca(marca))}</span></a>`;
  }).join("")}</nav>`;
}

document.getElementById("tipo-filter").addEventListener("change", (event) => {
  tipoActivo = event.target.value;
  pintarSeccion(categoriaActiva);
});

document.getElementById("marca-filter").addEventListener("change", (event) => {
  marcaActiva = event.target.value;
  pintarSeccion(categoriaActiva);
});

document.getElementById("condition-filter").addEventListener("change", (event) => {
  condicionActiva = event.target.value;
  pintarSeccion(categoriaActiva);
});

document.getElementById('catalog-search').addEventListener('input', () => pintarSeccion(categoriaActiva));

pintarCarrousel();
cargarCatalogo();
