// web/static/sw.js — service worker mínimo, solo para que el navegador
// ofrezca instalar el sitio como app (PWA). A propósito no cachea nada:
// precios, catálogo y JS/CSS tienen que llegar siempre frescos, así que
// cada request pasa directo a la red tal cual.

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", (event) => {
  event.respondWith(fetch(event.request));
});
