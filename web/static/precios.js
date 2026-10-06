// Mercado Pago, Point Tap, crédito en cuotas sin interés, cobro en el momento:
// 6,29% de cobro + el costo de las cuotas (18,69% en 6, 32,29% en 12), todo
// + IVA, más la retención de Ingresos Brutos de Córdoba, sobre lo que se
// cobra. Se calcula sobre la transferencia en pesos y solo se ofrece en
// productos con transferencia de hasta $500.000.
const MP_IIBB_CORDOBA = 0.0475;
const MP_RECARGO_CUOTAS = {
  6: (0.0629 + 0.1869) * 1.21 + MP_IIBB_CORDOBA,
  12: (0.0629 + 0.3229) * 1.21 + MP_IIBB_CORDOBA,
};
const MP_CUOTAS_TOPE_TRANSF = 500000;

function precioMp(pesosTransf, cuotas) {
  if (pesosTransf == null || pesosTransf > MP_CUOTAS_TOPE_TRANSF) return null;
  return Math.ceil(pesosTransf / (1 - MP_RECARGO_CUOTAS[cuotas]));
}

// Shared payment amounts for the storefront and cart. Round fees upward.
function preciosDe(p) {
  const dolares = p.usd ?? null;
  const pesos = p.pesos ?? null;
  const pesosTransf = pesos == null ? null : Math.ceil(pesos / 0.97);
  const mp6 = precioMp(pesosTransf, 6);
  const mp12 = precioMp(pesosTransf, 12);
  return {
    dolares,
    bancoUsa: dolares == null ? null : Math.ceil(dolares / 0.975),
    usdt: dolares == null ? null : Math.ceil(dolares / 0.99),
    pesos,
    pesosTransf,
    mp6,
    mp6Cuota: mp6 == null ? null : Math.ceil(mp6 / 6),
    mp12,
    mp12Cuota: mp12 == null ? null : Math.ceil(mp12 / 12),
  };
}

function etiquetaMp(precios, cuotas) {
  const cuota = precios[`mp${cuotas}Cuota`];
  return `MP ${cuotas} cuotas de $ ${cuota == null ? "-" : Number(cuota).toLocaleString("es-AR")}`;
}

// Solo las cuentas mayoristas reciben usd_publico: el precio que ve el
// público, para mostrarlo tachado al lado del suyo.
function preciosPublicosDe(p) {
  if (p.usd_publico == null) return null;
  return preciosDe({ usd: p.usd_publico, pesos: p.pesos_publico });
}

// Filas de la tabla mayorista: tipo de pago, descuento percibido y precio final.
function filasMayoristaDe(p) {
  const pub = preciosPublicosDe(p);
  if (!pub) return null;
  const pr = preciosDe(p);
  const fila = (tipo, signo, clave) => ({
    tipo,
    descuento: pr[clave] == null || pub[clave] == null ? null : `${signo} ${Number(pub[clave] - pr[clave]).toLocaleString("es-AR")}`,
    precio: pr[clave] == null ? "Consultar" : `${signo} ${Number(pr[clave]).toLocaleString("es-AR")}`,
  });
  return [
    fila("Dólares", "USD", "dolares"),
    fila("Banco USA", "USD", "bancoUsa"),
    fila("USDT", "USDT", "usdt"),
    fila("Pesos", "$", "pesos"),
    fila("Pesos transf.", "$", "pesosTransf"),
    ...(pr.mp6 == null ? [] : [fila(etiquetaMp(pr, 6), "$", "mp6")]),
    ...(pr.mp12 == null ? [] : [fila(etiquetaMp(pr, 12), "$", "mp12")]),
  ];
}

function tablaMayoristaHtml(p) {
  const filas = filasMayoristaDe(p);
  if (!filas) return "";
  return `<span class="tabla-mayorista">
    <span class="tm-cab">Pago</span><span class="tm-cab">Descuento</span><span class="tm-cab">Tu precio</span>
    ${filas.map((f) => `<span>${f.tipo}</span><span class="tm-desc">${f.descuento ? `-${f.descuento}` : "-"}</span><strong>${f.precio}</strong>`).join("")}
  </span>`;
}
