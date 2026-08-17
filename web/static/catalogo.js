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
  el.innerHTML = SECCIONES.map(
    (s) => `<button data-seccion="${s}" class="${s === activa ? "activa" : ""}">${s}</button>`
  ).join("");
  el.querySelectorAll("button").forEach((btn) => {
    btn.addEventListener("click", () => pintarSeccion(btn.dataset.seccion));
  });
}

let SECCIONES_DATA = {};

function pintarSeccion(nombre) {
  pintarTabs(nombre);
  const el = document.getElementById("secciones");
  const productos = SECCIONES_DATA[nombre] || [];
  if (productos.length === 0) {
    el.innerHTML = `<p class="mensaje-vacio">Todavía no hay productos cargados en ${nombre}.</p>`;
    return;
  }
  el.innerHTML = `<div class="grilla">${productos.map(tarjetaProducto).join("")}</div>`;
}

function tarjetaProducto(p) {
  return `
    <div class="card">
      <h3>${p.nombre}</h3>
      <p class="precios">
        <strong>U$D ${p.usd ?? "-"}</strong><br>
        $ ${p.pesos ?? "-"} contado<br>
        $ ${p.transferencia ?? "-"} transferencia
      </p>
    </div>
  `;
}

async function cargarCatalogo() {
  const r = await fetch("/api/catalogo");
  if (r.status === 401) {
    window.location.href = "/login.html";
    return;
  }
  const datos = await r.json();
  SECCIONES_DATA = datos.secciones || {};
  if (datos.mensaje) {
    document.getElementById("secciones").innerHTML =
      `<p class="mensaje-vacio">${datos.mensaje}</p>`;
    pintarTabs(null);
    return;
  }
  pintarSeccion(SECCIONES[0]);
}

document.getElementById("btn-logout").addEventListener("click", async () => {
  await fetch("/logout", { method: "POST" });
  window.location.href = "/login.html";
});

pintarCarrousel();
cargarCatalogo();
