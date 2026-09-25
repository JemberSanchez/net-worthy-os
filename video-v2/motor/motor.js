// Runtime del motor v2: construye UNA timeline GSAP a partir de PLAN (storyboard ya resuelto por
// construir.py: todas las anclas convertidas a segundos). Una función por tipo de escena del
// catálogo; el markup lo pone construir.py, aquí solo se anima. Determinista: PRNG con semilla.
(function () {
  const P = window.PLAN, D = P.D;
  const tl = gsap.timeline({ paused: true });
  let seed = 1337; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const $ = (id) => document.getElementById(id);
  const q = (sel) => document.querySelector(sel);
  const inn = (sel, at, from, dur = 0.3, ease = "power3.out") =>
    tl.fromTo(sel, from, { x: 0, y: 0, scale: 1, opacity: 1, rotation: 0, filter: "blur(0px)", duration: dur, ease }, at);
  const out = (sel, at, dur = 0.2) => tl.to(sel, { y: -160, opacity: 0, filter: "blur(12px)", duration: dur, ease: "power3.in" }, at);
  const drawP = (sel, at, dur) => document.querySelectorAll(sel).forEach((p, i) =>
    tl.fromTo(p, { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: dur, ease: "power2.out" }, at + i * 0.08));
  const flash = (at, a = 0.22) => {
    tl.fromTo("#flash", { opacity: 0 }, { opacity: a, duration: 0.05, ease: "none", immediateRender: false }, at);
    tl.to("#flash", { opacity: 0, duration: 0.35, ease: "power2.out" }, at + 0.05);
  };
  const strike = (sel, at) => tl.fromTo(sel, { scaleX: 0 }, { scaleX: 1, duration: 0.18, ease: "power3.out" }, at);
  const counter = (el, from, to, at, dur, fmt, ease = "power2.out") => {
    const o = { v: from };
    tl.fromTo(o, { v: from }, { v: to, duration: dur, ease, onUpdate: () => { el.textContent = fmt(o.v); } }, at);
  };
  const money = (p) => (v) => p + Math.round(v).toLocaleString("en-US");
  const burst = (host, at, n = 24) => {
    for (let i = 0; i < n; i++) {
      const c = document.createElement("div"); c.className = "coin"; c.id = host.id + "-bc" + i; c.textContent = "$"; host.appendChild(c);
      const a = rnd() * Math.PI * 2, d = 380 + rnd() * 480;
      tl.fromTo(c, { x: 0, y: 0, opacity: 1, scale: 0.4, rotation: 0 },
        { x: Math.cos(a) * d, y: Math.sin(a) * d * 0.9 + 160, scale: 0.8 + rnd(), rotation: (rnd() - 0.5) * 720, opacity: 0, duration: 0.9 + rnd() * 0.4, ease: "power3.out" }, at + rnd() * 0.05);
    }
  };

  // ---------- capas persistentes ----------
  tl.fromTo("#glow", { x: -120, y: 0 }, { x: 260, y: 260, duration: D, ease: "sine.inOut" }, 0);
  tl.fromTo("#progress", { scaleX: 0 }, { scaleX: 1, duration: D, ease: "none" }, 0);
  tl.fromTo("#grain", { x: 0, y: 0 }, { x: -180, y: -140, duration: D, ease: "steps(600)" }, 0);
  (P.aviso.ventanas || []).forEach(([a, b]) => {
    tl.fromTo("#aviso", { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: false }, a);
    tl.to("#aviso", { opacity: 0, duration: 0.2 }, b - 0.2);
  });
  if (P.aviso.final != null) tl.fromTo("#aviso", { opacity: 0 }, { opacity: 1, duration: 0.3, immediateRender: false }, P.aviso.final);

  // ---------- fotos: Ken Burns (dirección por preset; el cuadro nunca queda quieto) ----------
  const KB = {
    push: [{ scale: 1.08, x: 0, y: 30 }, { scale: 1.26, x: 0, y: -30 }],
    pull: [{ scale: 1.3, x: 0, y: -30 }, { scale: 1.08, x: 0, y: 30 }],
    izq: [{ scale: 1.3, x: 90, y: 0 }, { scale: 1.42, x: -90, y: 0 }],
    der: [{ scale: 1.3, x: -90, y: 0 }, { scale: 1.42, x: 90, y: 0 }],
    sube: [{ scale: 1.2, x: -30, y: 70 }, { scale: 1.06, x: 20, y: -50 }],
    final: [{ scale: 1.12, x: -80, y: 60 }, { scale: 1.5, x: 80, y: -160 }],
  };
  // b-roll de vídeo: el metraje ya se mueve; solo un empuje suave, sobre el CONTENEDOR (no el <video>)
  const KBV = { pull: [{ scale: 1.12 }, { scale: 1.02 }] };
  P.fotos.forEach((f) => {
    const sel = "#" + f.id + (f.video ? "" : "-img");
    const [a, b] = f.video ? KBV[f.mov] || [{ scale: 1.02 }, { scale: 1.12 }] : KB[f.mov] || KB.push;
    tl.fromTo(sel, { ...a, opacity: f.opacidad }, { ...b, opacity: f.opacidad, duration: f.t1 - f.t0, ease: "none" }, f.t0);
    if (f.aparece) tl.fromTo(sel, { opacity: 0 }, { opacity: f.opacidad, duration: 0.5, immediateRender: false }, f.aparece);
  });

  // ---------- catálogo de escenas ----------
  const ESC = {
    foto(s, id) {
      if (s.kicker) inn(`#${id}-kicker`, s.kicker.en, { y: 30, opacity: 0 }, 0.25);
      if (s.titulo) inn(`#${id}-titulo`, s.titulo.en, { scale: 1.8, opacity: 0, filter: "blur(18px)" }, 0.3, "power4.out");
      if (s.sub) inn(`#${id}-sub`, s.sub.en, { y: 20, opacity: 0 }, 0.25);
    },
    revelacion(s, id) {
      inn(`#${id}-l1`, s.t0 + 0.02, { y: 40, opacity: 0 }, 0.25);
      inn(`#${id}-l2`, s.linea2.en, { scale: 2.2, opacity: 0, filter: "blur(20px)" }, 0.28, "power4.out");
      if (s.golpe != null) {
        tl.to(`#${id}-l2`, { scale: 1.08, duration: 0.12, ease: "power4.out" }, s.golpe);
        tl.to(`#${id}-l2`, { scale: 1.0, duration: 0.4, ease: "power2.out" }, s.golpe + 0.12);
        tl.to(`#${id}-l1`, { opacity: 0.35, duration: 0.3 }, s.golpe);
        flash(s.golpe, 0.25); burst($(`${id}-burst`), s.golpe);
      }
      out(`#${id} .stack`, s.t1 - 0.2);
    },
    lista(s, id) {
      s.items.forEach((it, k) => {
        const from = s.icono === "x" ? { x: k % 2 ? 700 : -700, opacity: 0 } : { x: -500, opacity: 0 };
        inn(`#${id}-i${k}`, it.en - 0.06, from, 0.26, "power4.out");
        drawP(`#${id}-i${k} .mk path`, it.marca != null ? it.marca : it.en + 0.12, s.icono === "x" ? 0.16 : 0.2);
      });
      const n = s.items.length;
      if (s.icono === "x" && n > 1) tl.to(s.items.slice(0, -1).map((_, k) => `#${id}-i${k}`).join(","), { opacity: 0.55, duration: 0.2 }, s.items[n - 1].en);
      else tl.to(`#${id}-i${n - 1}`, { scale: 1.08, duration: 0.15, yoyo: true, repeat: 1 }, s.items[n - 1].en + 0.5);
      out(`#${id} .stack`, s.t1 - 0.2);
    },
    titulo(s, id) {
      if (s.kicker) inn(`#${id}-k`, s.kicker.en, { y: -20, opacity: 0 }, 0.22);
      (s.lineas || []).forEach((l, k) => {
        const from = l.estilo === "boton" ? { scale: 1.6, opacity: 0 } : k === 0 ? { y: 80, opacity: 0 } : { y: 60, opacity: 0 };
        inn(`#${id}-l${k}`, l.en - 0.05, from, 0.26, "power4.out");
      });
      if (s.icono) {
        inn(`#${id}-ico`, s.icono.en - 0.05, { scale: 0.3, opacity: 0, rotation: -90 }, 0.3, "back.out(2)");
        tl.fromTo(`#${id}-ico`, { rotation: 0 }, { rotation: 240, duration: s.t1 - s.icono.en, ease: "none", immediateRender: false }, s.icono.en + 0.3);
      }
      if (s.contador) counter($(`${id}-n`), 0, s.contador.valor, s.contador.en, 0.7, (v) => Math.round(v));
      if (s.cheque) {
        inn(`#${id}-cheque`, s.cheque.en - 0.05, { y: 400, rotation: 8, opacity: 0 }, 0.3);
        if (s.cheque.tachar != null) strike(`#${id}-cheque .strike`, s.cheque.tachar);
      }
      if (s.tachar) {
        strike(`#${id}-t${s.tachar.linea}`, s.tachar.en);
        tl.to(`#${id}-l${s.tachar.linea}`, { opacity: 0.45, scale: 0.92, duration: 0.3 }, s.tachar.en + 0.2);
      }
      if (s.alarma) tl.fromTo(`#${id}-scan`, { y: 0 }, { y: 1900, duration: 1.2, ease: "none", repeat: 1 }, s.t0);
      const last = (s.lineas || []).length ? s.lineas[s.lineas.length - 1].en : s.t0;
      tl.fromTo(`#${id} .stack`, { scale: 1 }, { scale: 1.07, duration: Math.max(0.3, s.t1 - last - 0.5), ease: "none", immediateRender: false }, last + 0.3);
      out(`#${id} .stack`, s.t1 - 0.2);
    },
    tarjetas(s, id) {
      s.imgs.forEach((c, k) => {
        const rot = [-9, 6, -3, 4][k % 4], dx = [-40, 30, 0, 20][k % 4];
        tl.fromTo(`#${id}-c${k}`, { y: 1300, rotation: rot * 3, x: dx, opacity: 1 }, { y: (k - 1) * 26, rotation: rot, x: dx, duration: 0.45, ease: "power3.out" }, c.en - 0.1);
      });
      tl.fromTo(`#${id} .cert img`, { scale: 1.12 }, { scale: 1.0, duration: s.t1 - s.t0, ease: "none" }, s.t0);
      if (s.titulo) inn(`#${id}-tit`, s.titulo.en - 0.05, { y: -30, opacity: 0 }, 0.25);
      if (s.flujo) {
        const f = s.flujo;
        inn(`#${id}-flujo`, f.en, { y: 30, opacity: 0 }, 0.25);
        if (f.contador) inn(`#${id}-cnt`, f.en, { y: 40, opacity: 0 }, 0.25);
        const host = $(`${id}-coins`), N = 12, c0 = f.en + 0.1, c1 = f.hasta;
        for (let i = 0; i < N; i++) {
          const c = document.createElement("div"); c.className = "coin"; c.id = `${id}-dc${i}`; c.textContent = "$"; host.appendChild(c);
          const t = c0 + (c1 - c0) * i / N;
          tl.fromTo(c, { x: (rnd() - 0.5) * 520, y: (rnd() - 0.5) * 300, opacity: 0, scale: 0.5 }, { x: 0, y: 420, opacity: 1, scale: 1, duration: 0.42, ease: "power2.in" }, t);
          tl.to(c, { opacity: 0, scale: 0.3, duration: 0.08 }, t + 0.42);
        }
        if (f.contador) {
          counter($(`${id}-cntn`), f.contador.desde, f.contador.valor, c0 + 0.4, c1 - c0 + 0.45, (v) => Math.round(v), "power1.in");
          tl.to(`#${id}-cnt .n`, { scale: 1.2, duration: 0.1, yoyo: true, repeat: 1 }, c1 - 0.2);
        }
      }
      tl.to(`#${id} .cert`, { y: -1400, rotation: 8, duration: 0.3, ease: "power3.in" }, s.t1 - 0.3);
    },
    contador3d(s, id) {
      const L = s.llega, t0 = s.t0 + 0.05, split = t0 + (L - t0) * 0.62;
      const P1 = [t0, split - t0, s.valor * 0.056], P2 = [split, L - split, s.valor];
      window.__P3D = { P1, P2, t0: s.t0, t1: s.t1, cols: s.columnas || 6, valor: s.valor };
      const m = { v: 0 }, el = $(`${id}-money`), f = money(s.prefijo || "$");
      tl.fromTo(m, { v: 0 }, { v: P1[2], duration: P1[1], ease: "power1.in", onUpdate: () => { el.textContent = f(m.v); } }, P1[0]);
      tl.to(m, { v: P2[2], duration: P2[1], ease: "power3.in", onUpdate: () => { el.textContent = f(m.v); } }, P2[0]);
      tl.to(`#${id}-money`, { color: "#d8b25a", scale: 1.12, duration: 0.12, ease: "power4.out" }, L);
      tl.to(`#${id}-money`, { scale: 1.0, duration: 0.3, ease: "power2.out" }, L + 0.12);
      flash(L, 0.22);
      if (s.kicker) inn(`#${id}-k`, s.kicker.en - 0.05, { y: -30, opacity: 0 }, 0.25);
      if (s.pill) inn(`#${id}-pill`, s.pill.en - 0.05, { y: 60, opacity: 0 }, 0.3, "back.out(1.8)");
    },
    curva(s, id) {
      const dibuja = s.fin || s.t0 + 0.8;
      tl.fromTo(`#${id}-curve`, { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: dibuja - s.t0, ease: "power1.in" }, s.t0 + 0.05);
      if (s.aportado) { inn(`#${id}-ap`, s.aportado.en, { x: -40, opacity: 0 }, 0.25); tl.fromTo(`#${id}-paid`, { opacity: 0 }, { opacity: 1, duration: 0.25 }, s.aportado.en); }
      if (s.area) { tl.fromTo(`#${id}-area`, { opacity: 0 }, { opacity: 1, duration: 0.5 }, s.area.en); inn(`#${id}-ar`, s.area.en, { scale: 0.7, opacity: 0 }, 0.3, "back.out(2)"); }
      else tl.fromTo(`#${id}-area`, { opacity: 0 }, { opacity: 0.6, duration: 0.5 }, s.t0 + 0.3);
      if (s.ilustrativo) inn(`#${id}-ill`, s.t0 + 0.1, { opacity: 0 }, 0.3);
      if (s.titulo) inn(`#${id}-tit`, s.titulo.en - 0.05, { y: -20, opacity: 0 }, 0.25);
      (s.escalas || []).forEach((e, k, arr) => {
        const a = k === 0 ? s.t0 + 0.3 : e.en;
        tl.fromTo(`#${id}-e${k}`, { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.14 }, a);
        if (k < arr.length - 1) tl.to(`#${id}-e${k}`, { opacity: 0, duration: 0.1 }, arr[k + 1].en);
      });
      if (s.encoger) tl.fromTo(`#${id}-svg`, { scale: 1, y: 0 }, { scale: 0.62, y: 160, duration: s.encoger.hasta - s.encoger.en, ease: "power2.inOut" }, s.encoger.en);
      else tl.fromTo(`#${id}-svg`, { scale: 0.94, y: 30 }, { scale: 1.04, y: -20, duration: s.t1 - s.t0, ease: "none", immediateRender: false }, s.t0);
      if (!s.encoger) out(`#${id}-svg`, s.t1 - 0.2);
    },
    puntos(s, id) {
      const host = $(`${id}-dots`), COLS = 12, N = s.n;
      for (let i = 0; i < N; i++) {
        const d = document.createElement("div"); d.className = "dot"; d.id = `${id}-d${i}`; host.appendChild(d);
        d.style.left = (i % COLS) * 70 + "px"; d.style.top = Math.floor(i / COLS) * 70 + "px";
        tl.fromTo(d, { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.18, ease: "back.out(3)" }, s.cuenta.en + i * (0.66 / N));
      }
      inn(`#${id}-num`, s.t0 + 0.05, { y: -40, opacity: 0 }, 0.25);
      counter($(`${id}-n`), 0, N, s.cuenta.en, 0.66, (v) => Math.round(v), "power1.out");
      if (s.cae) {
        const k = Math.floor(N * 0.46);
        tl.to(`#${id}-d${k}`, { background: "#e0533d", duration: 0.1 }, s.cae.en - 0.15);
        tl.to(`#${id}-d${k}`, { y: 700, rotation: 200, opacity: 0, duration: 0.7, ease: "power2.in" }, s.cae.en);
        if (s.cae.img) {
          tl.fromTo(`#${id}-card`, { opacity: 0, rotation: -14, scale: 1.3, y: 60 }, { opacity: 1, rotation: -5, scale: 1, y: 0, duration: 0.25, ease: "power3.out" }, s.cae.en);
          tl.to(`#${id}-card`, { opacity: 0, y: 500, rotation: 6, duration: 0.3, ease: "power3.in" }, s.cae.hasta);
        }
        if (s.cae.texto) { inn(`#${id}-l1`, s.cae.en + 0.25, { opacity: 0, y: 20 }, 0.2); tl.to(`#${id}-l1`, { opacity: 0, duration: 0.15 }, (s.atenuar ? s.atenuar.en : s.t1) - 0.5); }
      }
      if (s.atenuar) {
        const idx = [...Array(s.atenuar.n)].map((_, j) => Math.floor((j + 0.37) * N / s.atenuar.n));
        idx.forEach((k, j) => tl.to(`#${id}-d${k}`, { background: "rgba(224,83,61,0.35)", scale: 0.75, duration: 0.15 }, s.atenuar.en + j * 0.05));
        if (s.atenuar.texto) inn(`#${id}-l2`, s.atenuar.en, { opacity: 0, y: 20 }, 0.2);
      }
      tl.fromTo(`#${id}-dots`, { y: 0 }, { y: -30, duration: s.t1 - s.t0, ease: "none" }, s.t0);
    },
    anios(s, id) {
      const a = s.cuenta.en, b = s.fin, el = $(`${id}-yr`), yr = { v: s.desde };
      if (s.kicker) inn(`#${id}-k`, s.t0 + 0.05, { y: -20, opacity: 0 }, 0.2);
      tl.fromTo(yr, { v: s.desde }, { v: s.hasta, duration: b - a, ease: "none", onUpdate: () => { el.textContent = Math.round(yr.v); } }, a);
      tl.fromTo(`#${id}-fill`, { scaleX: 0 }, { scaleX: 1, duration: b - a, ease: "none" }, a);
      (s.hitos || []).forEach(([y], k) => {
        const t = a + (y - s.desde) / (s.hasta - s.desde) * (b - a);
        tl.fromTo(`#${id}-h${k}`, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.08 }, t - 0.05);
        tl.to(`#${id}-h${k}`, { opacity: 0, y: -30, duration: 0.12 }, t + 0.32);
      });
      if (s.etiqueta) inn(`#${id}-l`, s.etiqueta.en, { opacity: 0, y: 20 }, 0.2);
    },
    cta(s, id) {
      inn(`#${id}-a`, s.a.en - 0.05, { x: -500, opacity: 0 }, 0.25, "power4.out");
      inn(`#${id}-o`, s.a.en + 0.2, { scale: 0.5, opacity: 0 }, 0.2);
      inn(`#${id}-b`, s.b.en - 0.05, { x: 500, opacity: 0 }, 0.25, "power4.out");
      if (s.pregunta) {
        tl.to(`#${id}-vs`, { y: -60, scale: 0.8, duration: 0.35, ease: "power3.inOut" }, s.pregunta.en - 0.1);
        tl.to(`#${id}-o`, { opacity: 0, duration: 0.2 }, s.pregunta.en - 0.1);
        inn(`#${id}-q`, s.pregunta.en, { y: 40, opacity: 0 }, 0.25);
        if (s.botones && s.botones.length) tl.to(`#${id}-q`, { opacity: 0, y: -30, duration: 0.2 }, s.botones[0].en - 0.25);
      }
      (s.botones || []).forEach((b, k) => inn(`#${id}-p${k}`, b.en - 0.05, { y: 60, opacity: 0 }, 0.25, "back.out(2)"));
      // tarjeta final: la voz ya calló; movimiento REAL (medir_ritmo cazó 2,8 s quietos con solo un pulso sutil)
      const fin = P.fin_voz;
      inn(`#${id}-s`, fin, { opacity: 0, y: 20 }, 0.25);
      tl.to(`#${id} .pill`, { scale: 1.14, duration: 0.4, yoyo: true, repeat: 5, ease: "sine.inOut" }, fin + 0.2);
      tl.to(`#${id}-s`, { y: 22, duration: 0.35, yoyo: true, repeat: 5, ease: "sine.inOut" }, fin + 0.4);
      tl.fromTo(`#${id}-luz`, { x: -600, rotation: 14, opacity: 1 }, { x: 1300, rotation: 14, opacity: 1, duration: 1.3, ease: "power1.inOut", repeat: 1 }, fin + 0.05);
    },
  };
  P.escenas.forEach((s, k) => ESC[s.tipo](s, "s" + k));

  // ---------- subtítulos: grupos <=3 palabras; se omite el grupo que la escena YA muestra escrito ----------
  const W = P.words, caps = $("caps"), groups = []; let cur = [];
  const [C0, C1] = P.subtitulos;
  for (let i = C0; i <= C1; i++) {
    const x = W[i]; cur.push(x);
    const fin = /[.,?!]$/.test(x.text), gap = i < C1 ? W[i + 1].start - x.end : 1;
    if (cur.length === 3 || fin || gap > 0.25) { groups.push(cur); cur = []; }
  }
  if (cur.length) groups.push(cur);
  const nrm = (s) => s.toLowerCase().replace(/[^a-z0-9'$]/g, "");
  const HOT = new Set(P.calientes.map(nrm));
  const enPantalla = (t) => { const s = P.escenas.find((e) => t >= e.t0 && t < e.t1); return s ? new Set(s.texto_visible) : new Set(); };
  groups.forEach((g, gi) => {
    const vis = enPantalla(g[0].start);
    if (g.every((x) => vis.has(nrm(x.text)))) return;     // duplicado: la escena ya lo dice
    const el = document.createElement("div"); el.className = "cg"; el.id = "cg" + gi; caps.appendChild(el);
    const gS = g[0].start - 0.05;
    // Nunca ocultar antes de mostrar: con palabras de duración 0 (alineación interpolada) el
    // "siguiente grupo" podía empezar antes que este, el fade-out caía ANTES del fade-in y el
    // subtítulo se quedaba pegado el resto del vídeo (Grace Groner, 23-sep).
    const gE = Math.max(gS + 0.3, groups[gi + 1] ? Math.min(groups[gi + 1][0].start - 0.05, g[g.length - 1].end + 0.35) : g[g.length - 1].end + 0.4);
    tl.fromTo(el, { opacity: 0, y: 24, scale: 0.92 }, { opacity: 1, y: 0, scale: 1, duration: 0.1, ease: "power2.out" }, gS);
    tl.to(el, { opacity: 0, duration: 0.05 }, gE - 0.05);
    g.forEach((x, k) => {
      const s = document.createElement("span"); s.className = "w"; s.id = `w${gi}_${k}`; s.textContent = x.text.replace(/[.,?!]$/, ""); el.appendChild(s);
      const hot = HOT.has(nrm(x.text));
      tl.fromTo(s, { color: "#f4f6f3", scale: 1 }, { color: hot ? "#d8b25a" : "#9fe3c4", scale: hot ? 1.06 : 1.03, duration: 0.08, ease: "power2.out", immediateRender: false }, x.start - 0.04);
      tl.to(s, { color: "#f4f6f3", scale: 1, duration: 0.1 }, x.end);
    });
  });

  window.__timelines["main"] = tl;
})();
