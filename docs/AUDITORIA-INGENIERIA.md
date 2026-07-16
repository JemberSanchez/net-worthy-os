# AUDITORÍA DE INGENIERÍA TOTAL — revisión de nivel mundial (2026-07-15)

> Lente: Principal Engineer + Architect + Reliability + Security. Mandato: cuestionarlo TODO,
> sin apego a ninguna decisión previa; optimizar para años, no para hoy. Complementa a
> `docs/AUDITORIA.md` (07-15, lente producto/crecimiento); esta es la lente de ingeniería.

## Veredicto arquitectónico en una línea

**La arquitectura es correcta y no debe "evolucionar" — debe protegerse.** La forma
(cerebro Python por capas + motor HTML sin dependencias, acoplados solo por archivos) es la
adecuada para una operación unipersonal, y las alternativas "modernas" (microservicios, framework
web, Postgres, colas) serían peores hoy. El riesgo existencial del proyecto NO está en el código:
está en que **el activo completo vive en un solo disco sin redundancia**, y en dos loops que no
cierran. Eso es lo que arregla esta auditoría.

## El modelo mental (lo que se auditó)

```
feeds.json (12 RSS)      YouTube API
      │                       │
   sources/rss ─────── sources/youtube          [captura]
      │                       │
   omega.sqlite (observed_content, theme_demand, scanned_video)
      │                       │
   extractors/* ──► signals   analyze/demand + momentum + monetization
      │                       │
   analyze/hypothesis_engine (dominio: interpreta señales)
      │
   reasoning/* (KERNEL domain-agnostic, pureza por AST:
     beliefs + predictions falsables + decision_engine + abstención)
      │
   creative/* (CKB patterns, decisiones justificadas, DNA+analytics+outcome = EL MOAT)
      │
   cli.py (19 comandos, dispatch a mano, stdlib pura)

   docs/guiones/short-renderer.html (2.558 líneas, motor de video CONGELADO,
     acoplado al cerebro SOLO por archivos: data/voz-*.mp3 + JSONs)
```

Dependencias externas de runtime: **solo `feedparser`** (+ `anthropic` opcional). Eso es una
fortaleza inusual: cero superficie de supply-chain, cero build, arranca en cualquier máquina.

---

## HALLAZGOS (ordenados por severidad real, no por elegancia)

### 1. ⛔ CRÍTICO — El moat no tiene redundancia (pérdida total posible)
- **Estado actual:** `data/` está gitignored (correcto: privacidad + tamaño) y contiene TODO el
  activo: `omega.sqlite` (19 MB: outcomes, DNA, contexto, beliefs), las 4 voces MP3
  (irreemplazables: CapCut no reproduce la misma toma) y los JSONs de instrumentación. Único
  "backup": un `.bak` del 08-07, ANTERIOR a todo lo importante.
- **Problema/causa raíz:** el proyecto define su valor como "el dataset es el moat" y el moat
  tiene redundancia CERO. Nadie diseñó la persistencia como parte del sistema.
- **Consecuencia si no se corrige:** un fallo de disco/robo/ransomware borra el proyecto entero.
  Probabilidad baja por día, certeza a años vista — y optimizamos para años.
- **Solución:** comando `backup` de primera clase (snapshot consistente del SQLite vía API de
  backup + zip con MP3s/JSONs, con fecha) + copia manual a nube/USB. **Implementado hoy.**
- **Riesgo del cambio:** ninguno (solo lee). **Complejidad:** baja. **Prioridad: #1.**

### 2. ⛔ CRÍTICO — El código no tiene remote (`git remote -v` vacío)
- **Estado:** rama `master`, 60+ commits, un solo disco.
- **Solución:** repo privado (GitHub/GitLab) + `git push`. **Requiere una acción del usuario**
  (crear el repo/autenticarse); el sistema no puede ni debe hacerlo solo.
- **Prioridad: #1-bis.** 5 minutos de trabajo humano.

### 3. 🔴 ALTO (seguridad) — El servidor estático expone el repo a la LAN
- **Estado:** `.claude/launch.json` lanza `python -m http.server 8765`, que **escucha en
  0.0.0.0**: cualquier dispositivo de la red ve el repo entero, incluido `data/` (voces, DB).
- **Causa raíz:** default inseguro de `http.server`, nunca revisado.
- **Solución:** `--bind 127.0.0.1`. **Implementado hoy.** Riesgo: cero (el motor se usa local).

### 4. 🔴 ALTO (correctitud del cerebro) — El ciclo epistémico no cierra
- **Estado:** cada `decide` crea una predicción falsable a 14 días. `store.due_predictions()`
  existe y está testeado… **pero ningún comando del CLI las muestra ni las resuelve.** El propio
  docstring del kernel llama a esto "el fallo nº1: predicciones que nunca se comprueban". Hoy
  hay predicciones vencidas invisibles acumulándose con cada `decide` diario.
- **Causa raíz:** se construyó el aparato de calibración (bandas de confianza, log de creencias)
  y se olvidó el asa operativa. Mismo patrón que el loop de medición que cerró hoy la mañana:
  instrumento sin rutina de lectura.
- **Consecuencia:** la promesa central del kernel ("¿cuando decimos 70% acertamos 70%?") es
  inevaluable; deuda epistémica invisible crece sin límite.
- **Solución:** `status` muestra predicciones vencidas; nuevo comando
  `resolve-prediction <id> <confirmed|refuted|inconclusive> [nota]`. **Implementado hoy.**
- **Riesgo:** bajo (usa APIs del kernel ya testeadas). **Complejidad:** baja.

### 5. 🟠 MEDIO (calidad de señal) — Ruido de nombres de canal en la demanda
- **Estado:** la queja de la auditoría 07-15 ("cryptonews net" ganando `decide`) HOY no se
  reproduce — el rediseño de queries la mitigó y el `decide` actual da un top limpio
  ("housing market", con Buffett/Warsh de suplentes). Pero la causa raíz sigue: un canal que
  pone su nombre en sus títulos convierte su marca en "tema de demanda" (el guard `n>=2 videos`
  no protege: un mismo canal aporta N videos).
- **Solución de raíz (no stoplist manual, que es deuda de mantenimiento):** el escaneo YA conoce
  el canal de cada video → filtrar en origen los términos derivados del nombre del propio canal.
  **Implementado hoy** en `demand.theme_demand` + test.
- **Riesgo:** bajísimo — solo suprime el término para los videos del canal homónimo; si otros
  canales usan la frase, sobrevive.

### 6. 🟠 MEDIO (robustez de frontera) — Guards de entrada con traceback
- **Estado:** `record-outcome abc` revienta con traceback (`float()` sin guard);
  `record-analytics` con JSON sin `production_ref` da `KeyError`. La frontera de captura de
  datos es EL punto donde el proyecto exige rigor (guard del %, guard de rango) y justo ahí
  dos entradas malformadas dan stack traces en vez de mensajes.
- **Solución:** guards con mensajes accionables. **Implementado hoy.**

### 7. 🟡 REPORTADO (esquema) — `production_analytics` pisa la medición anterior
- **Estado:** PK = `production_ref`; re-medir (48h → 7d → 30d) sobrescribe. Hoy los snapshots
  con fecha viven en `production_context.medicion_YYYY_MM_DD` (aceptable en n=3).
- **Decisión:** NO migrar aún — churn de esquema antes de que exista la necesidad viola
  POLITICA. **Trigger definido:** cuando se haga la SEGUNDA medición programada del mismo video
  (el FED a 48h y luego a 7d), convertir PK a `(production_ref, measured_at)`.

### 8. 🟡 REPORTADO (deuda aceptada) — Motor HTML de 2.558 líneas sin tests automáticos
- La deuda es real pero el motor está CONGELADO por política, y un harness headless añade el
  stack (Node/puppeteer) que el proyecto evita a propósito. Testear código congelado rinde menos
  que testear código que cambia. **Trigger:** ANTES de la próxima feature del motor (cuando un
  experimento la justifique), montar el harness primero. Escrito aquí para que no se olvide.

### 9. 🟡 REPORTADO (código especulativo) — 5 módulos creative sin camino de producción
- `experiments.py`, `questions.py`, `reasoning_loop.py`, `tradeoffs.py`, `production.py`
  (~640 líneas): testeados, estables, importados SOLO por tests. Son la fábrica diseñada para
  n≥10 videos (experiments es la herramienta anti-confounding que POLITICA Regla 3 referencia).
- **Decisión razonada:** mantener. Coste de mantenimiento ≈ 0 (stdlib pura, sin churn), borrarlos
  rompe referencias en VISION/POLITICA, y git no es excusa para borrar lo que el plan activa en
  ~7 videos. **Trigger de borrado:** si al llegar a 10 videos medidos siguen sin usarse, fuera.
- Nota anti-repetición: NO añadir más capacidad de este tipo. La regla ya existe (POLITICA #1).

### 10. 🟡 REPORTADO — Dualidad `db.py` (dominio) vs `reasoning/store.py` (kernel)
- Dos estilos de acceso a SQLite con razón de ser (el kernel exige conexión explícita por pureza
  y testabilidad; el dominio usa module-functions con context manager). Consolidarlos = churn
  sin beneficio medible. La lección REAL del bug de `views` (cazado hoy) no es "unificar capas",
  es "**`CREATE TABLE IF NOT EXISTS` no migra**": el patrón `_ensure_columns` vive en
  `production_dna.py` y se generaliza a la segunda ocurrencia (regla de tres), no antes.

### 11. 🟡 REPORTADO — CLI con dispatch a mano (sin argparse)
- 19 comandos, un usuario, cero deps. Migrar a argparse/click daría `--help` más rico a cambio
  de churn en 612 líneas estables. **Decisión: no cambiar.** Un "no" explícito también es un
  resultado de auditoría.

### 12. 🔵 MENOR — Higiene de docs
- `docs/AUDIT.md` (07-09, señales) vs `docs/AUDITORIA.md` (07-15, producto) vs este archivo:
  nombres confusables. Los tres son históricos y valiosos; se referencian desde ESTADO.md con
  fecha y lente. No se renombra nada (los enlaces internos pesan más que la estética).

## Lo que está BIEN y no hay que tocar (anti-churn explícito)

1. **Kernel domain-agnostic con test de pureza por AST** — separación kernel/dominio real, no
   de diapositiva. Pocas bases de código de este tamaño la tienen.
2. **Belief/prediction con "No Silent Learning" estructural** (un solo camino de mutación, con
   causa + rationale obligatorios) — es enforcement, no convención.
3. **Guards de captura-en-origen** (fracción vs %, rangos, tags del CKB obligatorios) — ya
   cazaron errores reales.
4. **Modo $0 honesto** (export-prompt cuando no hay API key) — degradación elegante de verdad.
5. **Motor HTML sin dependencias** — doble clic y funciona; el muxer MP4 a mano está documentado
   con el porqué (MediaRecorder miente, verificado).
6. **Docs de traspaso** (ESTADO/POLITICA/VISION + trampas conocidas) — nivel que rara vez se ve.
7. **SQLite** — correcto a esta escala por años. La ruta a Postgres+pgvector ya está aislada
   tras `db.py` para cuando (si) llega.

## Qué se implementó hoy (verificado con tests) y qué queda en manos del usuario

| # | Acción | Estado |
|---|---|---|
| 1 | Comando `backup` (snapshot SQLite consistente + zip de data/) | ✅ implementado + test |
| 3 | `--bind 127.0.0.1` en el servidor estático | ✅ implementado |
| 4 | `status` muestra predicciones vencidas + `resolve-prediction` | ✅ implementado |
| 5 | Filtro de nombres de canal en `theme_demand` | ✅ implementado + test |
| 6 | Guards de entrada en `record-outcome` / `record-analytics` | ✅ implementado |
| 2 | **Crear repo remoto privado y `git push`** | ⚠️ ACCIÓN DEL USUARIO |
| 2b | **Copiar el zip de `backup` a nube/USB (rutina semanal)** | ⚠️ ACCIÓN DEL USUARIO |

## El juicio final (sin diplomacia)

Este repo NO necesita una "evolución arquitectónica": necesita **disciplina de operación**.
La ingeniería está por encima de la media (kernel puro, guards, docs); los fallos graves son
operacionales (sin redundancia, loops sin cerrar) y de proceso (construir por delante de la
evidencia — ya legislado en POLITICA). La pregunta "¿diseñaría Anthropic/DeepMind este módulo
así?" tiene respuesta incómoda: **diseñarían menos módulos y publicarían más videos.** El
sistema aprende por fila del dataset, y las filas las produce la cadencia, no el código.
Cada hora de ingeniería adicional aquí tiene hoy menor retorno que una hora de producción;
esta auditoría arregla justo lo que protege ese retorno (que nada se pierda y que los loops
cierren) y se detiene ahí a propósito — seguir "mejorando" sería el mismo error con otro nombre.
