// Fondo de "adentro" del agujero negro: un viaje por un agujero de gusano. Un túnel que se abre hacia un
// punto de luz, con vetas que giran en las paredes, estrellas que se estiran al pasar y aberración
// cromática en los bordes. Reemplaza al fondo de colores ámbar; el spiral slider no se toca.
(() => {
  const vertex = `attribute vec2 a_position;
void main() { gl_Position = vec4(a_position, 0., 1.); }`;

  const fragment = `precision highp float;
uniform vec2 u_res;
uniform float u_t;
uniform float u_abre;

float hash(vec2 p) { p = fract(p * vec2(123.34, 456.21)); p += dot(p, p + 45.32); return fract(p.x * p.y); }

// Estrella que viaja por la pared del túnel: fina en ángulo, larga en profundidad.
float estrella(float a, float z, float carriles, float velocidad, float semilla) {
  float ca = a * carriles;
  float id = floor(ca);
  float fa = fract(ca) - 0.5;
  float zz = z * velocidad + hash(vec2(id, semilla)) * 19.0;
  float zi = floor(zz);
  float fz = fract(zz);
  float azar = hash(vec2(id + semilla, zi));
  float prende = step(0.74, azar);
  float ancho = smoothstep(0.05, 0.0, abs(fa));
  float largo = smoothstep(0.5, 0.12, abs(fz - 0.5));
  return prende * ancho * largo * (0.45 + 0.55 * fract(azar * 7.0));
}

vec3 escena(vec2 p, float t) {
  float r = length(p);
  float a = atan(p.y, p.x) / 6.28318 + 0.5;
  float z = 0.32 / (r + 0.03);        // profundidad del túnel en ese píxel
  float zt = z + t * 1.5;             // avanzar = las marcas se alejan del centro
  float giro = fract(a + z * 0.085 + t * 0.02);

  // Paleta fría: azul profundo a cian eléctrico a violeta, con un núcleo blanco.
  float fase = 0.5 + 0.5 * sin(zt * 0.23 + t * 0.15);
  vec3 tinte = mix(vec3(0.04, 0.55, 0.78), vec3(0.52, 0.14, 0.92), fase);
  vec3 hielo = vec3(0.55, 0.9, 1.0);

  // Paredes: anillos que pasan y vetas que giran.
  float anillos = pow(0.5 + 0.5 * sin(zt * 3.1416), 10.0);
  float vetas = pow(0.5 + 0.5 * sin(giro * 6.28318 * 9.0 + zt * 1.1 + sin(zt * 0.7) * 2.2), 4.0);
  float tejido = 0.5 + 0.5 * sin(giro * 6.28318 * 23.0 - zt * 2.3);
  vec3 col = vec3(0.004, 0.012, 0.045);
  col += tinte * (0.2 * vetas + 0.12 * vetas * tejido) * smoothstep(0.02, 0.45, r);
  col += mix(tinte, hielo, 0.35) * anillos * 0.36 * smoothstep(0.03, 0.4, r);

  // Estrellas que se estiran al pasar (tres capas, más rápidas hacia adelante).
  float s = estrella(giro, zt, 90.0, 0.55, 1.0) + 0.8 * estrella(giro, zt, 150.0, 0.9, 7.0) + 0.6 * estrella(giro, zt, 56.0, 0.33, 13.0);
  col += mix(hielo, vec3(1.0), 0.5) * s * smoothstep(0.015, 0.2, r) * 0.8;

  // Al fondo, la salida: un punto de luz pequeño, sin quemar el centro donde va el texto.
  col += hielo * exp(-r * r * 110.0) * 0.6;
  col += tinte * exp(-r * 3.2) * 0.22;
  col *= mix(0.4, 1.0, smoothstep(0.0, 0.55, r));
  return col;
}

void main() {
  vec2 p = (gl_FragCoord.xy - 0.5 * u_res) / u_res.y;
  float t = u_t;
  p += 0.012 * vec2(sin(t * 0.31), cos(t * 0.23));
  // Aberración cromática: el rojo y el azul se separan hacia los bordes.
  float k = 0.012 * length(p) * 2.0;
  vec3 col;
  col.r = escena(p * (1.0 - k), t).r;
  col.g = escena(p, t).g;
  col.b = escena(p * (1.0 + k), t).b;
  // Se abre desde el centro al entrar.
  float r = length(p);
  col *= smoothstep(u_abre * 1.6 + 0.02, u_abre * 1.6 - 0.35, r) * smoothstep(0.0, 0.25, u_abre);
  // Viñeta suave y grano de película.
  col *= 1.0 - 0.72 * smoothstep(0.3, 1.0, length((gl_FragCoord.xy / u_res - 0.5) * vec2(u_res.x / u_res.y, 1.0)));
  col += (hash(gl_FragCoord.xy + t * 50.0) - 0.5) * 0.025;
  gl_FragColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}`;

  function montar(contenedor) {
    if (!contenedor || contenedor.querySelector('canvas')) return;
    const canvas = document.createElement('canvas');
    canvas.setAttribute('aria-hidden', 'true');
    canvas.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;display:block';
    contenedor.append(canvas);
    const gl = canvas.getContext('webgl', { antialias: false, alpha: false, powerPreference: 'default' });
    if (!gl) return;
    const compilar = (tipo, fuente) => {
      const s = gl.createShader(tipo); gl.shaderSource(s, fuente); gl.compileShader(s);
      return gl.getShaderParameter(s, gl.COMPILE_STATUS) ? s : null;
    };
    const vs = compilar(gl.VERTEX_SHADER, vertex), fs = compilar(gl.FRAGMENT_SHADER, fragment);
    if (!vs || !fs) return;
    const programa = gl.createProgram();
    gl.attachShader(programa, vs); gl.attachShader(programa, fs); gl.linkProgram(programa);
    if (!gl.getProgramParameter(programa, gl.LINK_STATUS)) return;
    gl.useProgram(programa);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
    const pos = gl.getAttribLocation(programa, 'a_position');
    gl.enableVertexAttribArray(pos); gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);
    const uRes = gl.getUniformLocation(programa, 'u_res'), uT = gl.getUniformLocation(programa, 'u_t'), uAbre = gl.getUniformLocation(programa, 'u_abre');
    const reducido = matchMedia('(prefers-reduced-motion: reduce)');
    // Se dibuja a media resolución: es un fondo en movimiento y deja la GPU para el spiral.
    const escala = Math.min(devicePixelRatio || 1, 1.5) * 0.6;
    let t = 0, abre = 0, previo = 0;
    function cuadro(ahora) {
      if (!canvas.isConnected) return;
      const dt = previo ? Math.min((ahora - previo) / 1000, 0.05) : 0;
      previo = ahora;
      const w = Math.max(1, Math.round(canvas.clientWidth * escala)), h = Math.max(1, Math.round(canvas.clientHeight * escala));
      if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; gl.viewport(0, 0, w, h); }
      abre = Math.min(abre + dt / 3.2, 1);
      // Arranca lento y toma velocidad: se siente entrar al túnel.
      t += dt * (reducido.matches ? 0.2 : 0.35 + 0.65 * Math.min(abre * 1.4, 1));
      gl.uniform2f(uRes, w, h); gl.uniform1f(uT, t); gl.uniform1f(uAbre, abre);
      gl.drawArrays(gl.TRIANGLES, 0, 6);
      if (!document.hidden) requestAnimationFrame(cuadro);
    }
    document.addEventListener('visibilitychange', () => { previo = 0; if (!document.hidden) requestAnimationFrame(cuadro); });
    requestAnimationFrame(cuadro);
  }
  window.TTRAAgujeroDeGusano = { montar };
})();
