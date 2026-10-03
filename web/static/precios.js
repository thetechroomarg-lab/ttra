// Shared payment amounts for the storefront and cart. Round fees upward.
function preciosDe(p) {
  const dolares = p.usd ?? null;
  const pesos = p.pesos ?? null;
  return {
    dolares,
    bancoUsa: dolares == null ? null : Math.ceil(dolares / 0.975),
    usdt: dolares == null ? null : Math.ceil(dolares / 0.99),
    pesos,
    pesosTransf: pesos == null ? null : Math.ceil(pesos / 0.97),
  };
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
