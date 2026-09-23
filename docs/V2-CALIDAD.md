# V2 — subir la calidad del video (decisión verificada, 23-sep-2026)

## Por qué se paró el canal
La calidad. Y el techo era de arquitectura, no de ajuste: `short-renderer.html` dibuja todo con
canvas 2D procedural (**0 `drawImage`**: ni fotos, ni metraje, ni ilustraciones). Cada escena
nueva es código a mano en un archivo de 311 KB, y todos los Shorts salen con el mismo layout
(fondo verde, texto, bola en pendiente, ~60 % del cuadro vacío). Eso limita la calidad y hace
imposible automatizar: un Short nuevo = programar otra escena.

## Qué se probó DE VERDAD (no de memoria)
Se instaló y se renderizó en el contenedor. PoC en `video-v2/poc-read-janitor/`.

| Qué | Resultado medido |
|---|---|
| Render sin navegador visible | ✅ 9,9 s de 1080x1920 en **32-35 s** con 4 núcleos y GPU por software. H.264+AAC |
| Determinismo | ✅ captura frame a frame (`beginframe`), sin carreras de reloj. Adiós a los bugs de sincronía del Lote |
| Voz | ✅ `hyperframes tts -v am_adam` = **la misma voz Kokoro del canal**, vía `kokoro-onnx` (onnxruntime + phonemizer; **sin** la cadena spacy→blis que obligó a un venv 3.12 aparte) |
| Linter | ✅ cazó 1 error y 4 avisos reales que `lint_motor.mjs` no ve (tweens que se pisan, medición del DOM dentro de callbacks, animar `letterSpacing`) |
| Catálogo | ✅ ~410 bloques/componentes: `apple-money-count`, `mk-line-graph`, `count-up`, `caption-pill-karaoke`, `grain-overlay`, transiciones… (la mayoría en 16:9: se adaptan) |
| Loudness | ⚠ sale en -16,1 LUFS → hace falta un `loudnorm` a -14 al final (queda en -14,5, pico -1,2) |
| `transcribe` / Whisper | ❌ no verificable aquí: HuggingFace bloqueado por la red del contenedor. En el PC se sigue usando `alinear_voz.py` |

## Por qué HyperFrames y no Remotion / agentcut / seguir con el canvas
- **HyperFrames** (Apache-2.0, HeyGen, v0.8.x, activo a diario): es HTML+GSAP, el mismo modelo
  mental que el motor actual. Trae `/faceless-explainer` (nuestro caso exacto), un catálogo de
  bloques, TTS Kokoro, mezcla de audio que baja la música bajo la voz, lint/check/snapshot como
  QA automático, y **Studio** (timeline editable en el que tú y el agente editáis el mismo
  archivo = la idea de agentcut, pero oficial y mantenida).
  Riesgo: pre-1.0 → **fijar versión** (`hyperframes@0.8.62` en `package.json`) y subirla solo
  con `upgrade --check` + `check`.
- **Remotion**: maduro, pero licencia source-available (gratis hasta 3 empleados), paso de build
  con React y sin catálogo de finanzas ni TTS integrado. No se renderizó aquí porque no aportaba
  nada que HyperFrames no cubra (HyperFrames trae además `/remotion-to-hyperframes`).
- **agentcut**: está pensado para editar grabaciones (vídeo largo → clips). Tiene 3 ⭐ y usa
  Remotion por debajo. Su idea buena (plantillas + reglas + memoria de correcciones) se copia
  como convención, no como dependencia.
- **Seguir con el canvas**: descartado; su techo es el problema.

## v3 (misma sesión): 3D, música con ducking y ritmo MEDIDO
- **3D real** (Three.js dentro de HyperFrames, determinista vía `hf-seek`): columnas de monedas
  sincronizadas por construcción con el contador. Funciona en render sin GPU (SwiftShader).
- **Música + voiceover carve**: el ducking lo escribe `carve.mjs` en el HTML, no se ajusta a mano.
- **Ritmo, con instrumento nuevo validado**: `tools/medir_ritmo.py` (tramo más largo sin cambio
  visual). PySceneDetect NO sirve para esto (1 corte detectado en un vídeo que cambia todo el
  rato). Motor viejo: **6,0 s** quieto y 90 % del tiempo quieto. v3: **0,8 s** y 4 %.
  La hipótesis `pacing_2_3s` pide ≤2-3 s: el motor viejo la incumplía por el doble.

## Lo que la PoC NO resuelve todavía (el siguiente salto de calidad)
1. **Imagen real a sangre**: fotos de archivo de dominio público, b-roll (Pexels API) e
   ilustraciones IA con un estilo fijo. Es lo que separa "motion graphics limpio" de "canal top".
2. **Música de verdad**: la base sintetizada demuestra el ducking, pero una librería con
   licencia suena mejor.
3. **Tiempos por palabra reales** (`alinear_voz.py` → formato de palabras de HyperFrames).

## Pipeline objetivo (automatizado, con puertas humanas solo donde la política lo exige)
decide → guion (Claude API) → storyboard → assets → voz + alineamiento → composición HyperFrames
→ lint/check/snapshot → render → loudnorm + `medir_loudness` + `analizar_video` (cambio visual
≤3 s) → borrador en YT/FB/IG → **aprobación humana** → analíticas por API.

⚠ Guardar `renderer_version` en el ADN: los resultados de v1 (canvas) y v2 no son comparables
(misma lógica que `score_version`).
