// web/static/preventa.js — página provisoria de preventa iPhone 18.
// Precios = costo del proveedor (AZ) + USD 100 de ganancia. Sin backend: la
// reserva se manda directo por WhatsApp (el "chat de Preventa" que menciona
// el texto de condiciones), Vladimir la gestiona a mano como el resto de
// los pedidos.
const WHATSAPP_PREVENTA = "543512145217";
const SENA_PORCENTAJE = 0.3;
const RECARGO_TRANSFERENCIA = 0.02; // solo transferencia en pesos, ver footer de condiciones
const COTIZACION_FALLBACK = 1565; // si /api/cotizacion no responde

const PRODUCTOS_PREVENTA = [
  { nombre: "iPhone 18 Pro 256GB", usd: 1650 },
  { nombre: "iPhone 18 Pro Max 256GB", usd: 1830 },
  { nombre: "iPhone 18 Pro Max 512GB", usd: 2020 },
];

// Colores oficiales reales del iPhone 18 Pro / Pro Max, anunciados por
// Apple el 9/9/2026 (Burgundy, Glacier, Black, Silver) — no inventados.
const COLORES_IPHONE_18 = ["Burgundy", "Glacier", "Black", "Silver"];

let cotizacionBlue = COTIZACION_FALLBACK;

function formatoPesos(valor) {
  return Math.round(valor).toLocaleString("es-AR");
}

function formatoUsd(valor) {
  // 2 decimales solo si hacen falta (30% de un usd entero puede dar centavos).
  return Number(valor.toFixed(2)).toLocaleString("es-AR", { minimumFractionDigits: 0, maximumFractionDigits: 2 });
}

function armarMensajeWhatsapp(producto, color, cantidad) {
  const lineas = [
    "Hola! Quiero reservar de la preventa de iPhone 18:",
    `📦 ${producto}`,
    `Cantidad: ${cantidad}`,
    color ? `Color preferido: ${color}` : "Color preferido: sin preferencia",
  ];
  return encodeURIComponent(lineas.join("\n"));
}

function crearCard(producto) {
  const card = document.createElement("div");
  card.className = "preventa-card";

  const idColor = `preventa-color-${producto.nombre.replace(/\s+/g, "-")}`;
  const idCantidad = `preventa-cantidad-${producto.nombre.replace(/\s+/g, "-")}`;

  card.innerHTML = `
    <h2>${producto.nombre}</h2>
    <div class="preventa-precio">🇺🇸 U$D ${producto.usd}</div>
    <label for="${idCantidad}">Cantidad</label>
    <select id="${idCantidad}">
      <option value="1">1</option>
      <option value="2">2</option>
      <option value="3">3</option>
    </select>
    <label for="${idColor}">Color de preferencia (opcional, sin garantía)</label>
    <select id="${idColor}">
      <option value="">Sin preferencia</option>
      ${COLORES_IPHONE_18.map((c) => `<option value="${c}">${c}</option>`).join("")}
    </select>

    <div class="preventa-sena">
      <div class="preventa-sena-titulo">Seña (30%) según forma de pago</div>
      <ul class="preventa-sena-lista">
        <li>🏦 <span data-sena="transferencia"></span> <span class="preventa-sena-nota">transferencia en pesos, blue del día +2%</span></li>
        <li>₿ <span data-sena="usdt"></span> <span class="preventa-sena-nota">USDT, sin interés</span></li>
        <li>🇦🇷 <span data-sena="pesos"></span> <span class="preventa-sena-nota">contado en pesos</span></li>
        <li>🇺🇸 <span data-sena="dolares"></span> <span class="preventa-sena-nota">contado en dólares</span></li>
      </ul>
    </div>

    <a class="preventa-reservar" target="_blank" rel="noopener">Reservar por WhatsApp</a>
  `;

  const boton = card.querySelector(".preventa-reservar");

  const actualizar = () => {
    const color = card.querySelector(`#${idColor}`).value.trim();
    const cantidad = parseInt(card.querySelector(`#${idCantidad}`).value, 10) || 1;

    const senaUsd = producto.usd * cantidad * SENA_PORCENTAJE;
    const senaPesos = senaUsd * cotizacionBlue;
    const senaTransferencia = senaPesos * (1 + RECARGO_TRANSFERENCIA);

    card.querySelector('[data-sena="transferencia"]').textContent = `$${formatoPesos(senaTransferencia)}`;
    card.querySelector('[data-sena="usdt"]').textContent = `USDT ${formatoUsd(senaUsd)}`;
    card.querySelector('[data-sena="pesos"]').textContent = `$${formatoPesos(senaPesos)}`;
    card.querySelector('[data-sena="dolares"]').textContent = `U$D ${formatoUsd(senaUsd)}`;

    const texto = armarMensajeWhatsapp(producto.nombre, color, cantidad);
    boton.href = `https://wa.me/${WHATSAPP_PREVENTA}?text=${texto}`;
  };

  card.querySelector(`#${idColor}`).addEventListener("change", actualizar);
  card.querySelector(`#${idCantidad}`).addEventListener("change", actualizar);
  card._actualizarSena = actualizar;
  actualizar();

  return card;
}

const contenedor = document.getElementById("preventa-modelos");
const cards = [];
if (contenedor) {
  PRODUCTOS_PREVENTA.forEach((p) => {
    const card = crearCard(p);
    cards.push(card);
    contenedor.appendChild(card);
  });
}

// La cotización real (misma base "dólar blue" que usa todo el catálogo, ver
// web/app.py::api_cotizacion) llega async; hasta que responda se usa el
// fallback para no dejar la seña en blanco.
fetch("/api/cotizacion")
  .then((r) => r.json())
  .then((data) => {
    if (data && data.valor) {
      cotizacionBlue = data.valor;
      cards.forEach((card) => card._actualizarSena());
    }
  })
  .catch(() => {
    // Sin conexión a la API: se queda con COTIZACION_FALLBACK.
  });
