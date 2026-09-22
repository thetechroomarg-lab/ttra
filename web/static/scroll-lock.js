// Keep the page in place while a floating panel or dialog owns the scroll.
// Read the actual open overlays so closing one dialog cannot unlock another.
(() => {
  const root = document.documentElement;
  const body = document.body;
  let savedScrollY = null;

  function hasOpenOverlay() {
    const cart = document.getElementById("overlay-carrito");
    const profile = document.getElementById("overlay-perfil");
    const share = document.getElementById("rc-panel-compartir");
    return Boolean(
      (cart && !cart.classList.contains("oculto")) ||
      (profile && !profile.classList.contains("oculto")) ||
      document.querySelector(".rc-logout-overlay.visible") ||
      document.querySelector(".rc-terminos-overlay.visible") ||
      (share && !share.hidden)
    );
  }

  function syncScrollLock() {
    if (hasOpenOverlay()) {
      if (savedScrollY !== null) return;
      savedScrollY = window.scrollY;
      body.style.setProperty("--ttra-scroll-lock-top", `${-savedScrollY}px`);
      body.style.setProperty("--ttra-scroll-lock-width", `${root.clientWidth}px`);
      root.classList.add("ttra-scroll-locked");
      body.classList.add("ttra-scroll-locked");
      return;
    }
    if (savedScrollY === null) return;
    const restoreY = savedScrollY;
    savedScrollY = null;
    root.classList.remove("ttra-scroll-locked");
    body.classList.remove("ttra-scroll-locked");
    body.style.removeProperty("--ttra-scroll-lock-top");
    body.style.removeProperty("--ttra-scroll-lock-width");
    // Classic uses smooth anchor scrolling; restoring this position is immediate.
    const previousBehavior = root.style.scrollBehavior;
    root.style.scrollBehavior = "auto";
    window.scrollTo(0, restoreY);
    root.style.scrollBehavior = previousBehavior;
  }

  new MutationObserver(syncScrollLock).observe(body, {
    attributes: true,
    attributeFilter: ["class", "hidden"],
    childList: true,
    subtree: true,
  });
  syncScrollLock();
})();
