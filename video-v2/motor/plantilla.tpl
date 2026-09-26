<!doctype html>
<!-- GENERADO por video-v2/motor/construir.py desde storyboard.json + assets/words.json. NO editar a mano. -->
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/_motor/gsap.min.js"></script>
    <style>
      @font-face { font-family: "Anton"; src: url("assets/_motor/fonts/anton.woff2") format("woff2"); font-weight: 400; }
      @font-face { font-family: "InterX"; src: url("assets/_motor/fonts/inter-latin-600-normal.woff2") format("woff2"); font-weight: 600; }
      @font-face { font-family: "InterX"; src: url("assets/_motor/fonts/inter-latin-800-normal.woff2") format("woff2"); font-weight: 800; }
      @font-face { font-family: "InterX"; src: url("assets/_motor/fonts/inter-latin-900-normal.woff2") format("woff2"); font-weight: 900; }
      :root { --bg: #0a1a14; --bg2: #0e241b; --ink: #f4f6f3; --gold: #d8b25a; --green: #1f9e6e; --mute: #8da298; --red: #e0533d; --red-txt: #ff6450; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: var(--bg); }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; font-family: "InterX", sans-serif; color: var(--ink); background: var(--bg); }

      #ground { position: absolute; inset: 0; background: radial-gradient(120% 80% at 50% 38%, #123a2a 0%, var(--bg2) 45%, var(--bg) 100%); }
      #glow { position: absolute; width: 1400px; height: 1400px; left: -160px; top: 120px; border-radius: 50%;
              background: radial-gradient(circle, rgba(216,178,90,0.18) 0%, rgba(216,178,90,0) 60%); }
      .ph { position: absolute; inset: 0; overflow: hidden; }
      .ph img { position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
      .ph video { position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
      .ph .shade { position: absolute; inset: 0;
        background: linear-gradient(180deg, rgba(10,26,20,0.6) 0%, rgba(10,26,20,0.32) 28%, rgba(10,26,20,0.38) 55%, rgba(10,26,20,0.93) 100%); }
      /* texto grande SIEMPRE legible sobre imagen o vídeo (puerta de contraste WCAG en producir.py) */
      .huge, .big, .mid, .row .tx, .yr, .money, .boton { text-shadow: 0 6px 0 rgba(0,0,0,0.35), 0 0 42px rgba(0,0,0,0.75); }
      #cam, #trans { position: absolute; inset: 0; transform-origin: 50% 45%; }
      #vignette { position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 45%, transparent 42%, rgba(0,0,0,0.7) 100%); }
      #grain { position: absolute; left: -200px; top: -200px; width: 1480px; height: 2320px; opacity: 0.13; mix-blend-mode: overlay;
               background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
      #flash { position: absolute; inset: 0; background: var(--gold); opacity: 0; mix-blend-mode: screen; }
      #brand { position: absolute; top: 118px; width: 100%; text-align: center; font-weight: 800; letter-spacing: 0.42em; font-size: 26px; color: var(--gold); }
      #progress { position: absolute; top: 0; left: 0; height: 10px; width: 1080px; background: linear-gradient(90deg, var(--green), var(--gold)); transform-origin: 0 50%; }
      #aviso { position: absolute; left: 70px; right: 70px; top: 1440px; text-align: center; font-weight: 600; font-size: 23px; line-height: 1.45; color: rgba(244,246,243,0.72); opacity: 0; }

      /* área útil de escena: 250-1150 px (debajo: subtítulos y la UI de Shorts) */
      .scene { position: absolute; inset: 0; }
      .stack { position: absolute; left: 60px; right: 60px; top: 250px; height: 900px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
      .stack.abajo { justify-content: flex-end; padding-bottom: 40px; }
      .stack.arriba { justify-content: flex-start; padding-top: 60px; }
      .kicker { font-weight: 800; font-size: 38px; letter-spacing: 0.3em; color: var(--gold); text-align: center; text-transform: uppercase; }
      .plate { background: rgba(10,26,20,0.86); padding: 16px 30px; border-radius: 14px; border: 2px solid rgba(216,178,90,0.45); }
      .huge { font-family: "Anton", sans-serif; font-size: 210px; line-height: 0.95; text-transform: uppercase; text-align: center; }
      .big { font-family: "Anton", sans-serif; font-size: 150px; line-height: 0.98; text-transform: uppercase; text-align: center; }
      .mid { font-family: "Anton", sans-serif; font-size: 104px; line-height: 1.0; text-transform: uppercase; text-align: center; }
      .sub { font-weight: 800; font-size: 36px; letter-spacing: 0.18em; color: var(--mute); text-align: center; margin-top: 26px; text-transform: uppercase; }
      .gold { color: var(--gold); } .green { color: var(--green); } .red { color: var(--red-txt); } .mute { color: var(--mute); } .ink { color: var(--ink); }
      .shadow { text-shadow: 0 8px 0 rgba(0,0,0,0.45), 0 0 50px rgba(0,0,0,0.6); }
      .linea { position: relative; margin: 14px 0; }
      .strike { position: absolute; left: -20px; right: -20px; top: 50%; height: 16px; margin-top: -8px; background: var(--red); transform-origin: 0 50%; border-radius: 8px; }
      .boton { font-family: "Anton", sans-serif; font-size: 120px; padding: 10px 70px; border-radius: 999px; background: var(--red); color: var(--ink); text-transform: uppercase; }
      .boton + .strike { background: var(--gold); }

      /* lista */
      .row { width: 920px; display: flex; align-items: center; gap: 32px; margin: 20px 0; padding: 24px 38px; border-radius: 26px;
             background: rgba(10,26,20,0.78); border: 3px solid rgba(216,178,90,0.35); }
      .row .mk { width: 92px; height: 92px; flex: none; }
      .row .mk path { fill: none; stroke-width: 15; stroke-linecap: round; stroke-linejoin: round; }
      .row.x .mk path { stroke: var(--red); }
      .row.check { background: none; border: none; padding: 0; }
      .row.check .mk { border-radius: 50%; background: var(--green); padding: 18px; }
      .row.check .mk path { stroke: var(--ink); }
      .row .tx { font-family: "Anton", sans-serif; font-size: 88px; text-transform: uppercase; line-height: 1; }

      /* tarjetas */
      .cert { position: absolute; left: 150px; top: 330px; width: 780px; height: 520px; border-radius: 10px; overflow: hidden;
              box-shadow: 0 40px 90px rgba(0,0,0,0.6); border: 4px solid rgba(216,178,90,0.7); }
      .cert img { width: 100%; height: 100%; object-fit: cover; display: block; }
      .pill { font-weight: 900; font-size: 44px; letter-spacing: 0.08em; padding: 18px 34px; border-radius: 999px; text-transform: uppercase; }
      .pill.gold { background: var(--gold); color: var(--bg); }
      .pill.line { border: 4px solid var(--gold); color: var(--gold); background: rgba(10,26,20,0.8); }
      .cnt { position: absolute; top: 950px; width: 100%; text-align: center; }
      .cnt .n { font-family: "Anton", sans-serif; font-size: 120px; color: var(--ink); font-variant-numeric: tabular-nums; }
      .tag { position: absolute; font-weight: 900; font-size: 34px; letter-spacing: 0.12em; text-transform: uppercase; }

      /* contador3d */
      #three-layer { position: absolute; inset: 0; width: 1080px; height: 1920px; }
      .money { position: absolute; top: 300px; width: 100%; text-align: center; font-family: "Anton", sans-serif; font-size: 172px; color: var(--ink); font-variant-numeric: tabular-nums; }

      /* curva */
      .chart { position: absolute; left: 110px; top: 380px; width: 860px; height: 620px; overflow: visible; }
      .chart .area { fill: url(#gArea); opacity: 0; }
      .chart .curve { fill: none; stroke: var(--gold); stroke-width: 9; stroke-linecap: round; stroke-linejoin: round; }
      .chart .paid { stroke: var(--green); stroke-width: 7; }
      .chart .axis { stroke: rgba(141,162,152,0.5); stroke-width: 3; }
      .chart .grid { stroke: rgba(244,246,243,0.14); stroke-width: 2; stroke-dasharray: 8 10; }
      .chart .tickl { stroke: rgba(244,246,243,0.45); stroke-width: 3; }
      .chart .tick { fill: #cfd8d3; font-weight: 800; font-size: 30px; letter-spacing: 0.04em; }
      .chart .playhead .dot { fill: #f4e6c0; } .chart .playhead .halo { fill: rgba(216,178,90,0.35); }
      .chart .phl { fill: #f4e6c0; font-weight: 900; font-size: 40px; paint-order: stroke; stroke: rgba(10,26,20,0.85); stroke-width: 10px; }

      /* puntos */
      .dots { position: absolute; left: 126px; top: 520px; width: 828px; height: 560px; }
      .dot { position: absolute; width: 50px; height: 50px; border-radius: 50%; background: var(--gold); opacity: 0; }
      .card { position: absolute; left: 300px; top: 470px; width: 480px; height: 636px; border: 5px solid var(--red); border-radius: 8px; overflow: hidden;
              box-shadow: 0 40px 90px rgba(0,0,0,0.7); opacity: 0; }
      .card img { width: 100%; height: 100%; object-fit: cover; display: block; }

      /* años */
      .yr { font-family: "Anton", sans-serif; font-size: 250px; color: var(--ink); font-variant-numeric: tabular-nums; line-height: 1; }
      .track { position: absolute; left: 120px; right: 120px; top: 1010px; height: 8px; background: rgba(141,162,152,0.35); border-radius: 4px; }
      .track .fill { position: absolute; left: 0; top: 0; bottom: 0; width: 840px; background: var(--gold); border-radius: 4px; transform-origin: 0 50%; }
      .hito { position: absolute; top: 760px; width: 100%; text-align: center; font-weight: 900; font-size: 50px; letter-spacing: 0.1em; color: var(--red-txt); opacity: 0; text-transform: uppercase; }

      /* titulo: icono y cheque */
      .gear { width: 230px; height: 230px; margin-bottom: 30px; }
      .gear path, .gear circle { fill: none; stroke: var(--gold); stroke-width: 14; }
      .cheque { width: 780px; height: 330px; border-radius: 26px; background: linear-gradient(160deg, #f4f6f3, #d9e2dc); color: #0a1a14; position: relative;
                box-shadow: 0 40px 90px rgba(0,0,0,0.55); padding: 40px 50px; margin-top: 60px; }
      .cheque .r { display: flex; justify-content: space-between; font-weight: 800; font-size: 28px; letter-spacing: 0.12em; color: #5e6f66; }
      .cheque .amt { font-family: "Anton", sans-serif; font-size: 110px; margin-top: 30px; color: #0a1a14; }
      .scan { position: absolute; left: 0; right: 0; top: 0; height: 6px; background: var(--red); opacity: 0.55; }

      /* cta */
      .vs { position: absolute; left: 0; right: 0; top: 300px; height: 540px; display: flex; flex-direction: column; }
      .vs .half { flex: 1; display: flex; align-items: center; justify-content: center; }
      .vs .o { text-align: center; font-weight: 900; font-size: 44px; letter-spacing: 0.3em; text-transform: uppercase; color: var(--mute); }
      .luz { position: absolute; top: -200px; left: 0; width: 420px; height: 2400px; opacity: 0; mix-blend-mode: screen;
             background: linear-gradient(90deg, rgba(216,178,90,0) 0%, rgba(216,178,90,0.55) 50%, rgba(216,178,90,0) 100%); }

      /* subtítulos */
      #caps { position: absolute; left: 50px; right: 50px; top: 1200px; height: 200px; }
      .cg { position: absolute; inset: 0; display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 0 40px; opacity: 0; }
      .w { font-weight: 900; font-size: 76px; text-transform: uppercase; color: var(--ink); letter-spacing: -0.01em; display: inline-block;
           text-shadow: 0 6px 0 rgba(0,0,0,0.6), 0 0 30px rgba(0,0,0,0.7); }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="__END__" data-width="1080" data-height="1920">
__AUDIO__

      <div id="groundclip" class="clip" data-start="0" data-duration="__END__" data-track-index="0"><div id="ground"><div id="glow"></div></div></div>
      <div id="trans"><div id="cam">
__FOTOS__

__ESCENAS__
      </div></div>

      <div id="flashclip" class="clip" data-start="0" data-duration="__END__" data-track-index="60"><div id="flash"></div></div>
      <div id="captions" class="clip" data-start="0" data-duration="__END__" data-track-index="61"><div id="caps"></div></div>
      <div id="chrome" class="clip" data-start="0" data-duration="__END__" data-track-index="62">
        <div id="progress"></div>
        <div id="brand">NET WORTHY</div>
        <div id="aviso">__AVISO__</div>
        <div id="vignette"></div>
        <div id="grain"></div>
      </div>
    </div>
    <script>window.PLAN = __PLAN__;</script>
    <script>
__MOTORJS__
    </script>
__MOTOR3D__
  </body>
</html>
