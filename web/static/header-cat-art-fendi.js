// Fendi: misma anatomía que catArtwork, recoloreada a dos tonos -cabeza,
// patitas y torso en marrón oscuro; orejas, cola y cachetes en marrón
// claro-, con ojos amarillos -ya venían así en el dibujo base, no hizo
// falta tocarlos-. Recolor puro por reemplazo de color, sin tocar ningún
// path/geometría.
import {catArtwork} from './header-cat-art.js';

const DARK = '#3c2a1d';   // cabeza, torso, patitas
const LIGHT = '#c99a68';  // orejas, cola, cachetes

const RECOLOR = [
  // Cabeza/torso/patas (incluye el pecho, antes un círculo claro que
  // quedaba raro sobre la patita: ahora es del mismo marrón oscuro).
  ['#fffdf8', DARK], ['#fffdf9', DARK], ['#f1eee7', DARK],
  ['#d8cfc4', '#22160e'],
  // Orejas y cola: marrón claro.
  ['#c9a581', LIGHT], ['#c4a07c', LIGHT],
  ['#b68e6b', '#6b3f22'], ['#eac5b5', LIGHT],
  // Raya del lomo / sombra del vientre (ocultas salvo en poses que Fendi no usa).
  ['#eee8df', LIGHT], ['#f1dfd6', LIGHT],
  // Cachetes: marrón claro (igual que orejas/cola).
  ['#efd2c9', LIGHT],
  ['#e9e3d9', '#000000'],
  // Nariz/lengua/almohadillas: tonos cálidos oscuros, no puro negro.
  ['#c98c89', '#5a3428'], ['#e5a0a1', '#b06a5f'], ['#e2b0aa', '#3a1f1f'],
  // Trazos/contornos -> oscuros.
  ['#775c4c', '#000000'], ['#705343', '#000000'], ['#8f7971', '#22160e'],
  ['#ab9b8d', '#4a3524'], ['#e5b7a0', '#6b3f22'], ['#302a25', '#000000'],
];

export const fendiArtwork = RECOLOR.reduce(
  (svg, [from, to]) => svg.split(from).join(to),
  catArtwork,
);
