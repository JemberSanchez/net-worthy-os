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
Tras publicar: `record-dna` · `record-cost` · `record-analytics` · `record-outcome <ref> <0..1>` · `dna` · `learnings`
Atajo: **/daily** corre ingest+youtube-scan+signals+decide.

## Tests
`python -m unittest discover -s tests -q`  (deben pasar TODOS antes de commitear lógica).

## POLÍTICA DE INGENIERÍA (docs/POLITICA.md) — respétala
El motor creativo está **CONGELADO**. NO añadir features nuevas al motor salvo que un experimento
publicado revele una limitación concreta. Excepción: instrumentación de captura-en-origen.
Hito actual: **10 videos instrumentados**. Progreso = filas del dataset, no commits ni módulos.
No sobre-interpretar n bajo (marca PROVISIONAL). Aislar variables antes de concluir.

## Estado actual (2026-07-10) — LEE `docs/ESTADO.md` ANTES DE TOCAR NADA
**Short #1 PUBLICADO** el 2026-07-10 (YouTube Shorts + Facebook Reels), ref
`build-wealth-short-03-stat`. Pero **`production_outcome` = 0 filas**: el moat no se llena al
publicar, se llena al MEDIR. **Lo único que importa: el sábado 2026-07-12 correr `record-analytics`
+ `record-cost` + `record-outcome` + `dna`.** 92 tests verdes. 2 de 10 videos instrumentados, 0 medidos.

- **Motor de video:** `docs/guiones/short-renderer.html` genera el Short entero (visuales + voz +
  subtítulos quemados) y exporta **MP4 H.264+AAC** listo para subir. Sin CapCut. Datos por Short en
  `SHORTS[...]`; el resto es motor. Tiene **calibrador automático** que deduce cortes y subtítulos
  del audio (verificado: reproduce exacto la calibración manual del S3).
- **Voz actual:** CapCut TTS. ElevenLabs aplazado: su plan gratis no da derechos comerciales y sus
  voces Default caducan el 31-dic-2026.
- **Confounder anotado:** el S3 se publicó a las 02:00 hora local con audiencia EN/US. Si retiene
  poco, puede ser la HORA, no el gancho. No atribuirlo a `hook_type`.
- **Siguiente:** producir S1 (escena de columnas LISTA en el motor multi-Short; solo falta la voz —
  runbook: `docs/guiones/PRODUCCION-S1.md`) → medir S3 el sábado 12 → S2, S4, S5.
- **NO construir un generador de posts de texto:** con 0 seguidores no se distribuyen (alcance
  orgánico de una Página = 1-6% de sus seguidores). "Contenido diario" = más Shorts.

## Docs (leer al retomar)
`docs/ESTADO.md` (traspaso — **empieza aquí**, trae las trampas conocidas) · `docs/POLITICA.md` ·
`docs/VISION.md` (arquitectura congelada) · `docs/guiones/` (guiones, motor, calibración) · `marca/`.

## Convenciones
- Responder en **español**; el contenido del canal va en **inglés**.
- Commits: mensaje via archivo si tiene comillas/`&`/`$` (PowerShell rompe here-strings con eso).
  Terminar con `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Rama de trabajo `master`.
- `data/` y `.env` están gitignored (nunca commitear). `YOUTUBE_API_KEY` vive en `.env`.
- Verificar antes de afirmar (correr tests / el comando real). Windows + PowerShell.
- Kernel `omega/reasoning/` es domain-agnostic (hay test de pureza por AST): no meterle nada de video.
