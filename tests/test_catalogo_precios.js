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
  assert.match(html, /<strong>U\$D 100 \(contado\)<\/strong>/);
  assert.match(html, /U\$D 103 \(Transf\. USA\)/);
  assert.match(html, /USDT 102/);
  assert.match(html, /\$ 150\.000 Pesos contado\./);
  assert.match(html, /\$ 155\.000 Pesos transf\./);
});

test('missing dollar prices do not become zero or NaN quotes', () => {
  for (const product of [{}, { usd: null }]) {
    const html = context.tarjetaProducto(product);
    assert.match(html, /U\$D - \(Transf\. USA\)/);
    assert.match(html, /USDT -/);
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

test('catalog cards restore image, specification and share actions', () => {
  const nombre = 'Samsung S26 Ultra';
  const html = context.tarjetaProducto({ nombre, usd: 100 });
  assert.match(html, /aria-label="Ver fotos en Google Imágenes"/);
  assert.ok(html.includes('https://www.google.com/search?tbm=isch&amp;q=Samsung%20S26%20Ultra'));
  assert.ok(html.includes('https://www.google.com/search?q=Samsung%20S26%20Ultra%20especificaciones'));
  assert.match(html, /aria-label="Compartir producto"/);
});

test('condition filter applies only to Apple phones', () => {
  assert.equal(context.permiteFiltroCondicion('Celulares', 'Apple'), true);
  for (const [category, brand] of [['Todos', 'Apple'], ['Tablets', 'Apple'], ['Celulares', 'Samsung'], ['Celulares', '']]) {
    assert.equal(context.permiteFiltroCondicion(category, brand), false);
  }
});

test('used phones include supplier battery information and refurbished models', () => {
  for (const p of [{nombre:'iPhone 13 USADO'}, {nombre:'iPhone 14', colores:['Blue 87%']}, {nombre:'iPhone reacondicionado'}]) {
    assert.equal(context.condicionProducto(p), 'usado');
  }
  assert.equal(context.condicionProducto({nombre:'iPhone 16 128GB', colores:['Black']}), 'nuevo');
});

test('CPO stays separate from new and used phones', () => {
  assert.equal(context.condicionProducto({nombre:'iPhone 11 CPO', colores:['Black']}), 'cpo');
});

test('single-color products keep a dropdown with exactly their one option', () => {
  const html = context.tarjetaProducto({nombre:'iPhone 16', colores:['Black']});
  assert.match(html, /Colores disponibles:/);
  assert.match(html, /<select/);
  assert.equal((html.match(/<option /g) || []).length, 2);
  assert.match(html, /value="" disabled selected hidden>Elegí una opción de color/);
  assert.match(html, /value="Black">Black/);
  assert.match(html, /<button class="btn-agregar"[^>]*disabled/);
});

test('used variants always use the battery label, even with only one option', () => {
  const html = context.tarjetaProducto({nombre:'iPhone 13 (Usado)', colores:['Blue 93%']});
  assert.match(html, /Color y % de batería:/);
  assert.equal((html.match(/<option /g) || []).length, 2);
  assert.match(html, /value="" disabled selected hidden>Elegí una opción de color/);
  assert.match(html, /value="Blue 93%">Blue 93%/);
});
