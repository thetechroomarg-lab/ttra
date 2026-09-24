// Este script sirve dos contextos, igual que perfil.js:
// 1) /pedidos standalone (link-volver existe): carga apenas corre el script.
// 2) Panel embebido en index.html (panel-pedidos existe): NO carga nada
//    hasta que se llama a window.abrirPanelPedidos() (ver landing.js), y
//    "cerrar" oculta el panel en vez de navegar.
const panelPedidosEmbebido = document.getElementById("panel-pedidos");
const btnCerrarPanelPedidos = document.getElementById("btn-cerrar-panel-pedidos");
const overlayPedidosEmbebido = document.getElementById("overlay-perfil");
const tabPedidosEnCurso = document.getElementById("tab-pedidos-en-curso");
const tabPedidosHistorial = document.getElementById("tab-pedidos-historial");
const listaPedidosEnCurso = document.getElementById("lista-pedidos-en-curso");
const listaPedidosHistorial = document.getElementById("lista-pedidos-historial");
const modalEditarDireccionPedido = document.getElementById("modal-editar-direccion-pedido");
const formEditarDireccionPedido = document.getElementById("form-editar-direccion-pedido");
const pedidoDireccionInput = document.getElementById("pedido-direccion");
const pedidoPisoInput = document.getElementById("pedido-piso");
const pedidoDeptoInput = document.getElementById("pedido-depto");
const btnCancelarEditarDireccionPedido = document.getElementById("btn-cancelar-editar-direccion-pedido");
let pedidoEnEdicionId = null;

function cerrarPanelPedidos() {
  if (!panelPedidosEmbebido) return;
  panelPedidosEmbebido.classList.add("oculto");
  if (overlayPedidosEmbebido) overlayPedidosEmbebido.classList.add("oculto");
}

if (btnCerrarPanelPedidos) {
  btnCerrarPanelPedidos.addEventListener("click", cerrarPanelPedidos);
}
if (overlayPedidosEmbebido) {
  overlayPedidosEmbebido.addEventListener("click", cerrarPanelPedidos);
}

function formatearMonedaUsd(valor) {
  return `U$D ${Number(valor || 0).toLocaleString("es-AR", { maximumFractionDigits: 0 })}`;
}

function descripcionDetallePedido(pedido) {
  const items = pedido.detalle && pedido.detalle.length ? pedido.detalle : (pedido.productos || []).map((nombre) => ({ nombre }));
  return items.map((item) => `${item.nombre}${item.cantidad ? ` x${item.cantidad}` : ""}`).join(", ");
}

function tarjetaPedidoEnCurso(pedido) {
  const tarjeta = document.createElement("div");
  tarjeta.className = "item-pedido";
  const info = document.createElement("div");
  info.className = "item-pedido-info";
  const pisoDepto = [pedido.piso_entrega && `Piso ${pedido.piso_entrega}`, pedido.depto_entrega && `Depto ${pedido.depto_entrega}`].filter(Boolean).join(" · ");
  info.innerHTML = `<p><strong>Entrega: ${pedido.fecha_entrega || "sin fecha"}</strong></p>`
    + `<p>${descripcionDetallePedido(pedido)}</p>`
    + `<p>${formatearMonedaUsd(pedido.total_usd)}</p>`
    + (pedido.direccion_entrega ? `<p class="item-pedido-direccion">${pedido.direccion_entrega}${pisoDepto ? ` (${pisoDepto})` : ""}</p>` : "<p class=\"item-pedido-direccion\">Sin dirección cargada</p>");
  tarjeta.append(info);

  const acciones = document.createElement("div");
  acciones.className = "item-domicilio-acciones";

  const btnEditarDireccion = document.createElement("button");
  btnEditarDireccion.type = "button";
  btnEditarDireccion.textContent = "Editar dirección de entrega";
  btnEditarDireccion.addEventListener("click", () => {
    pedidoEnEdicionId = pedido.id;
    pedidoDireccionInput.value = pedido.direccion_entrega || "";
    pedidoPisoInput.value = pedido.piso_entrega || "";
    pedidoDeptoInput.value = pedido.depto_entrega || "";
    document.getElementById("pedido-direccion-error").textContent = "";
    modalEditarDireccionPedido.classList.add("visible");
  });
  acciones.append(btnEditarDireccion);

  const btnEliminar = document.createElement("button");
  btnEliminar.type = "button";
  btnEliminar.textContent = "Eliminar pedido";
  btnEliminar.addEventListener("click", async () => {
    if (!confirm("¿Eliminar este pedido en curso?")) return;
    await fetch(`/api/pedidos/${pedido.id}`, { method: "DELETE" });
    cargarPedidos();
  });
  acciones.append(btnEliminar);

  tarjeta.append(acciones);
  return tarjeta;
}

function tarjetaPedidoHistorial(pedido) {
  const tarjeta = document.createElement("div");
  tarjeta.className = "item-pedido";
  const info = document.createElement("div");
  info.className = "item-pedido-info";
  const fechaCompra = pedido.recibo_emitido_en ? new Date(pedido.recibo_emitido_en).toLocaleDateString("es-AR") : (pedido.fecha ? new Date(pedido.fecha).toLocaleDateString("es-AR") : "—");
  info.innerHTML = `<p><strong>Compra del ${fechaCompra}</strong></p>`
    + `<p>${descripcionDetallePedido(pedido)}</p>`
    + `<p>${formatearMonedaUsd(pedido.total_usd)}</p>`
    + (pedido.direccion_entrega ? `<p class="item-pedido-direccion">Entregado en: ${pedido.direccion_entrega}</p>` : "");
  tarjeta.append(info);

  if (pedido.tiene_recibo) {
    const acciones = document.createElement("div");
    acciones.className = "item-domicilio-acciones";
    const linkRecibo = document.createElement("a");
    linkRecibo.href = `/api/pedidos/${pedido.id}/recibo.pdf`;
    linkRecibo.target = "_blank";
    linkRecibo.rel = "noopener";
    linkRecibo.textContent = "Ver recibo";
    acciones.append(linkRecibo);
    tarjeta.append(acciones);
  }
  return tarjeta;
}

async function cargarPedidos() {
  try {
    const r = await fetch("/api/pedidos");
    if (r.status === 401) {
      window.location.href = "/login.html";
      return;
    }
    if (!r.ok) return;
    const datos = await r.json();
    listaPedidosEnCurso.replaceChildren();
    if (!datos.en_curso.length) {
      const vacio = document.createElement("p");
      vacio.className = "carrito-nota";
      vacio.textContent = "No tenés pedidos en curso.";
      listaPedidosEnCurso.append(vacio);
    } else {
      datos.en_curso.forEach((pedido) => listaPedidosEnCurso.append(tarjetaPedidoEnCurso(pedido)));
    }
    listaPedidosHistorial.replaceChildren();
    if (!datos.historial.length) {
      const vacio = document.createElement("p");
      vacio.className = "carrito-nota";
      vacio.textContent = "Todavía no tenés compras finalizadas.";
      listaPedidosHistorial.append(vacio);
    } else {
      datos.historial.forEach((pedido) => listaPedidosHistorial.append(tarjetaPedidoHistorial(pedido)));
    }
  } catch {
    // Si falla, las listas quedan vacías — el resto de la página sigue usable.
  }
}

tabPedidosEnCurso.addEventListener("click", () => {
  tabPedidosEnCurso.classList.add("activo");
  tabPedidosHistorial.classList.remove("activo");
  listaPedidosEnCurso.classList.remove("oculto");
  listaPedidosHistorial.classList.add("oculto");
});
tabPedidosHistorial.addEventListener("click", () => {
  tabPedidosHistorial.classList.add("activo");
  tabPedidosEnCurso.classList.remove("activo");
  listaPedidosHistorial.classList.remove("oculto");
  listaPedidosEnCurso.classList.add("oculto");
});

function cerrarModalEditarDireccionPedido() {
  pedidoEnEdicionId = null;
  modalEditarDireccionPedido.classList.remove("visible");
}

btnCancelarEditarDireccionPedido.addEventListener("click", cerrarModalEditarDireccionPedido);

formEditarDireccionPedido.addEventListener("submit", async (e) => {
  e.preventDefault();
  const errorEl = document.getElementById("pedido-direccion-error");
  errorEl.textContent = "";
  if (!pedidoEnEdicionId) return;
  try {
    const r = await fetch(`/api/pedidos/${pedidoEnEdicionId}/direccion`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        direccion_entrega: pedidoDireccionInput.value,
        piso_entrega: pedidoPisoInput.value,
        depto_entrega: pedidoDeptoInput.value,
      }),
    });
    const datos = await r.json();
    if (!r.ok) {
      errorEl.textContent = datos.error || datos.detail || "No pude guardar la dirección";
      return;
    }
    cerrarModalEditarDireccionPedido();
    cargarPedidos();
  } catch {
    errorEl.textContent = "No pude conectar, probá de nuevo en un momento";
  }
});

if (panelPedidosEmbebido) {
  // Embebido: no se carga nada hasta que el usuario realmente abre el
  // panel (ver linkIrAPedidos en landing.js).
  window.abrirPanelPedidos = function abrirPanelPedidos() {
    // Comparten la misma franja "flotante sobre la home blureada" que el
    // carrito y el perfil -no tiene sentido ver más de uno a la vez.
    if (typeof cerrarCarrito === "function") cerrarCarrito();
    if (typeof cerrarPanelPerfil === "function") cerrarPanelPerfil();
    if (typeof sincronizarLimiteCarrito === "function") sincronizarLimiteCarrito();
    panelPedidosEmbebido.classList.remove("oculto");
    if (overlayPedidosEmbebido) overlayPedidosEmbebido.classList.remove("oculto");
    cargarPedidos();
  };
} else {
  // Standalone (/pedidos): comportamiento de siempre.
  cargarPedidos();
}
