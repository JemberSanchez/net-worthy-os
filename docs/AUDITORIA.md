# AUDITORÍA DEL PROYECTO — juicio profesional (2026-07-15)

> Escrito para encontrar mejoras REALES, no para dar palmaditas. Si algo suena duro, es porque
> un profesional que quiere que esto funcione te lo diría a la cara.

## Veredicto en una línea

**Construimos un MOTOR potente y un CEREBRO dormido.** El sistema se diseñó para *decidir qué crear
por datos y acumular qué funciona* — y tras 3 videos publicados tiene **0 outcomes medidos**. Casi
todo el esfuerzo fue a producir videos más bonitos; casi nada a que el sistema APRENDA.

## Los hechos (medidos hoy, no de memoria)

| Métrica | Valor | Lectura |
|---|---|---|
| Shorts publicados | 3 (S3, S1, S2) | volumen bajísimo para juzgar nada |
| `production_dna` (instrumentados) | 3 | bien |
| **`production_analytics` (medidos)** | **0** | ⛔ el 'qué pasó' no se registra |
| **`production_outcome` (el MOAT)** | **0** | ⛔ el sistema no ha aprendido NADA |
| `production_cost` | 0 | sin coste = no hay "rendimiento por hora" |
| Suscriptores | 0 | cold-start puro |
| Vistas (Facebook) | S1 259 · S2 218 · S3 67 | S3 confundido por hora (02:00) |
| Interacciones | 1–3 por video | engagement ≈ nulo |
| Líneas del motor de video | 2.558 | grande, potente, **sin tests automáticos** |
| Commits recientes que son features del motor | ~16 de 18 | desbalance total hacia el motor |

## Evaluación — dos lentes

### A) Crecimiento / marketing (la lente que decide si esto vive)

1. **El loop de medición está ABIERTO. Es el fallo #1.** Todo el thesis del proyecto es "el moat se
   llena al medir". Hay datos de 3 videos y no se han registrado. Esto se ha diferido una semana
   mientras construíamos features. **Un profesional para de construir y cierra el loop HOY.**
2. **3 videos no es nada.** La viralidad en un canal de 0 subs necesita **volumen** (10–30+ videos)
   y consistencia, no perfeccionar el 4º. Estamos optimizando la pieza equivocada.
3. **Cadencia rota.** Publicado 07-10, 11, 12… y hueco hasta hoy 15. El algoritmo premia consistencia.
   Sin un horario fijo diario, cada video arranca de cero.
4. **Distribución de un solo carril.** YouTube Shorts + FB Reels. **Falta TikTok** (enorme en
   finanzas) e **Instagram Reels**. Cross-postear multiplica los "at-bats" sin coste extra.
5. **Engagement casi nulo (1–3).** Los CTA "tell me below" no generan comentarios → el algoritmo no
   tiene señal que amplificar. Mejora: CTAs binarios/opinables ("team rent o team buy?").
6. **Hipótesis de estilo sin probar.** El estilo texto-sobre-verde, sin b-roll, sin caras, voz TTS,
   es distintivo pero pelea cuesta arriba contra el contenido sensorial del feed. No es un veredicto
   — es una hipótesis que SOLO se resuelve con volumen + medición.

### B) Ingeniería (donde SOBRE-invertimos)

1. **Over-engineering por delante de la evidencia.** Compositor multi-escena, 11 escenas, modo Video
   8-15 min, export streaming, audio procedural, calibrador adaptativo — todo para un canal con 3
   videos y 0 outcomes. Es montar la fábrica antes de validar el producto. El **long-form** sobre
   todo: capacidad que nadie ve todavía (0 subs) — el error exacto que `POLITICA.md` existe para evitar.
2. **El motor no tiene tests.** 92 tests cubren el kernel/omega en Python, pero `short-renderer.html`
   (2.558 líneas, todo el trabajo reciente) se verifica **a mano**. Es una deuda real: un cambio
   puede romper un Short y no lo caza nada automático.
3. **`decide` da ruido.** El top-1 sale como nombres de fuente ("cryptonews net") — bug del extractor
   de temas. La capacidad estrella ("el sistema elige el tema") es hoy **poco fiable**; por eso elegí
   el tema a mano con el youtube-scan. Falta un stoplist.
4. **El cerebro no gira.** El value-prop del sistema (acumular qué funciona) está inerte por dos
   cosas: (a) `decide` ruidoso, (b) 0 outcomes. Sin esas dos, `dna`/`patterns` no dicen nada.
5. **Calibrador: sync fino pendiente.** Los cortes de escena cuadran con la voz; los BEATS internos
   (checks, bullets) van en horario, no por palabra. Es la desincronía que se siente.

## El diagnóstico de fondo

Llevamos sesiones preguntando *"¿cómo hacemos el motor más creativo?"* cuando la pregunta real es
**"¿cómo hacemos que el SISTEMA APRENDA más rápido?"** — y eso está bloqueado por no medir, no por
ninguna feature que falte. El motor ya es más que suficiente para 20 videos. Lo que falta es el bucle:
**publicar → medir → `dna`/`patterns` → decidir el siguiente por evidencia.**

## Mejoras REALES, priorizadas (impacto ÷ esfuerzo)

1. **CERRAR EL LOOP (hoy, ~15 min).** `record-analytics` + `record-cost` + `record-outcome` de los 3
   publicados con los números de Facebook (y de YouTube Studio si hay). Sin esto, todo lo demás es a
   ciegas. **Es la mejora #1 y la más barata.**
2. **VOLUMEN + CADENCIA.** Comprometerse a 1 Short/día a la MISMA hora de mañana, 2–3 semanas. El
   motor ya lo permite. Es lo único que rompe un cold-start.
3. **DISTRIBUCIÓN.** Subir el MISMO MP4 también a TikTok e Instagram Reels. 3× los at-bats, coste ~0.
4. **Arreglar `decide`** (stoplist de nombres de fuente) → que el sistema vuelva a elegir tema.
5. **CTAs que generen comentario** (binarios/polémicos) → señal de engagement para el algoritmo.
6. **Sync por palabra** en checklist/bullets (usar los tiempos que el calibrador ya calcula).
7. **Tests del motor** (pureza + hash de frames clave headless) — deuda técnica creciente.

## Lo que deberíamos DEJAR de hacer

- **Parar de construir features del motor por delante de la evidencia** — especialmente el long-form.
  Ya está diseñado y probado; se retoma cuando haya audiencia que lo vea, no antes.
- Dejar de perfeccionar el video N+1 antes de medir los N ya publicados.

## Cómo funciona el sistema (para retomar sin contexto)

- **Cerebro (`omega/`):** ingesta RSS + escaneo de demanda YouTube → señales → `decide` (tema por
  demanda+RPM). Registro del ADN de cada video, sus analíticas medidas y su outcome (0..1). Con ≥10
  medidos, `dna`/`patterns` calibran qué gancho/tema/estilo retiene. Kernel de razonamiento
  domain-agnostic con test de pureza por AST. Tests: `python -m unittest discover -s tests -q`.
- **Motor de video (`docs/guiones/short-renderer.html`):** un HTML sin dependencias. Dual-modo
  (Short 9:16 / Video 16:9). Un Short = una escena base + overlays cronometrados; un Video = timeline
  de segmentos. 11 escenas componibles (gancho, columns, checklist, principle, stat, bullets, cita,
  capítulo, titulo, outro, chart). Calibrador que alinea los cortes a la voz por energía + sílabas.
  Export MP4 (H.264 24 Mbps + AAC) con diseño de sonido procedural opcional (`sfx:true`); long-form
  por streaming a disco (OPFS) sin techo de RAM. `drawFrame(t)` es PURA (el export re-renderiza
  offline). Verificación: canvas → POST a mini-servidor → mirar los frames (el screenshot del panel
  falla).
- **Producción de un Short:** tema (por datos) → guion (frases completas para el TTS, ≤500 chars/bloque
  CapCut) → voz Firme Pilot → cargar en el motor (calibra solo) → previsualizar → Grabar MP4 → subir
  a la misma hora → **medir a las 48h** → registrar. Runbooks: `docs/guiones/PRODUCCION-S1.md`,
  guiones en `shorts-pack-01.md`, arquitectura en `docs/ARQUITECTURA-MULTIESCENA.md`.
