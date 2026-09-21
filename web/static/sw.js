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

// Web Push del panel del cadete (ver web/push_cadete.py): el payload viaja
// como JSON {titulo, cuerpo, url}. Solo el cadete llega a suscribirse (no
// hay UI de suscripción en las páginas de admin que comparten este mismo
// sw.js), así que en la práctica esto solo dispara ahí.
self.addEventListener("push", (event) => {
  let datos = {};
  try {
    datos = event.data ? event.data.json() : {};
  } catch {
    datos = { titulo: "The Tech Room Arg", cuerpo: event.data ? event.data.text() : "" };
  }
  const titulo = datos.titulo || "The Tech Room Arg";
  event.waitUntil(
    self.registration.showNotification(titulo, {
      body: datos.cuerpo || "",
      icon: "/icon-192.png",
      badge: "/icon-192.png",
      data: { url: datos.url || "/admin/cadete" },
    })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = event.notification.data?.url || "/admin/cadete";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((lista) => {
      const abierta = lista.find((c) => c.url.includes(url));
      if (abierta) return abierta.focus();
      return self.clients.openWindow(url);
    })
  );
});
