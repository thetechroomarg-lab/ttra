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

function pintarTabs(activa) {
  const el = document.getElementById("tabs");
  el.innerHTML = ["Todos", ...SECCIONES].map(
    (s) => `<button type="button" data-seccion="${s}" class="${s === activa ? "activa" : ""}" aria-pressed="${s === activa}">${s}</button>`
  ).join("");
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => pintarSeccion(btn.dataset.seccion));
  });
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
  pintarTabs(nombre);
  const el = document.getElementById("secciones");
  const base = nombre === "Todos"
    ? Object.values(SECCIONES_DATA).flat()
    : (SECCIONES_DATA[nombre] || []);
  const productos = marcaActiva
    ? base.filter((producto) => (producto.marca || "Otras marcas") === marcaActiva)
    : base;
  document.getElementById("contador-productos").textContent =
    `${productos.length} ${productos.length === 1 ? "producto" : "productos"}`;
  if (productos.length === 0) {
    const detalle = marcaActiva
      ? ` de ${escapeHtml(marcaActiva)} en ${escapeHtml(nombre)}`
      : ` en ${escapeHtml(nombre)}`;
    el.innerHTML = `<p class="mensaje-vacio">Todavía no hay productos${detalle}.</p>`;
    return;
  }
  el.innerHTML = `<div class="grilla">${productos.map(tarjetaProducto).join("")}</div>`;
}

function escapeHtml(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  return div.innerHTML;
}

function tarjetaProducto(p) {
  const colores = Array.isArray(p.colores) && p.colores.length > 0
    ? `<p class="colores">${escapeHtml(p.colores.join(", "))}</p>`
    : "";
  return `
    <div class="card">
      <h3>${escapeHtml(p.nombre)}</h3>
      ${colores}
      <p class="precios">
        <strong>U$D ${p.usd ?? "-"}</strong><br>
        $ ${p.pesos ?? "-"} contado<br>
        $ ${p.transferencia ?? "-"} transferencia
      </p>
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
      pintarTabs(null);
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

pintarCarrousel();
cargarCatalogo();
