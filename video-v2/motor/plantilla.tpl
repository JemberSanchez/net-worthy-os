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
      @font-face { font-family: "NW Display"; src: url("assets/_motor/fonts/source-serif-4-latin-opsz-normal.woff2") format("woff2"); font-weight: 200 900; }
      @font-face { font-family: "NW Text"; src: url("assets/_motor/fonts/schibsted-grotesk-latin-600-normal.woff2") format("woff2"); font-weight: 600; }
      @font-face { font-family: "NW Text"; src: url("assets/_motor/fonts/schibsted-grotesk-latin-700-normal.woff2") format("woff2"); font-weight: 700; }
      @font-face { font-family: "NW Text"; src: url("assets/_motor/fonts/schibsted-grotesk-latin-800-normal.woff2") format("woff2"); font-weight: 800; }
      @font-face { font-family: "NW Data"; src: url("assets/_motor/fonts/ibm-plex-mono-latin-500-normal.woff2") format("woff2"); font-weight: 500; }
      @font-face { font-family: "NW Data"; src: url("assets/_motor/fonts/ibm-plex-mono-latin-600-normal.woff2") format("woff2"); font-weight: 600; }
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
        background: linear-gradient(180deg, rgba(10,26,20,0.55) 0%, rgba(10,26,20,0.18) 26%, rgba(10,26,20,0.2) 56%, rgba(10,26,20,0.82) 100%); }
      /* fondo NÍTIDO de escena de texto (1-oct): sombra general ligera; arriba la marca, abajo subtítulos */
      .ph .shade.fondo { background: linear-gradient(180deg, rgba(10,26,20,0.5) 0%, rgba(10,26,20,0.08) 22%, rgba(10,26,20,0.1) 60%, rgba(10,26,20,0.7) 100%); }
      /* sombra LOCAL detrás del bloque de texto: el resto del cuadro queda con la luz de la imagen */
      .scrim { position: absolute; left: -140px; right: -140px; top: 170px; height: 1080px; pointer-events: none;
               background: radial-gradient(ellipse 52% 46% at 50% 48%, rgba(4,12,9,0.72) 0%, rgba(4,12,9,0.5) 45%, rgba(4,12,9,0) 100%); }
      /* texto grande SIEMPRE legible sobre imagen o vídeo (puerta de contraste WCAG en producir.py) */
      .huge, .big, .mid, .row .tx, .yr, .money, .boton { text-shadow: 0 6px 0 rgba(0,0,0,0.35), 0 0 42px rgba(0,0,0,0.75); }
      #cam, #trans { position: absolute; inset: 0; transform-origin: 50% 45%; }
      #vignette { position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 45%, transparent 50%, rgba(0,0,0,0.5) 100%); }
      #grain { position: absolute; left: -200px; top: -200px; width: 1480px; height: 2320px; opacity: 0.13; mix-blend-mode: overlay;
               background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
      #flash { position: absolute; inset: 0; background: var(--gold); opacity: 0; mix-blend-mode: screen; }
      #brand { position: absolute; top: 118px; width: 100%; text-align: center; font-weight: 800; letter-spacing: 0.42em; font-size: 26px; color: var(--gold); text-transform: uppercase; }
      /* plate behind the brand: on a bright photo it read 2.05:1 (#9, cartel); a shadow alone gave 2.23:1 */
      #brand span { display: inline-block; padding: 8px 6px 8px 22px; border-radius: 10px; background: rgba(10,26,20,0.78); }
      /* la PRUEBA: documento real a pantalla completa + subrayador (tools/ocr_doc.py) */
      .prueba { position: absolute; inset: 0; overflow: hidden; background: var(--bg); }
      .prueba .pcam { position: absolute; inset: 0; }
      .prueba img { position: absolute; display: block; box-shadow: 0 30px 90px rgba(0,0,0,0.7); }
      /* foco: todo el documento se apaga salvo la frase (y las fotos de personas del periódico, de paso, no protagonizan) */
      .prueba .foco { position: absolute; border-radius: 8px; box-shadow: 0 0 0 4000px rgba(4,10,8,0.84); opacity: 0; }
      .prueba .marca { position: absolute; background: rgba(255, 208, 40, 0.62); mix-blend-mode: multiply; border-radius: 6px;
                       transform-origin: 0 50%; transform: scaleX(0); }
      /* sello de serie (storyboard.serie): bajo la marca, solo en el gancho */
      #serieclip { position: absolute; top: 166px; left: 0; width: 100%; display: flex; justify-content: center; }
      #serie { font-weight: 800; font-size: 25px; letter-spacing: 0.26em; text-transform: uppercase; color: var(--gold);
               padding: 9px 24px 9px 30px; border: 3px solid rgba(216,178,90,0.8); border-radius: 999px; background: rgba(10,26,20,0.78); }
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

      /* la gráfica viva: papel claro en vez del verde oscuro de marca */
      #root.claro { --bg: #f2ecdf; --bg2: #f2ecdf; --ink: #17211c; --gold: #8a5f0a; --green: #0d6b49; --mute: #4c5a52; --red-txt: #bf2c17; }
      #root.claro #ground { background: #f2ecdf url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='1080' height='1920'><filter id='p'><feTurbulence type='fractalNoise' baseFrequency='0.012' numOctaves='4' seed='7'/><feColorMatrix values='0 0 0 0 0.35 0 0 0 0 0.28 0 0 0 0 0.18 0 0 0 0.11 0'/></filter><rect width='1080' height='1920' filter='url(%23p)'/></svg>"); }
      #root.claro #glow, #root.claro .scrim { display: none; }
      #root.claro #brand { color: #f2ecdf; }
      .rot.huge { font-size: 130px; line-height: 1; }
      .rot.mega { font-family: "Anton", sans-serif; font-size: 230px; line-height: 1; top: 520px; }
      .rot.big { font-size: 88px; line-height: 1.05; }
      #root.claro #vignette { display: none; }
      #root.claro #caps { top: 1330px; }
      #root.claro #aviso { top: 1250px; }
      #root.claro #grain { mix-blend-mode: multiply; opacity: 0.1; }
      #root.claro .huge, #root.claro .big, #root.claro .mid, #root.claro .w { text-shadow: none; }
      #root.claro #aviso { color: var(--mute); }
      .rot { position: absolute; left: 50px; right: 50px; top: 210px; text-align: center; opacity: 0; }
      .graf { position: absolute; left: 30px; top: 330px; width: 1020px; height: 1020px; overflow: visible; font-family: "InterX", sans-serif; }
      .graf .ln { fill: none; stroke-width: 11; stroke-linecap: round; stroke-linejoin: round; }
      .graf .rej { stroke: #17211c; stroke-opacity: 0.14; stroke-width: 2; }
      .graf .tk { fill: #4c5a52; font-size: 30px; font-weight: 800; paint-order: stroke; stroke: #eae1d4; stroke-width: 10px; stroke-linejoin: round; }
      .graf text { paint-order: stroke; stroke: #f2ecdf; stroke-width: 10px; stroke-linejoin: round; }
      .graf .anio { font-family: "Anton", sans-serif; font-size: 260px; fill: #17211c; fill-opacity: 0.08; stroke: none; }
      .graf .ratio { font-family: "Anton", sans-serif; font-size: 170px; fill: #bf2c17; }
      .graf .ratiol { font-size: 34px; font-weight: 800; fill: #17211c; }
      .graf .val { font-size: 38px; font-weight: 900; }
      .graf .mc { font-size: 36px; font-weight: 900; fill: #17211c; }

      /* subtítulos */
      #caps { position: absolute; left: 50px; right: 50px; top: 1200px; height: 200px; }
      .cg { position: absolute; inset: 0; display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 0 40px; opacity: 0; }
      .w { font-weight: 900; font-size: 76px; text-transform: uppercase; color: var(--ink); letter-spacing: -0.01em; display: inline-block;
           text-shadow: 0 6px 0 rgba(0,0,0,0.6), 0 0 30px rgba(0,0,0,0.7); }

      /* tema editorial (docs/mejora/visual/SISTEMA.md): serif, left-aligned on a 72 px grid, no shadows or filters */
      #root.editorial { --ink: #f2ecdf; --gold: #e3bd63; --mute: #c3cfc7; --red-txt: #ff7a66; font-family: "NW Text", sans-serif; font-kerning: normal; }
      #root.editorial #ground { background: var(--bg); }
      #root.editorial .huge, #root.editorial .big, #root.editorial .mid { font-family: "NW Display", serif; font-weight: 900; text-transform: none; letter-spacing: -0.02em; text-shadow: none; }
      #root.editorial #glow, #root.editorial .scrim, #root.editorial #vignette { display: none; }
      #root.editorial #grain { opacity: 0.06; }
      #root.editorial .ph .shade { background: linear-gradient(180deg, rgba(8,9,10,0.84) 0%, rgba(8,9,10,0.76) 30%, rgba(8,9,10,0.6) 35%, rgba(8,9,10,0) 44%, rgba(8,9,10,0) 66%, rgba(8,9,10,0.62) 76%, rgba(8,9,10,0.72) 100%); }
      #root.editorial #brand { left: 72px; width: 936px; top: 150px; text-align: left; padding-bottom: 14px; border-bottom: 2px solid rgba(242,236,223,0.34);
        font: 700 34px "NW Display", serif; font-variation-settings: "opsz" 60; letter-spacing: 0; text-transform: none; color: var(--ink); }
      #root.editorial #brand span { padding: 0; border-radius: 0; background: none; }
      #root.editorial .rot { left: 72px; right: 72px; top: 226px; text-align: left; text-shadow: none; }
      #root.editorial .rot.big, #root.editorial .rot.huge, #root.editorial .rot.mid, #root.editorial .rot.mega { font-family: "NW Display", serif; font-variation-settings: "opsz" 60; text-transform: none; text-align: left; text-shadow: none; }
      #root.editorial .rot.mid { font-weight: 700; font-size: 76px; line-height: 1.08; letter-spacing: -0.01em; }
      #root.editorial .rot.big { font-weight: 800; font-size: 104px; line-height: 1.02; letter-spacing: -0.015em; }
      #root.editorial .rot.huge { font-weight: 900; font-size: 148px; line-height: 0.98; letter-spacing: -0.022em; }
      #root.editorial .rot.mega { font-weight: 900; font-size: 300px; line-height: 0.92; letter-spacing: -0.03em; font-variant-numeric: lining-nums tabular-nums; }
      #root.editorial .rot.nota { font-weight: 700; font-size: 44px; line-height: 1.2; }
      #root.editorial .scene.papel { background: #f2ecdf; box-shadow: 0 0 0 60px #f2ecdf; --ink: #17211c; --gold: #8a5f0a; --mute: #4c5a52; --red-txt: #bf2c17; color: var(--ink); }
      #root.editorial .graf { font-family: "NW Text", sans-serif; }
      /* display typeface rotated per video by edicion.py (TIPOGRAFIA); tipo-serif is the base above */
      #root.editorial.tipo-grotesca .huge, #root.editorial.tipo-grotesca .big, #root.editorial.tipo-grotesca .mid, #root.editorial.tipo-grotesca .rot.big, #root.editorial.tipo-grotesca .rot.huge, #root.editorial.tipo-grotesca .rot.mid, #root.editorial.tipo-grotesca .rot.mega, #root.editorial.tipo-grotesca #brand { font-family: "NW Text", sans-serif; font-weight: 800; letter-spacing: -0.03em; }
      #root.editorial.tipo-condensada .huge, #root.editorial.tipo-condensada .big, #root.editorial.tipo-condensada .mid, #root.editorial.tipo-condensada .rot.big, #root.editorial.tipo-condensada .rot.huge, #root.editorial.tipo-condensada .rot.mid, #root.editorial.tipo-condensada .rot.mega, #root.editorial.tipo-condensada #brand { font-family: "Anton", sans-serif; font-weight: 400; text-transform: uppercase; letter-spacing: 0; }
      #root.editorial .graf text { stroke: none; }
      #root.editorial .graf .anio { display: none; }
      #root.editorial .graf .tk { font-size: 32px; font-weight: 600; paint-order: stroke; stroke: #f2ecdf; stroke-width: 10px; }
      #root.editorial .graf .val { font-size: 40px; font-weight: 800; }
      #root.editorial .graf .mc { font-weight: 800; }
      #root.editorial .prueba .foco { border-radius: 0; }
      #root.editorial #caps { left: 72px; width: 858px; right: auto; top: 1276px; height: 150px; }
      #root.editorial .cg { display: block; text-wrap: balance; font-weight: 700; font-size: 62px; line-height: 1.26; letter-spacing: -0.008em; }
      #root.editorial .cg .ln { background: rgba(10,26,20,0.94); padding: 6px 16px; margin-left: -16px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
      #root.editorial .w { display: inline; font-weight: 700; font-size: 62px; text-transform: none; letter-spacing: inherit; color: #f2ecdf; text-shadow: none; padding: 0 6px; }
      #root.editorial #aviso { left: 72px; right: auto; width: 858px; top: 1440px; text-align: left; font-size: 28px; line-height: 1.34; color: #d9e2dc; background: rgba(10,26,20,0.86); padding: 6px 12px; margin-left: -12px; }
      /* aspecto cine (docs/mejora/auditoria.md, tells 3, 4, 9, 10), on top of editorial: the image keeps its own
         light. One soft vignette over images only, a scrim only behind text and only while the text is on. */
      #root.cine #ground { background: #0c0e0e; } /* evergreen flat fill was 51 % of the green-yellow pixels (medir_aspecto) */
      #root.cine .ph .shade, #root.cine .ph .shade.fondo { background: radial-gradient(ellipse 85% 65% at 50% 46%, rgba(0,0,0,0) 60%, rgba(0,0,0,0.2) 100%); }
      .tscrim { position: absolute; left: -140px; right: -140px; pointer-events: none; opacity: 0; }
      .tscrim.sup { top: -200px; height: 1040px; background: linear-gradient(180deg, rgba(6,8,8,0.72) 0%, rgba(6,8,8,0.66) 62%, rgba(6,8,8,0) 100%); }
      .tscrim.med { top: 300px; height: 900px; background: linear-gradient(180deg, rgba(6,8,8,0) 0%, rgba(6,8,8,0.68) 28%, rgba(6,8,8,0.68) 72%, rgba(6,8,8,0) 100%); }
      .tscrim.ter { top: 640px; height: 880px; background: linear-gradient(180deg, rgba(6,8,8,0) 0%, rgba(6,8,8,0.7) 32%, rgba(6,8,8,0.7) 76%, rgba(6,8,8,0) 100%); }
      .tscrim.baj { top: 800px; height: 1320px; background: linear-gradient(180deg, rgba(6,8,8,0) 0%, rgba(6,8,8,0.7) 24%, rgba(6,8,8,0.72) 100%); }
      #root.cine .rot { text-shadow: 0 1px 3px rgba(0,0,0,0.22); }
      #root.cine .scene.papel .rot { text-shadow: none; }
      #root.cine .rot.p-sup { top: 226px; }
      #root.cine .rot.p-med { top: 620px; }
      #root.cine .rot.p-ter { top: 960px; }
      #root.cine .rot.p-baj { top: 1120px; }
      #root.cine .rot.der { text-align: right; }
      #root.cine .rot.dato { font-family: "NW Data", monospace; font-weight: 600; font-size: 38px; line-height: 1.25; letter-spacing: 0; font-variant-numeric: tabular-nums; }
      #root.cine .graf .tk { font-family: "NW Data", monospace; font-weight: 500; font-size: 30px; }
      #root.cine #brand { width: auto; border-bottom: none; padding-bottom: 0; font-size: 30px; }
      #root.cine #brand span { padding: 4px 12px; margin-left: -12px; background: rgba(8,10,10,0.62); }
      #root.cine .cg .ln { background: rgba(8,10,10,0.8); }
      #root.cine #aviso { top: 1452px; width: auto; max-width: 858px; white-space: nowrap; font-size: 26px; font-weight: 600; line-height: 1.3; padding: 3px 10px; margin-left: -10px; background: rgba(8,10,10,0.7); }
      #avisofin { position: absolute; left: 72px; width: 858px; top: 1330px; opacity: 0; font-weight: 600; font-size: 30px; line-height: 1.34; color: #f2ecdf; padding: 10px 14px; margin-left: -14px; background: rgba(8,10,10,0.86); }
    </style>
  </head>
  <body>
    <div id="root" class="__TEMA__" data-composition-id="main" data-start="0" data-duration="__END__" data-width="1080" data-height="1920">
__AUDIO__

      <div id="groundclip" class="clip" data-start="0" data-duration="__END__" data-track-index="0"><div id="ground"><div id="glow"></div></div></div>
      <div id="trans"><div id="cam">
__FOTOS__

__ESCENAS__
      </div></div>

__PRUEBAS__
      <div id="flashclip" class="clip" data-start="0" data-duration="__END__" data-track-index="60"><div id="flash"></div></div>
      <div id="captions" class="clip" data-start="0" data-duration="__END__" data-track-index="61"><div id="caps"></div></div>
      <div id="chrome" class="clip" data-start="0" data-duration="__END__" data-track-index="62">
        <div id="brand"><span>Net Worthy</span></div>
        <div id="aviso"__AVISOESTILO__>__AVISO__</div>
__AVISOFIN__
        <div id="vignette"></div>
        <div id="grain"></div>
      </div>
__SERIE__
    </div>
    <script>window.PLAN = __PLAN__;</script>
    <script>
__MOTORJS__
    </script>
__MOTOR3D__
  </body>
</html>
