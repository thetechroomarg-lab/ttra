// Qué productos recorre la pizarra de la home (pizarra.js).
// Antes tomaba el primer producto de cada sección en orden de catálogo, así
// que mostraba SIEMPRE los mismos seis. Ahora arma un mazo al azar en cada
// visita: solo productos con foto, nunca usados/CPO, mezclando familias
// (iPhone, Android, Mac, notebooks, iPad/tablets, accesorios, gaming, electro)
// sin dos seguidos de la misma, y recuerda en el navegador lo ya mostrado para
// que la próxima visita arranque con otros.
(function (raiz) {
  const CLAVE = "ttra_pizarra_vistos_v1";
  const MAX_VISTOS = 400;
  const EXCLUIR = /usad|cpo|swap|sin caja|caja abierta|abollad/i;

  function familiaDe(seccion, p) {
    const texto = `${p.nombre || ""} ${p.marca || ""}`;
    if (seccion === "Celulares") return p.marca === "Apple" || /iphone/i.test(texto) ? "iPhone" : "Android";
    if (seccion === "Notebooks y Macbooks") return /macbook|mac mini|imac/i.test(texto) ? "Mac" : "Notebooks";
    return seccion;
  }

  function esElegible(p, tieneImagen) {
    if (!p || !p.nombre || p.usd == null || p.pesos == null) return false;
    if (EXCLUIR.test(p.nombre) || /usado|cpo/i.test(String(p.categoria || ""))) return false;
    return tieneImagen(p);
  }

  function barajar(lista, azar) {
    const copia = lista.slice();
    for (let i = copia.length - 1; i > 0; i--) {
      const j = Math.floor(azar() * (i + 1));
      [copia[i], copia[j]] = [copia[j], copia[i]];
    }
    return copia;
  }

  // Los no vistos primero (al azar), después los ya vistos (también al azar).
  function ordenar(lista, vistos, azar) {
    return barajar(lista.filter((x) => !vistos.has(x.producto.nombre)), azar)
      .concat(barajar(lista.filter((x) => vistos.has(x.producto.nombre)), azar));
  }

  function armarMazo({ secciones, tieneImagen = () => true, vistos = new Set(), azar = Math.random, tamano = 24 }) {
    const porFamilia = new Map();
    const nombres = new Set();
    for (const [seccion, lista] of Object.entries(secciones || {})) {
      for (const p of lista || []) {
        if (!esElegible(p, tieneImagen) || nombres.has(p.nombre)) continue;
        nombres.add(p.nombre);
        const familia = familiaDe(seccion, p);
        if (!porFamilia.has(familia)) porFamilia.set(familia, []);
        porFamilia.get(familia).push({ seccion, producto: p, familia });
      }
    }
    const colas = new Map([...porFamilia].map(([f, l]) => [f, ordenar(l, vistos, azar)]));
    const mazo = [];
    let ultima = null;
    while (mazo.length < tamano && [...colas.values()].some((c) => c.length)) {
      let ronda = barajar([...colas.keys()].filter((f) => colas.get(f).length), azar);
      // Dos de la misma familia seguidos no: el primero de la ronda no repite al último.
      if (ronda.length > 1 && ronda[0] === ultima) ronda.push(ronda.shift());
      for (const f of ronda) {
        if (mazo.length >= tamano) break;
        mazo.push(colas.get(f).shift());
        ultima = f;
      }
    }
    return mazo;
  }

  function leerVistos(storage) {
    try {
      const guardado = JSON.parse(storage.getItem(CLAVE) || "[]");
      return new Set(Array.isArray(guardado) ? guardado.filter((n) => typeof n === "string") : []);
    } catch {
      return new Set();
    }
  }

  function marcarVisto(storage, nombre) {
    try {
      const lista = [...leerVistos(storage)].filter((n) => n !== nombre);
      lista.push(nombre);
      storage.setItem(CLAVE, JSON.stringify(lista.slice(-MAX_VISTOS)));
    } catch {}
  }

  const api = { armarMazo, familiaDe, leerVistos, marcarVisto, CLAVE };
  raiz.TTRAPizarraSeleccion = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
