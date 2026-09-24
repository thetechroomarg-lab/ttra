// Fendi: misma anatomía que catArtwork (header-cat-art.js), recoloreada a
// carey (marrón oscuro de base, parches marrón medio y marrón claro, ojos
// amarillos -éstos ya venían así en el original, no hizo falta tocarlos-).
// Recolor puro por reemplazo de color, sin tocar ningún path/geometría.
import {catArtwork} from './header-cat-art.js';

const RECOLOR = [
  // Base del cuerpo/patas/orejas internas "blanco" -> carey oscuro.
  ['#fffdf8', '#3c2a1d'], ['#fffdf9', '#3c2a1d'],
  // Contorno claro sobre el blanco -> contorno oscuro que se note sobre el carey.
  ['#d8cfc4', '#22160e'],
  // Parches de orejas/cabeza/cola "canela" -> marrón medio (segundo tono carey).
  ['#c9a581', '#8a5a34'], ['#c4a07c', '#8a5a34'], ['#b68e6b', '#6b3f22'],
  // Pecho/vientre y raya del lomo, más claros -> marrón claro (tercer tono carey).
  ['#f1eee7', '#c99a68'], ['#eee8df', '#c99a68'], ['#f1dfd6', '#a9764a'],
  ['#eac5b5', '#b97a68'], ['#e9e3d9', '#4a3524'],
  // Rosas de nariz/lengua/mejillas -> tonos cálidos apagados, coherentes con pelaje oscuro.
  ['#efd2c9', '#a9674a'], ['#c98c89', '#8a4f4a'], ['#e5a0a1', '#b06a5f'],
  ['#e2b0aa', '#8a4f4a'],
  // Trazos/rayas de bigotes y contornos oscuros -> más oscuros todavía.
  ['#775c4c', '#2c1c12'], ['#705343', '#2c1c12'], ['#8f7971', '#4a3524'],
  ['#ab9b8d', '#6b4a34'], ['#e5b7a0', '#7a4a30'], ['#302a25', '#1a100a'],
];

export const fendiArtwork = RECOLOR.reduce(
  (svg, [from, to]) => svg.split(from).join(to),
  catArtwork,
);
