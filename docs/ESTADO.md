# ESTADO DEL PROYECTO — documento de traspaso

> **Para el nuevo chat:** lee este archivo primero, luego `docs/VISION.md` (arquitectura
> congelada) y `docs/AUDIT.md` (auditoría). Con eso entiendes todo. Ruta del proyecto:
> `C:\Users\Asus\Desktop\Proyecto AI`. Es un repo git (rama `master`).

---

## 1. Qué es (en una frase)

Un **sistema de inteligencia + laboratorio creativo** para decidir qué contenido crear, con
datos, y convertirlo en ideas extraordinarias. **NO es un generador de video** — el video es el
primer producto. El activo real es el conocimiento calibrado que acumula con el tiempo.

## 2. Nicho decidido (IMPORTANTE)

- **Nicho: FINANZAS / INVERSIONES / CRYPTO**, faceless, audiencia en **INGLÉS**.
- Por qué: es el nicho **mejor pagado** (RPM $10-40 vs $1-4 de lo viral), y el usuario **conoce
  el tema** → cubre la barrera de precisión (YMYL) que la IA no puede.
- Caveats a recordar: el usuario **debe verificar cada dato** (la IA alucina; en finanzas eso
  desmonetiza); crypto paga más pero tiene más riesgo de políticas; disclaimers "no es consejo
  financiero"; menos vistas que lo viral pero mucho más $/vista + patrocinios + afiliados.
- `feeds.json` ya está apuntado a este nicho (Google News mercados/crypto/economía + Cointelegraph
  + CoinDesk + Yahoo Finance + MarketWatch + Reddit finanzas).

## 3. El reparto mental clave (léelo bien)

```
SISTEMA decide QUÉ (tema, desde datos)   ← el paso MÁS DÉBIL hoy
   +
TU CLAUDE piensa CÓMO (ángulo creativo)  ← aquí está el valor, a mano / $0
   +
SISTEMA acumula QUÉ FUNCIONA (calibración) ← el moat que compone
```

Para finanzas: **el usuario es experto**, así que puede poner el tema él mismo; el sistema aporta
la **creatividad** (`think`) y la **memoria calibrada** (`learnings`). No dependas de que el
sistema "adivine" el tema desde titulares — es su parte más floja.

## 4. Estado de dinero / LLM

- **Presupuesto ~$0.** El usuario NO tiene API key de Anthropic (de pago) todavía. La comprará
  **si ve que el sistema da buenas ideas** (criterio: `learnings` con tasas altas y distintas).
- **Modo actual = $0 manual con la cuenta de Claude del usuario:** el sistema arma el prompt,
  el usuario lo pega en SU Claude (claude.ai / Claude Code), Claude piensa, y el resultado se
  registra. Es human-in-the-loop legítimo.
- Cuando ponga `ANTHROPIC_API_KEY`, el `think` piensa solo (automático), sin cambiar nada más.
  Modelo por defecto: `claude-opus-4-8`. Adaptador en `omega/llm/` con tiers (fast=haiku,
  smart=opus-4-8, max=fable-5).

## 5. Qué está construido (todo en git, 61 tests verdes, $0)

**Kernel domain-agnostic** `omega/reasoning/` (puro, con test de pureza por AST):
- `store.py`: belief / belief_update / prediction + `update_belief()` (único mutador, exige causa)
  + `calibration()`. Reglas: "Every belief is a prediction" + "No Silent Learning".
- `signals.py`, `hypotheses.py`, `opportunities.py`, `decision_engine.py`, `decisions.py`
  (Decision Record + `explain()` explicable).

**Capa de dominio (contenido)** `omega/`:
- `sources/rss.py` (con user-agent de navegador), `extractors/` (theme v0.2 con bigramas,
  language, title_length + registro auto), `analyze/momentum.py` + `analyze/hypothesis_engine.py`.

**Laboratorio creativo** `omega/creative/`:
- `patterns.py` (Creative Knowledge Base = vocabulario de craft), `decisions.py` (decisiones
  justificadas + calibración multi-dimensional), `combinator.py` (divergencia), `reasoning_loop.py`
  (mejora medible + propose + should_stop), `production.py` (cuello de botella), `tradeoffs.py`,
  `questions.py` (pregunta→principio), `thinking.py` (orquestador; inerte sin LLM a propósito).

**Adaptador LLM** `omega/llm/` (Anthropic, tiers, degradación a $0).

**Comandos CLI** (`python -m omega.cli <cmd>`):
`ingest, trends, signals, decide, patterns, combine, think, record-think, record-outcome,
learnings, hypotheses, status`.

## 6. Flujo de trabajo $0 (el que usa el usuario) — también en README.md

```bash
python -m omega.cli ingest              # observar (correr a diario para baseline)
python -m omega.cli decide              # tema propuesto (o el usuario pone el suyo)
python -m omega.cli think "el tema"     # arma data/think_pack.txt (3 pasos)
#   -> el usuario pega el pack en SU Claude, responde
#   -> copia data/think_result.template.json a think_result.json, lo rellena
python -m omega.cli record-think        # registra la idea (justificada con tags del CKB)
# (produce y publica el video)
python -m omega.cli record-outcome <id> 0.85   # tras publicar, resultado medido 0..1
python -m omega.cli learnings           # qué patrones funcionan (el moat visible)
```

## 7. Limitaciones conocidas / deuda

- **El detector de temas (`decide`) es débil en dominios diversos** como finanzas: dio 'million'
  (palabra genérica) porque las noticias financieras son variadas, sin una frase dominante. El
  arreglo real: (a) correr `ingest` varios días para baseline, (b) **YouTube API** (vistas reales),
  (c) más adelante, clustering/embeddings. NO seguir puliendo el extractor a mano (rendimientos
  decrecientes).
- **El momentum necesita baseline** (varios días de `ingest`); con base recién reseteada, ABSTIENE
  correctamente.
- **Reddit rate-limita** los feeds RSS (devuelve 0 en varios); Google News y feeds nativos sí van.
- **Hook roto de un plugin** (`check-sql-files.py`) falla en cada Write/Edit — es INOFENSIVO,
  ignorar por completo.

## 8. Decisiones pendientes del usuario

1. **Key GRATIS de YouTube Data API** (console.cloud.google.com → YouTube Data API v3 → crear
   clave). Si la consigue → construir `omega/sources/youtube.py` (un archivo, sin tocar el resto):
   el sistema verá qué videos de finanzas consiguen **vistas reales** (el detector de temas serio).
   Es GRATIS y distinta de la de pago de Claude.
2. **`ANTHROPIC_API_KEY` de pago** → automatiza el `think`. Solo si el bucle manual demuestra valor.
3. **Correr `ingest` a diario** unos días para que el baseline dé señal.

## 9. Próximo paso inmediato (donde quedamos)

El usuario iba a **elegir un tema de finanzas/crypto** para que Claude (a mano) le devolviera un
**ángulo de video extraordinario** — demostrando el valor en su terreno, como se hizo antes con
"Prime Day" (ángulo: *"Prime Day visto por el algoritmo"*). Alternativa: sacar la key gratis de
YouTube y construir el plugin.

**Cómo arrancar el nuevo chat:** dile *"Lee docs/ESTADO.md y docs/VISION.md del proyecto en
Desktop/Proyecto AI y continúa desde ahí"*, y luego dale un tema de finanzas para el primer video,
o pídele que construya el plugin de YouTube si ya tienes la key gratis.
