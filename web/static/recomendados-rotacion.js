// Rotación de los recomendados de la home: sale del catálogo vigente, al azar,
// y recuerda lo ya mostrado durante la sesión del navegador (sessionStorage)
// para que un mismo producto no vuelva a aparecer hasta haber pasado por el
// resto del catálogo. Al agotarse, arranca otra vuelta y no repite de entrada
// lo último que se vio.
(function (raiz) {
  const CLAVE = "ttra_reco_vistos_v1";
  const MEMORIA_AL_RECICLAR = 40;
  let memoriaVolatil = [];

  function leerVistos(storage) {
    try {
      const guardado = JSON.parse(storage.getItem(CLAVE) || "[]");
      return Array.isArray(guardado) ? guardado.filter((n) => typeof n === "string") : [];
    } catch {
      return memoriaVolatil.slice();
    }
  }

  function guardarVistos(storage, vistos) {
    memoriaVolatil = vistos.slice();
    try { storage.setItem(CLAVE, JSON.stringify(vistos)); } catch {}
  }

  function barajar(lista, azar) {
    const copia = lista.slice();
    for (let i = copia.length - 1; i > 0; i--) {
      const j = Math.floor(azar() * (i + 1));
      [copia[i], copia[j]] = [copia[j], copia[i]];
    }
    return copia;
  }

  // catalogo: productos elegibles (con nombre). preferidos: productos que se
  // priorizan hasta la mitad de los lugares (recomendación personalizada).
  function elegir({ catalogo, cantidad, preferidos = [], storage = raiz.sessionStorage, azar = Math.random }) {
    const porNombre = new Map();
    for (const p of catalogo || []) if (p && p.nombre && !porNombre.has(p.nombre)) porNombre.set(p.nombre, p);
    const total = porNombre.size;
    if (!total || cantidad <= 0) return [];

    let vistos = leerVistos(storage).filter((n) => porNombre.has(n));
    let libres = [...porNombre.keys()].filter((n) => !vistos.includes(n));
    if (libres.length < cantidad) {
      const memoria = Math.max(0, Math.min(MEMORIA_AL_RECICLAR, Math.floor((total - cantidad) / 2)));
      vistos = memoria ? vistos.slice(-memoria) : [];
      libres = [...porNombre.keys()].filter((n) => !vistos.includes(n));
    }

    const objetoPreferido = new Map();
    for (const p of preferidos) if (p && porNombre.has(p.nombre)) objetoPreferido.set(p.nombre, p);
    const libresSet = new Set(libres);
    const preferidosLibres = [...objetoPreferido.keys()].filter((n) => libresSet.has(n));
    const nPref = Math.min(preferidosLibres.length, Math.round(cantidad / 2));
    const elegidos = barajar(preferidosLibres, azar).slice(0, nPref);
    const yaElegidos = new Set(elegidos);
    const resto = barajar(libres.filter((n) => !yaElegidos.has(n)), azar);
    for (const n of resto) {
      if (elegidos.length >= cantidad) break;
      elegidos.push(n);
    }
    // Catálogo muy chico: si no alcanzó, completa con lo ya visto.
    if (elegidos.length < cantidad) {
      const usados = new Set(elegidos);
      for (const n of barajar([...porNombre.keys()], azar)) {
        if (elegidos.length >= cantidad) break;
        if (!usados.has(n)) { elegidos.push(n); usados.add(n); }
      }
    }

    const finales = barajar(elegidos, azar);
    guardarVistos(storage, vistos.filter((n) => !finales.includes(n)).concat(finales).slice(-total));
    return finales.map((n) => objetoPreferido.get(n) || porNombre.get(n));
  }

  const api = { elegir, CLAVE };
  raiz.TTRARotacion = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
