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

## 9. EL ÚNICO PASO QUE QUEDA — PUBLICAR el Short S3
El vídeo **ya se genera solo**. `docs/guiones/short-renderer.html` produce los 24s completos
(intro, curva, número dorado, CTA y subtítulos quemados) con la voz incrustada. No hay que editar.

```
1. Abre docs/guiones/short-renderer.html en Chrome
2. Carga data/voz-short-03.mp3  → dirá "✅ Es el audio calibrado"
3. "Grabar y descargar el Short"  → MP4/WebM 1080x1920, ~24s, con voz y subtítulos
4. (opcional, 2 min) CapCut: música de Pixabay a -18 dB bajo la voz
5. Publica en YouTube Shorts + Facebook Reels
6. CIERRA EL BUCLE (el primer dato real del sistema, production_outcome sigue en 0):
     python -m omega.cli record-analytics   (ctr/avd/retención como FRACCIÓN 0..1, no %)
     python -m omega.cli record-cost         (horas)
     python -m omega.cli record-outcome build-wealth-short-03-stat <0..1>
     python -m omega.cli dna
```

**Ya hecho (2026-07-09):** curva animada (`curva-compuesta.html`) · renderizador completo del Short ·
calibración del audio (`docs/guiones/calibracion-voz-short-03.md`) · zonas seguras de YouTube/Facebook ·
ADN registrado (`build-wealth-short-03-stat`, 7 bloques). 2 vídeos instrumentados de 10.

**Tres cifras falsas corregidas por el camino:** el gap no era $420k sino **$429,985** ($609,985
final, 7% nominal capitalizado mensual, no ~$600k) · el café "$18,000 invertido" era en realidad
$18,250 **sin invertir** (invertido: **$26,323**) · las voces Default de ElevenLabs **caducan el
31-dic-2026**, y su plan gratis no da derechos comerciales.

**NO construir más motor antes de publicar** (`docs/POLITICA.md`, Regla 1). El motor de vídeo
configurable (SHORTS como datos + escenas) está diseñado y esperando; se extrae DESPUÉS del S3,
y las escenas del S4/S5 se construyen cuando toque producirlos.

## 10. Cómo arrancar el nuevo chat
*"Lee docs/ESTADO.md y CLAUDE.md. Vamos a producir el primer video (build-wealth, Short). Ayúdame
con [la animación de la curva / el guion final / lo que sea]."* — o corre `/daily` para ver si el
sistema propone algo nuevo. Recuerda: el único pendiente real es PRODUCIR Y PUBLICAR.
