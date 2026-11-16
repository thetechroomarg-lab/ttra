// Gráfica de la oficina de la bienvenida: pantallas, cuadros y la película del televisor.
// Todo se dibuja en canvas; no hay imágenes externas.

const TITLE = 'Impact, "Arial Black", "Helvetica Neue", sans-serif';
const rng = seed => () => (seed = (seed * 16807) % 2147483647) / 2147483647;
const poly = (g, pts, fill) => { g.fillStyle = fill; g.beginPath(); pts.forEach((p, i) => i ? g.lineTo(p[0], p[1]) : g.moveTo(p[0], p[1])); g.closePath(); g.fill(); };
const disc = (g, x, y, r, fill) => { g.fillStyle = fill; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); };
const rect = (g, x, y, w, h, fill, r = 0) => { g.fillStyle = fill; g.beginPath(); g.roundRect(x, y, w, h, r); g.fill(); };
const grad = (g, x0, y0, x1, y1, stops) => { const s = g.createLinearGradient(x0, y0, x1, y1); stops.forEach((c, i) => s.addColorStop(i / (stops.length - 1), c)); return s; };
const text = (g, s, x, y, size, fill, font = TITLE, align = 'center') => { g.font = `${size}px ${font}`; g.textAlign = align; g.textBaseline = 'middle'; g.fillStyle = fill; g.fillText(s, x, y); };

// ---------- Monitor izquierdo: editor al estilo Visual Studio Code ----------
export function drawEditor(g, w, h) {
  const r = rng(41);
  rect(g, 0, 0, w, h, '#1e1e1e');
  rect(g, 0, 0, w, 20, '#323233'); // barra de título
  ['#ff5f57', '#febc2e', '#28c840'].forEach((c, i) => disc(g, 12 + i * 14, 10, 4, c));
  rect(g, w / 2 - 90, 5, 180, 10, '#454546', 5);
  rect(g, 0, 20, 34, h - 38, '#333333'); // barra de actividad
  for (let i = 0; i < 5; i++) rect(g, 10, 32 + i * 30, 14, 14, i === 0 ? '#ffffff' : '#858585', 3);
  rect(g, 34, 20, 128, h - 38, '#252526'); // explorador
  rect(g, 44, 30, 60, 5, '#bbbbbb', 2);
  const icons = ['#519aba', '#e37933', '#cbcb41', '#519aba', '#a074c4', '#8dc149'];
  for (let i = 0; i < 15; i++) {
    const y = 48 + i * 17, deep = i % 5 ? 12 : 0;
    if (i === 6) rect(g, 34, y - 5, 128, 16, '#37373d');
    rect(g, 46 + deep, y, 7, 7, deep ? icons[i % icons.length] : '#c5c5c5', 1.5);
    rect(g, 58 + deep, y + 1, 30 + r() * 52, 5, i === 6 ? '#ffffff' : '#9d9d9d', 2);
  }
  rect(g, 162, 20, w - 162, 24, '#252526'); // pestañas
  rect(g, 162, 20, 112, 24, '#1e1e1e'); rect(g, 162, 20, 112, 2, '#0078d4');
  [[172, 70, '#e2c08d'], [286, 58, '#8a8a8a'], [382, 66, '#8a8a8a']].forEach(([x, bw, c]) => rect(g, x, 30, bw, 5, c, 2));
  const pal = ['#569cd6', '#9cdcfe', '#ce9178', '#dcdcaa', '#c586c0', '#4ec9b0', '#d4d4d4', '#6a9955'];
  let indent = 0;
  for (let i = 0; i < 15; i++) {
    const y = 56 + i * 17;
    rect(g, 172, y, 10, 5, '#5a5a5a', 2); // número de línea
    if (i === 7) rect(g, 192, y - 5, w - 262, 15, '#2a2d2e');
    if (r() < .1) continue;
    indent = Math.max(0, Math.min(3, indent + (r() < .32 ? 1 : r() < .5 ? -1 : 0)));
    let x = 198 + indent * 18;
    for (let k = 0, n = 1 + Math.floor(r() * 4); k < n && x < w - 130; k++) { const bw = 16 + r() * 62; rect(g, x, y, bw, 5, pal[Math.floor(r() * pal.length)], 2); x += bw + 7; }
  }
  rect(g, w - 62, 44, 62, h - 144, '#1e1e1e'); // minimapa
  for (let i = 0; i < 44; i++) rect(g, w - 56 + (i % 3) * 4, 50 + i * 4, 10 + r() * 34, 2, pal[i % pal.length] + '88');
  rect(g, 162, h - 100, w - 162, 82, '#181818'); rect(g, 162, h - 100, w - 162, 1, '#3c3c3c'); // terminal
  rect(g, 174, h - 92, 52, 5, '#e7e7e7', 2); rect(g, 174, h - 85, 52, 1, '#0078d4');
  for (let i = 0; i < 4; i++) { rect(g, 174, h - 74 + i * 13, 8, 5, '#23d18b', 2); rect(g, 188, h - 74 + i * 13, 60 + r() * 220, 5, i === 3 ? '#cccccc' : '#8a8a8a', 2); }
  rect(g, 0, h - 18, w, 18, '#0078d4'); // barra de estado
  rect(g, 10, h - 12, 60, 5, '#ffffff', 2); rect(g, w - 150, h - 12, 40, 5, '#ffffff', 2); rect(g, w - 100, h - 12, 80, 5, '#ffffff', 2);
}

// ---------- Monitor derecho: la tienda, con el logo real ----------
export function drawStore(g, w, h, LOGO) {
  rect(g, 0, 0, w, h, '#1a1a1a');
  rect(g, 0, 0, w, 20, '#2b2b2c');
  ['#ff5f57', '#febc2e', '#28c840'].forEach((c, i) => disc(g, 12 + i * 14, 10, 4, c));
  rect(g, 120, 4, w - 240, 12, '#1a1a1a', 6); text(g, 'thetechroomarg.com', w / 2, 10.5, 9, '#bdbdbd', 'system-ui, sans-serif');
  rect(g, 0, 20, w, 72, '#101010');
  // Logo dibujado desde sus contornos oficiales.
  const k = 60 / LOGO.h, ox = 22, oy = 26;
  g.fillStyle = '#ffffff'; g.beginPath();
  for (const s of LOGO.rows.flat()) for (const ring of [s.o, ...s.h]) { ring.forEach((p, i) => i ? g.lineTo(ox + p[0] * k, oy + p[1] * k) : g.moveTo(ox + p[0] * k, oy + p[1] * k)); g.closePath(); }
  g.fill('evenodd');
  disc(g, ox + LOGO.dot[0] * k, oy + LOGO.dot[1] * k, LOGO.dot[2] * k, '#e2001a');
  rect(g, 130, 44, 300, 24, '#262626', 12); rect(g, 144, 53, 110, 6, '#6f6f6f', 3); // buscador
  [0, 1, 2].forEach(i => rect(g, 452 + i * 54, 51, 40, 8, '#cfcfcf', 4));
  disc(g, w - 22, 55, 11, '#262626'); disc(g, w - 14, 47, 5, '#e2001a');
  ['Celulares', 'Notebooks', 'Accesorios', 'Gaming'].forEach((c, i) => { rect(g, 22 + i * 96, 104, 86, 20, i ? '#262626' : '#f2f2f2', 10); text(g, c, 65 + i * 96, 114.5, 10, i ? '#e6e6e6' : '#101010', 'system-ui, sans-serif'); });
  const tones = ['#2b3440', '#3a2f2a', '#2d3a31', '#3a3340'];
  for (let i = 0; i < 4; i++) {
    const x = 22 + i * 152;
    rect(g, x, 138, 140, 204, '#262626', 10);
    rect(g, x + 10, 148, 120, 110, tones[i], 8);
    if (i === 1) { rect(g, x + 30, 176, 80, 52, '#c9ccd1', 4); rect(g, x + 34, 180, 72, 44, '#151a22', 2); rect(g, x + 22, 228, 96, 6, '#aeb1b6', 3); } // notebook
    else { rect(g, x + 48, 160, 44, 88, ['#d9d9de', '', '#31363d', '#e7d8c6'][i], 9); rect(g, x + 51, 163, 38, 82, '#0f1319', 7); disc(g, x + 70, 170, 2.5, '#2a2f38'); } // celular
    rect(g, x + 10, 270, 104, 7, '#e6e6e6', 3); rect(g, x + 10, 284, 70, 6, '#8f8f8f', 3);
    text(g, 'US$ ' + ['899', '1.249', '649', '1.099'][i], x + 10, 312, 15, '#ffffff', 'system-ui, sans-serif', 'left');
    rect(g, x + 96, 302, 34, 22, '#e2001a', 11);
  }
}

// ---------- Cuadros: ilustraciones propias de estética anime y afiches de rock ----------
const animeDuel = (g, w, h) => {
  rect(g, 0, 0, w, h, grad(g, 0, 0, 0, h, ['#7a1022', '#e2452f', '#f6a23c']));
  disc(g, w / 2, h * .42, w * .36, '#ffe9a8');
  poly(g, [[0, h * .78], [w * .3, h * .7], [w * .62, h * .76], [w, h * .68], [w, h], [0, h]], '#160a10');
  const x = w * .5, y = h * .74; // espadachín de espaldas, capa al viento
  poly(g, [[x - 14, y], [x - 9, y - 62], [x - 16, y - 96], [x + 14, y - 98], [x + 12, y - 60], [x + 16, y]], '#160a10');
  disc(g, x - 1, y - 110, 12, '#160a10');
  poly(g, [[x + 10, y - 96], [x + 70, y - 80], [x + 96, y - 52], [x + 52, y - 60], [x + 12, y - 70]], '#160a10');
  g.strokeStyle = '#160a10'; g.lineWidth = 3; g.beginPath(); g.moveTo(x - 14, y - 70); g.lineTo(x - 78, y - 20); g.stroke();
  rect(g, 14, 14, 34, 84, '#160a10'); text(g, '冒', 31, 38, 26, '#ffe9a8', 'sans-serif'); text(g, '険', 31, 74, 26, '#ffe9a8', 'sans-serif');
};
const animeEyes = (g, w, h) => {
  rect(g, 0, 0, w, h, '#fdf3f6');
  g.strokeStyle = '#1b1b24'; g.lineWidth = 1.2;
  const r = rng(9);
  for (let i = 0; i < 70; i++) { const a = r() * 6.283, d0 = w * (.5 + r() * .25); g.beginPath(); g.moveTo(w / 2 + Math.cos(a) * d0, h * .45 + Math.sin(a) * d0); g.lineTo(w / 2 + Math.cos(a) * w * 1.4, h * .45 + Math.sin(a) * w * 1.4); g.stroke(); }
  poly(g, [[0, 0], [w, 0], [w, h * .2], [w * .82, h * .32], [w * .7, h * .18], [w * .56, h * .34], [w * .42, h * .17], [w * .26, h * .33], [w * .14, h * .2], [0, h * .3]], '#23202e'); // flequillo
  for (const s of [-1, 1]) {
    const x = w / 2 + s * w * .22, y = h * .5;
    g.fillStyle = '#ffffff'; g.beginPath(); g.ellipse(x, y, w * .16, h * .11, 0, 0, 7); g.fill();
    const iris = g.createRadialGradient(x, y + 6, 2, x, y, w * .12); iris.addColorStop(0, '#7fe0ff'); iris.addColorStop(1, '#1d3fae');
    g.fillStyle = iris; g.beginPath(); g.ellipse(x, y + 2, w * .1, h * .1, 0, 0, 7); g.fill();
    disc(g, x, y + 2, w * .04, '#0d1030'); disc(g, x - w * .04, y - h * .04, w * .03, '#ffffff'); disc(g, x + w * .04, y + h * .05, w * .014, '#ffffff');
    g.strokeStyle = '#23202e'; g.lineWidth = 6; g.beginPath(); g.ellipse(x, y, w * .17, h * .115, 0, Math.PI * 1.05, Math.PI * 1.95); g.stroke();
  }
  rect(g, 0, h * .8, w, h * .12, '#e2365a'); text(g, 'EPISODIO 01', w / 2, h * .862, 24, '#ffffff');
};
const animeMecha = (g, w, h) => {
  rect(g, 0, 0, w, h, grad(g, 0, 0, 0, h, ['#0b1030', '#243a7a', '#5a3d8a']));
  disc(g, w * .74, h * .2, w * .16, '#f3f0ff');
  const r = rng(5);
  for (let x = 0; x < w; x += 22) { const bh = h * (.12 + r() * .16); rect(g, x, h - bh, 20, bh, '#0a0d22'); for (let k = 0; k < 4; k++) if (r() < .6) rect(g, x + 4 + (k % 2) * 8, h - bh + 8 + (k >> 1) * 14, 4, 6, '#ffd66b'); }
  const x = w * .42, y = h * .9; // robot gigante entre los edificios
  rect(g, x - 34, y - 96, 24, 96, '#c9d2e6', 3); rect(g, x + 10, y - 96, 24, 96, '#c9d2e6', 3);
  rect(g, x - 44, y - 190, 88, 100, '#e9eef8', 6); rect(g, x - 20, y - 168, 40, 30, '#e2365a', 4);
  rect(g, x - 78, y - 190, 30, 44, '#e2365a', 6); rect(g, x + 48, y - 190, 30, 44, '#e2365a', 6);
  rect(g, x - 72, y - 150, 20, 76, '#c9d2e6', 3); rect(g, x + 52, y - 150, 20, 76, '#c9d2e6', 3);
  rect(g, x - 20, y - 228, 40, 36, '#e9eef8', 5); rect(g, x - 14, y - 214, 28, 7, '#3ff0ff', 2);
  poly(g, [[x - 20, y - 228], [x - 34, y - 254], [x - 8, y - 228]], '#ffd66b'); poly(g, [[x + 20, y - 228], [x + 34, y - 254], [x + 8, y - 228]], '#ffd66b');
  text(g, 'メカ', w * .8, h * .52, 34, '#ffffff', 'sans-serif');
};
const animeNinja = (g, w, h) => {
  rect(g, 0, 0, w, h, grad(g, 0, 0, 0, h, ['#132a45', '#2b6a78', '#f0b6c8']));
  disc(g, w * .5, h * .4, w * .4, '#fff6ea');
  const x = w * .5, y = h * .4; // ninja en pleno salto, recortado contra la luna
  poly(g, [[x - 46, y + 26], [x - 10, y - 4], [x + 6, y - 30], [x + 30, y - 22], [x + 62, y - 44], [x + 66, y - 36], [x + 34, y - 6], [x + 18, y + 12], [x + 44, y + 44], [x + 36, y + 52], [x + 2, y + 26], [x - 40, y + 38]], '#141420');
  disc(g, x + 18, y - 38, 13, '#141420');
  poly(g, [[x + 8, y - 44], [x - 40, y - 62], [x - 30, y - 50], [x - 52, y - 46], [x + 8, y - 34]], '#c8263a'); // bandana
  g.strokeStyle = '#141420'; g.lineWidth = 3; g.beginPath(); g.moveTo(x - 14, y - 6); g.lineTo(x - 70, y - 52); g.stroke();
  const r = rng(77);
  for (let i = 0; i < 46; i++) disc(g, r() * w, r() * h, 2 + r() * 3, `rgba(255,${170 + r() * 50},${200 + r() * 40},.85)`);
  poly(g, [[0, h * .86], [w, h * .8], [w, h], [0, h]], '#141420');
  text(g, '忍', w * .14, h * .12, 44, '#ffffff', 'sans-serif');
};
const rockGuitar = (g, w, h) => {
  rect(g, 0, 0, w, h, '#101012');
  poly(g, [[w * .62, 0], [w * .3, h * .46], [w * .5, h * .46], [w * .22, h], [w * .78, h * .36], [w * .56, h * .36], [w * .86, 0]], '#ffd21f');
  g.save(); g.translate(w * .5, h * .5); g.rotate(-.5);
  rect(g, -9, -150, 18, 170, '#3a2416', 2); rect(g, -15, -182, 30, 38, '#1c1c1e', 5);
  g.fillStyle = '#d3122a'; g.beginPath(); g.ellipse(0, 46, 52, 42, 0, 0, 7); g.ellipse(0, 4, 38, 30, 0, 0, 7); g.fill();
  rect(g, -18, 20, 36, 10, '#e9e9ec', 2); rect(g, -18, 44, 36, 10, '#e9e9ec', 2); rect(g, -22, 68, 44, 8, '#bfc2c8', 2);
  g.strokeStyle = '#e9e9ec'; g.lineWidth = 1; for (let i = -2; i <= 2; i++) { g.beginPath(); g.moveTo(i * 3, -150); g.lineTo(i * 3, 72); g.stroke(); }
  g.restore();
  text(g, 'ROCK', w / 2, h * .1, 54, '#ffffff'); text(g, "& ROLL", w / 2, h * .92, 42, '#d3122a');
};
const rockVinyl = (g, w, h) => {
  rect(g, 0, 0, w, h, '#e0a526');
  const r = Math.min(w, h) * .4, x = w / 2, y = h * .46;
  disc(g, x, y, r, '#111113');
  g.strokeStyle = 'rgba(255,255,255,.14)'; g.lineWidth = 1; for (let k = .42; k < 1; k += .07) { g.beginPath(); g.arc(x, y, r * k, 0, 7); g.stroke(); }
  disc(g, x, y, r * .34, '#c8263a'); disc(g, x, y, r * .05, '#e0a526');
  text(g, 'EN VIVO', w / 2, h * .92, 30, '#111113');
};
const rockAmp = (g, w, h) => {
  rect(g, 0, 0, w, h, '#b8142a');
  for (let i = 0; i < 26; i++) poly(g, [[w / 2, h * .62], [w / 2 + Math.cos(i * .2417 * 2) * w * 1.4, h * .62 + Math.sin(i * .2417 * 2) * w * 1.4], [w / 2 + Math.cos(i * .2417 * 2 + .09) * w * 1.4, h * .62 + Math.sin(i * .2417 * 2 + .09) * w * 1.4]], 'rgba(0,0,0,.16)');
  rect(g, w * .2, h * .3, w * .6, h * .14, '#141416', 5); for (let i = 0; i < 6; i++) disc(g, w * .28 + i * w * .088, h * .37, 5, i ? '#d9d9de' : '#ffd21f');
  rect(g, w * .16, h * .45, w * .68, h * .46, '#141416', 6); rect(g, w * .2, h * .48, w * .6, h * .4, '#2a2a2e', 4);
  for (const [cx, cy] of [[.36, .58], [.64, .58], [.36, .78], [.64, .78]]) { disc(g, w * cx, h * cy, w * .115, '#101012'); disc(g, w * cx, h * cy, w * .04, '#3a3a40'); }
  text(g, 'A TODO', w / 2, h * .1, 40, '#ffffff'); text(g, 'VOLUMEN', w / 2, h * .215, 40, '#ffd21f');
};
const rockBill = (g, w, h) => {
  rect(g, 0, 0, w, h, '#efe6d2'); rect(g, 10, 10, w - 20, h - 20, '#141416'); rect(g, 16, 16, w - 32, h - 32, '#efe6d2');
  text(g, 'NOCHE', w / 2, h * .17, 62, '#141416'); text(g, 'DE ROCK', w / 2, h * .34, 52, '#c8263a');
  const x = w / 2, y = h * .58, R = w * .2; // estrella
  poly(g, Array.from({length: 10}, (_, i) => { const a = -Math.PI / 2 + i * Math.PI / 5, d = i % 2 ? R * .42 : R; return [x + Math.cos(a) * d, y + Math.sin(a) * d]; }), '#141416');
  rect(g, 30, h * .76, w - 60, 4, '#141416'); text(g, 'GIRA MUNDIAL', w / 2, h * .83, 30, '#141416'); text(g, 'ENTRADA LIBRE', w / 2, h * .915, 20, '#c8263a');
};
// Orden en la pared: se alternan anime y rock. `square` marca los cuadros cuadrados.
export const POSTERS = [
  {draw: animeDuel}, {draw: rockGuitar}, {draw: animeEyes}, {draw: rockVinyl, square: true},
  {draw: animeMecha}, {draw: rockBill}, {draw: animeNinja}, {draw: rockAmp},
];

// ---------- Televisor: escenas de acción en bucle (persecución, explosión, helicóptero) ----------
const SHOT = 1.7;
export function drawMovie(g, w, h, t) {
  const shot = Math.floor(t / SHOT) % 3, u = (t % SHOT) / SHOT, bar = Math.round(h * .11);
  const shake = Math.sin(t * 47) * 2.2, r = rng(shot * 13 + 3);
  g.save(); g.translate(shake, Math.cos(t * 39) * 1.6);
  const skyline = (speed, tone, top) => { for (let i = 0; i < 26; i++) { const bw = 18 + r() * 26, bh = h * (.14 + r() * top), x = ((i * 34 - t * speed) % (w + 80) + w + 80) % (w + 80) - 40; rect(g, x, h * .68 - bh, bw, bh, tone); } };
  if (shot === 0) { // persecución nocturna
    rect(g, -8, -8, w + 16, h + 16, grad(g, 0, 0, 0, h * .7, ['#0a1230', '#3b2a5c', '#ff7a3c']));
    skyline(60, '#151a33', .3); skyline(150, '#070914', .2);
    rect(g, -8, h * .68, w + 16, h, '#1b1b20');
    for (let i = 0; i < 9; i++) rect(g, ((i * 70 - t * 620) % (w + 70) + w + 70) % (w + 70) - 40, h * .8, 40, 4, '#e8d36a');
    const car = (x, y, body, s) => {
      poly(g, [[x, y], [x + 14 * s, y - 14 * s], [x + 34 * s, y - 24 * s], [x + 70 * s, y - 24 * s], [x + 88 * s, y - 13 * s], [x + 112 * s, y - 10 * s], [x + 114 * s, y], [x, y]], body);
      poly(g, [[x + 38 * s, y - 21 * s], [x + 68 * s, y - 21 * s], [x + 80 * s, y - 13 * s], [x + 30 * s, y - 13 * s]], '#0b1220');
      disc(g, x + 24 * s, y, 9 * s, '#050506'); disc(g, x + 90 * s, y, 9 * s, '#050506');
      poly(g, [[x + 112 * s, y - 8 * s], [x + 250 * s, y - 26 * s], [x + 250 * s, y + 8 * s]], 'rgba(255,240,180,.28)');
    };
    car(w * .08 + Math.sin(t * 3.1) * 14, h * .77, '#16171c', .8);
    car(w * .46 + Math.sin(t * 2.3 + 1) * 18, h * .8, '#d3122a', 1);
  } else if (shot === 1) { // explosión, y alguien que se aleja sin mirar atrás
    rect(g, -8, -8, w + 16, h + 16, grad(g, 0, 0, 0, h, ['#0b0d18', '#2a1420', '#55210f']));
    skyline(0, '#090a12', .34);
    const x = w * .6, y = h * .56, R = h * (.16 + .62 * Math.sqrt(u));
    const fire = g.createRadialGradient(x, y, 0, x, y, R);
    fire.addColorStop(0, '#fffbe0'); fire.addColorStop(.3, '#ffc233'); fire.addColorStop(.62, '#ff5a14'); fire.addColorStop(1, 'rgba(120,20,0,0)');
    g.fillStyle = fire; g.fillRect(-8, -8, w + 16, h + 16);
    g.strokeStyle = '#ffe9a0'; g.lineWidth = 2;
    for (let i = 0; i < 22; i++) { const a = r() * 6.283, d = R * (.5 + r() * .9) * (.4 + u); g.beginPath(); g.moveTo(x + Math.cos(a) * d * .8, y + Math.sin(a) * d * .8); g.lineTo(x + Math.cos(a) * d, y + Math.sin(a) * d); g.stroke(); }
    for (let i = 0; i < 9; i++) { const a = r() * 6.283, d = R * (.3 + r() * .8) * u; disc(g, x + Math.cos(a) * d, y + Math.sin(a) * d * .8 + u * u * 30, 3 + r() * 5, '#1a0d08'); }
    rect(g, -8, h * .8, w + 16, h, '#0a0808');
    const hx = w * .26 - u * 16, hy = h * .8; // héroe a contraluz
    poly(g, [[hx - 13, hy], [hx - 9, hy - 46], [hx - 15, hy - 86], [hx + 15, hy - 86], [hx + 10, hy - 46], [hx + 14, hy]], '#050405');
    disc(g, hx, hy - 98, 11, '#050405');
    if (u < .1) rect(g, -8, -8, w + 16, h + 16, `rgba(255,250,225,${1 - u / .1})`);
  } else { // helicóptero con reflector y trazadoras
    rect(g, -8, -8, w + 16, h + 16, grad(g, 0, 0, 0, h, ['#061021', '#12325a', '#2c6f8f']));
    skyline(40, '#07101d', .4);
    const x = w * (.2 + .5 * u), y = h * (.3 + .05 * Math.sin(t * 5));
    poly(g, [[x + 8, y + 10], [x - 60, h], [x + 90, h]], 'rgba(255,248,210,.2)');
    g.fillStyle = '#05080e'; g.beginPath(); g.ellipse(x, y, 30, 13, 0, 0, 7); g.fill();
    poly(g, [[x - 24, y - 4], [x - 78, y - 9], [x - 78, y - 3], [x - 24, y + 5]], '#05080e'); rect(g, x - 84, y - 20, 5, 20, '#05080e');
    rect(g, x - 3, y - 20, 6, 9, '#05080e'); rect(g, x - 56 * Math.abs(Math.sin(t * 60)) - 4, y - 22, 112 * Math.abs(Math.sin(t * 60)) + 8, 3, '#05080e');
    rect(g, x - 20, y + 15, 44, 3, '#05080e'); disc(g, x + 16, y - 1, 6, '#6fd6ff');
    g.strokeStyle = '#ffe36b'; g.lineWidth = 2.5;
    for (let i = 0; i < 5; i++) { const k = (u * 4 + i * .2) % 1; g.beginPath(); g.moveTo(x + 30 + k * 150, y + 8 + k * 80); g.lineTo(x + 30 + k * 150 + 22, y + 8 + k * 80 + 12); g.stroke(); }
    if (Math.sin(t * 34) > .4) disc(g, x + 32, y + 9, 7, '#fff4b0');
    rect(g, -8, h * .68, w + 16, h, '#04070c');
  }
  g.restore();
  rect(g, 0, 0, w, bar, '#000000'); rect(g, 0, h - bar, w, bar, '#000000'); // formato cine
}
