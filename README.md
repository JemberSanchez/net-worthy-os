# Content Intelligence OS — "El Analista" (MVP)

Sistema de inteligencia para creación de contenido. **No es un generador de videos.**
Es un laboratorio que observa el mercado, detecta qué temas suben/bajan y propone
las mejores ideas respaldadas por evidencia.

## Principio rector (léelo antes de tocar nada)

> El sistema aprende observando el mercado **externo** (N grande: miles de publicaciones
> de terceros), **no** de tu propia producción (N diminuto: 2-3 videos/día).
>
> Tus videos no son el experimento que genera conocimiento — son la capa de
> **validación** que confirma o refuta hipótesis ya formadas observando a otros.

A 2-3 videos/día es estadísticamente imposible "aprender de tus resultados". Por eso
la inteligencia vive en la observación externa. No lo olvides al añadir features.

## Decisiones estratégicas tomadas

- **Plataforma primaria: YouTube** (mejor fuente de datos vía API gratuita + mejor techo
  de ingresos: largo +8min paga $2-10 RPM). Shorts = embudo de descubrimiento, no ingreso.
- **Distribución secundaria gratis:** un asset → cross-post a Facebook Reels y TikTok (+1min).
- **Formato:** sesga a +1min / largo. El video corto (42s) es el formato **peor pagado**
  en todas las plataformas; sirve para crecer audiencia, no para monetizar.
- **Presupuesto $0:** todo local (SQLite, RSS sin key, análisis stdlib). Se migra a
  Postgres/embeddings/API cuando entre dinero y volumen lo justifique.

## Arquitectura (estado actual)

```
RSS (sin key) ──► SQLite (observed_content) ──► momentum (alza/caída) ──► reporte + prompt
   [sources/]          [db.py]                     [analyze/]              [cli.py]
```

Diseñado para crecer sin reescribir: las fuentes son plugins (`sources/base.py`),
el almacenamiento está aislado (`db.py`), el análisis es reemplazable (`analyze/`).

## Uso

```bash
pip install -r requirements.txt

# Inteligencia / observación
python -m omega.cli ingest       # captura RSS -> SQLite. CORRE ESTO A DIARIO.
python -m omega.cli trends       # reporte de temas en alza/caída
python -m omega.cli signals      # extrae señales (extractores-plugin) de lo observado
python -m omega.cli decide       # Decision Record diario: 3 candidatos o ABSTENERSE (explicable)

# Director creativo
python -m omega.cli patterns     # Creative Knowledge Base (vocabulario de craft)
python -m omega.cli combine <s>  # divergencia: k encuadres distintos de un sujeto
python -m omega.cli think <s>    # el director PIENSA un sujeto (LLM si hay key; si no, modo $0)

python -m omega.cli status       # estado de la base de conocimiento
```

## Flujo de trabajo $0 (con tu cuenta de Claude, manual)

Sin API key, el sistema piensa con **tu** Claude (claude.ai / Claude Code) y acumula el
conocimiento igual que si fuera automático. Por cada video:

```bash
# 1. El sistema arma el "paquete de pensamiento"
python -m omega.cli think "tu tema"
#    -> data/think_pack.txt (3 pasos) + data/think_result.template.json

# 2. Pega data/think_pack.txt en tu Claude. Responde los 3 pasos.

# 3. Devuelve el resultado al sistema:
#    copia la plantilla a data/think_result.json, rellena "angle" y "pattern_tags", y:
python -m omega.cli record-think

# 4. Produce y publica el video con ese ángulo.

# 5. Tras publicar, registra cómo rindió (0..1):
python -m omega.cli record-outcome <id-del-video> 0.85

# 6. Mira si el sistema aprende de verdad:
python -m omega.cli learnings    # patrón de craft -> tasa de éxito real
```

**Cuándo comprar la API key:** si tras ~10-15 videos `learnings` muestra patrones con tasas
**altas y distintas entre sí**, el sistema aprende algo real → automatiza poniendo
`ANTHROPIC_API_KEY` (el mismo `think` empieza a pensar solo). Si las tasas son ruidosas/iguales,
aún no vale la pena pagar.

**Importante:** el momentum solo tiene señal real tras correr `ingest` varios días
seguidos (necesita baseline histórico). El día 1 todo "sube desde 0". Automatiza
`ingest` con el Programador de tareas de Windows (1-2 veces/día).

## Roadmap

- **Fase 1 — El Analista (ACTUAL):** observar externo → detectar tendencias → proponer.
- **Fase 1.5:** fuente YouTube Data API (key gratis) + Reddit API. Sustituir term-momentum
  por clustering semántico (TF-IDF, luego embeddings) → temas reales, no palabras sueltas.
- **Fase 2 — El Productor:** pipeline de generación (guión→voz→video) con proveedores
  intercambiables + panel de revisores LLM (storytelling, retención, riesgo de políticas).
- **Fase 3 — El Científico:** captura de métricas en el tiempo + calibración de revisores
  contra resultados reales + actualización bayesiana de hipótesis. Bucle cerrado.

## Deuda técnica conocida

- `term-momentum` cuenta palabras sueltas, no temas. Es un placeholder honesto; el salto
  a clusters semánticos es la Fase 1.5.
- Baseline vacío en arranque (inherente; se cura con uso diario).
- Pulido cosmético en el formato del reporte (prefijo `+` en momentum negativos).
