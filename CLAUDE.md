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

## Estado actual
Sistema construido, auditado, sin bugs que afecten decisiones (87 tests, DB reseteada limpia).
`decide` ya pondera por DINERO (feature monetization/RPM), no solo vistas. `production_outcome = 0`:
el moat está vacío hasta el primer video. **Marca hecha y EN VIVO** (Net Worthy @networthytv; kit en
`marca/`). Primer video decidido, empaquetado e instrumentado: build-wealth "assets vs habits", ref
`build-wealth-assets-vs-habits-2026-07` (paquete en `docs/guiones/build-wealth-PAQUETE-COMPLETO.md`).
Producción: stack gratis (ElevenLabs voz Brian + CapCut + Pexels). **El único pendiente real es
PRODUCIR Y PUBLICAR el video #1** (empezar por el Short de 45s). Detalle de todo en `docs/ESTADO.md`.

## Docs (leer al retomar)
`docs/ESTADO.md` (traspaso) · `docs/VISION.md` (arquitectura congelada) · `docs/POLITICA.md` ·
`docs/guiones/` (paquetes de producción) · `marca/` (kit de marca).

## Convenciones
- Responder en **español**; el contenido del canal va en **inglés**.
- Commits: mensaje via archivo si tiene comillas/`&`/`$` (PowerShell rompe here-strings con eso).
  Terminar con `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`. Rama de trabajo `master`.
- `data/` y `.env` están gitignored (nunca commitear). `YOUTUBE_API_KEY` vive en `.env`.
- Verificar antes de afirmar (correr tests / el comando real). Windows + PowerShell.
- Kernel `omega/reasoning/` es domain-agnostic (hay test de pureza por AST): no meterle nada de video.
