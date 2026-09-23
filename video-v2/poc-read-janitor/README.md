# PoC v2 — gancho de Ronald Read en HyperFrames

Prueba técnica (23-sep-2026) para decidir el motor v2. **No es un Short publicable**: son los
primeros 9,9 s, sin imágenes reales ni música.

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
- `assets/*.wav` de SFX: sintetizados con numpy (whoosh, impacto, ding), sin licencias.
- Fuentes: Anton + Inter (OFL, vía @fontsource). GSAP empaquetado en local: el render no
  depende de la red.
