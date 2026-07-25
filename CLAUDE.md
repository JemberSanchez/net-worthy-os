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

## Estado actual (2026-07-24, verificado contra la DB) — LEE `docs/ESTADO.md` ANTES DE TOCAR NADA
**5 de 10 instrumentados, 4 medidos.** 104 tests verdes. `production_cost` = **0 filas**.
Score: `success = vistas_totales(FB+YT) / 750`.
- **#6 Buffett publicado (~17-jul) pero a medias en el moat:** tiene analytics+context, le falta
  `record-dna` y `record-outcome`. Sus analytics son un **baseline de 17h**, NO comparable con los
  28d de S1/S2 → **re-medir a 28d antes de registrar**, o se envenena el dataset.
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
- **Voz actual:** CapCut TTS. ElevenLabs aplazado: su plan gratis no da derechos comerciales y sus
  voces Default caducan el 31-dic-2026.
- **Confounder anotado:** el S3 se publicó a las 02:00 hora local con audiencia EN/US. Si retiene
  poco, puede ser la HORA, no el gancho. No atribuirlo a `hook_type`.
- **Siguiente:** cerrar #6 Buffett en el moat (re-medir 28d → `record-dna` + `record-outcome`) = 6/10,
  luego #7 Ronald Read = 7/10. Progreso = filas del dataset, no commits.
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
