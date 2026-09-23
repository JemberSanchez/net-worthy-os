# PoC v2 — gancho de Ronald Read en HyperFrames

Prueba técnica (23-sep-2026) para decidir el motor v2. **No es un Short publicable**: son los
primeros 9,9 s, sin imágenes reales (las fuentes de imagen estaban bloqueadas en el contenedor).

QA del MP4 final: `medir_loudness.py` → -14,47 LUFS / -1,32 dBTP ✓ · `medir_ritmo.py` → tramo
quieto máximo 0,8 s, 4 % del tiempo quieto ✓ (el motor canvas viejo: 6,0 s y 90 %).

## Correr en tu PC
Requisitos: Node 22+, FFmpeg **con ffprobe** en el PATH, Chrome.
```
npm run dev      # Studio: timeline editable (tú y el agente editáis el mismo HTML)
npm run lint     # gate de calidad del framework (0 errores antes de renderizar)
npm run render   # -> renders/poc-read.mp4 (H.264+AAC, 1080x1920, 30fps)
```
Loudness: el render sale en ~-16 LUFS; normalizar a -14 con
`ffmpeg -i renders/poc-read.mp4 -af loudnorm=I=-14:TP=-1.5:LRA=11 -c:v copy -c:a aac out.mp4`
y verificar con `python tools/medir_loudness.py out.mp4`.

## De dónde sale cada cosa
- `assets/voice.wav`: `npx hyperframes tts "<guion>" -v am_adam` (Kokoro vía `kokoro-onnx`).
- Tiempos por palabra: **estimados** desde los silencios reales del audio (HuggingFace estaba
  bloqueado en el contenedor). En producción salen de `tools/alinear_voz.py`.
- `assets/*.wav` de SFX y `assets/music-bed.wav`: sintetizados con numpy (whoosh, impacto,
  ding; base en La menor con redoble que acelera y caída en el golpe de los $8M). Sin licencias.
- Ducking: `node <skill hyperframes-audio>/scripts/carve.mjs --comp index.html` escribió
  `data-fx-chain`/`data-automation` en `#music-bed`: la música se aparta de la voz solo en las
  bandas donde la voz habla (dinámico), no bajando todo el volumen.
- Escena 3D (Three.js r181, empaquetado en `assets/three/`): columnas de monedas por década. Cada
  moneda aparece en el instante exacto en que el contador HTML pasa por su valor (misma curva
  `power1.in` → `power3.in`, invertida), así que la cifra y el 3D no pueden desincronizarse.
  Con WebGL el render usa 1 worker: ~60 s en vez de ~35 s en 4 núcleos sin GPU.
- Fuentes: Anton + Inter (OFL, vía @fontsource). GSAP empaquetado en local: el render no
  depende de la red.
