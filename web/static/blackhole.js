// Pantalla "Black Hole": un fragment shader a pantalla completa (agujero negro con disco de
// acreción amarillo, en el estilo de SpectralRibbon). Cualquier click o tap vuelve al inicio.
(() => {
  const canvas = document.getElementById('agujero');
  const volver = () => location.assign('/');
  // Si el navegador bloqueó el sonido (iOS/Safari), el primer toque lo habilita y el segundo vuelve.
  let tocado = false;
  canvas.addEventListener('click', () => {
    const sonido = window.blackholeAudio;
    if (sonido && !tocado && sonido.necesitaGesto()) { tocado = true; sonido.habilitar(); return; }
    if (sonido) sonido.salir(volver); else volver();
  });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') volver(); });

  const vertex = `attribute vec2 a_position;
void main() { gl_Position = vec4(a_position, 0., 1.); }`;

  // Mismo lenguaje visual que SpectralRibbon (cinta de luz con bloom amplio, domain warp líquido y
  // grano de película), pero la cinta se cierra en órbita alrededor de un horizonte negro y la
  // paleta es solo amarillo/ámbar.
  const fragment = `precision highp float;
uniform vec2 u_resolution;
uniform float u_time;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123); }

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}

float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  mat2 m = mat2(0.8, 0.6, -0.6, 0.8);
  for (int i = 0; i < 4; i++) {
    v += a * noise(p);
    p = m * p * 2.02;
    a *= 0.5;
  }
  return v;
}

const float TAU = 6.28318530718;

// Órbita cerrada: elipse con un leve vaivén para que respire.
vec2 orbitPoint(float s, float time, vec2 radius, float roll, float phase) {
  float a = s * TAU;
  float wob = 1.0 + 0.035 * sin(a * 3.0 + time * 0.6 + phase) + 0.02 * cos(a * 2.0 - time * 0.4);
  vec2 q = vec2(cos(a) * radius.x, sin(a) * radius.y) * wob;
  float c = cos(roll);
  float sn = sin(roll);
  return vec2(q.x * c - q.y * sn, q.x * sn + q.y * c);
}

// Franja cálida: crema al lado del horizonte, oro en el vientre, ámbar hacia afuera.
vec3 warm(float across, float along) {
  float h = clamp(0.5 + across * 0.5 + along * 0.05, 0.0, 1.0);
  vec3 cream = vec3(1.0, 0.9, 0.62);
  vec3 gold = vec3(1.0, 0.74, 0.26);
  vec3 amber = vec3(1.0, 0.5, 0.1);
  vec3 ember = vec3(0.72, 0.24, 0.03);
  vec3 c = mix(cream, gold, smoothstep(0.1, 0.45, h));
  c = mix(c, amber, smoothstep(0.4, 0.75, h));
  return mix(c, ember, smoothstep(0.7, 1.0, h));
}

// Brillo de una órbita en el punto p: devuelve rgb y, en w, qué tan "adelante" del horizonte pasa.
vec4 ribbon(vec2 p, float time, vec2 radius, float roll, float phase, float thickness, float strength) {
  float minDist = 1e5;
  float closestT = 0.0;
  float side = 0.0;
  vec2 prev = orbitPoint(0.0, time, radius, roll, phase);
  for (int i = 1; i <= 64; i++) {
    float s = float(i) / 64.0;
    vec2 cur = orbitPoint(s, time, radius, roll, phase);
    vec2 pa = p - prev;
    vec2 ba = cur - prev;
    float h = clamp(dot(pa, ba) / max(dot(ba, ba), 1e-5), 0.0, 1.0);
    float d = length(p - (prev + ba * h));
    if (d < minDist) {
      minDist = d;
      closestT = mix(s - 1.0 / 64.0, s, h);
      side = pa.x * ba.y - pa.y * ba.x;
    }
    prev = cur;
  }

  float thick = thickness;
  float across = clamp((minDist * -sign(side)) / (thick * 2.8), -1.2, 1.2);

  float core = exp(-pow(minDist / (thick * 0.7), 2.0));
  float body = exp(-pow(minDist / (thick * 1.8), 2.0));
  float bloom = exp(-pow(minDist / (thick * 4.2), 2.0));
  float haze = exp(-pow(minDist / (thick * 7.5), 2.0));

  vec3 tint = warm(across, closestT);
  tint = mix(vec3(1.0, 0.93, 0.75), tint, smoothstep(0.0, 0.55, abs(across)));

  // Efecto Doppler: el lado izquierdo (que se acerca) brilla más.
  float a = closestT * TAU;
  float doppler = 0.55 + 0.75 * (0.5 - 0.5 * cos(a - roll));

  vec3 col = tint * (body * 0.55 + bloom * 0.85 + haze * 0.4);
  col += tint * core * 0.35;
  col += vec3(1.0, 0.96, 0.84) * pow(core, 0.85) * 0.55;
  col *= doppler * strength;

  float mask = clamp(body * 0.7 + bloom + haze * 0.55, 0.0, 1.6);
  float front = smoothstep(0.15, -0.35, sin(a)); // 1 en la mitad que pasa por delante
  return vec4(col * mask, front);
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_resolution;
  float aspect = u_resolution.x / max(u_resolution.y, 1.0);
  vec2 p = (uv - 0.5) * vec2(aspect, 1.0);
  // En vertical se aleja la cámara para que la órbita entre en pantalla.
  p *= max(1.0, 0.95 / aspect);
  float time = u_time;

  // Domain warp suave: líquido, no mecánico.
  float warp = fbm(p * 1.2 + vec2(time * 0.1, -time * 0.07));
  p += (warp - 0.5) * 0.06;

  float R = 0.2;                 // horizonte de sucesos
  float r = length(p);

  // Disco de acreción (órbita inclinada) y su imagen lensada sobre el horizonte.
  vec4 disk = ribbon(p, time, vec2(0.62, 0.17), 0.12, 0.0, 0.024, 0.55);
  vec4 lensed = ribbon(p, time, vec2(R * 1.14), 0.0, 2.0, 0.009, 0.5);

  vec3 col = disk.rgb + lensed.rgb;

  // El horizonte es negro: solo lo cruza la parte del disco que pasa por delante.
  float inside = 1.0 - smoothstep(R * 0.97, R * 1.01, r);
  vec3 frontOnly = disk.rgb * disk.w;
  col = mix(col, frontOnly, inside);

  float vignette = smoothstep(1.3, 0.3, length((uv - 0.5) * vec2(aspect, 1.0)));
  col *= mix(0.6, 1.0, vignette);

  float mask = clamp(dot(col, vec3(0.33)) * 3.0, 0.0, 1.0);
  col += (hash(gl_FragCoord.xy + time * 40.0) - 0.5) * 0.06 * 0.45 * mask;

  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}`;

  const gl = canvas.getContext('webgl', { antialias: false, alpha: false, powerPreference: 'high-performance' });
  if (!gl) { document.body.classList.add('sin-webgl'); return; }

  function compile(type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    return gl.getShaderParameter(shader, gl.COMPILE_STATUS) ? shader : null;
  }
  const vs = compile(gl.VERTEX_SHADER, vertex);
  const fs = compile(gl.FRAGMENT_SHADER, fragment);
  const program = gl.createProgram();
  if (!vs || !fs) { document.body.classList.add('sin-webgl'); return; }
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) { document.body.classList.add('sin-webgl'); return; }
  gl.useProgram(program);

  const buffer = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, 'a_position');
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
  const uResolution = gl.getUniformLocation(program, 'u_resolution');
  const uTime = gl.getUniformLocation(program, 'u_time');

  // Tope de 1.5x de densidad de píxeles: el shader es pesado y a pantalla completa en un celular alcanza.
  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    const width = Math.max(1, Math.round(canvas.clientWidth * dpr));
    const height = Math.max(1, Math.round(canvas.clientHeight * dpr));
    if (canvas.width !== width || canvas.height !== height) { canvas.width = width; canvas.height = height; }
    gl.viewport(0, 0, width, height);
  }
  window.addEventListener('resize', resize);

  const reducido = matchMedia('(prefers-reduced-motion: reduce)');
  let previo = 0;
  let transcurrido = 0;
  let cuadro = 0;
  // El tiempo avanza con delta acotado: al volver de otra pestaña no pega un salto.
  function frame(now) {
    cuadro = 0;
    if (previo) transcurrido += Math.min((now - previo) / 1000, 0.05) * (reducido.matches ? 0.25 : 1);
    previo = now;
    resize();
    gl.uniform2f(uResolution, canvas.width, canvas.height);
    gl.uniform1f(uTime, transcurrido);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    if (!document.hidden) cuadro = requestAnimationFrame(frame);
  }
  function arrancar() {
    cancelAnimationFrame(cuadro);
    previo = 0;
    if (!document.hidden) cuadro = requestAnimationFrame(frame);
  }
  document.addEventListener('visibilitychange', arrancar);
  canvas.addEventListener('webglcontextlost', (event) => {
    event.preventDefault();
    cancelAnimationFrame(cuadro);
  });
  // Al restaurarse el contexto se recarga la pantalla: es lo más simple y no tiene estado que perder.
  canvas.addEventListener('webglcontextrestored', () => location.reload());
  arrancar();
})();
