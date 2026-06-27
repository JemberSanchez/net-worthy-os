# OMEGA — Visión y arquitectura congelada (ADR maestro)

> Nombre interno: **AIIS — Autonomous IP Intelligence System.** El video es un mecanismo de
> distribución, no el producto. El producto es la IP propia, descubierta y validada con datos.

> Estado: **CONGELADA**. La arquitectura convergió tras varias iteraciones de auditoría
> crítica (ver [AUDIT.md](AUDIT.md) para el detalle del triage y las eliminaciones).
> La próxima evolución debe venir de un sistema en funcionamiento con datos reales,
> **no** de más diseño en abstracto. "Seguir hablando es procrastinar con elegancia."

---

## Misión

> **No estamos construyendo un generador de videos. Estamos construyendo un motor de
> razonamiento que toma mejores decisiones creativas basadas en evidencia. El contenido es
> el PRIMER DOMINIO donde validamos que ese razonamiento genera valor económico real — no
> el centro del proyecto, sino su primer experimento.**

El centro es la **calidad del razonamiento**, no el contenido. El video es el **primer
adaptador**, no la arquitectura. El núcleo permanece independiente del formato de salida: si
el sistema demuestra que decide mejor que un humano, el mismo kernel sirve para publicidad,
branding, productos digitales u otros activos creativos (**visión, no alcance del MVP**). Si en
10 años el medio dominante cambia, el corazón del sistema sigue teniendo sentido.

## Principio rector

> El sistema aprende observando el mercado **externo** (N grande). Su propia producción
> (2-3/día, N diminuto) **valida** hipótesis, no las descubre. Todo es hipótesis con nivel
> de confianza, nunca verdad. El sistema **predice y verifica**; observar sin predecir es
> un dashboard, no aprendizaje. "ABSTENERSE hoy" es una decisión válida y de primera clase.

## Regla transversal: *Every belief is a prediction*

Toda **creencia** del sistema se registra como una **predicción falsable con fecha y criterio
de refutación**. No se almacenan opiniones ni conclusiones permanentes; se almacena un historial
de creencias que evolucionan con la evidencia.

- **Creencias vs hechos:** las *observaciones* (hechos medidos: "el video X tiene 1.2M vistas
  hoy") se loguean como hechos, sin ceremonia. El rigor de predicción aplica a las *creencias*
  (afirmaciones falsables). No envolver hechos en el esquema de predicción.
- **Fecha + umbral:** la fecha esperada evita predicciones que nunca se verifican; el criterio
  de refutación pre-comprometido evita la verificación motivada. Ambos son obligatorios.
- **Escalonado:** esquema completo solo para creencias *consecuentes* (qué producir, qué IP
  promover, qué nicho entrar). Lo trivial se loguea como hecho. Disciplina total sobre todo =
  burocracia que se rutea por fuera.
- **Dónde paga rápido:** las predicciones sobre el mercado externo se resuelven rápido y en N
  grande → calibración real en semanas. Las de producción propia, lento. Este principio es el
  motor del aprendizaje externo primero.
- **El moat que genera:** convierte el Knowledge Engine de "base de conocimiento" en **track
  record auditable** — un historial de predicciones resueltas que *demuestra* (no afirma) que
  el motor predice. Defensibilidad demostrable: "N predicciones falsables, calibradas al X%".

## Regla transversal: *No Silent Learning*

El sistema **nunca** modifica una creencia de forma implícita. Toda actualización registra qué
cambió, qué evidencia la provocó, qué predicciones se confirmaron/refutaron, y **por qué** cambió
el nivel de confianza. El objetivo no es guardar la nueva creencia, sino **preservar la evolución
completa del razonamiento** — reconstruible años después.

- **La creencia es entidad de primera clase**, con su propio log append-only de updates. No basta
  el Decision Record (prediction-centric): muchos cambios de confianza **no tienen predicción
  dueña** (el patrón dejó de aparecer = observación; el intervalo se ensanchó = decaimiento;
  herencia de una creencia relacionada; override humano). Esos solo viven aquí.
- **Enforcement estructural:** la confianza es **inmutable salvo vía un evento de update logueado
  que cita su causa**. Ningún código escribe `confidence = X` directo; todo pasa por
  `update_belief(causa, evidencia_refs, old, new)`. El aprendizaje silencioso es imposible por
  construcción.
- **Anti-confabulación (crítico):** el "por qué" es una **causa estructurada derivada de los
  inputs reales del update** (qué predicciones se resolvieron, qué deltas de evidencia, qué
  decaimiento), opcionalmente renderizada a prosa. **Nunca** narración libre de un LLM generada
  a posteriori — eso sería un rastro de auditoría *fabricado*, peor que el silencio.

> **Simetría del ciclo de vida de una creencia:** *Every belief is a prediction* gobierna cómo se
> **crean y prueban**; *No Silent Learning* gobierna cómo se **actualizan y retiran**. Las dos
> mitades cierran el modelo epistémico. No falta una tercera regla.

---

## El núcleo: kernel (domain-agnostic) + capa de dominio

**Corrección de coherencia (jun 2026):** la versión previa listaba 4 componentes como "núcleo".
Eso violaba el principio de independencia del formato: Identity y Audience son conceptos del
**dominio de contenido** (personajes, lore, audiencia), no del kernel universal. Reclasificados.

### Kernel — domain-agnostic, reutilizable en cualquier dominio

No sabe nada de video, YouTube ni "contenido". Manipula creencias, predicciones, evidencia y
resultados. Es lo que se reutiliza si el sistema pasa a publicidad, productos, branding, etc.

| Componente | Qué es | Por qué es moat |
|---|---|---|
| **Reasoning Engine** *(público: Knowledge Engine)* | Creencias/predicciones/evidencia/resultados/updates en un bucle predict→verify; calibración | Moat de **tiempo**: historial calibrado y explicable, irreplicable sin años |
| **Decision Engine** | Juicio que asigna recursos a 3 altitudes (pieza / activo / portafolio) | Disciplina de evidencia + abstención |

Las *mecánicas* de inteligencia (cambios de estrategia de un competidor, lifecycle de tendencias,
minería de demanda) son patrones **domain-agnostic**; se *instancian* con fuentes de un dominio.
Las fuentes son adaptadores.

### Capa de dominio — el PRIMER dominio: contenido creativo / IP

Lo que se reemplazaría al aplicar el kernel a otro dominio.

| Componente | Qué es |
|---|---|
| **Sources** *(adapter)* | YouTube, Reddit, RSS... de dónde observa este dominio |
| **Identity Engine** | IP propia: canon + resonancia + gusto calibrado (el activo del dominio creativo) |
| **Audience Engine** | Relación propia off-platform (semi-transversal, pero ligada a la ejecución del dominio) |
| **Generation** *(adapter)* | Salida: video hoy; otro formato mañana. Commodity externalizado |

**Constraint duro:** el kernel **NO depende de ningún formato de salida**. El Decision Record
guarda creencias/evidencia como payload genérico — **sin columnas tipadas de video**. El video
es el primer adaptador, no la arquitectura.

### Insight rector: "el mismo motor, distinta altitud"

No se crea un motor por cada idea. El **Decision Engine** decide a tres niveles con la
misma maquinaria (evidencia → opciones rankeadas → asignación → abstención):

```
Video      → Decision Engine   (qué pieza producir hoy)
IP         → Decision Engine   (qué identidad merece promoción de experimento a inversión)
Portafolio → Decision Engine   (crear IP nueva vs invertir en existente; cuándo abandonar)
```

La "fábrica de empresas de medios" es el Decision Engine a altitud de portafolio. **No se
construye hasta que exista un portafolio (≥2 IP exitosas).** El portafolio es el *resultado*
del éxito, no la estrategia para lograrlo. El foco gana IP; el volumen la diluye.

### Knowledge Engine: unidad atómica — el Decision Record

No almacena hechos ni resultados sueltos. Almacena **predicciones falsables que evolucionan**.
Campos mínimos del Decision Record (para creencias consecuentes):

```
fecha_creación
creencia / hipótesis           (+ alternativas descartadas, incertidumbres)
evidencia utilizada
nivel_de_confianza (%)
predicción falsable
método_de_verificación
criterio_de_refutación         (umbral pre-comprometido: "refutada si X < T")
fecha_esperada_de_verificación
resultado_observado
actualización_de_la_creencia
```

- **Por qué razonamiento y no solo resultados:** sin la creencia registrada no puedes
  distinguir **suerte de habilidad**, ni actualizar nada. Es preregistro científico.
- **Por qué la fecha + el umbral:** la fecha evita predicciones que nunca se verifican (fallo
  nº1 de los sistemas que dicen "aprender"); el umbral pre-comprometido evita la verificación
  motivada. Sin ambos, no es falsable de verdad.
- **Línea roja:** el valor está en que decisiones futuras **recuperen y usen** el razonamiento.
  Sin recuperación, no construir el almacén (sería un cementerio write-only).
- **Captura barata:** el LLM que decide emite el razonamiento como parte del Decision Record
  (coste marginal ≈ 0).
- **Esquema mínimo primero:** no formalizar una ontología antes de que los datos enseñen qué
  campos importan (evitar el pantano de la representación del conocimiento).

### Identity Engine: detalles

- **No auto-genera IP a escala** (diluiría la escasez que persigue). Es **canon-keeper +
  resonance-tracker + consistency-enforcer**.
- El **"gusto" (Taste) NO es un componente aparte**: emerge de Knowledge + Identity + feedback
  real de la audiencia. Es la dimensión evaluativa del Identity, **calibrada con señal
  propietaria**. La rúbrica genérica es commodity; la calibración con tu audiencia es el moat.
- **Advertencia:** el gusto genérico **homogeneiza hacia la media = muerte en un mercado
  sobreofertado.** Calibrar premiando "divisivo pero resonante", no "pulido". Distinción, no pulcritud.
- **Modos (explore→exploit, no interruptores paralelos):**
  - *Trend-Driven* = R&D barato que descubre candidatos de identidad.
  - *IP-Driven* = compounding que dobla la apuesta en el ganador **medido**.
  - Un personaje **gana** la promoción de Trend a IP por resonancia, no por decisión a priori.
  - **Origen del candidato:** *Human Seed* (humano propone) **+** *AI Discovery* (IA propone,
    capacidad experimental validada con datos). La escasez se protege en la **compuerta de
    promoción**, no en el origen. Esperar que AI Discovery ocupe la mitad "recombinación";
    las apuestas trascendentes vendrán más de humanos. Medir, no asumir paridad.

---

## Qué es commodity (se invoca, no se construye)

Generación (guion, voz, imagen, video, música, miniaturas), edición, publicación, y —en el
mundo de la inundación— incluso la detección de tendencias y las rúbricas genéricas de calidad.
La generación se trata como **adapter externalizado desde el día 1**.

## Qué se mató y por qué (resumen; detalle en AUDIT.md)

- **Simulation Engine** (predecir CTR/retención): ficción a 2-3/día. Reformulado a **pre-flight
  review cualitativo** (detección de defectos, no predicción), fusionado al panel.
- **A/B sobre output propio**: muerto por N. Los experimentos corren sobre **datos externos**.
- **ROI estimado**: requiere predecir ingresos = ficción. Se estima **coste** (real), no ROI.
- **11 agentes → 4** (Estrategia/Mkt · Creativo/Guion · Originalidad+Políticas[veto] · Técnico).
- **Strategy Engine autónomo → parámetro** (Strategy Profile fijado por humano, logueado).
- **17 "engines" → 4 componentes** + capas/vistas/parámetros (Market Map = vista de síntesis;
  Taste = dimensión de Identity; Portafolio = Decision a otra altitud).

## Advertencias estratégicas (riesgos reales)

1. **La IP es un negocio de hits**: la mayoría fracasa. El Knowledge *reduce* el azar, no lo
   elimina. No prometer "IP bajo demanda".
2. **No posees tu audiencia en la plataforma**: la propiedad real necesita un canal off-platform
   (de ahí el Audience Engine).
3. **Análisis visual**: metadatos y miniaturas son obtenibles; cortes/ritmo/música requieren el
   archivo de video → caro y viola ToS a escala. Distinguir obtenible de estimable.
4. **Consistencia de personajes** generados por IA: aún no resuelta (deriva de modelos). El canon
   la mitiga, no la garantiza.

## Fuentes legales (MVP)

YouTube Data API (metadatos + stats + **comentarios** + miniaturas) · Reddit · RSS/Noticias.
TikTok/IG/Facebook = **solo destino de publicación** (cross-post), nunca fuente (sin API pública
de descubrimiento). X/Pinterest fuera del MVP.

---

## Roadmap y métricas falsables (anti-vanidad)

**Prohibido medir éxito por vistas/viralidad en fases tempranas** (no se controlan, N diminuto).

| Fase | Construir | Métrica de éxito falsable |
|------|-----------|---------------------------|
| **1 — El Decididor** | Bucle predict→verify del Knowledge Engine, alimentado por Competitor + Comment mining → Decision Record diario (3 candidatos o ABSTENERSE) | % decisiones con evidencia reconstruible; **test ciego: sistema ≥ tu intuición** |
| **2 — Inteligencia** | Knowledge graph + Market Map (vista) | **Precisión out-of-sample**: ¿los temas marcados "en declive" cayeron en 30 días? |
| **3 — Identidad** | Identity Engine (canon + resonancia); primer candidato de IP | Resonancia medible y repetible de elementos de identidad |
| **4 — Generación** | Adapter de generación + panel de 4 revisores + Quality Gate | coste/asset · tasa de aprobación · consistencia de canon |
| **5 — Audiencia** | Audience Engine (relación off-platform) | % de audiencia alcanzable sin la plataforma |
| **6 — Portafolio/Escala** | Decision a altitud de portafolio; migración a Postgres/colas cuando los datos lo exijan | coste/decisión · calibración de creencias vs realidad |

---

## Decisión: el siguiente paso es código

Construir **el bucle predict→verify del Knowledge Engine**, alimentado por **Competitor
Intelligence + Comment mining** (los dos sensores de mayor señal), produciendo un **Decision
Record** diario que almacena el cuádruple (creencia→predicción→resultado→actualización).

Es el único módulo cuyo valor compone durante una década. Todo lo demás se construye encima.
