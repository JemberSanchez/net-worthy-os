# ESTADO DEL PROYECTO — documento de traspaso

> **Para el nuevo chat:** lee este archivo primero, luego `CLAUDE.md`, `docs/POLITICA.md` y
> `docs/VISION.md`. Ruta: `C:\Users\Asus\Desktop\Proyecto AI` (repo git, rama `master`).
> Hay memoria en `~/.claude/projects/.../memory/` (índice `MEMORY.md`) que se carga sola.

---

## 1. Qué es
Sistema de inteligencia que decide **QUÉ** contenido crear (por datos: demanda + dinero) y
acumula **qué funciona**. NO es un generador de video. Nicho: **finanzas/inversiones/crypto,
faceless, audiencia EN**. Canal: **Net Worthy** (@networthytv).

## 2. El reparto mental (lo más importante)
```
SISTEMA decide QUÉ (tema, por demanda+RPM)  →  TU CLAUDE piensa CÓMO (ángulo estructurado)
                                            →  SISTEMA acumula QUÉ FUNCIONA (record-outcome)
```
Regla dura (memoria [[raw-term-is-que-not-video]]): un término del detector ("build wealth") es
una **señal de demanda, NO un video**. SIEMPRE estructurarlo en un catch-up explainer (hook → qué
cambió → datos → alcista → riesgo → "y a mí qué" → cierre) + aviso YMYL.

## 3. Qué está construido (todo en git, **87 tests verdes**, auditado y sin bugs que afecten decisiones)
- **Kernel** `omega/reasoning/` (domain-agnostic, test de pureza AST): beliefs/predictions,
  signals, hypotheses, opportunities, decision_engine (score = confianza + Σ peso·feature), decisions.
- **Observación + decisión** `omega/`: `sources/rss.py` (12 feeds) · **`sources/youtube.py`**
  (YouTube Data API, filtro de idioma solo-EN) · `analyze/momentum.py` (presencia RSS) ·
  **`analyze/demand.py`** (demanda por vistas + `related`) · **`analyze/monetization.py`**
  (RPM por sub-nicho) · `analyze/hypothesis_engine.py` (genera candidatas de 2 orígenes).
- **`decide` pondera 4 señales de audiencia + dinero:** demand (vistas) · gap (desatendido) ·
  demand_momentum (emergente) · **monetization (RPM — rentabilidad, no viralidad)**.
  Además YouTube **origina** temas (frases de alta demanda) aunque RSS no las levante.
- **Laboratorio creativo** `omega/creative/`: patterns (CKB), decisions+calibración, combinator,
  reasoning_loop, production, tradeoffs, experiments, questions, thinking (inerte sin LLM).
- **Instrumentación** `omega/creative/production_dna.py`: ADN por video (hook/story/cta/bloques)
  + analíticas (CTR/AVD/retención) + coste (horas/$/tiempo) + `dna_calibration` (con guard de
  confounding: marca PROVISIONAL con n bajo). Comandos record-dna/record-analytics/record-cost/dna.

## 4. Comandos (`python -m omega.cli <cmd>`) — y `/daily`
Diario: `ingest` · `youtube-scan` · `signals` · `decide` (o el atajo **`/daily`**).
Idea: `think "<tema>"` → pegar pack en Claude → rellenar data/think_result.json → `record-think`.
Explorar: `trends` · `youtube <q>` · `related <tema>` · `patterns` · `combine`.
Tras publicar: `record-dna` · `record-cost` · `record-analytics` · `record-outcome <ref> <0..1>` · `dna` · `learnings`.
Tests: `python -m unittest discover -s tests -q`.

## 5. MARCA — hecha y EN VIVO
- Canal **Net Worthy**, handle **@networthytv** (mismo en las 4 redes idealmente).
- Tagline: **"Wealth, explained plainly."**
- Símbolo: la **N** con la pata derecha convertida en flecha dorada hacia arriba (net worth ↑),
  fondo cuadrado full-bleed verde. Paleta "green felt & brass" (`#0A1A14` ink · `#1F9E6E` growth ·
  `#D8B25A` brass · `#F4F6F3` paper).
- Kit completo con descargas PNG en **`marca/export.html`** (+ `marca/README.md`). Avatar y banner
  ya subidos al canal.

## 6. PRIMER VIDEO — decidido, empaquetado, instrumentado
- El sistema (corrido en fresco) eligió **"build wealth"** por demanda+RPM (venció a SpaceX/crypto).
- Ángulo: **"No construyes riqueza con hábitos, sino con activos"** (assets vs habits).
- Gancho: **Marcus vs Dylan** (dos hombres, mismo sueldo, uno se jubila pobre y otro rico) — recurso
  narrativo para enganchar, se resuelve al min ~4 (= activos).
- Paquete completo (Short 45s + largo 7min palabra por palabra, retención, títulos, miniaturas,
  b-roll, YMYL): **`docs/guiones/build-wealth-PAQUETE-COMPLETO.md`**.
- Registrado: `creative_decision` + `production_dna` con ref **`build-wealth-assets-vs-habits-2026-07`**.

## 7. PRODUCCIÓN — stack (ver memoria [[production-stack]])
- **Voz:** ElevenLabs — voz **Brian**, modelo **Multilingual v2**, stability 50 / similarity 75 /
  style 35 / speaker boost ON. Guion listo para TTS en `docs/guiones/short-TTS.txt`.
  ⚠️ **REQUIERE plan Starter ($5/mes)**: el gratis no da licencia comercial, prohíbe canales
  monetizados y exige "elevenlabs.io" en el título. Los derechos se conceden AL GENERAR, así que
  el audio hecho en gratis NO se legaliza pagando después. Alternativas gratis con derechos:
  Google Cloud TTS / Piper (peor calidad).
- **Edición:** CapCut (subtítulos auto). **B-roll:** Pexels/Pixabay. **Miniatura:** Canva.
  **Música:** YouTube Audio Library. **IA imagen:** Ideogram/Bing.
- Nota MCP: en sesiones no-interactivas Claude **no** puede conectar/usar MCPs (OAuth). ElevenLabs
  conectado por el usuario pero no llega a la sesión. No bloquea: el pipeline es manual con apps web.

## 8. Estado honesto / lo más flojo
`production_outcome = 0` → **el moat está VACÍO.** Todo está construido, auditado y limpio, pero el
sistema **aún no ha aprendido nada real** porque no hay ni un video publicado. No es un bug; es lo
que el primer video arregla. La DB se reseteó (limpia; backup `.bak` en data/). Política: motor
CONGELADO (docs/POLITICA.md), hito = 10 videos instrumentados.

## 9. EL ÚNICO PASO QUE QUEDA — producir y publicar el video #1
Camino más barato = el **Short de 45s** (hook Marcus vs Dylan) para probar el gancho:
```
1. Voz    → ElevenLabs (Brian, ajustes de §7), pega el guion del Short → MP3
2. Editor → CapCut: voz + b-roll Pexels + subtítulos + animación curva + música
     La curva YA está hecha: abre `docs/guiones/curva-compuesta.html` en Chrome →
     "Grabar y descargar video" → .webm 9:16 (y "Frame final PNG" = miniatura B). $180k→$610k.
3. Publica → Short en YouTube + cross-post TikTok/IG/FB
4. Mide y cierra el bucle (PRIMER dato real del sistema):
     python -m omega.cli record-analytics   (CTR/retención)
     python -m omega.cli record-cost         (horas)
     python -m omega.cli record-outcome build-wealth-assets-vs-habits-2026-07 <0..1>
     python -m omega.cli dna
```
~~Pendiente: animación de la curva.~~ **HECHA** (2026-07-09): `docs/guiones/curva-compuesta.html`
— se auto-graba a `.webm` (9:16 y 16:9) y exporta PNG de miniatura. Verificada en navegador.
De paso se corrigió una cifra falsa del guion: el gap NO era $420k sino **$429,985** ($609,985
final, no ~$600k). Convención: 7% nominal capitalizado mensual.

## 10. Cómo arrancar el nuevo chat
*"Lee docs/ESTADO.md y CLAUDE.md. Vamos a producir el primer video (build-wealth, Short). Ayúdame
con [la animación de la curva / el guion final / lo que sea]."* — o corre `/daily` para ver si el
sistema propone algo nuevo. Recuerda: el único pendiente real es PRODUCIR Y PUBLICAR.
