<!doctype html>
<!-- GENERADO por build.py desde plantilla.tpl + assets/words.json. Edita la plantilla, no index.html. -->
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <script src="assets/gsap.min.js"></script>
    <style>
      @font-face { font-family: "Anton"; src: url("assets/fonts/anton.woff2") format("woff2"); font-weight: 400; }
      @font-face { font-family: "InterX"; src: url("assets/fonts/inter-latin-600-normal.woff2") format("woff2"); font-weight: 600; }
      @font-face { font-family: "InterX"; src: url("assets/fonts/inter-latin-800-normal.woff2") format("woff2"); font-weight: 800; }
      @font-face { font-family: "InterX"; src: url("assets/fonts/inter-latin-900-normal.woff2") format("woff2"); font-weight: 900; }
      :root { --bg: #0a1a14; --bg2: #0e241b; --ink: #f4f6f3; --gold: #d8b25a; --green: #1f9e6e; --mute: #8da298; --red: #e0533d; }
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: var(--bg); }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; font-family: "InterX", sans-serif; color: var(--ink); background: var(--bg); }
      .full { position: absolute; inset: 0; }

      /* fondo base + fotos a sangre (duotono horneado por tools/duotono.py) */
      #ground { position: absolute; inset: 0; background: radial-gradient(120% 80% at 50% 38%, #123a2a 0%, var(--bg2) 45%, var(--bg) 100%); }
      #glow { position: absolute; width: 1400px; height: 1400px; left: -160px; top: 120px; border-radius: 50%;
              background: radial-gradient(circle, rgba(216,178,90,0.18) 0%, rgba(216,178,90,0) 60%); }
      .ph { position: absolute; inset: 0; overflow: hidden; }
      .ph img { position: absolute; left: 0; top: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
      .ph .shade { position: absolute; inset: 0;
        background: linear-gradient(180deg, rgba(10,26,20,0.55) 0%, rgba(10,26,20,0.05) 30%, rgba(10,26,20,0.15) 55%, rgba(10,26,20,0.92) 100%); }

      /* capas de acabado */
      #vignette { position: absolute; inset: 0; background: radial-gradient(ellipse at 50% 45%, transparent 42%, rgba(0,0,0,0.7) 100%); }
      #grain { position: absolute; left: -200px; top: -200px; width: 1480px; height: 2320px; opacity: 0.13; mix-blend-mode: overlay;
               background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='300' height='300'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>"); }
      #flash { position: absolute; inset: 0; background: var(--gold); opacity: 0; mix-blend-mode: screen; }
      #brand { position: absolute; top: 118px; width: 100%; text-align: center; font-weight: 800; letter-spacing: 0.42em; font-size: 26px; color: var(--gold); }
      #progress { position: absolute; top: 0; left: 0; height: 10px; width: 1080px; background: linear-gradient(90deg, var(--green), var(--gold)); transform-origin: 0 50%; }
      #aviso { position: absolute; left: 70px; right: 70px; top: 1440px; text-align: center; font-weight: 600; font-size: 23px; line-height: 1.45; color: rgba(244,246,243,0.72); opacity: 0; }

      /* escenas: el área útil es 250-1150 px (debajo van subtítulos y la UI de Shorts) */
      .scene { position: absolute; inset: 0; }
      .stack { position: absolute; left: 60px; right: 60px; top: 250px; height: 900px; display: flex; flex-direction: column; align-items: center; justify-content: center; }
      .kicker { font-weight: 800; font-size: 38px; letter-spacing: 0.3em; color: var(--gold); text-align: center; }
      .plate { background: rgba(10,26,20,0.86); padding: 16px 30px; border-radius: 14px; border: 2px solid rgba(216,178,90,0.45); }
      .huge { font-family: "Anton", sans-serif; font-size: 210px; line-height: 0.95; text-transform: uppercase; text-align: center; }
      .big { font-family: "Anton", sans-serif; font-size: 150px; line-height: 0.98; text-transform: uppercase; text-align: center; }
      .mid { font-family: "Anton", sans-serif; font-size: 104px; line-height: 1.0; text-transform: uppercase; text-align: center; }
      .sub { font-weight: 800; font-size: 36px; letter-spacing: 0.18em; color: var(--mute); text-align: center; margin-top: 26px; text-transform: uppercase; }
      .gold { color: var(--gold); }
      .green { color: var(--green); }
      .red { color: var(--red); }
      .blk { display: block; }
      .shadow { text-shadow: 0 8px 0 rgba(0,0,0,0.45), 0 0 50px rgba(0,0,0,0.6); }

      /* checklist (No big salary...) */
      .row { width: 900px; display: flex; align-items: center; gap: 34px; margin: 22px 0; padding: 26px 40px; border-radius: 26px;
             background: rgba(10,26,20,0.78); border: 3px solid rgba(216,178,90,0.35); }
      .row .x { width: 96px; height: 96px; flex: none; }
      .row .x path { fill: none; stroke: var(--red); stroke-width: 16; stroke-linecap: round; }
      .row .tx { font-family: "Anton", sans-serif; font-size: 92px; text-transform: uppercase; }

      /* certificados */
      .cert { position: absolute; left: 150px; top: 330px; width: 780px; height: 520px; border-radius: 10px; overflow: hidden;
              box-shadow: 0 40px 90px rgba(0,0,0,0.6); border: 4px solid rgba(216,178,90,0.7); }
      .cert img { width: 100%; height: 100%; object-fit: cover; display: block; }
      .coin { position: absolute; left: 510px; top: 560px; width: 64px; height: 64px; border-radius: 50%;
              background: radial-gradient(circle at 35% 30%, #f3dc9a, #d8b25a 55%, #9c7a2e); color: #6b5217; font-family: "Anton", sans-serif; font-size: 40px;
              display: flex; align-items: center; justify-content: center; opacity: 0; }
      .pill { font-weight: 900; font-size: 44px; letter-spacing: 0.08em; padding: 18px 34px; border-radius: 999px; text-transform: uppercase; }
      .pill.gold { background: var(--gold); color: var(--bg); }
      .pill.line { border: 4px solid var(--gold); color: var(--gold); background: rgba(10,26,20,0.8); }
      #shares { position: absolute; top: 950px; width: 100%; text-align: center; }
      #shares .n { font-family: "Anton", sans-serif; font-size: 120px; color: var(--ink); font-variant-numeric: tabular-nums; }

      /* 3D + contador */
      #three-layer { position: absolute; inset: 0; width: 1080px; height: 1920px; }
      #money { position: absolute; top: 300px; width: 100%; text-align: center; font-family: "Anton", sans-serif; font-size: 172px; color: var(--ink);
               font-variant-numeric: tabular-nums; }
      #k3d { position: absolute; top: 250px; width: 100%; }
      #paid { position: absolute; top: 520px; width: 100%; text-align: center; }

      /* gráfico */
      .chart { position: absolute; left: 110px; top: 380px; width: 860px; height: 620px; overflow: visible; }
      .chart .area { fill: url(#gArea); opacity: 0; }
      .chart .curve { fill: none; stroke: var(--gold); stroke-width: 9; stroke-linecap: round; stroke-linejoin: round; }
      .chart .paid { stroke: var(--green); stroke-width: 7; }
      .chart .axis { stroke: rgba(141,162,152,0.5); stroke-width: 3; }
      .tag { position: absolute; font-weight: 900; font-size: 34px; letter-spacing: 0.12em; text-transform: uppercase; }

      /* 95 posiciones */
      #dots { position: absolute; left: 126px; top: 520px; width: 828px; height: 560px; }
      .dot { position: absolute; width: 50px; height: 50px; border-radius: 50%; background: var(--gold); opacity: 0; }
      #n95n { position: absolute; top: 280px; width: 100%; text-align: center; }
      #crash { position: absolute; left: 300px; top: 470px; width: 480px; height: 636px; border: 5px solid var(--red); border-radius: 8px; overflow: hidden;
               box-shadow: 0 40px 90px rgba(0,0,0,0.7); opacity: 0; }
      #crash img { width: 100%; height: 100%; object-fit: cover; display: block; }

      /* años */
      #yr { font-family: "Anton", sans-serif; font-size: 250px; color: var(--ink); font-variant-numeric: tabular-nums; line-height: 1; }
      #track { position: absolute; left: 120px; right: 120px; top: 1010px; height: 8px; background: rgba(141,162,152,0.35); border-radius: 4px; }
      #trackFill { position: absolute; left: 0; top: 0; bottom: 0; width: 840px; background: var(--gold); border-radius: 4px; transform-origin: 0 50%; }
      .crisis { position: absolute; top: 760px; width: 100%; text-align: center; font-weight: 900; font-size: 50px; letter-spacing: 0.1em; color: var(--red); opacity: 0; }

      /* varios */
      .strike { position: absolute; left: 60px; right: 60px; top: 50%; height: 16px; background: var(--red); transform-origin: 0 50%; border-radius: 8px; }
      #check { width: 780px; height: 330px; border-radius: 26px; background: linear-gradient(160deg, #f4f6f3, #d9e2dc); color: #0a1a14; position: relative;
               box-shadow: 0 40px 90px rgba(0,0,0,0.55); padding: 40px 50px; margin-top: 60px; }
      #check .r { display: flex; justify-content: space-between; font-weight: 800; font-size: 28px; letter-spacing: 0.12em; color: #5e6f66; }
      #check .amt { font-family: "Anton", sans-serif; font-size: 110px; margin-top: 30px; color: #0a1a14; }
      .gear { width: 230px; height: 230px; margin-bottom: 30px; }
      .gear path, .gear circle { fill: none; stroke: var(--gold); stroke-width: 14; }
      .bl { width: 920px; display: flex; align-items: center; gap: 30px; margin: 20px 0; }
      .bl .ck { width: 90px; height: 90px; flex: none; border-radius: 50%; background: var(--green); display: flex; align-items: center; justify-content: center; }
      .bl .ck svg { width: 56px; height: 56px; }
      .bl .ck path { fill: none; stroke: var(--ink); stroke-width: 14; stroke-linecap: round; stroke-linejoin: round; }
      .bl .tx { font-family: "Anton", sans-serif; font-size: 84px; text-transform: uppercase; }
      #vs { position: absolute; left: 0; right: 0; top: 300px; height: 540px; display: flex; flex-direction: column; }
      #vs .half { flex: 1; display: flex; align-items: center; justify-content: center; }
      #vsOr { text-align: center; font-weight: 900; font-size: 44px; letter-spacing: 0.3em; text-transform: uppercase; color: var(--mute); }

      /* subtítulos: grupos de <=3 palabras, palabra activa en dorado */
      #caps { position: absolute; left: 50px; right: 50px; top: 1200px; height: 200px; }
      .cg { position: absolute; inset: 0; display: flex; flex-wrap: wrap; align-items: center; justify-content: center; gap: 0 30px; opacity: 0; }
      .w { font-weight: 900; font-size: 76px; text-transform: uppercase; color: var(--ink); letter-spacing: -0.01em; display: inline-block;
           text-shadow: 0 6px 0 rgba(0,0,0,0.6), 0 0 30px rgba(0,0,0,0.7); }
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="__END__" data-width="1080" data-height="1920">
      <!-- audio: voz (Kokoro am_adam, misma del #7) + base + sfx -->
      <audio id="vo" src="assets/voice.mp3" data-start="0" data-track-index="20" data-volume="1"></audio>
      <audio id="music-bed" src="assets/music-bed.wav" data-start="0" data-track-index="19" data-volume="0.5"></audio>
__AUDIO_SFX__

      <div id="groundclip" class="clip" data-start="0" data-duration="__END__" data-track-index="0"><div id="ground"><div id="glow"></div></div></div>
__FOTOS__

      <!-- ============ ESCENAS ============ -->
      <section id="sc-gas" class="clip scene" __CLIP_gas__>
        <div class="stack" style="justify-content:flex-end;padding-bottom:40px"><div id="k-gas" class="kicker plate" style="font-size:46px">PUMPED GAS</div></div>
      </section>
      <section id="sc-sweep" class="clip scene" __CLIP_sweep__>
        <div class="stack"><div id="t-janitor" class="huge shadow">A janitor.</div></div>
      </section>
      <section id="sc-bratt" class="clip scene" __CLIP_bratt__>
        <div class="stack" style="justify-content:flex-end;padding-bottom:40px">
          <div id="k-bratt" class="kicker plate" style="font-size:40px">BRATTLEBORO, VERMONT</div>
          <div id="s-bratt" class="sub plate" style="color:var(--ink);margin-top:14px">his whole life · 1921–2014</div>
        </div>
      </section>
      <section id="sc-reveal" class="clip scene" __CLIP_reveal__>
        <div class="stack">
          <div id="t-rev1" class="mid" style="color:var(--mute);margin-bottom:50px">A janitor.</div>
          <div id="t-rev2" class="huge gold shadow">$8 million.</div>
        </div>
        <div id="burst"></div>
      </section>
      <section id="sc-no" class="clip scene" __CLIP_no__>
        <div class="stack">
          <div class="row" id="r1"><svg class="x" viewBox="0 0 100 100"><path pathLength="1" d="M18 18 L82 82" /><path pathLength="1" d="M82 18 L18 82" /></svg><div class="tx">No big salary</div></div>
          <div class="row" id="r2"><svg class="x" viewBox="0 0 100 100"><path pathLength="1" d="M18 18 L82 82" /><path pathLength="1" d="M82 18 L18 82" /></svg><div class="tx">No hot tips</div></div>
          <div class="row" id="r3"><svg class="x" viewBox="0 0 100 100"><path pathLength="1" d="M18 18 L82 82" /><path pathLength="1" d="M82 18 L18 82" /></svg><div class="tx">No tech stocks</div></div>
        </div>
      </section>
      <section id="sc-habits" class="clip scene" __CLIP_habits__>
        <div class="stack">
          <div id="h-3" class="big"><span class="gold">3</span> boring habits</div>
          <div id="h-60" class="huge"><span id="h60n">0</span> <span class="gold">years</span></div>
        </div>
      </section>
      <section id="sc-certs" class="clip scene" __CLIP_certs__>
        <div id="c-lbl1" class="tag" style="top:220px;left:0;right:0;text-align:center;color:var(--gold)">Companies that pay you</div>
        <div class="cert" id="cert1"><img src="assets/t/cert1.jpg" alt="" /></div>
        <div class="cert" id="cert2"><img src="assets/t/cert2.jpg" alt="" /></div>
        <div class="cert" id="cert3"><img src="assets/t/cert3.jpg" alt="" /></div>
        <div id="dcoins"></div>
        <div id="c-lbl2" class="tag" style="top:880px;left:0;right:0;text-align:center;color:var(--green)">Every dividend reinvested</div>
        <div id="shares"><div class="n"><span id="sharesN">100</span></div><div class="sub" style="margin-top:0">shares owned</div></div>
      </section>
      <section id="sc-coins3d" class="clip scene" __CLIP_coins3d__>
        <canvas id="three-layer" width="1080" height="1920"></canvas>
        <div id="k3d" class="kicker">SIXTY YEARS LATER</div>
        <div id="money">$0</div>
        <div id="paid"><span class="pill line" id="paidPill">He put in: $122,400</span></div>
      </section>
      <section id="sc-chart" class="clip scene" __CLIP_chart__>
        <div class="tag" id="ch-ill" style="top:250px;right:90px;color:var(--mute);font-size:26px">Illustrative</div>
        <svg class="chart" id="chart1" viewBox="0 0 860 620">
          <defs><linearGradient id="gArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d8b25a" stop-opacity="0.75" /><stop offset="1" stop-color="#d8b25a" stop-opacity="0.05" /></linearGradient></defs>
          <line class="axis" x1="0" y1="620" x2="860" y2="620" />
          <path class="area" id="ch-area" d="__AREA__" />
          <path class="curve" id="ch-curve" pathLength="1" d="__LINEA__" />
          <line class="paid" id="ch-paid" x1="0" y1="620" x2="860" y2="__PAGADO_Y__" />
        </svg>
        <div class="tag" id="ch-l1" style="top:1030px;left:110px;color:var(--green)">$122,400 he put in</div>
        <div class="tag" id="ch-l2" style="top:600px;left:150px;right:150px;text-align:center;color:var(--ink);font-size:52px">Dividends buying dividends</div>
        <div class="tag" id="ch-8m" style="top:320px;right:100px;color:var(--gold);font-size:48px">$8M</div>
      </section>
      <section id="sc-machine" class="clip scene" __CLIP_machine__>
        <div class="stack">
          <svg class="gear" id="gear" viewBox="0 0 100 100"><circle cx="50" cy="50" r="17" /><path d="M50 8 L50 22 M50 78 L50 92 M8 50 L22 50 M78 50 L92 50 M20 20 L30 30 M70 70 L80 80 M80 20 L70 30 M30 70 L20 80" /><circle cx="50" cy="50" r="31" /></svg>
          <div id="m1" class="big gold">The machine.</div>
          <div id="check"><div class="r"><span>PAYCHECK</span><span>WEEKLY</span></div><div class="amt">$ 32.00</div><div class="strike" id="chkStrike"></div></div>
        </div>
      </section>
      <section id="sc-nobody" class="clip scene" __CLIP_nobody__>
        <div class="stack">
          <div id="nb-k" class="kicker" style="color:var(--red)">NOW</div>
          <div id="nb-t" class="big">The part <span class="blk red">nobody says.</span></div>
        </div>
        <div id="scan" style="position:absolute;left:0;right:0;top:0;height:6px;background:var(--red);opacity:0.55"></div>
      </section>
      <section id="sc-n95" class="clip scene" __CLIP_n95__>
        <div id="n95n"><div class="huge" style="font-size:190px"><span id="n95c">0</span> <span class="gold">stocks</span></div></div>
        <div id="dots"></div>
        <div id="crash"><img src="assets/t/crash.jpg" alt="" /></div>
        <div class="tag" id="n95l1" style="top:1110px;left:0;right:0;text-align:center;color:var(--gold)">One collapse can't sink him</div>
        <div class="tag" id="n95l2" style="top:1110px;left:0;right:0;text-align:center;color:var(--red)">Some cut their dividends</div>
      </section>
      <section id="sc-sell" class="clip scene" __CLIP_sell__>
        <div class="stack">
          <div id="sl1" class="big">He never had</div>
          <div style="position:relative;margin-top:40px"><div id="sl2" class="pill" style="font-size:120px;padding:10px 70px;background:var(--red);color:var(--ink);font-family:Anton,sans-serif">SELL</div><div class="strike" id="sellStrike" style="background:var(--gold)"></div></div>
        </div>
      </section>
      <section id="sc-years" class="clip scene" __CLIP_years__>
        <div class="stack" style="justify-content:flex-start;padding-top:60px">
          <div id="y-k" class="kicker">60 YEARS · NEVER SOLD</div>
          <div id="yr">1954</div>
        </div>
        <div class="crisis" id="cr1">1962 · KENNEDY SLIDE</div>
        <div class="crisis" id="cr2">1973 · OIL SHOCK CRASH</div>
        <div class="crisis" id="cr3">1987 · BLACK MONDAY</div>
        <div class="crisis" id="cr4">2000 · DOT-COM BUST</div>
        <div class="crisis" id="cr5">2008 · FINANCIAL CRISIS</div>
        <div id="track"><div id="trackFill"></div></div>
        <div class="tag" id="y-l" style="top:1060px;left:0;right:0;text-align:center;color:var(--gold)">No emergency big enough</div>
      </section>
      <section id="sc-rare" class="clip scene" __CLIP_rare__>
        <div class="stack">
          <div id="ra1" class="big">That's the <span class="gold">rare part.</span></div>
          <div id="ra2" class="mid" style="color:var(--mute);margin-top:40px">Not the picking.</div>
        </div>
      </section>
      <section id="sc-need" class="clip scene" __CLIP_need__>
        <div class="stack">
          <div id="nd-k" class="kicker">YOU DON'T NEED</div>
          <div style="position:relative;margin-top:20px"><div id="nd-n" class="huge gold" style="font-size:170px">$8,000,000</div><div class="strike" id="ndStrike"></div></div>
        </div>
      </section>
      <section id="sc-engine" class="clip scene" __CLIP_engine__>
        <div id="en-k" class="tag" style="top:250px;left:0;right:0;text-align:center;color:var(--gold);font-size:52px">Same engine. Any size.</div>
        <svg class="chart" id="chart2" viewBox="0 0 860 620">
          <line class="axis" x1="0" y1="620" x2="860" y2="620" />
          <path class="area" id="ch2-area" d="__AREA__" style="opacity:0.6" />
          <path class="curve" id="ch2-curve" pathLength="1" d="__LINEA__" />
        </svg>
        <div class="tag" id="en-a" style="top:330px;right:100px;color:var(--gold);font-size:48px">$8M</div>
        <div class="tag" id="en-b" style="top:330px;right:100px;color:var(--gold);font-size:48px">$800K</div>
        <div class="tag" id="en-c" style="top:330px;right:100px;color:var(--gold);font-size:48px">$80K</div>
      </section>
      <section id="sc-own" class="clip scene" __CLIP_own__>
        <div class="stack">
          <div class="bl" id="b1"><div class="ck"><svg viewBox="0 0 60 60"><path pathLength="1" d="M12 31 L25 44 L48 17" /></svg></div><div class="tx">Own what pays you</div></div>
          <div class="bl" id="b2"><div class="ck"><svg viewBox="0 0 60 60"><path pathLength="1" d="M12 31 L25 44 L48 17" /></svg></div><div class="tx">Reinvest it</div></div>
          <div class="bl" id="b3"><div class="ck" style="background:var(--gold)"><svg viewBox="0 0 60 60"><path pathLength="1" d="M12 31 L25 44 L48 17" /></svg></div><div class="tx gold">Don't interrupt it</div></div>
        </div>
      </section>
      <section id="sc-cta" class="clip scene" __CLIP_cta__>
        <div id="vs">
          <div class="half" id="vsL"><div class="huge" style="font-size:170px">Skill</div></div>
          <div id="vsOr">or just</div>
          <div class="half" id="vsR"><div class="huge gold" style="font-size:170px">Time</div></div>
        </div>
        <div id="cta-q" class="tag" style="top:860px;left:60px;right:60px;text-align:center;color:var(--ink);font-size:58px">On a gas station paycheck?</div>
        <div id="cta-p" style="position:absolute;top:1040px;left:0;right:0;display:flex;justify-content:center;gap:30px">
          <div class="pill line" id="pl1">Team skill</div><div class="pill gold" id="pl2">Team time</div>
        </div>
        <div id="lightbar" style="position:absolute;top:-200px;left:0;width:420px;height:2400px;opacity:0;mix-blend-mode:screen;background:linear-gradient(90deg, rgba(216,178,90,0) 0%, rgba(216,178,90,0.55) 50%, rgba(216,178,90,0) 100%)"></div>
        <div id="cta-s" class="sub" style="position:absolute;top:1170px;left:0;right:0;color:var(--ink)">drop your verdict ↓</div>
      </section>

      <!-- ============ ACABADO ============ -->
      <div id="flashclip" class="clip" data-start="0" data-duration="__END__" data-track-index="60"><div id="flash"></div></div>
      <div id="captions" class="clip" data-start="0" data-duration="__END__" data-track-index="61"><div id="caps"></div></div>
      <div id="chrome" class="clip" data-start="0" data-duration="__END__" data-track-index="62">
        <div id="progress"></div>
        <div id="brand">NET WORTHY</div>
        <div id="aviso">Illustrative · ~$170/mo reinvested at ~10%/yr nominal · before inflation<span class="blk">Blue chips can cut dividends or fail · Not financial advice</span></div>
        <div id="vignette"></div>
        <div id="grain"></div>
      </div>
    </div>

    <script>
      const WORDS = __WORDS__;
      const S = __S__;
      const D = __END__;
      const w = (i) => WORDS[i].start;
      const we = (i) => WORDS[i].end;
      const tl = gsap.timeline({ paused: true });
      let seed = 1337; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
      const $ = (id) => document.getElementById(id);
      const inn = (sel, at, from, dur = 0.3, ease = "power3.out") => tl.fromTo(sel, from, { x: 0, y: 0, scale: 1, opacity: 1, rotation: 0, filter: "blur(0px)", duration: dur, ease }, at);
      const out = (sel, at, dur = 0.2) => tl.to(sel, { y: -160, opacity: 0, filter: "blur(12px)", duration: dur, ease: "power3.in" }, at);
      const drawP = (sel, at, dur) => document.querySelectorAll(sel).forEach((p, i) => tl.fromTo(p, { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: dur, ease: "power2.out" }, at + i * 0.08));
      const flash = (at, a = 0.2) => { tl.fromTo("#flash", { opacity: 0 }, { opacity: a, duration: 0.05, ease: "none", immediateRender: false }, at); tl.to("#flash", { opacity: 0, duration: 0.35, ease: "power2.out" }, at + 0.05); };

      // ---------- persistente ----------
      tl.fromTo("#glow", { x: -120, y: 0 }, { x: 260, y: 260, duration: D, ease: "sine.inOut" }, 0);
      tl.fromTo("#progress", { scaleX: 0 }, { scaleX: 1, duration: D, ease: "none" }, 0);
      tl.fromTo("#grain", { x: 0, y: 0 }, { x: -180, y: -140, duration: D, ease: "steps(600)" }, 0);
      // aviso YMYL: mientras hay cifras ilustrativas en pantalla, y en la tarjeta final
      tl.fromTo("#aviso", { opacity: 0 }, { opacity: 1, duration: 0.3 }, S.coins3d[0] + 0.4);
      tl.to("#aviso", { opacity: 0, duration: 0.2 }, S.chart[1] - 0.2);
      tl.to("#aviso", { opacity: 1, duration: 0.3 }, we(161) + 0.1);

      // ---------- fotos: Ken Burns (cada una con su dirección, para que el cuadro nunca quede quieto) ----------
      const kb = [
        ["#ph-gas-img", { scale: 1.18, x: 60, y: 0 }, { scale: 1.32, x: -60, y: -20 }],
        ["#ph-sweep-img", { scale: 1.08, x: 0, y: 40 }, { scale: 1.24, x: 0, y: -30 }],
        ["#ph-bratt-img", { scale: 1.2, x: -30, y: -60 }, { scale: 1.06, x: 20, y: 40 }],
        ["#ph-no-img", { scale: 1.3, x: 80, y: 0 }, { scale: 1.42, x: -80, y: 0 }],
        ["#ph-n95-img", { scale: 1.1, x: 0, y: -40 }, { scale: 1.28, x: 0, y: 40 }],
        ["#ph-years-img", { scale: 1.35, x: -100, y: 0 }, { scale: 1.2, x: 100, y: 0 }],
        ["#ph-rare-img", { scale: 1.15, x: 0, y: 0 }, { scale: 1.3, x: -40, y: -40 }],
        ["#ph-cta-img", { scale: 1.12, x: -80, y: 60 }, { scale: 1.5, x: 80, y: -160 }],
      ];
      kb.forEach(([sel, a, b]) => {
        const host = document.querySelector(sel).parentElement;
        const t0 = +host.dataset.start, d = +host.dataset.duration;
        tl.fromTo(sel, a, { ...b, duration: d, ease: "none" }, t0);
      });
      tl.set("#ph-no .shade, #ph-n95 .shade, #ph-years .shade, #ph-rare .shade", { opacity: 1 }, 0);
      tl.fromTo("#ph-no-img, #ph-n95-img, #ph-years-img, #ph-rare-img", { opacity: 0.4 }, { opacity: 0.4, duration: 0.01 }, 0);
      tl.fromTo("#ph-cta-img", { opacity: 0 }, { opacity: 0.55, duration: 0.5, ease: "power2.out" }, S.cta[0] + 0.01);

      // ---------- GANCHO ----------
      inn("#k-gas", w(1), { y: 30, opacity: 0 }, 0.25);
      inn("#t-janitor", w(4) + 0.05, { scale: 1.8, opacity: 0, filter: "blur(18px)" }, 0.3, "power4.out");
      inn("#k-bratt", w(6), { y: 30, opacity: 0 }, 0.25);
      inn("#s-bratt", w(7) + 0.1, { y: 20, opacity: 0 }, 0.25);
      inn("#t-rev1", S.reveal[0] + 0.02, { y: 40, opacity: 0 }, 0.25);
      inn("#t-rev2", w(12) - 0.02, { scale: 2.2, opacity: 0, filter: "blur(20px)" }, 0.28, "power4.out");
      tl.to("#t-rev2", { scale: 1.08, duration: 0.12, ease: "power4.out" }, w(14));
      tl.to("#t-rev2", { scale: 1.0, duration: 0.4, ease: "power2.out" }, w(14) + 0.12);
      tl.to("#t-rev1", { opacity: 0.35, duration: 0.3 }, w(14));
      flash(w(14), 0.25);
      const burst = $("burst");
      for (let i = 0; i < 24; i++) {
        const c = document.createElement("div"); c.className = "coin"; c.id = "bc" + i; c.textContent = "$"; burst.appendChild(c);
        const a = rnd() * Math.PI * 2, d = 380 + rnd() * 480;
        tl.fromTo(c, { x: 0, y: 0, opacity: 1, scale: 0.4, rotation: 0 },
          { x: Math.cos(a) * d, y: Math.sin(a) * d * 0.9 + 160, scale: 0.8 + rnd(), rotation: (rnd() - 0.5) * 720, opacity: 0, duration: 0.9 + rnd() * 0.4, ease: "power3.out" }, w(14) + rnd() * 0.05);
      }

      // ---------- NO / NO / NO ----------
      [[1, 15], [2, 18], [3, 21]].forEach(([k, i]) => {
        inn("#r" + k, w(i) - 0.06, { x: k % 2 ? -700 : 700, opacity: 0 }, 0.26, "power4.out");
        drawP("#r" + k + " .x path", w(i + 1), 0.16);
      });
      tl.to("#r1, #r2", { opacity: 0.55, duration: 0.2 }, w(21));

      // ---------- 3 hábitos / 60 años ----------
      inn("#h-3", w(25) - 0.05, { y: 120, opacity: 0 }, 0.3, "power4.out");
      inn("#h-60", w(29) - 0.08, { scale: 0.6, opacity: 0 }, 0.3, "back.out(2)");
      const y60 = { v: 0 };
      tl.fromTo(y60, { v: 0 }, { v: 60, duration: 0.7, ease: "power2.out", onUpdate: () => { $("h60n").textContent = Math.round(y60.v); } }, w(29));
      tl.to("#h-3", { opacity: 0.5, duration: 0.2 }, w(29));

      // ---------- certificados + dividendos que compran acciones ----------
      [["#cert1", 32, -9, -40], ["#cert2", 33, 6, 30], ["#cert3", 34, -3, 0]].forEach(([s, i, rot, dx]) => {
        tl.fromTo(s, { y: 1300, rotation: rot * 3, x: dx, opacity: 1 }, { y: (i - 33) * 26, rotation: rot, x: dx, duration: 0.45, ease: "power3.out" }, w(i) - 0.1);
      });
      tl.fromTo("#cert1 img, #cert2 img, #cert3 img", { scale: 1.12 }, { scale: 1.0, duration: S.certs[1] - S.certs[0], ease: "none" }, S.certs[0]);
      inn("#c-lbl1", w(35) - 0.05, { y: -30, opacity: 0 }, 0.25);
      inn("#c-lbl2", w(41), { y: 30, opacity: 0 }, 0.25);
      inn("#shares", w(41), { y: 40, opacity: 0 }, 0.25);
      const dc = $("dcoins"), sh = { v: 100 };
      const nCoins = 12, c0 = w(41) + 0.1, c1 = w(46) + 0.1;
      for (let i = 0; i < nCoins; i++) {
        const c = document.createElement("div"); c.className = "coin"; c.id = "dc" + i; c.textContent = "$"; dc.appendChild(c);
        const t = c0 + (c1 - c0) * i / nCoins;
        const sx = (rnd() - 0.5) * 520, sy = (rnd() - 0.5) * 300;
        tl.fromTo(c, { x: sx, y: sy, opacity: 0, scale: 0.5 }, { x: 0, y: 420, opacity: 1, scale: 1, duration: 0.42, ease: "power2.in" }, t);
        tl.to(c, { opacity: 0, scale: 0.3, duration: 0.08 }, t + 0.42);
      }
      tl.fromTo(sh, { v: 100 }, { v: 152, duration: c1 - c0 + 0.45, ease: "power1.in", onUpdate: () => { $("sharesN").textContent = Math.round(sh.v); } }, c0 + 0.4);
      tl.to("#shares .n", { scale: 1.2, duration: 0.1, yoyo: true, repeat: 1 }, w(45));
      tl.to("#cert1, #cert2, #cert3", { y: -1400, rotation: 8, duration: 0.3, ease: "power3.in" }, S.certs[1] - 0.3);

      // ---------- 3D: 60 años -> $8M (el contador HTML y las monedas 3D comparten la curva) ----------
      const P1 = [S.coins3d[0] + 0.05, w(49) - S.coins3d[0] - 0.05, 450000], P2 = [w(49), w(50) - w(49), 8000000];
      window.__P = { P1, P2, t0: S.coins3d[0], t1: S.coins3d[1] };
      const money = { v: 0 };
      const paint = () => { $("money").textContent = "$" + Math.round(money.v).toLocaleString("en-US"); };
      inn("#k3d", w(47) - 0.05, { y: -30, opacity: 0 }, 0.25);
      tl.fromTo(money, { v: 0 }, { v: P1[2], duration: P1[1], ease: "power1.in", onUpdate: paint }, P1[0]);
      tl.to(money, { v: P2[2], duration: P2[1], ease: "power3.in", onUpdate: paint }, P2[0]);
      tl.to("#money", { color: "#d8b25a", scale: 1.12, duration: 0.12, ease: "power4.out" }, w(50));
      tl.to("#money", { scale: 1.0, duration: 0.3, ease: "power2.out" }, w(50) + 0.12);
      flash(w(50), 0.22);
      inn("#paid", w(53) - 0.05, { y: 60, opacity: 0 }, 0.3, "back.out(1.8)");

      // ---------- gráfico: todo lo que pasa de lo que él puso ----------
      tl.fromTo("#ch-curve", { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: w(65) - w(61), ease: "power1.in" }, w(61));
      inn("#ch-l1", w(62), { x: -40, opacity: 0 }, 0.25);
      tl.fromTo("#ch-paid", { opacity: 0 }, { opacity: 1, duration: 0.25 }, w(62));
      tl.fromTo("#ch-area", { opacity: 0 }, { opacity: 1, duration: 0.5 }, w(66));
      inn("#ch-l2", w(66), { scale: 0.7, opacity: 0 }, 0.3, "back.out(2)");
      inn("#ch-8m", w(65), { y: 20, opacity: 0 }, 0.2);
      inn("#ch-ill", S.chart[0] + 0.1, { opacity: 0 }, 0.3);
      tl.fromTo("#chart1", { scale: 0.94, y: 30 }, { scale: 1.04, y: -20, duration: S.chart[1] - S.chart[0], ease: "none" }, S.chart[0]);

      // ---------- la máquina, no la nómina ----------
      inn("#gear", w(71) - 0.05, { scale: 0.3, opacity: 0, rotation: -90 }, 0.3, "back.out(2)");
      tl.fromTo("#gear", { rotation: 0 }, { rotation: 240, duration: S.machine[1] - w(71), ease: "none", immediateRender: false }, w(71) + 0.3);
      inn("#m1", w(71), { y: 60, opacity: 0 }, 0.25, "power4.out");
      inn("#check", w(72) - 0.05, { y: 400, rotation: 8, opacity: 0 }, 0.3);
      tl.fromTo("#chkStrike", { scaleX: 0 }, { scaleX: 1, duration: 0.18, ease: "power3.out" }, w(74));

      // ---------- lo que nadie dice ----------
      inn("#nb-k", w(75) - 0.05, { opacity: 0, y: -20 }, 0.2);
      inn("#nb-t", w(76), { opacity: 0, scale: 0.85 }, 0.35);
      tl.to("#nb-t", { scale: 1.1, duration: S.nobody[1] - w(79), ease: "none" }, w(79));
      tl.fromTo("#scan", { y: 0 }, { y: 1900, duration: 1.2, ease: "none", repeat: 1 }, S.nobody[0]);

      // ---------- 95 posiciones, una se hunde, algunas recortan ----------
      const dots = $("dots"), n95 = { v: 0 }, COLS = 12;
      for (let i = 0; i < 95; i++) {
        const d = document.createElement("div"); d.className = "dot"; d.id = "d" + i; dots.appendChild(d);
        d.style.left = (i % COLS) * 70 + "px"; d.style.top = Math.floor(i / COLS) * 70 + "px";
        tl.fromTo(d, { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.18, ease: "back.out(3)" }, w(82) + i * 0.007);
      }
      tl.fromTo(n95, { v: 0 }, { v: 95, duration: 0.66, ease: "power1.out", onUpdate: () => { $("n95c").textContent = Math.round(n95.v); } }, w(82));
      inn("#n95n", w(80) - 0.1, { y: -40, opacity: 0 }, 0.25);
      // "one collapse": una cae (roja) y entra el titular del crash de 1929 como ilustración de "colapso"
      tl.to("#d44", { background: "#e0533d", duration: 0.1 }, w(85));
      tl.to("#d44", { y: 700, rotation: 200, opacity: 0, duration: 0.7, ease: "power2.in" }, w(86));
      tl.fromTo("#crash", { opacity: 0, rotation: -14, scale: 1.3, y: 60 }, { opacity: 1, rotation: -5, scale: 1, y: 0, duration: 0.25, ease: "power3.out" }, w(86));
      tl.to("#crash", { opacity: 0, y: 500, rotation: 6, duration: 0.3, ease: "power3.in" }, w(88) + 0.05);
      inn("#n95l1", w(87), { opacity: 0, y: 20 }, 0.2);
      tl.to("#n95l1", { opacity: 0, duration: 0.15 }, w(91) - 0.1);
      [3, 17, 29, 52, 66, 81, 90].forEach((k, j) => tl.to("#d" + k, { background: "rgba(224,83,61,0.35)", scale: 0.75, duration: 0.15 }, w(93) + j * 0.05));
      inn("#n95l2", w(93), { opacity: 0, y: 20 }, 0.2);
      tl.fromTo("#dots", { y: 0 }, { y: -30, duration: S.n95[1] - S.n95[0], ease: "none" }, S.n95[0]);

      // ---------- nunca vendió ----------
      inn("#sl1", w(96) - 0.05, { y: 80, opacity: 0 }, 0.25, "power4.out");
      inn("#sl2", w(99), { scale: 1.6, opacity: 0 }, 0.2, "power4.out");
      tl.fromTo("#sellStrike", { scaleX: 0 }, { scaleX: 1, duration: 0.14, ease: "power3.out" }, w(101));
      tl.fromTo("#sl2", { rotation: 0 }, { rotation: -6, duration: 0.14, ease: "power3.out", immediateRender: false }, w(101));

      // ---------- 60 años sin emergencia que le hiciera vender ----------
      const Y0 = 1954, Y1 = 2014, ty0 = w(102), ty1 = we(110);
      const yr = { v: Y0 };
      inn("#y-k", S.years[0] + 0.05, { y: -20, opacity: 0 }, 0.2);
      tl.fromTo(yr, { v: Y0 }, { v: Y1, duration: ty1 - ty0, ease: "none", onUpdate: () => { $("yr").textContent = Math.round(yr.v); } }, ty0);
      tl.fromTo("#trackFill", { scaleX: 0 }, { scaleX: 1, duration: ty1 - ty0, ease: "none" }, ty0);
      [[1, 1962], [2, 1973], [3, 1987], [4, 2000], [5, 2008]].forEach(([k, y]) => {
        const t = ty0 + (y - Y0) / (Y1 - Y0) * (ty1 - ty0);
        tl.fromTo("#cr" + k, { opacity: 0, y: 30 }, { opacity: 1, y: 0, duration: 0.08 }, t - 0.05);
        tl.to("#cr" + k, { opacity: 0, y: -30, duration: 0.12 }, t + 0.32);
      });
      inn("#y-l", w(104), { opacity: 0, y: 20 }, 0.2);

      // ---------- lo raro / no hace falta el $8M / mismo motor ----------
      inn("#ra1", w(111) - 0.05, { y: 80, opacity: 0 }, 0.25, "power4.out");
      inn("#ra2", w(116) - 0.05, { y: 60, opacity: 0 }, 0.25);
      tl.to("#ra1", { scale: 1.06, duration: S.rare[1] - w(111), ease: "none" }, w(111) + 0.3);
      inn("#nd-k", w(119) - 0.05, { y: -20, opacity: 0 }, 0.2);
      inn("#nd-n", w(121), { scale: 1.3, opacity: 0 }, 0.25, "power4.out");
      tl.fromTo("#ndStrike", { scaleX: 0 }, { scaleX: 1, duration: 0.2, ease: "power3.out" }, w(123));
      tl.to("#nd-n", { opacity: 0.45, scale: 0.92, duration: 0.3 }, w(124));
      inn("#en-k", w(126) - 0.05, { y: -20, opacity: 0 }, 0.25);
      tl.fromTo("#ch2-curve", { strokeDasharray: 1, strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 0.7, ease: "power1.in" }, S.engine[0] + 0.05);
      tl.fromTo("#chart2", { scale: 1.0, y: 0 }, { scale: 0.62, y: 160, duration: w(131) - w(126), ease: "power2.inOut" }, w(126));
      inn("#en-a", S.engine[0] + 0.3, { opacity: 0 }, 0.15);
      tl.to("#en-a", { opacity: 0, duration: 0.1 }, w(129));
      tl.fromTo("#en-b", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.12 }, w(129));
      tl.to("#en-b", { opacity: 0, duration: 0.1 }, w(131));
      tl.fromTo("#en-c", { opacity: 0, y: 20 }, { opacity: 1, y: 0, duration: 0.12 }, w(131));

      // ---------- la receta ----------
      [[1, 133], [2, 138], [3, 140]].forEach(([k, i]) => {
        inn("#b" + k, w(i) - 0.08, { x: -500, opacity: 0 }, 0.26, "power4.out");
        drawP("#b" + k + " .ck path", w(i) + 0.1, 0.2);
      });
      tl.to("#b3", { scale: 1.08, duration: 0.15, yoyo: true, repeat: 1 }, w(141));

      // ---------- CTA: una sola dicotomía (skill vs time), igual que el #7 ----------
      inn("#vsL", w(144) - 0.05, { x: -500, opacity: 0 }, 0.25, "power4.out");
      inn("#vsOr", w(145), { scale: 0.5, opacity: 0 }, 0.2);
      inn("#vsR", w(147) - 0.05, { x: 500, opacity: 0 }, 0.25, "power4.out");
      tl.to("#vs", { y: -60, scale: 0.8, duration: 0.35, ease: "power3.inOut" }, w(148) - 0.1);
      tl.to("#vsOr", { opacity: 0, duration: 0.2 }, w(148) - 0.1);
      inn("#cta-q", w(148), { y: 40, opacity: 0 }, 0.25);
      tl.to("#cta-q", { opacity: 0, y: -30, duration: 0.2 }, w(157) - 0.25);
      inn("#pl1", w(157) - 0.05, { y: 60, opacity: 0 }, 0.25, "back.out(2)");
      inn("#pl2", w(160) - 0.05, { y: 60, opacity: 0 }, 0.25, "back.out(2)");
      inn("#cta-s", we(161), { opacity: 0, y: 20 }, 0.25);
      // Tarjeta final: la voz ya calló y aquí se pide el comentario. medir_ritmo midió 2,8 s de
      // cuadro "muerto" con solo un pulso sutil -> barrido de luz (x2) + pulso marcado.
      tl.to("#pl1, #pl2", { scale: 1.14, duration: 0.4, yoyo: true, repeat: 5, ease: "sine.inOut" }, we(161) + 0.2);
      tl.to("#cta-s", { y: 22, duration: 0.35, yoyo: true, repeat: 5, ease: "sine.inOut" }, we(161) + 0.4);
      tl.fromTo("#lightbar", { x: -600, rotation: 14, opacity: 1 }, { x: 1300, rotation: 14, opacity: 1, duration: 1.3, ease: "power1.inOut", repeat: 1 }, we(161) + 0.05);

      // ---------- salidas de escena (el runtime oculta el clip; esto es solo el gesto) ----------
      out("#sc-reveal .stack", S.reveal[1] - 0.2);
      out("#sc-no .stack", S.no[1] - 0.2);
      out("#sc-habits .stack", S.habits[1] - 0.2);
      out("#sc-chart .chart", S.chart[1] - 0.2);
      out("#sc-machine .stack", S.machine[1] - 0.2);
      out("#sc-nobody .stack", S.nobody[1] - 0.2);
      out("#sc-sell .stack", S.sell[1] - 0.2);
      out("#sc-rare .stack", S.rare[1] - 0.2);
      out("#sc-need .stack", S.need[1] - 0.2);
      out("#sc-own .stack", S.own[1] - 0.2);

      // ---------- subtítulos: thesis..lesson (igual que el #7: sin intro ni CTA, que llevan su texto) ----------
      const HOT = new Set(["salary.", "tips.", "stocks.", "sixty", "years.", "reinvested", "dividend", "Sixty", "eight", "million", "dollars.", "little", "dividends", "machine,", "ninety-five", "collapse", "sell.", "emergency", "rare", "reinvest,", "interrupt", "million."]);
      const caps = $("caps"), groups = []; let cur = [];
      const C0 = 15, C1 = 142;
      for (let i = C0; i <= C1; i++) {
        const x = WORDS[i]; cur.push(x);
        const fin = /[.,?]$/.test(x.text), gap = i < C1 ? WORDS[i + 1].start - x.end : 1;
        if (cur.length === 3 || fin || gap > 0.25) { groups.push(cur); cur = []; }
      }
      if (cur.length) groups.push(cur);
      groups.forEach((g, gi) => {
        const el = document.createElement("div"); el.className = "cg"; el.id = "cg" + gi; caps.appendChild(el);
        const gS = g[0].start - 0.05, gE = groups[gi + 1] ? Math.min(groups[gi + 1][0].start - 0.05, g[g.length - 1].end + 0.35) : g[g.length - 1].end + 0.4;
        tl.fromTo(el, { opacity: 0, y: 24, scale: 0.92 }, { opacity: 1, y: 0, scale: 1, duration: 0.1, ease: "power2.out" }, gS);
        tl.to(el, { opacity: 0, duration: 0.05 }, gE - 0.05);
        g.forEach((x, k) => {
          const s = document.createElement("span"); s.className = "w"; s.id = `w${gi}_${k}`; s.textContent = x.text.replace(/[.,?]$/, ""); el.appendChild(s);
          const hot = HOT.has(x.text);
          tl.fromTo(s, { color: "#f4f6f3", scale: 1 }, { color: hot ? "#d8b25a" : "#9fe3c4", scale: hot ? 1.1 : 1.04, duration: 0.08, ease: "power2.out", immediateRender: false }, x.start - 0.04);
          tl.to(s, { color: "#f4f6f3", scale: 1, duration: 0.1 }, x.end);
        });
      });

      window.__timelines["main"] = tl;
    </script>

    <script type="module">
      import * as THREE from "./assets/three/three.module.min.js";
      import { RoomEnvironment } from "./assets/three/RoomEnvironment.js";

      // Misma curva que el contador HTML (GSAP power1.in = u^2, power3.in = u^4) -> invertida: cada
      // moneda aparece en el instante exacto en que la cifra pasa por su valor. No pueden desincronizarse.
      const { P1, P2, t0: T0, t1: T1 } = window.__P;
      const timeForValue = (v) => v <= P1[2]
        ? P1[0] + P1[1] * Math.sqrt(v / P1[2])
        : P2[0] + P2[1] * Math.pow((v - P1[2]) / (P2[2] - P1[2]), 0.25);
      const TLAND = P2[0] + P2[1];

      const canvas = document.getElementById("three-layer");
      const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, preserveDrawingBuffer: true });
      renderer.setSize(1080, 1920, false); renderer.setPixelRatio(1);
      renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.15;
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      const scene = new THREE.Scene();
      const pmrem = new THREE.PMREMGenerator(renderer);
      scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
      const camera = new THREE.PerspectiveCamera(30, 1080 / 1920, 0.1, 200);
      const key = new THREE.DirectionalLight(0xfff1d0, 2.4); key.position.set(4, 9, 6); scene.add(key);
      const rim = new THREE.DirectionalLight(0x1f9e6e, 1.6); rim.position.set(-6, 3, -5); scene.add(rim);
      const burst = new THREE.PointLight(0xffd27a, 0, 30); burst.position.set(3.8, 5, 2.5); scene.add(burst);
      const grid = new THREE.GridHelper(24, 24, 0x1f9e6e, 0x1f9e6e);
      grid.material.transparent = true; grid.material.opacity = 0.22; scene.add(grid);

      // 6 columnas = 6 décadas; pesos exponenciales (suma = $8M). La primera capa de cada columna es "lo que puso él".
      const COLS = 6, SP = 1.25, CH = 0.14, wts = [...Array(COLS)].map((_, i) => Math.exp(0.75 * i));
      const WS = wts.reduce((a, b) => a + b, 0);
      const counts = wts.map((x) => Math.round(30 * x / wts[COLS - 1]) + 1);
      const coins = []; let cum = 0;
      for (let c = 0; c < COLS; c++) {
        const colValue = 8000000 * wts[c] / WS, unit = colValue / counts[c];
        for (let j = 0; j < counts[c]; j++) coins.push({ c, j, t: Math.min(timeForValue(Math.min(cum + unit * (j + 0.5), 7999999)), TLAND - 0.01) });
        cum += colValue;
      }
      const geo = new THREE.CylinderGeometry(0.52, 0.52, CH * 0.86, 48);
      const mat = [new THREE.MeshStandardMaterial({ color: 0xa8812f, metalness: 0.95, roughness: 0.42 }), new THREE.MeshStandardMaterial({ color: 0xe6c46e, metalness: 0.85, roughness: 0.18 }), new THREE.MeshStandardMaterial({ color: 0xe6c46e, metalness: 0.85, roughness: 0.18 })];
      const mesh = new THREE.InstancedMesh(geo, mat, coins.length); scene.add(mesh);
      const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), pos = new THREE.Vector3(), sc = new THREE.Vector3(1, 1, 1), up = new THREE.Vector3(0, 1, 0);
      let seed = 99; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
      coins.forEach((k) => { k.dx = (rnd() - 0.5) * 0.06; k.dz = (rnd() - 0.5) * 0.06; k.rot = rnd() * 6.28; });
      const clamp = (x) => Math.max(0, Math.min(1, x));

      function renderAt(time) {
        const FALL = 0.24;
        coins.forEach((k, i) => {
          const u = clamp((time - k.t) / FALL), vis = time >= k.t;
          const drop = (1 - u * u) * 3.2;
          const settle = u >= 1 ? Math.max(0, 0.05 * Math.sin((time - k.t - FALL) * 30) * Math.exp(-(time - k.t - FALL) * 12)) : 0;
          pos.set((k.c - (COLS - 1) / 2) * SP + k.dx, CH / 2 + k.j * CH + drop + settle, k.dz);
          q.setFromAxisAngle(up, k.rot); sc.setScalar(vis ? 1 : 0.0001);
          m4.compose(pos, q, sc); mesh.setMatrixAt(i, m4);
        });
        mesh.instanceMatrix.needsUpdate = true;
        // cámara: órbita lenta + acercamiento durante TODO el plano (nunca quieta), temblor en el golpe de $8M
        const p = clamp((time - T0) / (T1 - T0));
        const yaw = -0.35 + 0.55 * p, dist = 26 - 4 * p;
        const hit = time > TLAND ? Math.exp(-(time - TLAND) * 9) : 0;
        const shake = hit * 0.12 * Math.sin(time * 90);
        camera.position.set(Math.sin(yaw) * dist + shake, 9 + 1.2 * p, Math.cos(yaw) * dist);
        camera.lookAt(0.2, 2.2 + shake, 0);
        burst.intensity = hit * 60;
        renderer.render(scene, camera);
      }
      window.addEventListener("hf-seek", (e) => renderAt(e.detail.time));
      renderAt(window.__hfThreeTime || 0);
    </script>
  </body>
</html>
