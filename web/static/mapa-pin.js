// Mini mapa con un pin arrastrable para marcar la puerta exacta de un domicilio.
// Usa la API de Google Maps que ya cargó el autocompletado de direcciones, y
// solo se muestra después de elegir una dirección (cada mapa visible es una
// carga facturada por Google).
(() => {
  function crear(contenedor, alMover) {
    let mapa = null;
    let pin = null;

    async function mostrar(lat, lng) {
      if (!contenedor || lat == null || lng == null || !window.google?.maps?.importLibrary) return;
      const posicion = { lat: Number(lat), lng: Number(lng) };
      contenedor.hidden = false;
      if (!mapa) {
        const { Map } = await google.maps.importLibrary("maps");
        const { Marker } = await google.maps.importLibrary("marker");
        const lienzo = contenedor.querySelector(".mapa-pin-lienzo");
        mapa = new Map(lienzo, {
          center: posicion,
          zoom: 17,
          disableDefaultUI: true,
          zoomControl: true,
          gestureHandling: "greedy",
          clickableIcons: false,
        });
        pin = new Marker({ map: mapa, position: posicion, draggable: true, title: "Tu ubicación exacta" });
        const avisar = (latLng) => alMover({ lat: latLng.lat(), lng: latLng.lng() });
        pin.addListener("dragend", () => avisar(pin.getPosition()));
        mapa.addListener("click", (evento) => {
          pin.setPosition(evento.latLng);
          avisar(evento.latLng);
        });
        return;
      }
      pin.setPosition(posicion);
      mapa.setCenter(posicion);
    }

    function ocultar() {
      if (contenedor) contenedor.hidden = true;
    }

    return { mostrar, ocultar };
  }

  window.TTRAMapaPin = { crear };
})();
