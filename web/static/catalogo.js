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

function pintarMarcas() {
  const selector = document.getElementById("marca-filter");
  const marcas = [...new Set(Object.values(SECCIONES_DATA).flat()
    .map((producto) => producto.marca || "Otras marcas"))].sort((a, b) => a.localeCompare(b, "es"));
  for (const marca of marcas) {
    const opcion = document.createElement("option");
    opcion.value = marca;
    opcion.textContent = marca;
    selector.appendChild(opcion);
  }
}

function pintarSeccion(nombre) {
  categoriaActiva = nombre;
  const el = document.getElementById("secciones");
  const base = nombre === "Todos"
    ? Object.values(SECCIONES_DATA).flat()
    : (SECCIONES_DATA[nombre] || []);
  const porMarca = marcaActiva
    ? base.filter((producto) => (producto.marca || "Otras marcas") === marcaActiva)
    : base;
  const normalizarBusqueda = (texto) => texto.toLocaleLowerCase('es').normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  const consulta = normalizarBusqueda(document.getElementById('catalog-search').value.trim());
  const productos = consulta ? porMarca.filter(producto => normalizarBusqueda(`${producto.nombre || ''} ${producto.marca || ''}`).includes(consulta)) : porMarca;
  document.getElementById("contador-productos").textContent =
    `${productos.length} ${productos.length === 1 ? "producto" : "productos"}`;
  if (productos.length === 0) {
    const detalle = marcaActiva
      ? ` de ${escapeHtml(marcaActiva)} en ${escapeHtml(nombre)}`
      : ` en ${escapeHtml(nombre)}`;
    el.innerHTML = consulta
      ? '<p class="mensaje-vacio">No encontré productos que coincidan con tu búsqueda.</p>'
      : `<p class="mensaje-vacio">Todavía no hay productos${detalle}.</p>`;
    return;
  }
  el.innerHTML = `<div class="grilla">${productos.map(tarjetaProducto).join("")}</div>`;
  el.querySelectorAll('.card').forEach((card) => {
    const producto = productos[Number(card.dataset.productIndex)];
    card.addEventListener('click', () => registrarConsultaProducto(producto));
    card.addEventListener('focusin', () => registrarConsultaProducto(producto));
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

function tarjetaProducto(p, indice = 0) {
  const precios = preciosDe(p);
  const monto = (valor) => valor == null ? "-" : Number(valor).toLocaleString("es-AR");
  const opciones = Array.isArray(p.colores) ? p.colores : [];
  const elegirColor = opciones.length > 1;
  const colores = elegirColor
    ? `<label for="catalog-color-${indice}">Color</label>
       <select id="catalog-color-${indice}" required>
         <option value="" disabled selected>Elegí un color</option>
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
        <button class="btn-agregar" type="button" ${elegirColor ? 'disabled' : ''}>Agregar al carrito</button>
        <p class="catalog-card-status" role="status">${elegirColor ? 'Elegí un color para agregar.' : ''}</p>
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
    pintarMarcas();
    const parametros = new URLSearchParams(window.location.search);
    const marcaSolicitada = parametros.get("marca");
    const selectorMarca = document.getElementById("marca-filter");
    if (marcaSolicitada && [...selectorMarca.options].some((opcion) => opcion.value === marcaSolicitada)) {
      selectorMarca.value = marcaSolicitada;
      marcaActiva = marcaSolicitada;
    }
    const categoriaSolicitada = parametros.get("categoria");
    pintarSeccion(SECCIONES.includes(categoriaSolicitada) ? categoriaSolicitada : "Todos");
    if (parametros.get("buscar") === "1") {
      document.querySelector('.catalog-search-wrap').hidden = false;
      document.getElementById("catalog-search").focus();
    }
    if (parametros.get("filtro") === "marca") selectorMarca.focus({ preventScroll: true });
  } catch {
    document.getElementById("secciones").innerHTML =
      '<p class="mensaje-vacio">No pude cargar el catálogo. Probá de nuevo en un momento.</p>';
    document.getElementById("contador-productos").textContent = "Catálogo no disponible";
  }
}

document.getElementById("marca-filter").addEventListener("change", (event) => {
  marcaActiva = event.target.value;
  pintarSeccion(categoriaActiva);
});

document.getElementById('catalog-search').addEventListener('input', () => pintarSeccion(categoriaActiva));

pintarCarrousel();
cargarCatalogo();
