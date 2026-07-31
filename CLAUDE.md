# Proyecto AI — Content Intelligence OS + canal "Net Worthy"

## Qué es
Un sistema que decide QUÉ contenido crear (por datos: demanda + dinero) y acumula qué funciona.
NO es un generador de video. El video es el primer producto; el activo es el conocimiento calibrado.
Nicho: **finanzas/inversiones/crypto, faceless, audiencia EN**. Canal: **Net Worthy** (@networthytv).

## El reparto mental (lo más importante)
```
SISTEMA decide QUÉ (tema, por demanda+RPM)   →  TU CLAUDE piensa CÓMO (ángulo estructurado)
                                             →  SISTEMA acumula QUÉ FUNCIONA (record-outcome)
```
Regla dura (memoria `raw-term-is-que-not-video`): un término que saca el detector ("build wealth")
es una SEÑAL DE DEMANDA, no un video. SIEMPRE convertirlo en un catch-up explainer estructurado
(hook → qué cambió → datos → alcista → riesgo → "y a mí qué" → cierre) + aviso YMYL.

## Comandos (python -m omega.cli <cmd>)
Diario:   `ingest` (RSS) · `youtube-scan` (demanda YouTube) · `signals` · `decide` (tema por $)
Idea:     `think "<tema>"` → pegar pack en Claude → rellenar data/think_result.json → `record-think`
Explorar: `trends` · `youtube <q>` · `related <tema>` · `patterns` · `combine <s>`
Publicar: `publish <ref>` (YouTube) · `meta-auth` (setup una vez) · `publish-fb <ref> [--publicar]` ·
  `publish-ig <ref> [--publicar]` — los tres privados/borrador por defecto; `--publicar` los hace
  públicos. Meta (FB/IG) SIEMPRE requiere confirmación explícita en el chat antes de correr
  `--publicar` — no se automatiza publicar en vivo sin que el usuario lo vea primero.
Tras publicar: `record-dna` · `record-cost` · `record-analytics` · `record-outcome <ref> <0..1>` · `dna` · `learnings`
Atajo: **/daily** corre ingest+youtube-scan+signals+decide.

## Tests
`python -m unittest discover -s tests -q`  (deben pasar TODOS antes de commitear lógica).
**Motor de video, ANTES de abrir el navegador** (los dos tardan <1s y cazan lo que la consola calla):
- `node tools/check_motor.mjs` — SINTAXIS. Un error aquí no da error en consola: el navegador
  aborta el script entero y la página "carga" sin hacer nada.
- `node tools/lint_motor.mjs` — CORRECCIÓN (ESLint, solo reglas de bug). `no-redeclare` es el que
  habría cazado en 100 ms los dos fallos que costaron horas el 26-jul: `pintarChecklist` (ya
  existía para el panel → la escena salía en blanco) y `reloj` (ya declarado → script abortado).
Luego `tests-motor.html` en el navegador.

## Sincronía de subtítulos — RESUELTO, no volver a tocarlo a ojo
Antes de renderizar un Short: **`python tools/alinear_voz.py <clave-del-short>`**. Pone el tiempo
REAL de cada palabra (reconocimiento de voz local, gratis e ilimitado) en `data/<voz>.align.json`;
el motor lo carga solo al pulsar "Usar la voz del proyecto". Sin él, el calibrador ESTIMA dentro de
cada bloque y el desfase vuelve. **El LEAD no es la palanca** (se ajustó seis veces sin arreglarlo:
el error era dispersión, no offset).

## Voz automática — Kokoro por defecto, Piper y CapCut siguen disponibles
`python tools/generar_voz.py <clave-del-short> [--motor piper|kokoro] [--voz <nombre>]` sintetiza
el guion y encadena el alineamiento en el mismo comando: sale con audio + `.align.json` listos.
**No sobrescribe una voz ya existente sin `--forzar`** — la de un Short ya revisado no se toca sola.

**Motor por defecto: Kokoro, voz `am_adam`** (elegida por el usuario 2026-07-30 en una comparativa
a ciego de 7 voces, medidas por tono real en Hz para poder pedir "más grave" con datos). Kokoro
corre en un venv de **Python 3.12 aparte** (`tools/.venv-voces/`, gitignored — el proyecto sigue en
3.14): la cadena `kokoro -> misaki[en] -> spacy -> thinc -> blis<1.1.0` no tiene wheel para 3.14
(verificado forzando la instalación: falla al COMPILAR, no es un límite de metadata sin más). Si el
venv no existe, `generar_voz.py` avisa con el comando exacto para crearlo — no falla en silencio.

`--motor piper` sigue disponible (voz `en_US-ryan-high`, MIT, corre en el 3.14 principal sin
dependencias extra — fue el primero en automatizarse). CapCut también sigue siendo válido. Ningún
motor se elige unilateralmente: siempre a partir de audio real escuchado por el usuario.

## QA del vídeo exportado (sobre el archivo, no sobre el modelo)
- `python tools/medir_loudness.py <mp4>` — loudness real contra el estándar de la plataforma
  (YouTube/FB normalizan a **-14 LUFS**, pico < -1 dBTP). Solo mide; no toca la mezcla del motor
  (congelado, `docs/POLITICA.md`) salvo que el gap sea grande y consistente entre videos.
- `python tools/analizar_video.py <mp4>` — cortes de plano con PySceneDetect (fiable, es de
  terceros) + picos de movimiento con optical flow (⚠ ruidoso con contadores/texto animado —
  probado y documentado en el propio script: úsalo para elegir dónde mirar, nunca como veredicto).

## POLÍTICA DE INGENIERÍA (docs/POLITICA.md) — respétala
El motor creativo está **CONGELADO**. NO añadir features nuevas al motor salvo que un experimento
publicado revele una limitación concreta. Excepción: instrumentación de captura-en-origen.
Hito actual: **10 videos instrumentados**. Progreso = filas del dataset, no commits ni módulos.
No sobre-interpretar n bajo (marca PROVISIONAL). Aislar variables antes de concluir.

## Estado actual (2026-07-24, verificado contra la DB) — LEE `docs/ESTADO.md` ANTES DE TOCAR NADA
**6 de 10 instrumentados, 5 medidos.** 117 tests verdes. `production_cost` = **0 filas**.
**Score v2 (28-jul, `omega/creative/scoring.py`): `0.70·min(1, retención/0.50) + 0.30·min(1, alcance/750)`.**
Se calcula desde `production_analytics` con `python -m omega.cli rescore`, NO se teclea a mano, y
cada outcome guarda su `score_version`. Motivo: desde el 31-mar-2025 una "vista" de Shorts incluye
scroll-by sin mínimo de tiempo (lo que antes era vista ahora es *engaged view*), así que el v1
—alcance/750— mezclaba a quien vio el vídeo con quien pasó por encima. La retención es la palanca:
el umbral para que el algoritmo empuje un Short de 30-60s es ~50% y el canal va por 6-16%.
⚠ v1 y v2 NO son comparables: mirar siempre `score_version` antes de comparar dos outcomes.
- **#6 Buffett CERRADO** (256 vistas → 0.341, 2º de 5). **FLATLINEÓ**: entre las 17h y los 7 días
  sumó +1 vista. En Reels el veredicto llega en las primeras ~17h — una ventana corta ya es casi
  el número final. Primera curva de retención del canal: **24,1% a 3s → 10,0% a 20s**. El gancho
  es el mejor del canal y aun así se cae entre 3s y 20s: **el problema no es el gancho**.
- **#7 Ronald Read:** montado en el motor (18-jul), **cero filas en la DB**.
- **⚠ La captura está PARADA:** último `ingest` 15-jul, últimas `signals` 12-jul. **Correr `/daily`
  antes de volver a usar `decide`** — opera sobre un corpus congelado.
- Predicciones #15-#18 resueltas `inconclusive` el 24-jul: falló el instrumento (hueco de datos +
  el extractor cambió de v0.2.0 a v0.2.1 dentro del horizonte), no la hipótesis. Ver `ESTADO.md`
  para el gap metodológico que destapó (predicciones sin `extractor_version` sellada).

- **Motor de video:** `docs/guiones/short-renderer.html` genera el Short entero (visuales + voz +
  subtítulos quemados) y exporta **MP4 H.264+AAC** listo para subir. Sin CapCut. Datos por Short en
  `SHORTS[...]`; el resto es motor. Tiene **calibrador automático** que deduce cortes y subtítulos
  del audio (verificado: reproduce exacto la calibración manual del S3).
- **Renderizar SIEMPRE por la cola de "Lote"** (campo + botón "Lote"), incluso para 1 solo Short —
  no el flujo manual de seleccionar+cargar voz+grabar. El lote ya encadena cargarShort → traer
  `data/<voz>` (la que deja `generar_voz.py`) → calibrar → exportar sin tocar nada a mano, y evita
  una condición de carrera real (30-jul): seleccionar un Short dejaba `cortesMedidos=true` desde el
  instante de elegirlo (antes de calibrar su voz), así que exportar demasiado rápido en el flujo
  manual podía quemar los subtítulos/tiempos de **S3** (el primer Short) encima de la voz nueva —
  visto en Ronald Read. Fix de una línea en `cargarShort` (línea ~3707); el lote nunca lo sufrió
  porque ya esperaba a que la calibración real terminara antes de exportar.
- **Voz actual:** CapCut TTS. ElevenLabs aplazado: su plan gratis no da derechos comerciales y sus
  voces Default caducan el 31-dic-2026.
- **Confounder anotado:** el S3 se publicó a las 02:00 hora local con audiencia EN/US. Si retiene
  poco, puede ser la HORA, no el gancho. No atribuirlo a `hook_type`.
- **Siguiente:** #7 Ronald Read (montado en el motor, sin publicar) = 7/10. Progreso = filas del
  dataset, no commits. La palanca que señalan los datos es la RETENCIÓN entre 3s y 20s, no el gancho.
- **NO construir un generador de posts de texto:** con 0 seguidores no se distribuyen (alcance
  orgánico de una Página = 1-6% de sus seguidores). "Contenido diario" = más Shorts.

## Docs (leer al retomar)
`docs/ESTADO.md` (traspaso — **empieza aquí**, trae las trampas conocidas) · `docs/POLITICA.md` ·
`docs/VISION.md` (arquitectura congelada) · `docs/guiones/` (guiones, motor, calibración) · `marca/`.

## CÓMO TRABAJAR (método — sale de errores medidos, no de teoría)
- **Si algo se resiste DOS rondas, la pregunta no es "¿qué parámetro muevo?" sino "¿esto ya está
  resuelto?".** El desfase de subtítulos costó SEIS rondas ajustando el LEAD; la solución era
  alineamiento forzado, estándar desde hace años (`tools/alinear_voz.py`).
- **Antes de creer una medición, validar el instrumento.** Tres métricas propias dieron falsos
  positivos (solapes sin aplicar la matriz del canvas; sincronía contra "el arranque de voz más
  cercano" aunque fuera de otra tarjeta) y llevaron a "arreglar" cosas que no estaban rotas.
- **Sustituir juicio por medición siempre que se pueda.** Lo que más ha mejorado el motor no es
  pensar mejor: es `alinear_voz.py`, `check_motor.mjs` y `lint_motor.mjs`.
- **Lo barato primero.** `check_motor` + `lint_motor` tardan <1s y cazan lo que el navegador calla:
  correrlos SIEMPRE antes de abrir el preview o renderizar (3 min).

## ECONOMÍA DE CONTEXTO (el usuario lo pidió explícitamente)
- **Devolver agregados, no listados**: media, máximo y los 3 peores casos. Nada de volcar 50 filas.
- **Agrupar cambios y verificar UNA vez por lote**, no tras cada constante.
- **Las imágenes son lo más caro del turno.** Primero el número; la imagen solo para juicio visual
  o confirmación final. Nunca una hoja de contactos entera si bastan 2 frames.
- **Un render de vídeo por lote cerrado.** Cada uno son ~3 min y polling.
- Preferir `Grep` con contexto a `Read` de bloques grandes del motor (288 KB).

## Convenciones
- Responder en **español**; el contenido del canal va en **inglés**.
- Commits: mensaje via archivo si tiene comillas/`&`/`$` (PowerShell rompe here-strings con eso).
  Terminar con `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Rama de trabajo `master`.
- `data/` y `.env` están gitignored (nunca commitear). `YOUTUBE_API_KEY` vive en `.env`.
- Verificar antes de afirmar (correr tests / el comando real). Windows + PowerShell.
- Kernel `omega/reasoning/` es domain-agnostic (hay test de pureza por AST): no meterle nada de video.
