// Retención de Ingresos Brutos de Córdoba sobre lo cobrado con tarjeta.
const IIBB_CORDOBA = 0.0475;
// La financiación se calcula sobre la transferencia en pesos y solo se ofrece
// en productos con transferencia de hasta $500.000.
const CUOTAS_TOPE_TRANSF = 500000;

// Mercado Pago, Point Tap, crédito en cuotas sin interés, cobro en el momento:
// 6,29% de cobro + el costo de las cuotas (18,69% en 6, 32,29% en 12), todo
// + IVA, más IIBB, sobre lo que se cobra.
const MP_RECARGO_CUOTAS = {
  6: (0.0629 + 0.1869) * 1.21 + IIBB_CORDOBA,
  12: (0.0629 + 0.3229) * 1.21 + IIBB_CORDOBA,
};

// Plan Z de Naranja X: 3 cuotas sin interés con tarjeta Naranja X, costo de
// financiación bonificado durante octubre 2026. Queda la comisión de cobro de
// Nave + IVA, más IIBB. PROVISORIO: comisión igual a la de MP hasta tener la
// real de Nave.
const PLAN_Z_COMISION_NAVE = 0.0629;
const PLAN_Z_RECARGO = PLAN_Z_COMISION_NAVE * 1.21 + IIBB_CORDOBA;
const PLAN_Z_VENCE = Date.parse("2026-11-01T00:00:00-03:00");

function financiable(pesosTransf) {
  return pesosTransf != null && pesosTransf <= CUOTAS_TOPE_TRANSF;
}

function precioMp(pesosTransf, cuotas) {
  if (!financiable(pesosTransf)) return null;
  return Math.ceil(pesosTransf / (1 - MP_RECARGO_CUOTAS[cuotas]));
}

function precioPlanZ(pesosTransf) {
  if (!financiable(pesosTransf) || Date.now() >= PLAN_Z_VENCE) return null;
  return Math.ceil(pesosTransf / (1 - PLAN_Z_RECARGO));
}

// Shared payment amounts for the storefront and cart. Round fees upward.
function preciosDe(p) {
  const dolares = p.usd ?? null;
  const pesos = p.pesos ?? null;
  const pesosTransf = pesos == null ? null : Math.ceil(pesos / 0.97);
  const planZ = precioPlanZ(pesosTransf);
  const mp6 = precioMp(pesosTransf, 6);
  const mp12 = precioMp(pesosTransf, 12);
  return {
    dolares,
    bancoUsa: dolares == null ? null : Math.ceil(dolares / 0.975),
    usdt: dolares == null ? null : Math.ceil(dolares / 0.99),
    pesos,
    pesosTransf,
    planZ,
    planZCuota: planZ == null ? null : Math.ceil(planZ / 3),
    mp6,
    mp6Cuota: mp6 == null ? null : Math.ceil(mp6 / 6),
    mp12,
    mp12Cuota: mp12 == null ? null : Math.ceil(mp12 / 12),
  };
}

// Líneas de financiación disponibles para un producto, en el orden en que se
// muestran: "Plan Z (3 cuotas de $ X)" con su total en pesos.
const PLANES_CUOTAS = [["planZ", "Plan Z", 3], ["mp6", "MP", 6], ["mp12", "MP", 12]];
function cuotasDe(precios) {
  return PLANES_CUOTAS.filter(([clave]) => precios[clave] != null).map(([clave, nombre, cuotas]) => ({
    clave,
    total: precios[clave],
    etiqueta: `${nombre} (${cuotas} cuotas de $ ${Number(precios[`${clave}Cuota`]).toLocaleString("es-AR")})`,
  }));
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
    ...cuotasDe(pr).map((c) => fila(c.etiqueta, "$", c.clave)),
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
