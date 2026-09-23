# Short #7 Ronald Read — v2 (HyperFrames), completo

Re-montaje del #7 publicado (YouTube `sbQDcmFadME`) con el motor v2, para compararlo con la
versión canvas. **Única variable que cambia: el renderer.** El guion es el de
`SHORTS['read-janitor']` palabra por palabra y la voz es la misma Kokoro `am_adam` generada con el
mismo pipeline (`tools/generar_voz.py`, `kokoro` + misaki en el venv 3.12). Se registra con
`renderer_version: "v2-hyperframes"` en el ADN: sus resultados NO se comparan con los de v1 sin
mirar esa columna.

**QA del MP4 final** (23-sep, tras `loudnorm`): `hyperframes lint` 0 errores · `medir_loudness`
**-14,55 LUFS / -1,11 dBTP** ✓ · `medir_ritmo` tramo quieto máximo **1,4 s**, 14 % quieto ✓
(tope 2,5 s; el #7 v1 medido con el mismo instrumento: 6,0 s y 90 %). 49,8 s, 1080x1920, H.264+AAC,
render de ~6 min. La 1ª pasada falló el ritmo (2,8 s en la tarjeta final) y se corrigió con
movimiento real, no subiendo el umbral.

## Reproducir
Requisitos: Node 22+, Python 3.11+, FFmpeg **con ffprobe**, Chrome (en Linux:
`HYPERFRAMES_BROWSER_PATH=/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell`).
```
python tools/generar_voz.py read-janitor --motor kokoro --forzar   # voz + data/voz-short-read.align.json
cp data/voz-short-read.mp3 video-v2/read-janitor/assets/voice.mp3  # y words.json (ver abajo)
python tools/imagenes_libres.py lote video-v2/read-janitor/assets/imagenes.txt   # originales + créditos
HF_CORE=<carpeta con @hyperframes/core@0.8.62> npm run build   # música + index.html + ducking (carve)
npm run lint && npm run render
ffmpeg -i renders/read-janitor-v2.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy -c:a aac -b:a 192k renders/final.mp4
python ../../tools/medir_loudness.py renders/final.mp4 && python ../../tools/medir_ritmo.py renders/final.mp4 --max 2.5
```
`assets/words.json` sale del `.align.json` (campos `w/t0/t1` -> `text/start/end`).

## Cómo está hecho
- **`build.py` genera `index.html`** desde `plantilla.tpl` + `assets/words.json`. Cada escena se
  ancla por ÍNDICE de palabra (`w(47)` = "Sixty" de "Sixty years later"): voz nueva del mismo
  guion = re-alinear + `build.py`, sin recalcular ~40 tiempos a mano. **Edita la plantilla, no
  `index.html`.** La plantilla es `.tpl` a propósito: un segundo `.html` con
  `data-composition-id` hace que el linter lo trate como otra composición raíz (audio duplicado).
- **Ducking**: `build.py` corre `carve.mjs` (skill `hyperframes-audio`) DESPUÉS de generar el
  HTML; si falta `HF_CORE` lo avisa en vez de dejar la música pisando la voz en silencio.
- **Imagen real** (todas verificadas por la API de Commons, `assets/img/creditos.json`): 8 de
  dominio público (FSA/OWI 1940-41 — Jack Delano en **Brattleboro**, el pueblo de Read; Russell
  Lee; Biblioteca del Congreso; certificados del XIX; Carol M. Highsmith) + 1 CC BY 2.0 (portada
  del Santa Ana Register, 28-oct-1929, Orange County Archives — **exige atribución**). Ninguna
  foto de Ronald Read: las que existen son de prensa y tienen copyright.
  Créditos para la descripción: `python tools/imagenes_libres.py creditos video-v2/read-janitor/assets/img`.
- **Tratamiento**: `tools/duotono.py` hornea el duotono verde #0A1A14 -> dorado #D8B25A (una vez,
  no un filtro CSS por frame). El grano (SVG animado) y el Ken Burns van en la composición.
- **3D**: columnas de monedas (Three.js) sincronizadas por construcción con el contador de $8M
  (misma curva invertida). Con WebGL el render usa 1 worker.
- **Música**: `gen_musica.py`, sintetizada y determinista, sigue la forma del guion (tensión en
  el gancho, groove, caída a oscuro en "the part nobody says", resolución, CTA).
- **Cifras**: la curva es la ILUSTRATIVA del #7 ($170/mes, 10 %/año nominal, 60 años -> $8M) y
  el aviso YMYL del #7 sale mientras hay cifras en pantalla y en la tarjeta final. Las crisis de
  la línea de años (1962, 1973, 1987, 2000, 2008) son hechos históricos, no datos de su cartera.

## Deuda técnica conocida
- Composición **monolítica** (1 archivo): `lint` da 31 avisos `nested_structure_needs_subcomposition`.
  Render correcto; lo que se pierde es la edición cómoda en Studio (una fila por escena). Partir
  en sub-composiciones cuando se haga el segundo Short v2 — ahí se ve qué es plantilla común.
- La voz se copia de `data/` (gitignored) a `assets/`: la del repo es la que se renderizó.
