// Runtime del motor v2: construye UNA timeline GSAP a partir de PLAN (storyboard ya resuelto por
// construir.py: todas las anclas convertidas a segundos). Una función por tipo de escena del
// catálogo; el markup lo pone construir.py, aquí solo se anima. Determinista: PRNG con semilla.
(function () {
  const P = window.PLAN,
    D = P.D;
  const tl = gsap.timeline({ paused: true });
  let seed = 1337;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const $ = (id) => document.getElementById(id);
  const q = (sel) => document.querySelector(sel);
  // Text entrance chosen per video (edicion.py). It replaces only generic rises: opacity + small x/y.
  const ENTRADA = P.edicion && P.edicion.texto;
  const generica = (f) =>
    Object.keys(f).every((k) => ["opacity", "x", "y"].includes(k)) &&
    Math.abs(f.x || 0) <= 60 &&
    Math.abs(f.y || 0) <= 60;
  const inn = (sel, at, from, dur = 0.3, ease = "power3.out") => {
    const pre = ENTRADA && generica(from) ? ENTRADA : null;
    return tl.fromTo(
      sel,
      pre ? pre.from : from,
      {
        x: 0,
        y: 0,
        scale: 1,
        opacity: 1,
        rotation: 0,
        filter: "blur(0px)",
        ...(pre ? pre.to : {}),
        duration: pre ? dur * pre.k : dur,
        ease,
      },
      at,
    );
  };
  const out = (sel, at, dur = 0.2) =>
    tl.to(
      sel,
      {
        y: -160,
        opacity: 0,
        filter: "blur(12px)",
        duration: dur,
        ease: "power3.in",
      },
      at,
    );
  const drawP = (sel, at, dur) =>
    document
      .querySelectorAll(sel)
      .forEach((p, i) =>
        tl.fromTo(
          p,
          { strokeDasharray: 1, strokeDashoffset: 1 },
          { strokeDashoffset: 0, duration: dur, ease: "power2.out" },
          at + i * 0.08,
        ),
      );
  const flash = (at, a = 0.22) => {
    tl.fromTo(
      "#flash",
      { opacity: 0 },
      { opacity: a, duration: 0.05, ease: "none", immediateRender: false },
      at,
    );
    tl.to(
      "#flash",
      { opacity: 0, duration: 0.35, ease: "power2.out" },
      at + 0.05,
    );
  };
  const strike = (sel, at) =>
    tl.fromTo(
      sel,
      { scaleX: 0 },
      { scaleX: 1, duration: 0.18, ease: "power3.out" },
      at,
    );
  const counter = (el, from, to, at, dur, fmt, ease = "power2.out") => {
    const o = { v: from };
    tl.fromTo(
      o,
      { v: from },
      {
        v: to,
        duration: dur,
        ease,
        onUpdate: () => {
          el.textContent = fmt(o.v);
        },
      },
      at,
    );
  };
  const money = (p) => (v) => p + Math.round(v).toLocaleString("en-US");
  // Temblor de cámara en los golpes grandes (revelación, llegada del contador): lenguaje de edición
  // real en vez del estallido de monedas de clip-art (26-sep). Solo x/y de #cam: el punch-in usa scale.
  const sacudida = (at, a = 16) => {
    const pasos = [
      [a, -a * 0.6],
      [-a * 0.8, a * 0.5],
      [a * 0.5, a * 0.35],
      [-a * 0.3, -a * 0.2],
      [0, 0],
    ];
    let prev = [0, 0];
    pasos.forEach(([x, y], i) => {
      tl.fromTo(
        "#cam",
        { x: prev[0], y: prev[1] },
        { x, y, duration: 0.045, ease: "none", immediateRender: false },
        at + i * 0.045,
      );
      prev = [x, y];
    });
  };

  // ---------- capas persistentes ----------
  tl.fromTo(
    "#glow",
    { x: -120, y: 0 },
    { x: 260, y: 260, duration: D, ease: "sine.inOut" },
    0,
  );
  tl.fromTo(
    "#grain",
    { x: 0, y: 0 },
    { x: -180, y: -140, duration: D, ease: "steps(600)" },
    0,
  );
  (P.aviso.ventanas || []).forEach(([a, b]) => {
    tl.fromTo(
      "#aviso",
      { opacity: 0 },
      { opacity: 1, duration: 0.3, immediateRender: false },
      a,
    );
    tl.to("#aviso", { opacity: 0, duration: 0.2 }, b - 0.2);
  });
  if (P.aviso.final != null)
    tl.fromTo(
      P.aviso.completo ? "#avisofin" : "#aviso",
      { opacity: 0 },
      { opacity: 1, duration: 0.3, immediateRender: false },
      P.aviso.final,
    );
  // la PRUEBA: el documento entra de golpe, la cámara empuja hacia la frase y el subrayador la marca
  (P.pruebas || []).forEach((pr) => {
    const c = "#" + pr.id + "-cam";
    tl.fromTo(
      c,
      { scale: 1.14, rotation: -1.2, opacity: 0 },
      {
        scale: 0.96,
        rotation: 0,
        opacity: 1,
        duration: 0.2,
        ease: "power3.out",
        immediateRender: false,
      },
      pr.t0,
    );
    tl.fromTo(
      c,
      { scale: 0.96 },
      {
        scale: 1.06,
        duration: Math.max(0.2, pr.t1 - pr.t0 - 0.2),
        ease: "sine.out",
        immediateRender: false,
      },
      pr.t0 + 0.2,
    );
    tl.fromTo(
      "#" + pr.id + "-f",
      { opacity: 0 },
      {
        opacity: 1,
        duration: 0.25,
        ease: "power1.out",
        immediateRender: false,
      },
      Math.min(pr.t0 + 0.12, pr.marca - 0.1),
    );
    tl.fromTo(
      "#" + pr.id + "-m",
      { scaleX: 0 },
      { scaleX: 1, duration: 0.35, ease: "power2.out", immediateRender: false },
      pr.marca,
    );
    tl.to(c, { opacity: 0, duration: 0.15 }, pr.t1 - 0.15);
  });
  // sello de serie: entra con el logo sonoro y sale antes de la 2ª frase (no compite con el gancho)
  if (P.serie) {
    tl.fromTo(
      "#serie",
      { opacity: 0, y: -14, scale: 0.9 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.35,
        ease: "back.out(2)",
        immediateRender: false,
      },
      P.serie.t0,
    );
    tl.to(
      "#serie",
      { opacity: 0, y: -10, duration: 0.25, ease: "power2.in" },
      P.serie.t1 - 0.25,
    );
  }

  // ---------- fotos: Ken Burns (dirección por preset; el cuadro nunca queda quieto) ----------
  const KB = {
    push: [
      { scale: 1.08, x: 0, y: 30 },
      { scale: 1.26, x: 0, y: -30 },
    ],
    pull: [
      { scale: 1.3, x: 0, y: -30 },
      { scale: 1.08, x: 0, y: 30 },
    ],
    izq: [
      { scale: 1.3, x: 90, y: 0 },
      { scale: 1.42, x: -90, y: 0 },
    ],
    der: [
      { scale: 1.3, x: -90, y: 0 },
      { scale: 1.42, x: 90, y: 0 },
    ],
    sube: [
      { scale: 1.2, x: -30, y: 70 },
      { scale: 1.06, x: 20, y: -50 },
    ],
    final: [
      { scale: 1.12, x: -80, y: 60 },
      { scale: 1.5, x: 80, y: -160 },
    ],
  };
  // b-roll de vídeo: el metraje ya se mueve; solo un empuje suave, sobre el CONTENEDOR (no el <video>)
  const KBV = { pull: [{ scale: 1.12 }, { scale: 1.02 }] };
  P.fotos.forEach((f) => {
    const sel = "#" + f.id + (f.video ? "" : "-img");
    const [a, b] = f.cam
      ? [f.cam.a, f.cam.b]
      : f.video
        ? KBV[f.mov] || [{ scale: 1.02 }, { scale: 1.12 }]
        : KB[f.mov] || KB.push;
    tl.fromTo(
      sel,
      { ...a, opacity: f.opacidad },
      {
        ...b,
        opacity: f.opacidad,
        duration: f.t1 - f.t0,
        ease: f.cam ? f.cam.ease : "none",
      },
      f.t0,
    );
    if (f.aparece)
      tl.fromTo(
        sel,
        { opacity: 0 },
        { opacity: f.opacidad, duration: 0.5, immediateRender: false },
        f.aparece,
      );
  });

  // ---------- catálogo de escenas ----------
  const ESC = {
    foto(s, id) {
      if (s.kicker)
        inn(`#${id}-kicker`, s.kicker.en, { y: 30, opacity: 0 }, 0.25);
      if (s.titulo)
        inn(
          `#${id}-titulo`,
          s.titulo.en,
          { scale: 1.8, opacity: 0, filter: "blur(18px)" },
          0.3,
          "power4.out",
        );
      if (s.sub) inn(`#${id}-sub`, s.sub.en, { y: 20, opacity: 0 }, 0.25);
    },
    revelacion(s, id) {
      inn(`#${id}-l1`, s.t0 + 0.02, { y: 40, opacity: 0 }, 0.25);
      inn(
        `#${id}-l2`,
        s.linea2.en,
        { scale: 2.2, opacity: 0, filter: "blur(20px)" },
        0.28,
        "power4.out",
      );
      if (s.golpe != null) {
        tl.to(
          `#${id}-l2`,
          { scale: 1.08, duration: 0.12, ease: "power4.out" },
          s.golpe,
        );
        tl.to(
          `#${id}-l2`,
          { scale: 1.0, duration: 0.4, ease: "power2.out" },
          s.golpe + 0.12,
        );
        tl.to(
          `#${id}-l1`,
          { opacity: P.aspecto === "cine" ? 0.55 : 0.35, duration: 0.3 }, // 0.35 read 2.72:1 (critic L1)
          s.golpe,
        );
        flash(s.golpe, 0.25);
        sacudida(s.golpe);
      }
      out(`#${id} .stack`, s.t1 - 0.2);
    },
    lista(s, id) {
      s.items.forEach((it, k) => {
        const from =
          s.icono === "x"
            ? { x: k % 2 ? 700 : -700, opacity: 0 }
            : { x: -500, opacity: 0 };
        inn(`#${id}-i${k}`, it.en - 0.06, from, 0.26, "power4.out");
        drawP(
          `#${id}-i${k} .mk path`,
          it.marca != null ? it.marca : it.en + 0.12,
          s.icono === "x" ? 0.16 : 0.2,
        );
      });
      const n = s.items.length;
      if (s.icono === "x" && n > 1)
        tl.to(
          s.items
            .slice(0, -1)
            .map((_, k) => `#${id}-i${k}`)
            .join(","),
          { opacity: 0.55, duration: 0.2 },
          s.items[n - 1].en,
        );
      else
        tl.to(
          `#${id}-i${n - 1}`,
          { scale: 1.08, duration: 0.15, yoyo: true, repeat: 1 },
          s.items[n - 1].en + 0.5,
        );
      out(`#${id} .stack`, s.t1 - 0.2);
    },
    titulo(s, id) {
      if (s.kicker) inn(`#${id}-k`, s.kicker.en, { y: -20, opacity: 0 }, 0.22);
      (s.lineas || []).forEach((l, k) => {
        const from =
          l.estilo === "boton"
            ? { scale: 1.6, opacity: 0 }
            : k === 0
              ? { y: 80, opacity: 0 }
              : { y: 60, opacity: 0 };
        inn(`#${id}-l${k}`, l.en - 0.05, from, 0.26, "power4.out");
      });
      if (s.icono) {
        inn(
          `#${id}-ico`,
          s.icono.en - 0.05,
          { scale: 0.3, opacity: 0, rotation: -90 },
          0.3,
          "back.out(2)",
        );
        tl.fromTo(
          `#${id}-ico`,
          { rotation: 0 },
          {
            rotation: 240,
            duration: s.t1 - s.icono.en,
            ease: "none",
            immediateRender: false,
          },
          s.icono.en + 0.3,
        );
      }
      if (s.contador)
        counter($(`${id}-n`), 0, s.contador.valor, s.contador.en, 0.7, (v) =>
          Math.round(v),
        );
      if (s.cheque) {
        inn(
          `#${id}-cheque`,
          s.cheque.en - 0.05,
          { y: 400, rotation: 8, opacity: 0 },
          0.3,
        );
        if (s.cheque.tachar != null)
          strike(`#${id}-cheque .strike`, s.cheque.tachar);
      }
      if (s.tachar) {
        strike(`#${id}-t${s.tachar.linea}`, s.tachar.en);
        tl.to(
          `#${id}-l${s.tachar.linea}`,
          { opacity: 0.45, scale: 0.92, duration: 0.3 },
          s.tachar.en + 0.2,
        );
      }
      if (s.alarma)
        tl.fromTo(
          `#${id}-scan`,
          { y: 0 },
          { y: 1900, duration: 1.2, ease: "none", repeat: 1 },
          s.t0,
        );
      const last = (s.lineas || []).length
        ? s.lineas[s.lineas.length - 1].en
        : s.t0;
      tl.fromTo(
        `#${id} .stack`,
        { scale: 1 },
        {
          scale: 1.07,
          duration: Math.max(0.3, s.t1 - last - 0.5),
          ease: "none",
          immediateRender: false,
        },
        last + 0.3,
      );
      out(`#${id} .stack`, s.t1 - 0.2);
    },
    tarjetas(s, id) {
      s.imgs.forEach((c, k) => {
        const rot = [-9, 6, -3, 4][k % 4],
          dx = [-40, 30, 0, 20][k % 4];
        tl.fromTo(
          `#${id}-c${k}`,
          { y: 1300, rotation: rot * 3, x: dx, opacity: 1 },
          {
            y: (k - 1) * 26,
            rotation: rot,
            x: dx,
            duration: 0.45,
            ease: "power3.out",
          },
          c.en - 0.1,
        );
      });
      tl.fromTo(
        `#${id} .cert img`,
        { scale: 1.12 },
        { scale: 1.0, duration: s.t1 - s.t0, ease: "none" },
        s.t0,
      );
      if (s.titulo)
        inn(`#${id}-tit`, s.titulo.en - 0.05, { y: -30, opacity: 0 }, 0.25);
      if (s.flujo) {
        const f = s.flujo;
        inn(`#${id}-flujo`, f.en, { y: 30, opacity: 0 }, 0.25);
        if (f.contador) inn(`#${id}-cnt`, f.en, { y: 40, opacity: 0 }, 0.25);
        const c0 = f.en + 0.1,
          c1 = f.hasta; // sin monedas que caen: los certificados reales ya lo cuentan
        if (f.contador) {
          counter(
            $(`${id}-cntn`),
            f.contador.desde,
            f.contador.valor,
            c0 + 0.4,
            c1 - c0 + 0.45,
            (v) => Math.round(v),
            "power1.in",
          );
          tl.to(
            `#${id}-cnt .n`,
            { scale: 1.2, duration: 0.1, yoyo: true, repeat: 1 },
            c1 - 0.2,
          );
        }
      }
      tl.to(
        `#${id} .cert`,
        { y: -1400, rotation: 8, duration: 0.3, ease: "power3.in" },
        s.t1 - 0.3,
      );
    },
    contador3d(s, id) {
      const L = s.llega,
        t0 = s.t0 + 0.05,
        split = t0 + (L - t0) * 0.62;
      const P1 = [t0, split - t0, s.valor * 0.056],
        P2 = [split, L - split, s.valor];
      window.__P3D = {
        P1,
        P2,
        t0: s.t0,
        t1: s.t1,
        cols: s.columnas || 6,
        valor: s.valor,
      };
      const m = { v: 0 },
        el = $(`${id}-money`),
        f = money(s.prefijo ?? "$");
      tl.fromTo(
        m,
        { v: 0 },
        {
          v: P1[2],
          duration: P1[1],
          ease: "power1.in",
          onUpdate: () => {
            el.textContent = f(m.v);
          },
        },
        P1[0],
      );
      tl.to(
        m,
        {
          v: P2[2],
          duration: P2[1],
          ease: "power3.in",
          onUpdate: () => {
            el.textContent = f(m.v);
          },
        },
        P2[0],
      );
      tl.to(
        `#${id}-money`,
        { color: "#d8b25a", scale: 1.12, duration: 0.12, ease: "power4.out" },
        L,
      );
      tl.to(
        `#${id}-money`,
        { scale: 1.0, duration: 0.3, ease: "power2.out" },
        L + 0.12,
      );
      flash(L, 0.22);
      sacudida(L, 20);
      if (s.kicker)
        inn(`#${id}-k`, s.kicker.en - 0.05, { y: -30, opacity: 0 }, 0.25);
      if (s.pill)
        inn(
          `#${id}-pill`,
          s.pill.en - 0.05,
          { y: 60, opacity: 0 },
          0.3,
          "back.out(1.8)",
        );
    },
    curva(s, id) {
      const dibuja = s.fin || s.t0 + 0.8;
      tl.fromTo(
        `#${id}-curve`,
        { strokeDasharray: 1, strokeDashoffset: 1 },
        { strokeDashoffset: 0, duration: dibuja - s.t0, ease: "power1.in" },
        s.t0 + 0.05,
      );
      // punto que recorre la línea con año y valor: misma curva de avance (power1.in) que el trazo,
      // muestreado sobre los puntos del plan (no getPointAtLength: seek-safe y sin depender del layout)
      const pts = s.curva_pts || [],
        ph = $(`${id}-ph`),
        lab = $(`${id}-phl`);
      if (pts.length > 1 && ph && lab) {
        const L = pts.length - 1,
          fmt = money("$");
        const pon = (p) => {
          const f = Math.min(L, Math.max(0, p * L)),
            i = Math.floor(f),
            u = f - i,
            a = pts[i],
            b = pts[Math.min(L, i + 1)];
          const x = a[0] + (b[0] - a[0]) * u,
            y = a[1] + (b[1] - a[1]) * u,
            v = a[2] + (b[2] - a[2]) * u,
            an = a[3] + (b[3] - a[3]) * u;
          ph.setAttribute(
            "transform",
            `translate(${x.toFixed(1)},${y.toFixed(1)})`,
          );
          lab.setAttribute("x", Math.min(760, Math.max(100, x)).toFixed(1));
          lab.setAttribute("y", Math.max(40, y - 40).toFixed(1));
          const anio = s.curva_desde
            ? String(Math.floor(an))
            : `Yr ${Math.floor(an)}`;
          lab.textContent = s.curva_valores ? `${anio} · ${fmt(v)}` : anio;
        };
        const o = { p: 0 };
        tl.fromTo(
          o,
          { p: 0 },
          {
            p: 1,
            duration: dibuja - s.t0,
            ease: "power1.in",
            onUpdate: () => pon(o.p),
            immediateRender: false,
          },
          s.t0 + 0.05,
        );
        tl.fromTo(
          [ph, lab],
          { opacity: 0 },
          { opacity: 1, duration: 0.2 },
          s.t0 + 0.05,
        );
        pon(0);
      }
      if (s.aportado) {
        inn(`#${id}-ap`, s.aportado.en, { x: -40, opacity: 0 }, 0.25);
        tl.fromTo(
          `#${id}-paid`,
          { opacity: 0 },
          { opacity: 1, duration: 0.25 },
          s.aportado.en,
        );
      }
      if (s.area) {
        tl.fromTo(
          `#${id}-area`,
          { opacity: 0 },
          { opacity: 1, duration: 0.5 },
          s.area.en,
        );
        inn(
          `#${id}-ar`,
          s.area.en,
          { scale: 0.7, opacity: 0 },
          0.3,
          "back.out(2)",
        );
      }
      // el área entra cuando la línea LLEGA: antes destapaba el final de la curva (Grace, 26-sep)
      else
        tl.fromTo(
          `#${id}-area`,
          { opacity: 0 },
          { opacity: 0.6, duration: 0.4 },
          dibuja + 0.05,
        );
      if (s.ilustrativo) inn(`#${id}-ill`, s.t0 + 0.1, { opacity: 0 }, 0.3);
      if (s.titulo)
        inn(`#${id}-tit`, s.titulo.en - 0.05, { y: -20, opacity: 0 }, 0.25);
      (s.escalas || []).forEach((e, k, arr) => {
        const a = k === 0 ? s.t0 + 0.3 : e.en;
        tl.fromTo(
          `#${id}-e${k}`,
          { opacity: 0, y: 20 },
          { opacity: 1, y: 0, duration: 0.14 },
          a,
        );
        if (k < arr.length - 1)
          tl.to(`#${id}-e${k}`, { opacity: 0, duration: 0.1 }, arr[k + 1].en);
      });
      if (s.encoger)
        tl.fromTo(
          `#${id}-svg`,
          { scale: 1, y: 0 },
          {
            scale: 0.62,
            y: 160,
            duration: s.encoger.hasta - s.encoger.en,
            ease: "power2.inOut",
          },
          s.encoger.en,
        );
      else
        tl.fromTo(
          `#${id}-svg`,
          { scale: 0.94, y: 30 },
          {
            scale: 1.04,
            y: -20,
            duration: s.t1 - s.t0,
            ease: "none",
            immediateRender: false,
          },
          s.t0,
        );
      if (!s.encoger) out(`#${id}-svg`, s.t1 - 0.2);
    },
    puntos(s, id) {
      const host = $(`${id}-dots`),
        COLS = 12,
        N = s.n;
      for (let i = 0; i < N; i++) {
        const d = document.createElement("div");
        d.className = "dot";
        d.id = `${id}-d${i}`;
        host.appendChild(d);
        d.style.left = (i % COLS) * 70 + "px";
        d.style.top = Math.floor(i / COLS) * 70 + "px";
        tl.fromTo(
          d,
          { scale: 0, opacity: 0 },
          { scale: 1, opacity: 1, duration: 0.18, ease: "back.out(3)" },
          s.cuenta.en + i * (0.66 / N),
        );
      }
      inn(`#${id}-num`, s.t0 + 0.05, { y: -40, opacity: 0 }, 0.25);
      counter(
        $(`${id}-n`),
        0,
        N,
        s.cuenta.en,
        0.66,
        (v) => Math.round(v),
        "power1.out",
      );
      if (s.cae) {
        const k = Math.floor(N * 0.46);
        tl.to(
          `#${id}-d${k}`,
          { background: "#e0533d", duration: 0.1 },
          s.cae.en - 0.15,
        );
        tl.to(
          `#${id}-d${k}`,
          {
            y: 700,
            rotation: 200,
            opacity: 0,
            duration: 0.7,
            ease: "power2.in",
          },
          s.cae.en,
        );
        if (s.cae.img) {
          tl.fromTo(
            `#${id}-card`,
            { opacity: 0, rotation: -14, scale: 1.3, y: 60 },
            {
              opacity: 1,
              rotation: -5,
              scale: 1,
              y: 0,
              duration: 0.25,
              ease: "power3.out",
            },
            s.cae.en,
          );
          tl.to(
            `#${id}-card`,
            {
              opacity: 0,
              y: 500,
              rotation: 6,
              duration: 0.3,
              ease: "power3.in",
            },
            s.cae.hasta,
          );
        }
        if (s.cae.texto) {
          inn(`#${id}-l1`, s.cae.en + 0.25, { opacity: 0, y: 20 }, 0.2);
          tl.to(
            `#${id}-l1`,
            { opacity: 0, duration: 0.15 },
            (s.atenuar ? s.atenuar.en : s.t1) - 0.5,
          );
        }
      }
      if (s.atenuar) {
        const idx = [...Array(s.atenuar.n)].map((_, j) =>
          Math.floor(((j + 0.37) * N) / s.atenuar.n),
        );
        idx.forEach((k, j) =>
          tl.to(
            `#${id}-d${k}`,
            { background: "rgba(224,83,61,0.35)", scale: 0.75, duration: 0.15 },
            s.atenuar.en + j * 0.05,
          ),
        );
        if (s.atenuar.texto)
          inn(`#${id}-l2`, s.atenuar.en, { opacity: 0, y: 20 }, 0.2);
      }
      tl.fromTo(
        `#${id}-dots`,
        { y: 0 },
        { y: -30, duration: s.t1 - s.t0, ease: "none" },
        s.t0,
      );
    },
    anios(s, id) {
      const a = s.cuenta.en,
        b = s.fin,
        el = $(`${id}-yr`),
        yr = { v: s.desde };
      if (s.kicker) inn(`#${id}-k`, s.t0 + 0.05, { y: -20, opacity: 0 }, 0.2);
      tl.fromTo(
        yr,
        { v: s.desde },
        {
          v: s.hasta,
          duration: b - a,
          ease: "none",
          onUpdate: () => {
            el.textContent = Math.round(yr.v);
          },
        },
        a,
      );
      tl.fromTo(
        `#${id}-fill`,
        { scaleX: 0 },
        { scaleX: 1, duration: b - a, ease: "none" },
        a,
      );
      (s.hitos || []).forEach(([y], k) => {
        const t = a + ((y - s.desde) / (s.hasta - s.desde)) * (b - a);
        tl.fromTo(
          `#${id}-h${k}`,
          { opacity: 0, y: 30 },
          { opacity: 1, y: 0, duration: 0.08 },
          t - 0.05,
        );
        tl.to(`#${id}-h${k}`, { opacity: 0, y: -30, duration: 0.12 }, t + 0.32);
      });
      if (s.etiqueta)
        inn(`#${id}-l`, s.etiqueta.en, { opacity: 0, y: 20 }, 0.2);
    },
    // La gráfica viva: TODO es función pura del tiempo (seek-safe), un solo tween recorre la escena.
    grafica(s, id) {
      const NS = "http://www.w3.org/2000/svg",
        svg = $(`${id}-svg`),
        W = 850,
        H = 830,
        X0 = 60;
      const el = (tag, attrs, txt) => {
        const e = document.createElementNS(NS, tag);
        Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v));
        if (txt != null) e.textContent = txt;
        svg.appendChild(e);
        return e;
      };
      const suave = (u) => u * u * (3 - 2 * u),
        cl = (u) => Math.min(1, Math.max(0, u));
      const mezcla = (p, q, u) => p + (q - p) * u;
      const lineas = s.lineas,
        av = s.avance,
        a0 = av[0].anio,
        amax = av[av.length - 1].anio;
      const fmt =
        s.unidad === "%"
          ? (v) => `${v > 0 ? "+" : ""}${Number(v.toFixed(2))}%`
          : (v) =>
              v >= 1000 ? `$${(v / 1000).toFixed(2)}T` : `$${Math.round(v)}B`;
      const fmtR = (r) =>
        r < 0.995 ? `${Math.round(r * 100)}¢` : `$${r.toFixed(2)}`;
      const anioEn = (t) => {
        if (t <= av[0].en) return a0;
        for (let k = 1; k < av.length; k++)
          if (t <= av[k].en)
            return mezcla(
              av[k - 1].anio,
              av[k].anio,
              suave((t - av[k - 1].en) / (av[k].en - av[k - 1].en)),
            );
        return amax;
      };
      const valor = (pts, a) => {
        for (let k = 1; k < pts.length; k++)
          if (a <= pts[k][0])
            return mezcla(
              pts[k - 1][1],
              pts[k][1],
              (a - pts[k - 1][0]) / (pts[k][0] - pts[k - 1][0]),
            );
        return pts[pts.length - 1][1];
      };
      // framing: starts tight on the data drawn so far, then each keyframe blends over its duration
      const vista = (t, a) => {
        let top = 0;
        lineas.forEach((l) =>
          l.puntos.forEach((p) => {
            if (p[0] <= a) top = Math.max(top, p[1]);
          }),
        );
        let c = {
          desde: a0,
          ymin: s.ymin ?? 0,
          ymax: s.ymax ?? Math.max(480, 1.45 * top),
        };
        (s.encuadres || []).forEach((k) => {
          const u = suave(cl((t - k.en) / (k.dur || 1.2)));
          c = {
            desde: mezcla(c.desde, k.desde, u),
            ymin: mezcla(c.ymin, k.ymin, u),
            ymax: mezcla(c.ymax, k.ymax, u),
          };
        });
        return c;
      };
      const estado = (l, t) => {
        let c = { ancho: 11, op: 1 };
        (l.estados || []).forEach((k) => {
          const u = suave(cl((t - k.en) / (k.dur || 0.3)));
          c = {
            ancho: mezcla(c.ancho, k.ancho ?? c.ancho, u),
            op: mezcla(c.op, k.op ?? c.op, u),
          };
        });
        return c;
      };
      const fondoAnio = el(
        "text",
        { class: "anio", x: X0 + W, y: H - 24, "text-anchor": "end" },
        "",
      );
      const reja = (s.rejilla || []).map((v) => [
        v,
        el("line", { class: "rej", x1: X0, x2: X0 + W }),
        el("text", { class: "tk", x: X0, "text-anchor": "start" }, fmt(v)),
      ]);
      const tks = (s.ticks || []).map((a) => [
        a,
        el(
          "text",
          { class: "tk", y: H + 50, "text-anchor": "middle" },
          String(a),
        ),
      ]);
      // zooming must not let a line escape the plot into the subtitles
      const clip = el("clipPath", { id: `${id}-clip` });
      clip.appendChild(
        el("rect", { x: X0, y: -40, width: W + 30, height: H + 40 }),
      );
      const hueco = el("path", {
        fill: lineas[0].color,
        "fill-opacity": 0.2,
        stroke: "none",
        "clip-path": `url(#${id}-clip)`,
      });
      const trazos = lineas.map((l) =>
        el("path", {
          class: "ln",
          stroke: l.color,
          "clip-path": `url(#${id}-clip)`,
        }),
      );
      reja.forEach(([, , tx]) => svg.appendChild(tx));
      const cabezas = lineas.map((l) => el("circle", { r: 15, fill: l.color }));
      const vals = lineas.map((l) =>
        el("text", { class: "val", fill: l.color, "text-anchor": "start" }, ""),
      );
      const marcas = (s.marcas || []).map((m) => [
        m,
        el("circle", {
          r: 26,
          fill: "none",
          stroke: "#17211c",
          "stroke-width": 7,
        }),
        el("text", { class: "mc", "text-anchor": "end" }, m.texto),
      ]);
      const ratio = s.ratio && [
        el("text", { class: "ratio", x: X0, y: 150 }, ""),
        el("text", { class: "ratiol", x: X0, y: 196 }, s.ratio.texto),
      ];
      (s.marcas || []).forEach((m) => {
        if (m.golpe) {
          flash(m.en, 0.2);
          sacudida(m.en, 10);
        }
      });
      const pinta = (t) => {
        const a = anioEn(t),
          v = vista(t, a),
          span = amax - v.desde;
        const X = (x) => X0 + ((x - v.desde) / span) * W,
          Y = (y) => H - ((y - v.ymin) / (v.ymax - v.ymin)) * H;
        fondoAnio.textContent = String(Math.floor(a));
        const opR = ratio
          ? cl((t - s.ratio.en) / 0.2) *
            (s.ratio.hasta != null ? 1 - cl((t - s.ratio.hasta) / 0.2) : 1)
          : 0;
        reja.forEach(([y, ln, tx]) => {
          // gridlines fade out before they run into the big ratio figure
          const on =
            (y >= v.ymin && y <= v.ymax ? 1 : 0) *
            (1 - opR * (1 - cl((Y(y) - 215) / 40)));
          ln.setAttribute("y1", Y(y));
          ln.setAttribute("y2", Y(y));
          ln.setAttribute("opacity", on);
          tx.setAttribute("y", Y(y) - 10);
          tx.setAttribute("opacity", on);
        });
        tks.forEach(([x, tx]) => {
          tx.setAttribute("x", X(x));
          tx.setAttribute(
            "opacity",
            x >= v.desde && (span > 20 ? x % 10 === 0 : x % 2 === 0) ? 1 : 0,
          );
        });
        const heads = lineas.map((l, k) => {
          const vis = l.puntos.filter((p) => p[0] <= a && p[0] >= v.desde);
          const y = valor(l.puntos, a),
            hx = X(a),
            hy = Y(y),
            pts = [...vis, [a, y]],
            e = estado(l, t);
          trazos[k].setAttribute(
            "d",
            "M" +
              pts
                .map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`)
                .join(" L"),
          );
          trazos[k].setAttribute("stroke-width", e.ancho.toFixed(2));
          trazos[k].setAttribute("opacity", e.op.toFixed(3));
          cabezas[k].setAttribute("cx", hx);
          cabezas[k].setAttribute("cy", hy);
          cabezas[k].setAttribute("opacity", e.op.toFixed(3));
          return { k, v: y, hx, hy, pts };
        });
        // labels never overlap: the lower one is pushed down when the lines run close
        let yPrev = -1e9;
        [...heads]
          .sort((p, r) => p.hy - r.hy)
          .forEach((h, i) => {
            const ed = P.tema === "editorial";
            const y = ed
              ? Math.min(...heads.map((q) => q.hy)) - (i ? 34 : 84) // stacked above the top head, the lines never reach there
              : Math.max(h.hy - 34, yPrev + 50);
            yPrev = y;
            vals[h.k].setAttribute("text-anchor", ed ? "end" : "start");
            vals[h.k].setAttribute(
              "x",
              ed
                ? Math.max(h.hx + 8, X0 + 360)
                : Math.min(h.hx + 26, X0 + W - 340),
            );
            vals[h.k].setAttribute("y", y);
            // discrete series: label the last real point, never an interpolated value between two of them
            const real = s.unidad === "%"
              ? lineas[h.k].puntos.filter((q) => q[0] <= a).at(-1)?.[1] ?? h.v
              : h.v;
            vals[h.k].textContent = `${lineas[h.k].nombre} ${fmt(real)}`;
          });
        if (s.hueco_desde != null && a > s.hueco_desde) {
          const [p, r] = heads.map((h) =>
            h.pts.filter((q) => q[0] >= s.hueco_desde),
          );
          hueco.setAttribute(
            "d",
            "M" +
              [...p, ...[...r].reverse()]
                .map((q) => `${X(q[0]).toFixed(1)},${Y(q[1]).toFixed(1)}`)
                .join(" L") +
              " Z",
          );
        } else hueco.setAttribute("d", "");
        marcas.forEach(([m, c, tx]) => {
          const op =
            cl((t - m.en) / 0.2) *
            (m.hasta != null ? 1 - cl((t - m.hasta) / 0.2) : 1);
          const mx = X(m.anio),
            my = Y(valor(lineas[0].puntos, m.anio));
          c.setAttribute("cx", mx);
          c.setAttribute("cy", my);
          c.setAttribute("opacity", op);
          // editorial: below-right of the point, the only area the value labels never reach
          tx.setAttribute(
            "text-anchor",
            P.tema === "editorial" && !m.izq ? "start" : "end",
          );
          tx.setAttribute(
            "x",
            P.tema === "editorial"
              ? mx + (m.izq ? -64 : 34) // izq: a mark near the right edge would clip
              : Math.max(X0 + 350, mx - 40),
          );
          tx.setAttribute("y", P.tema === "editorial" ? my + 74 : my - 60);
          tx.setAttribute("opacity", op);
        });
        if (ratio) {
          ratio[0].textContent = fmtR(
            valor(lineas[0].puntos, a) / valor(lineas[1].puntos, a),
          );
          ratio.forEach((e) => e.setAttribute("opacity", opR));
        }
      };
      // the chart stays hidden during the hook and appears when the story reaches it
      if (s.muestra)
        tl.fromTo(
          svg,
          { opacity: 0 },
          { opacity: 1, duration: 0.25 },
          s.muestra.en,
        );
      const o = { t: s.t0 };
      tl.fromTo(
        o,
        { t: s.t0 },
        {
          t: s.t1,
          duration: s.t1 - s.t0,
          ease: "none",
          onUpdate: () => pinta(o.t),
          immediateRender: false,
        },
        s.t0,
      );
      pinta(s.t0);
    },
    cta(s, id) {
      inn(
        `#${id}-a`,
        s.a.en - 0.05,
        { x: -500, opacity: 0 },
        0.25,
        "power4.out",
      );
      inn(`#${id}-o`, s.a.en + 0.2, { scale: 0.5, opacity: 0 }, 0.2);
      inn(
        `#${id}-b`,
        s.b.en - 0.05,
        { x: 500, opacity: 0 },
        0.25,
        "power4.out",
      );
      if (s.pregunta) {
        tl.to(
          `#${id}-vs`,
          { y: -60, scale: 0.8, duration: 0.35, ease: "power3.inOut" },
          s.pregunta.en - 0.1,
        );
        tl.to(`#${id}-o`, { opacity: 0, duration: 0.2 }, s.pregunta.en - 0.1);
        inn(`#${id}-q`, s.pregunta.en, { y: 40, opacity: 0 }, 0.25);
        if (s.botones && s.botones.length)
          tl.to(
            `#${id}-q`,
            { opacity: 0, y: -30, duration: 0.2 },
            s.botones[0].en - 0.25,
          );
      }
      (s.botones || []).forEach((b, k) =>
        inn(
          `#${id}-p${k}`,
          b.en - 0.05,
          { y: 60, opacity: 0 },
          0.25,
          "back.out(2)",
        ),
      );
      // tarjeta final: la voz ya calló; movimiento REAL (medir_ritmo cazó 2,8 s quietos con solo un pulso sutil)
      const fin = P.fin_voz;
      inn(`#${id}-s`, fin, { opacity: 0, y: 20 }, 0.25);
      tl.to(
        `#${id} .pill`,
        {
          scale: 1.14,
          duration: 0.4,
          yoyo: true,
          repeat: 5,
          ease: "sine.inOut",
        },
        fin + 0.2,
      );
      tl.to(
        `#${id}-s`,
        { y: 22, duration: 0.35, yoyo: true, repeat: 5, ease: "sine.inOut" },
        fin + 0.4,
      );
      tl.fromTo(
        `#${id}-luz`,
        { x: -600, rotation: 14, opacity: 1 },
        {
          x: 1300,
          rotation: 14,
          opacity: 1,
          duration: 1.3,
          ease: "power1.inOut",
          repeat: 1,
        },
        fin + 0.05,
      );
    },
  };
  P.escenas.forEach((s, k) => {
    ESC[s.tipo](s, "s" + k);
    (s.rotulos || []).forEach((r, j) => {
      inn(
        `#s${k}-r${j}`,
        Math.max(0, r.en - 0.05),
        { y: 24, opacity: 0, scale: 0.94 },
        0.22,
      );
      if (r.hasta != null)
        tl.to(`#s${k}-r${j}`, { opacity: 0, duration: 0.12 }, r.hasta - 0.12);
    });
    // aspecto cine: the scrim lives and dies with the text, so the shot opens and can close clean
    const rs = s.rotulos || [];
    if ($(`s${k}-ts`) && rs.length) {
      tl.fromTo(
        `#s${k}-ts`,
        { opacity: 0 },
        { opacity: 1, duration: 0.2, immediateRender: false },
        Math.max(0, Math.min(...rs.map((r) => r.en)) - 0.05),
      );
      if (rs.every((r) => r.hasta != null))
        tl.to(
          `#s${k}-ts`,
          { opacity: 0, duration: 0.15 },
          Math.max(...rs.map((r) => r.hasta)) - 0.12,
        );
    }
  });
  // planos limpios: only the image and the voice
  const LIMPIOS = P.escenas.filter((s) => s.limpio);
  LIMPIOS.forEach((s) => {
    tl.set("#brand", { opacity: 0 }, s.t0);
    tl.set("#brand", { opacity: 1 }, s.t1);
  });
  const ED = P.tema === "editorial";
  if (ED) {
    // brand and disclaimer live above the scenes: dark ink on paper, light ink on photos and dimmed documents
    const papel = P.escenas.filter((s) => s.papel);
    const docs = P.pruebas || [];
    const claro = (t) =>
      papel.some((s) => t >= s.t0 && t < s.t1) &&
      !docs.some((d) => t >= d.t0 && t < d.t1);
    [
      ...new Set(
        [...papel, ...docs].flatMap((x) => [x.t0, x.t1]).sort((a, b) => a - b),
      ),
    ].forEach((t) => {
      const c = claro(t + 0.001);
      tl.set(
        "#brand",
        {
          color: c ? "#17211c" : "#f2ecdf",
          borderBottomColor: c
            ? "rgba(23,33,28,0.24)"
            : "rgba(242,236,223,0.34)",
        },
        t,
      );
      tl.set(
        "#aviso",
        {
          color: c ? "#4c5a52" : "#d9e2dc",
          backgroundColor: c
            ? "rgba(10,26,20,0)"
            : P.aspecto === "cine"
              ? "rgba(8,10,10,0.7)"
              : "rgba(10,26,20,0.86)",
        },
        t,
      );
      if (P.aspecto === "cine")
        tl.set(
          "#brand span",
          { backgroundColor: c ? "rgba(8,10,10,0)" : "rgba(8,10,10,0.62)" },
          t,
        );
    });
  }

  // ---------- subtítulos: grupos <=3 palabras; se omite el grupo que la escena YA muestra escrito ----------
  const W = P.words,
    caps = $("caps"),
    groups = [];
  let cur = [];
  const [C0, C1] = P.subtitulos;
  for (let i = C0; i <= C1; i++) {
    const x = W[i];
    cur.push(x);
    const fin = /[.,?!]$/.test(x.text),
      gap = i < C1 ? W[i + 1].start - x.end : 1;
    const lleno = ED
      ? cur.length >= 6 || cur.map((w) => w.text).join(" ").length >= 40
      : cur.length === 3;
    if (lleno || fin || gap > 0.25) {
      groups.push(cur);
      cur = [];
    }
  }
  if (cur.length) groups.push(cur);
  const nrm = (s) => s.toLowerCase().replace(/[^a-z0-9'$]/g, "");
  const TINTA = P.tema === "claro" ? "#17211c" : "#f4f6f3";
  const HOT = new Set(P.calientes.map(nrm));
  const enPantalla = (t) => {
    const s = P.escenas.find((e) => t >= e.t0 && t < e.t1);
    return s ? new Set(s.texto_visible) : new Set();
  };
  groups.forEach((g, gi) => {
    const vis = enPantalla(g[0].start);
    // duplicado: la escena ya dice la MAYORÍA del grupo (con "todas" se colaba "NOBODY CAN ACTUALLY"
    // bajo "ALMOST NOBODY CAN MAKE" — Grace, 26-sep). Grupos de 1-2 palabras: todas.
    if (g.filter((x) => vis.has(nrm(x.text))).length * 3 >= g.length * 2)
      return;
    const medio = (g[0].start + g[g.length - 1].end) / 2;
    if (LIMPIOS.some((s) => medio >= s.t0 && medio < s.t1)) return;
    const el = document.createElement("div");
    el.className = "cg";
    el.id = "cg" + gi;
    caps.appendChild(el);
    const gS = g[0].start - 0.05;
    // Nunca ocultar antes de mostrar: con palabras de duración 0 (alineación interpolada) el
    // "siguiente grupo" podía empezar antes que este, el fade-out caía ANTES del fade-in y el
    // subtítulo se quedaba pegado el resto del vídeo (Grace Groner, 23-sep).
    const entra = LIMPIOS.find((s) => s.t0 > gS); // a clean shot cuts the caption dead
    const gE = Math.max(
      gS + 0.3,
      Math.min(
        groups[gi + 1]
          ? Math.min(groups[gi + 1][0].start - 0.05, g[g.length - 1].end + 0.35)
          : g[g.length - 1].end + 0.4,
        entra ? entra.t0 : Infinity,
      ),
    );
    tl.fromTo(
      el,
      ED ? { opacity: 0 } : { opacity: 0, y: 24, scale: 0.92 },
      ED
        ? { opacity: 1, duration: 0.06, ease: "none" }
        : { opacity: 1, y: 0, scale: 1, duration: 0.1, ease: "power2.out" },
      gS,
    );
    tl.to(el, { opacity: 0, duration: 0.05 }, gE - 0.05);
    let ln = null;
    g.forEach((x, k) => {
      const s = document.createElement("span");
      s.className = "w";
      s.id = `w${gi}_${k}`;
      s.textContent = x.text.replace(/[.,?!]$/, "");
      const hot = HOT.has(nrm(x.text));
      if (ED) {
        if (!ln) {
          ln = document.createElement("span");
          ln.className = "ln";
          el.appendChild(ln);
        }
        ln.appendChild(s);
        ln.appendChild(document.createTextNode(" "));
        if (hot)
          tl.fromTo(
            s,
            { backgroundColor: "rgba(240,203,107,0)", color: "#f2ecdf" },
            {
              backgroundColor: "rgba(240,203,107,1)",
              color: "#17211c",
              duration: 0.06,
              ease: "none",
              immediateRender: false,
            },
            x.start - 0.04,
          );
        return;
      }
      el.appendChild(s);
      tl.fromTo(
        s,
        { color: TINTA, scale: 1 },
        {
          color: hot
            ? P.tema === "claro"
              ? "#bf2c17"
              : "#d8b25a"
            : P.tema === "claro"
              ? TINTA
              : "#9fe3c4",
          scale: hot ? 1.06 : 1.03,
          duration: 0.08,
          ease: "power2.out",
          immediateRender: false,
        },
        x.start - 0.04,
      );
      tl.to(s, { color: TINTA, scale: 1, duration: 0.1 }, x.end);
    });
  });

  // ---------- transiciones en los cortes (los mismos que llevan whoosh) ----------
  // Van en #trans (contenedor de #cam) para no pelear con el punch-in por `scale`. La escena que
  // sale acelera hacia el corte con desenfoque de movimiento y la que entra frena desde él.
  // fromTo + immediateRender:false: el render salta a cualquier instante (seek).
  const TR = {
    zoom: [{ scale: 1.14 }, { scale: 1.14 }],
    izq: [{ x: -150 }, { x: 150 }],
    sube: [{ y: -220 }, { y: 220 }],
  };
  const ORDEN = ["zoom", "izq", "zoom", "sube"];
  const REPOSO = { scale: 1, x: 0, y: 0 };
  // Chosen per video (edicion.py): data only, hard cut everywhere else. Reflection = mirror tile, so a
  // long push/whip never shows the empty frame. Everything goes back to none after the entrance.
  (P.transiciones || []).forEach((tr) => {
    // "initial", not "none": GSAP ignores "none" on this property (checked in the browser)
    const ref = (lado) => ({ webkitBoxReflect: lado });
    if (tr.reflejo) tl.set("#trans", ref(tr.reflejo[0]), tr.t - tr.dur_sale);
    tl.fromTo(
      "#trans",
      { ...tr.reposo },
      {
        ...tr.reposo,
        ...tr.sale,
        duration: tr.dur_sale,
        ease: tr.ease_sale,
        immediateRender: false,
      },
      tr.t - tr.dur_sale,
    );
    if (tr.reflejo) tl.set("#trans", ref(tr.reflejo[1]), tr.t);
    tl.fromTo(
      "#trans",
      { ...tr.reposo, ...tr.entra },
      {
        ...tr.reposo,
        duration: tr.dur_entra,
        ease: tr.ease_entra,
        immediateRender: false,
      },
      tr.t,
    );
    tl.set(
      "#trans",
      { filter: "none", clipPath: "none", ...ref("initial") },
      tr.t + tr.dur_entra + 0.01,
    );
  });
  if (!ED && !P.transiciones)
    P.cortes.forEach((t, i) => {
      const [sale, entra] = TR[ORDEN[i % ORDEN.length]];
      tl.fromTo(
        "#trans",
        { ...REPOSO, filter: "blur(0px)" },
        {
          ...REPOSO,
          ...sale,
          filter: "blur(12px)",
          duration: 0.12,
          ease: "power2.in",
          immediateRender: false,
        },
        t - 0.12,
      );
      tl.fromTo(
        "#trans",
        { ...REPOSO, ...entra, filter: "blur(12px)" },
        {
          ...REPOSO,
          filter: "blur(0px)",
          duration: 0.24,
          ease: "power3.out",
          immediateRender: false,
        },
        t,
      );
      tl.set("#trans", { filter: "none" }, t + 0.25);
    });

  // ---------- punch-in de cámara (zoom-cut): el recurso nº 1 de edición en Shorts ----------
  // Prioridad a los golpes; después, palabras calientes. Separación mínima 1,8 s (más seguido marea)
  // y nunca en el primer 0,8 s (el gancho ya entra con su propia animación).
  const HUECO = 1.8,
    hechos = [];
  const libre = (t) =>
    t >= 0.8 && t <= P.fin_voz && hechos.every((h) => Math.abs(h - t) >= HUECO);
  // [offset, level (1 = peak), duration, ease, rotation]; shape chosen per video (edicion.py)
  const PASOS = (P.edicion && P.edicion.punch) || [
    [-0.02, 1, 0.07, "power3.out", 0],
    [0.08, 0, 0.65, "power2.inOut", 0],
  ];
  const punch = (t, z) => {
    if (!libre(t)) return;
    // fromTo con valores explícitos: el render salta a cualquier instante (seek) y un `to` fuera de
    // orden sobre la misma propiedad cogería un valor inicial equivocado
    let nivel = 0,
      giro = 0;
    PASOS.forEach(([off, n, dur, ease, rot]) => {
      tl.fromTo(
        "#cam",
        { scale: 1 + (z - 1) * nivel, rotation: giro },
        {
          scale: 1 + (z - 1) * n,
          rotation: rot,
          duration: dur,
          ease,
          immediateRender: false,
        },
        t + off,
      );
      nivel = n;
      giro = rot;
    });
    hechos.push(t);
  };
  P.golpes.forEach((t) => punch(t, ED ? 1.04 : 1.08));
  if (!ED)
    W.filter((x) => HOT.has(nrm(x.text))).forEach((x) => punch(x.start, 1.05));

  window.__timelines["main"] = tl;
})();
