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

function pintarSeccion(nombre) {
  pintarTabs(nombre);
  const el = document.getElementById("secciones");
  const productos = nombre === "Todos"
    ? Object.values(SECCIONES_DATA).flat()
    : (SECCIONES_DATA[nombre] || []);
  document.getElementById("contador-productos").textContent =
    `${productos.length} ${productos.length === 1 ? "producto" : "productos"}`;
  if (productos.length === 0) {
    el.innerHTML = `<p class="mensaje-vacio">Todavía no hay productos cargados en ${escapeHtml(nombre)}.</p>`;
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
    pintarSeccion("Todos");
  } catch {
    document.getElementById("secciones").innerHTML =
      '<p class="mensaje-vacio">No pude cargar el catálogo. Probá de nuevo en un momento.</p>';
    document.getElementById("contador-productos").textContent = "Catálogo no disponible";
  }
}

document.getElementById("btn-logout").addEventListener("click", async () => {
  await fetch("/logout", { method: "POST" });
  window.location.href = "/login.html";
});

async function sincronizarSesion() {
  try {
    const respuesta = await fetch("/api/me");
    if (!respuesta.ok) return;
    document.getElementById("catalog-login").hidden = true;
    document.getElementById("btn-logout").hidden = false;
  } catch {
    // El catálogo público sigue disponible aunque falle la consulta de sesión.
  }
}

pintarCarrousel();
sincronizarSesion();
cargarCatalogo();
