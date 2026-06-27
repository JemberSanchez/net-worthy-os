# OMEGA / CIOS — Auditoría de arquitectura y visión

> Auditoría crítica solicitada. Objetivo: encontrar errores, matar sobreingeniería,
> separar lo que es ventaja competitiva real de lo que es fantasía o commodity.
> No es complaciente a propósito.

---

## 0. Veredicto ejecutivo (la verdad incómoda)

Tu visión mezcla **dos productos distintos** bajo un mismo nombre:

1. **Un sistema de inteligencia** (Knowledge + Trend + Decision). Este SÍ es un activo
   difícil de replicar — pero madura **lento** y su moat es el conocimiento acumulado,
   no el código.
2. **Una fábrica de video** (Generation). Esto es **commodity**: todos usan las mismas
   APIs de IA. No hay moat aquí. Cero.

**El error fatal que se repite en toda la especificación:** quieres *aprender,
experimentar, simular y predecir* a partir de **tus propios 2-3 videos/día**. Eso es
**estadísticamente imposible** (lo establecimos: N≈90/mes contra varianza de power-law
y decenas de variables confundidas). El **Simulation Engine**, el **Experiment Engine**,
la estimación de **ROI** y el **bucle de aprendizaje sobre tu output** heredan todos ese
defecto. Producirán **números con apariencia de evidencia que en realidad son ficción**.

Y eso es **peor que no tener sistema**: corrompe tu premisa "basada en evidencia" con
evidencia falsa. Un score de "retención: 7.4/10" generado por un LLM sobre un video que
nadie ha visto no es una medición — es una alucinación con decimales.

**El moat real son exactamente tres cosas:**
- **Knowledge Engine** — conocimiento estructurado que se acumula y compone con el tiempo.
- **Trend lifecycle** — detectar nacimiento→saturación→declive sobre datos externos (N grande).
- **Decision Engine con disciplina de abstención** — saber decir "hoy no hay evidencia".

Todo lo demás es commodity (generación) o prematuro (simulación, experimentos, ML pesado).

---

## 1. Errores y falsas expectativas

| # | Error | Por qué es un problema | Veredicto |
|---|-------|------------------------|-----------|
| 1 | **Simulation Engine** predice retención/CTR antes de generar | No tienes datos de entrenamiento y nunca los tendrás a 2-3/día. Ni los grandes estudios predicen esto. Da falsa confianza. | **MATAR** (o degradar a checklist cualitativo SIN números) |
| 2 | **Experiment Engine** (Hook A/B, Narrador A/B) sobre tu output | Para detectar diferencia de CTR contra el ruido del algoritmo necesitas cientos de ensayos por brazo. Produces 90/mes. Muerto al nacer. | **REFORMULAR**: experimentos sobre datos EXTERNOS (N grande), no propios |
| 3 | **ROI esperado** en Cost Intelligence | Estimar ROI exige predecir ingresos = predecir rendimiento = la fantasía del #1. | **MATAR el ROI**, mantener solo coste real |
| 4 | **Psychology Engine** como motor causal "emoción → rendimiento" | Etiquetas emocionales de un LLM son subjetivas; la relación es correlación confundida, no causa. | **DEGRADAR** a etiquetado descriptivo |
| 5 | **11 agentes** especializados | Son el mismo LLM con prompts distintos: opiniones correlacionadas, no independientes. 11× coste, 11× latencia, 0 garantía de mejor juicio. | **FUSIONAR a 4** |
| 6 | "El mejor sistema del mundo / difícil de replicar" vía generación | La generación es commodity. El moat es el conocimiento, y madura lento. | **Recalibrar expectativa** |
| 7 | Bucle "aprender de resultados" como motor central temprano | Estará casi mudo durante meses (N pequeño). No es el motor; es calibración lenta. | **Mover a Fase 5**, expectativa realista |

---

## 2. Sobreingeniería a eliminar (triage de los 14 "engines")

| "Engine" | Decisión | Justificación |
|----------|----------|---------------|
| Knowledge Engine | **KEEP** (núcleo) | El activo real. Conocimiento que se compone. |
| Trend Engine | **KEEP** (núcleo) | Lifecycle sobre datos externos = predicción validable con N grande. |
| Comment Engine | **KEEP** (alto valor) | Comentarios de YouTube SÍ son accesibles por API. Señal de demanda insatisfecha. |
| Decision Engine | **KEEP** (núcleo) | La disciplina de abstención es lo que de verdad te diferencia. |
| Hypothesis Engine | **SIMPLIFICAR** | No es un "engine": es una estructura de datos + un prompt. |
| Quality Gate | **KEEP** | Barato y sensato: un umbral sobre los scores de revisores. |
| Generation Engine | **KEEP como ADAPTER** | Commodity, reemplazable, se construye **el último**. |
| Multi-Agent Review | **FUSIONAR 11→4** | Estrategia/Marketing · Creativo/Guion · Originalidad+Políticas (con veto) · Técnico. |
| Memory | **FUSIONAR** | = Knowledge + un log append-only de eventos. No es componente aparte. |
| Observability | **KEEP transversal** | Log de decisiones append-only = trazabilidad gratis. No es un "engine". |
| Cost Intelligence | **PARCIAL** | Estimar coste (tokens/GPU) = real, útil. Estimar ROI = ficción, fuera. |
| Psychology Engine | **DEGRADAR** | A feature de etiquetado dentro de Análisis. |
| Experiment Engine | **DIFERIR (Fase 5)** | Y reformulado a datos externos. |
| Simulation Engine | **MATAR** | La eliminación más importante de toda la auditoría. |

**De 14 "engines" → 5 capacidades reales:** Ingesta · Análisis (con sub-módulos) ·
Knowledge · Decisión · Generación (adapter). Lo demás son features o capas transversales.

---

## 3. Limitaciones técnicas (obtenible vs estimable — lo pediste explícito)

El gran malentendido: **las APIs te dan METADATOS, no los bytes del video.** Analizar
"cantidad de cortes", "ritmo" o "tipo de música" exige **descargar el video** y correr
visión por computador — lo cual es caro y, a escala, viola los ToS de casi todas las plataformas.

| Señal que quieres analizar | ¿Obtenible legalmente? | Realidad |
|----------------------------|------------------------|----------|
| Título, descripción, hashtags, duración, vistas, likes | ✅ Obtenible | YouTube/Reddit API |
| **Comentarios** | ✅ Obtenible (YouTube) | Esto habilita el Comment Engine. Real. |
| Miniatura (colores, texto, caras) | ✅ Obtenible | El thumbnail es una URL pública → CV barato sobre la imagen |
| Hook (primeros segundos) | ⚠️ Estimable | Requiere el video; a veces inferible del título/transcripción |
| Cortes, ritmo, edición | ❌ Mayormente no | Requiere el archivo de video + CV. No viable a escala/ToS |
| Tipo de voz, música | ❌ Mayormente no | Requiere audio del video |
| Emociones | ⚠️ Estimable (texto/thumbnail) | Inferencia de LLM, etiquétalo como estimación con incertidumbre |

**Otra limitación honesta:** la **consistencia de personajes** entre escenas generadas por
IA sigue siendo un problema no resuelto (los modelos derivan). No prometas personajes
perfectamente consistentes; es un riesgo de calidad real en la Fase 4.

---

## 4. Limitaciones legales y de APIs

| Fuente | Acceso real | Nota |
|--------|-------------|------|
| **YouTube** | ✅ Data API v3 (gratis, cuota limitada) | Metadatos + stats públicas + **comentarios** + thumbnails. Tu mejor fuente. |
| **Reddit** | ⚠️ API de pago (tier gratis limitado) | Buen termómetro de narrativas. |
| **Google Trends** | ⚠️ No oficial / proxy de pago | Validación macro. |
| **Noticias/RSS/Blogs/Foros** | ✅ Libre | Señal temprana de temas. |
| **X (Twitter)** | ❌ API cara/restringida | Fuera del MVP. |
| **Pinterest** | ⚠️ API limitada | Marginal. |
| **TikTok** | ❌ Sin API pública de descubrimiento | Solo datos licenciados de terceros (de pago). |
| **Instagram / Facebook** | ❌ Graph API solo tus cuentas | Descubrimiento público cerrado. No prometer. |

**Conjunto realista del MVP:** YouTube (incl. comentarios) + Reddit + RSS/Noticias.
TikTok/IG/FB entran solo como **destino de publicación** (cross-post), no como fuente.

---

## 5. Qué módulos son ventaja competitiva real

| Módulo | ¿Moat? | Por qué |
|--------|--------|---------|
| **Knowledge Engine** | ✅✅✅ | Conocimiento estructurado y validado que se acumula. Difícil de replicar **con el tiempo**. El activo central. |
| **Trend lifecycle** | ✅✅ | Detectar saturación/declive antes que otros, sobre N grande externo. Validable científicamente. |
| **Decision Engine (abstención)** | ✅✅ | Disciplina de "hoy no". Casi nadie la tiene. Diferenciador conductual. |
| **Comment mining** | ✅ | Demanda insatisfecha directa de la audiencia. Barato y feasible en YouTube. |
| Generation | ❌ | Commodity total. |
| Simulation / Experiment (propio) | ❌ | Ficción a tu escala. |

**Insight clave:** el único sitio donde tienes N grande para *validar predicciones desde
el día 1* es el **contenido externo**, no tus videos. El sistema gana credibilidad
científica prediciendo la **trayectoria del mercado** (p. ej. "este tema saturará en 30
días") y verificándolo después con N grande — **antes de publicar un solo video propio**.
Ese es tu verdadero "Experiment Engine".

---

## 6. Arquitectura propuesta (evolutiva, no enorme)

Monolito modular (rechazo microservicios a esta escala). Fronteras internas estrictas.

```
FUENTES (plugins)            YouTube · Reddit · RSS · (comentarios YT)
      │  eventos "content.observed"
      ▼
OBSERVED STORE               SQLite ahora → Postgres+pgvector cuando haya $/volumen
      │
      ▼
ANÁLISIS (plugins)           trend-lifecycle · comment-mining · thumbnail-CV ·
      │                       emotion-tag (estimación) · clustering semántico
      ▼
KNOWLEDGE ENGINE             grafo: temas·hooks·narrativas·competidores·hipótesis·
      │                       aprendizajes + niveles de confianza
      ▼
DECISION ENGINE              produce DECISION RECORD:
      │                       · 3 candidatos rankeados, cada uno responde las 8
      │                         preguntas "¿por qué?" con nivel de evidencia
      │                       · o "ABSTENERSE: evidencia insuficiente"
      ▼  [GATE humano]
GENERATION (adapter)         guion→storyboard→voz→imagen→video... proveedor intercambiable
      ▼
REVIEWER PANEL (4)           Estrategia/Mkt · Creativo/Guion · Originalidad+Políticas(veto) · Técnico
      ▼
QUALITY GATE                 umbral configurable → iterar o descartar
      ▼
PUBLICACIÓN + TELEMETRÍA      captura métricas en el tiempo
      └──────► calibración LENTA de vuelta al Knowledge (Fase 5)

TRANSVERSAL: Append-only DECISION LOG  → observabilidad + trazabilidad + "memoria" en uno.
            Toda decisión se reconstruye desde el log. Cero caja negra, cero coste extra.
```

El **log de decisiones append-only** satisface de un golpe tres de tus requisitos
(Memory, Observability, "cada decisión reconstruible") sin tres componentes separados.

---

## 7. MVP en pocas semanas — "El Decididor"

Construye sobre lo que ya existe ("El Analista": ingesta RSS + momentum). El MVP automatiza
**la decisión**, no la creación — que es tu principio fundamental.

- **Entrada:** YouTube API (+ comentarios) + Reddit + RSS.
- **Proceso:** trend-lifecycle + comment-mining + knowledge graph mínimo.
- **Salida diaria:** un **Decision Record**:
  - **3 candidatos** rankeados; cada uno responde *por qué este tema / por qué ahora /
    por qué este formato / duración / emoción / plataforma*, **con evidencia y nivel de
    confianza, distinguiendo dato de hipótesis**.
  - o **"ABSTENERSE hoy"** con su justificación.
- **Generación:** manual por ahora (tú la ejecutas). Cero acoplamiento.

Esto entrega tu visión central — *automatizar decisiones basadas en evidencia* — en semanas,
sin tocar la parte commodity.

---

## 8. Métricas de éxito por fase (falsables, anti-vanidad)

**Regla:** en fases tempranas PROHIBIDO medir éxito por vistas/viralidad (no las controlas
y N es diminuto). Se mide **calidad de decisión** y **validez predictiva sobre datos externos**.

| Fase | Objetivo | Métrica de éxito (falsable) |
|------|----------|------------------------------|
| **0 — Validación** | ¿La idea sirve? | Un experto humano juzga el Decision Record "razonable" ≥70% de los días; el sistema **abstiene correctamente** en días pobres |
| **1 — MVP "El Decididor"** | Decisiones trazables | % de decisiones con evidencia reconstruible desde el log; **test ciego: las elecciones del sistema ≥ tus elecciones por intuición** |
| **2 — Inteligencia** | Trend lifecycle | **Precisión out-of-sample**: ¿los temas marcados "en declive" realmente cayeron en 30 días? (medible con N grande) |
| **3 — Experimentación (externa)** | Validez predictiva | % de predicciones de trayectoria de mercado acertadas vs baseline |
| **4 — Generación** | Eficiencia | Coste/asset · tasa de aprobación del panel · tiempo-a-asset · consistencia de personajes |
| **5 — Aprendizaje** | Cerrar el bucle | **Calibración** de scores de revisores vs rendimiento real · tasa de confirmación de hipótesis |
| **6 — Escala** | Operación | Coste/decisión · latencia · uptime |

---

## 9. Riesgo conductual (sombrero de Psicólogo)

El mayor fallo no es técnico — eres **tú confiando en un número con apariencia de
certeza**. Diseña *contra* la falsa confianza:
- Mostrar **siempre** el nivel de evidencia y la incertidumbre junto a cada afirmación.
- Hacer de **"ABSTENERSE" una salida de primera clase**, celebrada, no un fallo.
- Prohibir que el sistema muestre métricas predichas como si fueran medidas.

---

## 10. Plan de implementación (solo tras validar la arquitectura)

Condicional a tu visto bueno de las secciones 1-9.

- **Fase 1 (semanas):** YouTube API + comentarios → Observed Store → trend-lifecycle +
  comment-mining → Decision Record. (Extiende "El Analista".)
- **Fase 2:** Knowledge graph + validación out-of-sample de tendencias.
- **Fase 3:** motor de predicción de trayectoria de mercado (tu "experimento" real).
- **Fase 4:** Generation adapter + panel de 4 revisores + Quality Gate.
- **Fase 5:** telemetría + calibración lenta.
- **Fase 6:** migración a Postgres/colas/escala solo cuando los datos lo exijan.
```
```
