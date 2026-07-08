# ESTADO DEL PROYECTO — documento de traspaso

> **Para el nuevo chat:** lee este archivo primero, luego `docs/VISION.md` (arquitectura
> congelada) y `docs/AUDIT.md` (auditoría). Con eso entiendes todo. Ruta del proyecto:
> `C:\Users\Asus\Desktop\Proyecto AI`. Es un repo git (rama `master`).
>
> Hay **memoria de proyecto** en `~/.claude/projects/.../memory/` (índice en `MEMORY.md`).
> El próximo Claude la lee sola: contiene principios de trabajo ya acordados con el usuario.

---

## 1. Qué es (en una frase)

Un **sistema de inteligencia + laboratorio creativo** para decidir qué contenido crear, con
datos, y convertirlo en ideas extraordinarias. **NO es un generador de video** — el video es el
primer producto. El activo real es el conocimiento calibrado que acumula con el tiempo.

## 2. Nicho decidido

- **FINANZAS / INVERSIONES / CRYPTO**, faceless, audiencia en **INGLÉS** (RPM $10-40 vs $0.5-2 de
  mercados de bajo CPM). El usuario conoce el tema → cubre la barrera de precisión (YMYL).
- Caveats: el usuario **verifica cada dato** (la IA alucina; en finanzas eso desmonetiza);
  disclaimers "no es consejo financiero".
- `feeds.json` apuntado al nicho. Las **queries del nicho para YouTube** están en
  `config.YOUTUBE_NICHE_QUERIES` (framings de narrativa/entidad/evento, NO de categoría/stream).

## 3. El reparto mental clave (LO MÁS IMPORTANTE — el usuario lo reforzó esta sesión)

```
SISTEMA decide QUÉ (tema, desde demanda real)   ← ya arreglado (antes era el paso débil)
   +
TU CLAUDE piensa CÓMO (ángulo estructurado)     ← AQUÍ está el valor, a mano / $0
   +
SISTEMA acumula QUÉ FUNCIONA (calibración)      ← el moat que compone (AÚN VACÍO)
```

**Regla dura (guardada en memoria, `raw-term-is-que-not-video`):** un término que saca el
detector ("spacex ipo") es una **señal de demanda, NO un video**. Por sí solo es mala idea.
SIEMPRE convertirlo en un **catch-up explainer estructurado** (hook → qué cambió → datos →
alcista → riesgo → "y a mí qué" → cierre) + aviso YMYL. El sistema da el QUÉ; el CÓMO lo cocinas.

## 4. Estado de dinero / LLM

- **Presupuesto ~$0.** No hay `ANTHROPIC_API_KEY` (de pago) todavía. Se compra **si `learnings`
  muestra tasas altas y distintas** tras publicar varios videos.
- **YA HAY `YOUTUBE_API_KEY`** (gratis, en `.env`, gitignored). Cuota 10.000/día. Funciona.
- **Modo actual = $0 manual:** `think` arma un prompt, el usuario lo pega en SU Claude, y el
  resultado se registra con `record-think`. Con `ANTHROPIC_API_KEY`, `think` piensa solo.

## 5. Qué está construido (todo en git, **77 tests verdes**, $0)

**Kernel domain-agnostic** `omega/reasoning/` (puro, test de pureza por AST):
- beliefs/predictions (`store.py`, único mutador `update_belief`), signals, hypotheses,
  opportunities, `decision_engine.py` (score = confianza + Σ peso·feature; el kernel NO conoce el
  significado de las features), `decisions.py` (Decision Record explicable).

**Capa de dominio (contenido)** `omega/`:
- `sources/rss.py` (12 feeds, user-agent navegador), **`sources/youtube.py`** (YouTube Data API v3
  con solo stdlib + **filtro de idioma duro solo-EN**), `extractors/` (theme v0.2 con bigramas),
  `analyze/momentum.py` (presencia RSS), **`analyze/demand.py`** (demanda por vistas + adyacencia),
  `analyze/hypothesis_engine.py` (genera candidatas de DOS orígenes).

**⭐ La capa nueva de esta sesión — DEMANDA REAL de YouTube (el gran salto):**
El detector de temas pasó de contar titulares a medir **vistas reales**. `decide` ahora pondera
**cuatro señales de audiencia** (todas medidas, cero ficción del "Viral Engine" muerto):
- `demand` — vistas totales (cuánta atención mueve).
- `gap` (#3) — vistas por video: mucha demanda + poca oferta = **desatendido** = oportunidad.
- `demand_momentum` (#2) — cambio de demanda entre escaneos: **subiendo = emergente** (adelantarse).
- (adyacencia #1, `related`) — qué MÁS ve esa audiencia (co-ocurrencia); input a la creatividad.
Además, YouTube **ORIGINA temas** (frases específicas de alta demanda) aunque RSS no las levante.

**Laboratorio creativo** `omega/creative/`: patterns (CKB), decisions+calibración, combinator,
reasoning_loop, production, questions, experiments, thinking (orquestador; inerte sin LLM).

**Adaptador LLM** `omega/llm/` (Anthropic, tiers, degradación a $0).

## 6. Comandos CLI (`python -m omega.cli <cmd>`)

`ingest` · `trends` · **`youtube <query>`** · **`youtube-scan`** (barre nicho→cachea demanda) ·
**`related <tema>`** (adyacencia) · `signals` · `decide` · `patterns` · `combine` · `think` ·
`record-think` · `record-outcome` · `learnings` · `hypotheses` · `status`.

## 7. Flujo de trabajo $0 (el que usa el usuario)

```bash
python -m omega.cli ingest              # RSS a diario (baseline de presencia)
python -m omega.cli youtube-scan        # demanda real de YouTube a diario (baseline de demanda)
python -m omega.cli decide              # tema propuesto por demanda real (o el usuario pone el suyo)
python -m omega.cli related "el tema"   # opcional: qué más ve esa audiencia (adyacencia)
python -m omega.cli think "el tema ESTRUCTURADO como CÓMO"   # arma data/think_pack.txt
#   -> pega el pack en TU Claude, responde -> rellena data/think_result.json -> record-think
python -m omega.cli record-think
# (produce y publica el video)
python -m omega.cli record-outcome <id> 0.85
python -m omega.cli learnings           # qué patrones funcionan (el moat visible)
```

## 8. Dónde está MÁS FLOJO / qué mejorar (leer antes de decidir el próximo paso)

1. **EL BUCLE NUNCA SE HA CERRADO.** Cero videos publicados → cero `record-outcome` → `learnings`
   VACÍO → **el moat (memoria calibrada) NO EXISTE aún**. Todo lo construido es el motor; falta el
   combustible, que solo llega **publicando**. Es, con diferencia, lo más flojo. Hay 2 ideas ya
   registradas sin resultado (`strategy-btc-sale-noir-...`, `spacex-30-days-public-explainer-...`).
2. **`demand_momentum` necesita escaneos separados en DÍAS.** Back-to-back mezcla subida real con
   variación de muestreo (capado a [-2,2] para que no dispare el score). Hay que correr
   `youtube-scan` a diario (Programador de tareas de Windows) para que dé señal de tendencia limpia.
3. **`think` es inerte a $0** (necesita que el usuario pegue el prompt, o API key). El CÓMO
   depende de un humano en el bucle.
4. **No existe la Capa 2 (producción):** guion/shotlist/hooks/título/miniatura/render. Nada.
5. **Extractores v0:** `gap` (vistas/video) es un proxy honesto de "desabastecido"; theme sigue
   siendo bigramas, no clustering semántico. Mejora futura: embeddings (Fase 1.5), NO pulir a mano.
6. **Predicción de hipótesis originada-por-demanda dice "momentum de presencia"** aunque nació de
   demanda; debería verificar crecimiento de DEMANDA. Deuda menor anotada.
7. **Sin comentarios de YouTube** (sensor de máxima señal según VISION) ni job que verifique
   predicciones a los 14 días.

## 9. Decisiones pendientes del usuario

1. **Automatizar `ingest` + `youtube-scan` a diario** (Programador de Windows) → baselines con señal.
2. **Cerrar UN bucle de punta a punta** (producir + publicar + `record-outcome`) → primera gota
   del moat. **Es el paso que convierte "arquitectura bonita" en "sistema que aprende".**
3. `ANTHROPIC_API_KEY` de pago → automatiza `think`. Solo si el bucle manual demuestra valor.

## 10. Dónde quedamos (última sesión)

Se construyó toda la capa de **demanda real de YouTube** (8 commits): la fuente, el filtro de
idioma, las queries afinadas, y las **3 mecánicas de "adelantarse"** (gap/momentum/adyacencia).
El detector pasó de dar tokens genéricos ('million') a temas de demanda real emergente. El usuario
aportó el principio clave (término crudo = QUÉ, no video) que quedó en memoria, y se registró la
idea de SpaceX estructurada. **Próximo paso natural: producir el primer video y cerrar el bucle**
(punto 8.1 / 9.2), que es lo único que falta para que el sistema empiece a aprender de verdad.
