// Banda sonora de /blackhole, sintetizada con Web Audio (sin archivos): pad grave en re menor,
// latido sub-grave, viento de ruido y una melodía chiptune cuantizada a 32 niveles ("32 bits"),
// con eco y reverb. Loop infinito sobre cuatro acordes: Dm - Bb - Gm - Am.
(() => {
  const Contexto = window.AudioContext || window.webkitAudioContext;
  if (!Contexto) return;
  const ctx = new Contexto();
  const BARRA = 8; // segundos por acorde
  const hz = (midi) => 440 * Math.pow(2, (midi - 69) / 12);

  const master = ctx.createGain();
  master.gain.value = 0;
  master.connect(ctx.destination);

  // Reverb: impulso de ruido que decae (5 s).
  const largo = ctx.sampleRate * 5;
  const impulso = ctx.createBuffer(2, largo, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const datos = impulso.getChannelData(c);
    for (let i = 0; i < largo; i++) datos[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / largo, 2.6);
  }
  const reverb = ctx.createConvolver();
  reverb.buffer = impulso;
  const reverbGain = ctx.createGain();
  reverbGain.gain.value = 0.7;
  reverb.connect(reverbGain).connect(master);
  const seco = ctx.createGain();
  seco.gain.value = 0.55;
  seco.connect(master);
  const bus = ctx.createGain();
  bus.connect(seco);
  bus.connect(reverb);

  // Eco del lead: 0.62 s con realimentación oscura.
  const eco = ctx.createDelay(2);
  eco.delayTime.value = 0.62;
  const ecoFb = ctx.createGain();
  ecoFb.gain.value = 0.5;
  const ecoTono = ctx.createBiquadFilter();
  ecoTono.type = 'lowpass';
  ecoTono.frequency.value = 1800;
  eco.connect(ecoTono).connect(ecoFb).connect(eco);
  ecoTono.connect(bus);

  // Cuantizador de 32 niveles para el lead.
  const curva = new Float32Array(4097);
  for (let i = 0; i < curva.length; i++) curva[i] = Math.round(((i / 2048) - 1) * 16) / 16;
  const crush = ctx.createWaveShaper();
  crush.curve = curva;
  const leadGain = ctx.createGain();
  leadGain.gain.value = 0.11;
  crush.connect(leadGain);
  leadGain.connect(bus);
  leadGain.connect(eco);

  // Onda de pulso al 25 % (sonido de consola de 8/16 bits).
  const N = 32;
  const real = new Float32Array(N);
  const imag = new Float32Array(N);
  for (let n = 1; n < N; n++) imag[n] = (2 / (n * Math.PI)) * Math.sin(n * Math.PI * 0.25);
  const pulso = ctx.createPeriodicWave(real, imag);

  const acordes = [
    { bajo: 26, pad: [50, 53, 57, 62] }, // Dm
    { bajo: 34, pad: [46, 50, 53, 58] }, // Bb
    { bajo: 31, pad: [43, 46, 50, 55] }, // Gm
    { bajo: 33, pad: [45, 48, 52, 57] }, // Am
  ];
  const escala = [62, 64, 65, 67, 69, 70, 72, 74, 76, 77, 79, 81]; // re menor natural
  let melodia = 9;

  function voz(tipo, frecuencia, t0, duracion, volumen, ataque, destino, filtro) {
    const osc = ctx.createOscillator();
    osc.type = tipo;
    osc.frequency.value = frecuencia;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0, t0);
    g.gain.linearRampToValueAtTime(volumen, t0 + ataque);
    g.gain.setValueAtTime(volumen, t0 + duracion - ataque);
    g.gain.linearRampToValueAtTime(0, t0 + duracion + ataque);
    let salida = osc;
    if (filtro) { osc.connect(filtro); salida = filtro; }
    salida.connect(g).connect(destino);
    osc.start(t0);
    osc.stop(t0 + duracion + ataque + 0.1);
    return osc;
  }

  function barra(t0, indice) {
    const acorde = acordes[indice % acordes.length];
    // Sub-grave y su octava.
    voz('sine', hz(acorde.bajo), t0, BARRA, 0.5, 2.5, seco);
    voz('triangle', hz(acorde.bajo + 12), t0, BARRA, 0.1, 2.5, bus);
    // Pad: tres sierras desafinadas por nota a través de un pasabajos que respira.
    for (const nota of acorde.pad) {
      const filtro = ctx.createBiquadFilter();
      filtro.type = 'lowpass';
      filtro.frequency.setValueAtTime(260, t0);
      filtro.frequency.linearRampToValueAtTime(700, t0 + BARRA * 0.6);
      filtro.frequency.linearRampToValueAtTime(260, t0 + BARRA + 2);
      filtro.Q.value = 0.7;
      for (const cents of [-9, 0, 9]) {
        const osc = voz('sawtooth', hz(nota), t0, BARRA, 0.028, 3, bus, filtro);
        osc.detune.value = cents;
      }
    }
    // Latido sub-grave, uno por cada dos segundos.
    for (let b = 0; b < BARRA; b += 2) {
      const osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(58, t0 + b);
      osc.frequency.exponentialRampToValueAtTime(30, t0 + b + 0.5);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0.0001, t0 + b);
      g.gain.exponentialRampToValueAtTime(0.38, t0 + b + 0.03);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + b + 0.9);
      osc.connect(g).connect(seco);
      osc.start(t0 + b);
      osc.stop(t0 + b + 1);
    }
    // Viento espacial: ruido con pasabanda que barre despacio.
    const ruido = ctx.createBufferSource();
    const buf = ctx.createBuffer(1, ctx.sampleRate * (BARRA + 4), ctx.sampleRate);
    const d = buf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    ruido.buffer = buf;
    const banda = ctx.createBiquadFilter();
    banda.type = 'bandpass';
    banda.Q.value = 6;
    banda.frequency.setValueAtTime(300 + Math.random() * 300, t0);
    banda.frequency.linearRampToValueAtTime(700 + Math.random() * 900, t0 + BARRA);
    const gr = ctx.createGain();
    gr.gain.setValueAtTime(0, t0);
    gr.gain.linearRampToValueAtTime(0.05, t0 + 4);
    gr.gain.linearRampToValueAtTime(0, t0 + BARRA + 3);
    ruido.connect(banda).connect(gr).connect(bus);
    ruido.start(t0);
    ruido.stop(t0 + BARRA + 4);
    // Melodía triste: pocas notas, con sesgo a bajar y silencios largos.
    for (let paso = 0; paso < BARRA; paso += 1) {
      if (Math.random() > 0.38) continue;
      melodia = Math.max(2, Math.min(escala.length - 1, melodia + (Math.random() < 0.62 ? -1 : 1) * (1 + (Math.random() < 0.25 ? 1 : 0))));
      const t = t0 + paso + 0.02;
      const osc = ctx.createOscillator();
      osc.setPeriodicWave(pulso);
      osc.frequency.value = hz(escala[melodia]);
      const vib = ctx.createOscillator();
      vib.frequency.value = 5;
      const vibGain = ctx.createGain();
      vibGain.gain.value = 3;
      vib.connect(vibGain).connect(osc.detune);
      const g = ctx.createGain();
      g.gain.setValueAtTime(0, t);
      g.gain.linearRampToValueAtTime(1, t + 0.03);
      g.gain.exponentialRampToValueAtTime(0.001, t + 1.8);
      osc.connect(g).connect(crush);
      osc.start(t); vib.start(t);
      osc.stop(t + 2); vib.stop(t + 2);
    }
  }

  // Planificador: siempre hay dos compases agendados por delante.
  let proximo = 0;
  let indice = 0;
  let timer = 0;
  function agendar() {
    if (!proximo) proximo = ctx.currentTime + 0.1;
    while (proximo < ctx.currentTime + BARRA * 2) {
      barra(proximo, indice++);
      proximo += BARRA;
    }
  }

  let arrancado = false;
  function arrancar() {
    if (arrancado) return;
    arrancado = true;
    agendar();
    timer = setInterval(agendar, 1000);
    master.gain.setValueAtTime(0, ctx.currentTime);
    master.gain.linearRampToValueAtTime(0.8, ctx.currentTime + 6);
  }
  // Si el navegador no deja sonar sin un gesto, queda esperando: el primer toque lo habilita.
  function intentar() {
    ctx.resume().catch(() => {});
    if (ctx.state === 'running') arrancar();
  }
  ctx.addEventListener('statechange', () => { if (ctx.state === 'running') arrancar(); });
  intentar();

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) ctx.suspend(); else ctx.resume();
  });

  window.blackholeAudio = {
    // true si el primer toque tiene que servir para habilitar el sonido (iOS/Safari).
    necesitaGesto: () => ctx.state !== 'running',
    habilitar: () => { intentar(); ctx.resume().then(arrancar).catch(() => {}); },
    salir: (despues) => {
      clearInterval(timer);
      master.gain.cancelScheduledValues(ctx.currentTime);
      master.gain.setValueAtTime(master.gain.value, ctx.currentTime);
      master.gain.linearRampToValueAtTime(0, ctx.currentTime + 0.25);
      setTimeout(despues, 260);
    },
  };
})();
