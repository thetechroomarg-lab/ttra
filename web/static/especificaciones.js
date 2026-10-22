/* Especificaciones leídas del nombre del producto, para los filtros del
   catálogo. Los productos no traen campos de RAM, disco, etc.: solo se
   devuelve lo que el nombre dice de forma inequívoca. Si un dato no está (los
   iPhone no informan RAM, una mochila no tiene procesador), queda sin valor y
   el producto no aparece al filtrar por ese dato. Nada se completa a ojo. */
(function (global) {
  "use strict";

  // Cada filtro: clave, etiqueta y cómo ordenar/mostrar sus valores.
  const FILTROS = {
    procesador: { etiqueta: "Procesador" },
    ram: { etiqueta: "RAM", numerico: true },
    almacenamiento: { etiqueta: "Memoria", numerico: true },
    disco: { etiqueta: "Disco", numerico: true },
    pantalla: { etiqueta: "Pantalla", numerico: true },
    grafica: { etiqueta: "Gráfica de video" },
  };

  // Qué filtros tiene cada sección del catálogo.
  const FILTROS_POR_SECCION = {
    "Celulares": ["ram", "almacenamiento"],
    "Tablets": ["ram", "almacenamiento"],
    "Notebooks y Macbooks": ["procesador", "ram", "disco", "pantalla", "grafica"],
  };

  const formatoGb = (gb) => (gb >= 1024 && gb % 1024 === 0 ? `${gb / 1024} TB` : `${gb} GB`);

  // "16GB", "1TB", "6 GB": valor en GB y lo que viene después ("RAM", "SSD").
  function capacidades(texto) {
    const lista = [];
    const re = /(\d+(?:[.,]\d+)?)\s*(GB|TB)\b\s*([A-Z]*)/g;
    let m;
    while ((m = re.exec(texto))) {
      const numero = Number(m[1].replace(",", "."));
      if (!Number.isFinite(numero)) continue;
      lista.push({ gb: m[2] === "TB" ? numero * 1024 : numero, sufijo: m[3] });
    }
    return lista;
  }

  // Celulares y tablets: "8GB 256GB" es RAM + memoria; "256GB" solo, memoria.
  function deMovil(texto) {
    const caps = capacidades(texto);
    const ram = caps.find((c) => c.sufijo === "RAM");
    const resto = caps.filter((c) => c !== ram);
    const mayor = resto.length ? Math.max(...resto.map((c) => c.gb)) : null;
    // A lone capacity is the storage only when it can't be RAM (iPhone 17 256GB).
    const almacenamiento = mayor != null && (resto.length > 1 || ram || mayor >= 32) && mayor >= 16 ? mayor : null;
    let ramGb = ram ? ram.gb : null;
    if (ramGb == null && almacenamiento != null) {
      const chicas = resto.filter((c) => c.gb < almacenamiento && c.gb <= 24 && c.sufijo !== "SSD");
      if (chicas.length === 1) ramGb = chicas[0].gb;
    }
    return { ram: ramGb, almacenamiento };
  }

  const GPU = /\b(?:NVIDIA\s+)?(?:GEFORCE\s+)?(?:RTX|GTX)\s*\d{3,4}\w*(?:\s+TI)?(?:\s*\d+\s*(?:GB|MB))?|\bRADEON\s+RX\s*\d{3,4}\w*(?:\s*\d+\s*(?:GB|MB))?/g;

  function procesadorDe(texto, esMac) {
    let m;
    if (esMac && (m = texto.match(/\bM([1-9])(?:\s+(PRO|MAX|ULTRA))?\b/))) {
      return `Apple M${m[1]}${m[2] ? ` ${m[2][0]}${m[2].slice(1).toLowerCase()}` : ""}`;
    }
    if (esMac && (m = texto.match(/\bA(1\d)(\s+PRO)?\b/))) return `Apple A${m[1]}${m[2] ? " Pro" : ""}`;
    if ((m = texto.match(/\b(?:CORE|INTEL)\s+ULTRA\s+([579])\b/))) return `Intel Core Ultra ${m[1]}`;
    if ((m = texto.match(/\b(?:CORE\s+)?I([3579])[-\s]?\d{4,5}[A-Z]*\b/)) || (m = texto.match(/\bCORE\s+I([3579])\b/))) return `Intel Core i${m[1]}`;
    if ((m = texto.match(/\bCORE\s+([3579])[-\s]+\d{3}[A-Z]*\b/))) return `Intel Core ${m[1]}`;
    if ((m = texto.match(/\bRYZEN\s*(?:PRO\s*)?([3579])\b/))) return `AMD Ryzen ${m[1]}`;
    if ((m = texto.match(/\bINTEL\s+(?:CELERON\s+)?N(\d{2,3})\b/))) return `Intel N${m[1]}`;
    return null;
  }

  function pantallaDe(texto, esMac) {
    const m = texto.match(/\b(1\d(?:[.,]\d)?)\s*(?:"|''|”|¨|PULGADAS\b|PULG\b)/);
    if (m) return Number(m[1].replace(",", "."));
    const mac = esMac && texto.match(/\bMACBOOK\s+(?:AIR|PRO|NEO)\s+(1[3-6])\b/);
    return mac ? Number(mac[1]) : null;
  }

  function deComputadora(texto, producto) {
    const esMac = producto.categoria === "Mac" || /\bMAC\s?(?:BOOK|MINI)\b/.test(texto);
    const dedicada = /\b(?:RTX|GTX|GEFORCE|NVIDIA)\b|\bRADEON\s+RX\b/.test(texto);
    const sinGpu = texto.replace(GPU, " ");
    const caps = capacidades(sinGpu);
    const procesador = procesadorDe(sinGpu, esMac);
    const ramToken = caps.find((c) => c.sufijo === "RAM");
    const discoToken = caps.find((c) => /^(SSD|HDD|EMMC|NVME)$/.test(c.sufijo));
    const grandes = caps.filter((c) => c !== ramToken && c.gb >= 128);
    const disco = discoToken ? discoToken.gb : (grandes.length ? Math.max(...grandes.map((c) => c.gb)) : null);
    let ram = ramToken ? ramToken.gb : null;
    if (ram == null) {
      const chicas = caps.filter((c) => c.gb <= 128 && c.gb !== disco && !/^(SSD|HDD|EMMC|NVME)$/.test(c.sufijo));
      if (chicas.length === 1) ram = chicas[0].gb;
    }
    // Sin procesador ni RAM no es una computadora (mochilas, fundas, cargadores).
    if (!procesador && ram == null) return {};
    return {
      procesador,
      ram,
      disco,
      pantalla: pantallaDe(texto, esMac),
      grafica: dedicada ? "dedicada" : "integrada",
    };
  }

  function especificacionesDe(producto, seccion) {
    const texto = String(producto?.nombre || "").toUpperCase();
    if (seccion === "Notebooks y Macbooks") return deComputadora(texto, producto);
    if (seccion === "Celulares" || seccion === "Tablets") return deMovil(texto);
    return {};
  }

  function etiquetaValor(clave, valor) {
    if (clave === "ram" || clave === "almacenamiento" || clave === "disco") return formatoGb(valor);
    if (clave === "pantalla") return `${String(valor).replace(".", ",")}"`;
    if (clave === "grafica") return valor === "dedicada" ? "Con gráfica dedicada" : "Sin gráfica dedicada";
    return String(valor);
  }

  // Valores presentes en los productos, con cuántos productos tiene cada uno.
  function opcionesDe(productos, seccion, clave) {
    const cuenta = new Map();
    for (const p of productos) {
      const valor = especificacionesDe(p, seccion)[clave];
      if (valor == null) continue;
      cuenta.set(valor, (cuenta.get(valor) || 0) + 1);
    }
    const valores = [...cuenta.keys()];
    if (FILTROS[clave]?.numerico) valores.sort((a, b) => a - b);
    else valores.sort((a, b) => String(a).localeCompare(String(b), "es", { numeric: true }));
    return valores.map((valor) => ({ valor, etiqueta: etiquetaValor(clave, valor), cantidad: cuenta.get(valor) }));
  }

  const api = { FILTROS, FILTROS_POR_SECCION, especificacionesDe, opcionesDe, etiquetaValor };
  global.TTRAEspecificaciones = api;
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
