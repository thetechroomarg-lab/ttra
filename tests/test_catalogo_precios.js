const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const { join } = require('node:path');

const staticPath = join(__dirname, '../web/static');
const pricing = readFileSync(join(staticPath, 'precios.js'), 'utf8');
const catalog = readFileSync(join(staticPath, 'catalogo.js'), 'utf8');

// Evaluate the real render functions without starting catalog network requests.
const context = {
  document: {
    createElement: () => ({
      set textContent(value) { this.innerHTML = String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;'); },
    }),
  },
};
runInNewContext(pricing + catalog.slice(0, catalog.indexOf('async function cargarCatalogo()')), context);

test('bank USD and USDT use existing fee rules and round upward', () => {
  for (const [usd, bank, usdt] of [[100, 103, 102], [975, 1000, 985], [1650, 1693, 1667]]) {
    const prices = context.preciosDe({ usd });
    assert.equal(prices.bancoUsa, bank);
    assert.equal(prices.usdt, usdt);
  }
});

test('catalog renders all five payment amounts, preserving the supplied peso prices', () => {
  const html = context.tarjetaProducto({ usd: 100, pesos: 150000, transferencia: 155000 });
  assert.match(html, /U\$D 100 contado/);
  assert.match(html, /U\$D 103 transferencia banco USA/);
  assert.match(html, /102 USDT/);
  assert.match(html, /\$ 150\.000 contado/);
  assert.match(html, /\$ 155\.000 transferencia/);
});

test('missing dollar prices do not become zero or NaN quotes', () => {
  for (const product of [{}, { usd: null }]) {
    const html = context.tarjetaProducto(product);
    assert.match(html, /U\$D - transferencia banco USA/);
    assert.match(html, /- USDT/);
    assert.doesNotMatch(html, /NaN|undefined/);
  }
});

test('home and catalog load shared pricing before their entry script', () => {
  for (const [page, entry] of [['index.html', 'landing.js'], ['catalogo.html', 'catalogo.js']]) {
    const html = readFileSync(join(staticPath, page), 'utf8');
    const dependency = html.indexOf('<script src="precios.js">');
    assert.ok(dependency >= 0);
    assert.ok(dependency < html.indexOf(`<script src="${entry}">`));
  }
});
