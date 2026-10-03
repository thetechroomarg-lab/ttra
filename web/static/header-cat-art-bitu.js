// Bitu: misma anatomía que catArtwork, recoloreada toda a negro -sin
// manchitas- con ojos amarillos -ya venían así en el dibujo base, no hizo
// falta tocarlos-.
import {catArtwork} from './header-cat-art.js';

const RECOLOR = [
  // Base del cuerpo/patas/pecho -> negro.
  ['#fffdf8', '#161616'], ['#fffdf9', '#161616'], ['#f1eee7', '#161616'],
  ['#d8cfc4', '#050505'],
  // Orejas/cola -> gris muy oscuro, apenas se distingue del negro (da volumen).
  ['#c9a581', '#201d1a'], ['#c4a07c', '#201d1a'], ['#b68e6b', '#0d0b09'],
  ['#eee8df', '#201d1a'], ['#f1dfd6', '#201d1a'], ['#eac5b5', '#201d1a'],
  ['#e9e3d9', '#000000'], ['#efd2c9', '#201d1a'],
  // Nariz/lengua/almohadillas: tonos oscuros cálidos, no puro negro (se lee mejor).
  ['#c98c89', '#2a1414'], ['#e5a0a1', '#b06a5f'], ['#e2b0aa', '#3a1f1f'],
  // Trazos/contornos -> negro.
  ['#775c4c', '#000000'], ['#705343', '#000000'], ['#8f7971', '#000000'],
  ['#ab9b8d', '#3a3a3a'], ['#e5b7a0', '#4a4a4a'], ['#302a25', '#000000'],
];

export const bituArtwork = RECOLOR.reduce(
  (svg, [from, to]) => svg.split(from).join(to),
  catArtwork,
);
