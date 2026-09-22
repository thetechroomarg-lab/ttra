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
