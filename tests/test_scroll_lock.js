const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { runInNewContext } = require('node:vm');
const { join } = require('node:path');

function fixture() {
  const classes = () => {
    const values = new Set();
    return {
      add: (name) => values.add(name),
      remove: (name) => values.delete(name),
      contains: (name) => values.has(name),
    };
  };
  const style = () => {
    const values = new Map();
    return {
      values,
      scrollBehavior: '',
      setProperty: (name, value) => values.set(name, value),
      removeProperty: (name) => values.delete(name),
    };
  };
  const elements = new Map([
    ['overlay-carrito', { classList: classes() }],
    ['overlay-perfil', { classList: classes() }],
    ['rc-terminos-mayorista', { classList: classes() }],
    ['rc-panel-compartir', { hidden: true }],
  ]);
  elements.get('overlay-carrito').classList.add('oculto');
  elements.get('overlay-perfil').classList.add('oculto');
  const root = { classList: classes(), style: style(), clientWidth: 1200 };
  const body = { classList: classes(), style: style() };
  const scrollCalls = [];
  const window = { scrollY: 640, scrollTo: (...args) => scrollCalls.push(args) };
  let observer;
  class MutationObserver {
    constructor(callback) { observer = callback; }
    observe() {}
  }
  const document = {
    documentElement: root,
    body,
    getElementById: (id) => elements.get(id),
    querySelector: (selector) => selector === '.rc-logout-overlay.visible' &&
      elements.get('rc-terminos-mayorista').classList.contains('visible')
      ? elements.get('rc-terminos-mayorista') : null,
  };
  const source = readFileSync(join(__dirname, '../web/static/scroll-lock.js'), 'utf8');
  runInNewContext(source, { document, window, MutationObserver });
  return { elements, root, body, window, scrollCalls, sync: () => observer() };
}

test('profile locks the background and restores its exact scroll position', () => {
  const page = fixture();
  page.elements.get('overlay-perfil').classList.remove('oculto');
  page.sync();
  assert.equal(page.root.classList.contains('ttra-scroll-locked'), true);
  assert.equal(page.body.classList.contains('ttra-scroll-locked'), true);
  assert.equal(page.body.style.values.get('--ttra-scroll-lock-top'), '-640px');
  assert.equal(page.body.style.values.get('--ttra-scroll-lock-width'), '1200px');
  page.elements.get('overlay-perfil').classList.add('oculto');
  page.sync();
  assert.equal(page.root.classList.contains('ttra-scroll-locked'), false);
  assert.deepEqual(page.scrollCalls, [[0, 640]]);
  assert.equal(page.body.style.values.size, 0);
});

test('closing one of multiple overlays keeps the page locked', () => {
  const page = fixture();
  page.elements.get('overlay-carrito').classList.remove('oculto');
  page.sync();
  page.elements.get('rc-terminos-mayorista').classList.add('visible');
  page.sync();
  page.elements.get('overlay-carrito').classList.add('oculto');
  page.sync();
  assert.equal(page.root.classList.contains('ttra-scroll-locked'), true);
  assert.equal(page.scrollCalls.length, 0);
  page.elements.get('rc-terminos-mayorista').classList.remove('visible');
  page.sync();
  assert.deepEqual(page.scrollCalls, [[0, 640]]);
});

test('dynamic share dialog also locks and releases the background', () => {
  const page = fixture();
  page.elements.get('rc-panel-compartir').hidden = false;
  page.sync();
  assert.equal(page.root.classList.contains('ttra-scroll-locked'), true);
  page.elements.get('rc-panel-compartir').hidden = true;
  page.sync();
  assert.equal(page.root.classList.contains('ttra-scroll-locked'), false);
});
