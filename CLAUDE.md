# Proyecto AI — Content Intelligence OS + canal "Net Worthy"

## Qué es

Un sistema que decide QUÉ contenido crear (por datos: demanda + dinero) y acumula qué funciona.
NO es un generador de video. El video es el primer producto; el activo es el conocimiento calibrado.
Nicho: **finanzas/inversiones/crypto, faceless, audiencia EN**. Canal: **Net Worthy** (@networthytv).

```
SISTEMA decide QUÉ (tema, por demanda+RPM)   →  TU CLAUDE piensa CÓMO (ángulo estructurado)
                                             →  SISTEMA acumula QUÉ FUNCIONA (record-outcome)
```

Regla dura (`raw-term-is-que-not-video`): un término del detector ("build wealth") es una SEÑAL DE
DEMANDA, no un video. SIEMPRE convertirlo en un explainer estructurado (hook → qué cambió → datos →
alcista → riesgo → "y a mí qué" → cierre) + aviso YMYL.

**Estado actual: `docs/ESTADO.md`, léelo antes de tocar nada.** Historial y versión anterior de
este archivo (motor v1, base v1, confounder del S3, carrera del Lote): `docs/archivo/`.

## Comandos (python -m omega.cli <cmd>)

Diario: `ingest` (RSS) · `youtube-scan` (demanda YouTube) · `signals` · `decide` (tema por $). Atajo: **/daily**.
Idea: `think "<tema>"` → pegar pack en Claude → rellenar data/think_result.json → `record-think`
Explorar: `trends` · `youtube <q>` · `related <tema>` · `patterns` · `combine <s>`
Publicar: `youtube-auth` (una vez; también Analytics; repetir una vez para comentar, scope `youtube.force-ssl`) · `publish <ref>` · `meta-auth` (una vez) · `publish-fb <ref> [--publicar]` ·
`publish-ig <ref> [--publicar]`: privados/borrador por defecto. **Meta (FB/IG) SIEMPRE requiere
confirmación explícita en el chat antes de `--publicar`**: no se automatiza publicar en vivo.
Páginas: `python video-v2/motor/social.py video-v2/<ref>` (carrusel + historia + textos; lo hace producir.py) · `publish-social <ref> [--publicar]` (sin --publicar solo el plan; --publicar SOLO con confirmación en el chat)
Aprobar: `programar <ref>` (Short privado → 12:00 de Nueva York; `--ahora`) · `comentar <ref>` (fijarlo es a mano en Studio)
Medir: `analytics-sync [<ref>]` (retención, tráfico, búsquedas + rescore) · `meta-sync [<ref>...]` (reels FB/IG + rescore), ambos automáticos en /producir · `vincular <ref> <video_id>` · `rescore`
Estado/nube: `estado-bajar` · `estado-subir` · `produccion-guardar video-v2/<ref>` (repo PRIVADO `ESTADO_REPO`)
Tras publicar: `record-dna` · `record-cost` · `record-analytics` · `record-outcome <ref> <0..1>` · `dna` · `learnings`

## Tests

`python -m unittest discover -s tests -q` (deben pasar TODOS antes de commitear lógica).
Antes de abrir el navegador o renderizar (<1 s, cazan lo que la consola calla):

- `node tools/check_motor.mjs`: SINTAXIS. Un error no da error en consola: el navegador aborta el script.
- `node tools/lint_motor.mjs`: CORRECCIÓN (ESLint, reglas de bug; `no-redeclare` caza lo que costó horas el 26-jul).

## Motor v2 (HyperFrames): `video-v2/motor/README.md`

Un Short = `storyboard.json` (guion + escenas ancladas a `frase:palabra`, nunca segundos) →
`motor/voz.py` → `motor/construir.py` (valida, imágenes, música, HTML) → lint → render → QA.
Nadie escribe HTML. Referencia: `video-v2/read-janitor/storyboard.json`. Registrar el ADN con
`"renderer_version": "v2-hyperframes"`. Catálogo de escenas, b-roll, sonido, serie y pruebas: el README.

- Medios con licencia (lista cerrada PD/CC0/CC BY + Pexels License; fuera SA/NC/ND):
  `tools/imagenes_libres.py` (⚠ Commons limita por IP: `lote`, nunca bucles de `bajar`) ·
  `tools/broll.py` (Pexels: `PEXELS_API_KEY` + dominio `videos.pexels.com`) · `tools/musica_libre.py` · `tools/sfx_libre.py` · `tools/ocr_doc.py` · `tools/duotono.py`.
- "Todo real, nada genérico": metraje, documento o dato real con ejes reales (años verificados o "Yr N").
- **NO construir un generador de posts de texto:** con 0 seguidores no se distribuyen. Los carruseles
  sí (IG los recomienda a no seguidores); las historias solo llegan a seguidores.

## Voz y sincronía (RESUELTO, no tocar a ojo)

`python tools/generar_voz.py <clave> [--motor piper|kokoro] [--voz <nombre>]` sintetiza y alinea.
No sobrescribe una voz existente sin `--forzar`. Por defecto **Kokoro `am_adam`** (elección del
usuario), en venv Python 3.12 aparte (`tools/.venv-voces/`, gitignored: sin wheel para 3.14; si
falta, el script da el comando). Ningún motor se elige unilateralmente: siempre con audio real.
Alineamiento real con `tools/alinear_voz.py` (`.align.json`). **El LEAD no es la palanca**: se ajustó
seis veces en vano; el error era dispersión, no offset.

## Score v3 (5-nov, `omega/creative/scoring.py`)

`0.70·min(1, retención/0.50) + 0.30·min(1, alcance/750)`, ahora con YouTube, Facebook e Instagram
(alcance = suma, retención = media ponderada por vistas). Una plataforma solo aporta con ≥30 vistas
(PROVISIONAL); sin ninguna no hay score. Cada una queda en `score_parts`. Se calcula con `rescore`, no
se teclea. v1, v2 y v3 no son comparables: mirar `score_version`. Una "vista" de Shorts incluye
scroll-by desde el 31-mar-2025: la retención es la palanca.

## Crítico automático (`video-v2/motor/critico.py`, rúbrica en `docs/RUBRICA.md`)

`python video-v2/motor/critico.py video-v2/<ref> [--mp4 <x>] [--solo-revisar] [--rondas 2]`: medidores
sobre el MP4 final → fallos con segundo y escena → parches del storyboard (catálogo cerrado) →
re-render sin subir, máx. 2 rondas, se queda la mejor ronda MEDIDA. Medidores: `tools/medir_texto.py`,
`medir_voz.py`, `medir_mezcla.py`, `medir_parecido.py`. El juicio (J1-J6) lo escribe Claude en
`renders/critica/rN/juicio.json` mirando UNA hoja de contactos. Rúbrica **PROVISIONAL** hasta ~10
notas a ciegas del usuario. Umbrales en `motor/rubrica.json`.

## QA del vídeo exportado (sobre el archivo, no sobre el modelo)

- `python tools/medir_loudness.py <mp4>`: YouTube/FB normalizan a **-14 LUFS**, pico < -1 dBTP.
- `python tools/analizar_video.py <mp4>`: cortes + picos de movimiento (⚠ ruidoso: elige dónde mirar, no es veredicto).
- `python tools/medir_ritmo.py <mp4> [--max 2.5]`: tramo más largo sin cambio visual; código 1 si se pasa.

## POLÍTICA DE INGENIERÍA (docs/POLITICA.md), respétala

El motor NO está congelado. Una mejora entra si sube una métrica MEDIDA: calificación a ciegas del
usuario, distancia a Shorts de referencia del nicho, o retención real. Nada de mejorar a ojo en
círculos. Hito: juez automático que coincida con el usuario → autonomía. No sobre-interpretar n bajo
(PROVISIONAL). Aislar variables antes de concluir.

## Docs

`docs/ESTADO.md` (traspaso) · `docs/PLAN.md` (plan vigente: calidad primero, autonomía solo cuando el
usuario lo diga) · `docs/POLITICA.md` · `docs/RUBRICA.md` · `docs/V2-CALIDAD.md` · `docs/VISION.md`
(arquitectura congelada) · `docs/guiones/` · `marca/` · `docs/archivo/` (historia).

## CÓMO TRABAJAR (método: sale de errores medidos, no de teoría)

- **Si algo se resiste DOS rondas, la pregunta no es "¿qué parámetro muevo?" sino "¿esto ya está
  resuelto?".** El desfase de subtítulos costó seis rondas; la solución era alineamiento forzado.
- **Antes de creer una medición, validar el instrumento.** Tres métricas propias dieron falsos
  positivos y llevaron a "arreglar" cosas que no estaban rotas.
- **Sustituir juicio por medición siempre que se pueda.**
- **Lo barato primero.** `check_motor` + `lint_motor` antes de abrir el preview o renderizar (3 min).

## ECONOMÍA DE CONTEXTO (el usuario lo pidió explícitamente)

- **Devolver agregados, no listados**: media, máximo y los 3 peores casos. Nada de volcar 50 filas.
- **Agrupar cambios y verificar UNA vez por lote**, no tras cada constante.
- **Imágenes:** primero el número; la imagen solo para juicio visual o confirmación final. Nunca una
  hoja de contactos entera si bastan 2 frames.
- **Un render de vídeo por lote cerrado.** Lánzalo en segundo plano y espera el aviso: nada de
  `tail`/`sleep`, cada consulta relee todo el contexto.
- **Preferir `Grep` con contexto a `Read` de bloques grandes**: motor v1 (288 KB), storyboards (44 KB).
- **No retomar en frío una sesión grande:** tras >1 h sin actividad la caché caduca y el primer
  mensaje reescribe todo el contexto. Mejor nota de traspaso y sesión nueva.

## Convenciones

- Responder en **español**; el contenido del canal va en **inglés**.
- Commits: mensaje via archivo si tiene comillas/`&`/`$` (PowerShell rompe here-strings con eso).
  Terminar con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Rama de trabajo `master`.
- `data/` y `.env` están gitignored (nunca commitear). `YOUTUBE_API_KEY` vive en `.env`.
- Verificar antes de afirmar (correr tests / el comando real). Windows + PowerShell.
- Kernel `omega/reasoning/` es domain-agnostic (hay test de pureza por AST): no meterle nada de video.
