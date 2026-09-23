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
Todo sale de **`storyboard.json`** con el motor común (`video-v2/motor/`, ver su README):
```
python video-v2/motor/voz.py video-v2/read-janitor --forzar        # voz + words.json (medidos)
HF_CORE=<dir con @hyperframes/core@0.8.62> python video-v2/motor/construir.py video-v2/read-janitor
cd video-v2/read-janitor && npm run lint && npm run render
ffmpeg -i renders/read-janitor.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy -c:a aac -b:a 192k renders/final.mp4
python ../../tools/medir_loudness.py renders/final.mp4 && python ../../tools/medir_ritmo.py renders/final.mp4 --max 2.5
```
Este Short se hizo primero a mano (23-sep) y después se migró al storyboard como **prueba de oro**
del motor: mismo resultado en lint y QA (-14,54 LUFS; tramo quieto máx. 2,0 s frente a 1,4 s a mano,
en la escena "same engine"). ⚠ Kokoro no es determinista bit a bit entre síntesis (mismo largo,
±0,2 s en 15/162 palabras): el alineamiento se hace SIEMPRE sobre el audio final.

## Deuda técnica conocida
- Composición **monolítica** (1 archivo): `lint` da 31 avisos `nested_structure_needs_subcomposition`.
  Render correcto; lo que se pierde es la edición cómoda en Studio (una fila por escena). Partir
  en sub-composiciones cuando se haga el segundo Short v2 — ahí se ve qué es plantilla común.
- La voz se copia de `data/` (gitignored) a `assets/`: la del repo es la que se renderizó.
