# POLÍTICA DE INGENIERÍA — congela el motor, genera datos

> Adoptada tras converger en que el cuello de botella ya NO es el código, es la INFORMACIÓN.
> El siguiente activo que necesita Omega no es un archivo Python. Es la primera fila real del dataset.

## Regla 1 — Ninguna feature del motor creativo sin una limitación revelada por un experimento REAL
No se añade una nueva capacidad al motor creativo a menos que un experimento **publicado y medido**
haya revelado una limitación concreta que esa capacidad resolvería.

```
❌  idea → módulo → idea → módulo → nunca publicar
✅  publicar → detectar limitación → diseñar exactamente la capacidad necesaria → publicar
```
El sistema crece porque la realidad lo obliga, no porque aparezcan ideas interesantes.

**Excepción única:** instrumentación de *captura-en-origen* (ADN de producción, coste, analíticas).
Se permite ANTES de tener datos porque, si no se captura al producir, la señal se pierde para
siempre. No es motor; es el aparato de medición. Ya está construida — no hace falta más.

## Regla 2 — No sobre-interpretar los primeros resultados
Un resultado con n bajo es una **observación**, no una regla. Si el primer Short retiene
extraordinariamente bien o mal, es UN dato. `dna_calibration` marca `PROVISIONAL` hasta tener n
suficiente; respétalo. La utilidad del sistema no está en acertar el primer experimento, sino en
que cada experimento mejora las decisiones futuras.

## Regla 3 — Aislar antes de concluir (anti-confounding)
La gráfica de retención dice **DÓNDE** cae la gente, no **POR QUÉ** (el bloque co-varía con
b-roll/voz/música/ritmo). Para atribuir causa: acumula volumen con variación, o aísla la variable
con un experimento controlado (`creative/experiments.py` y su guard de significancia). No conviertas
una correlación de n=3 en "ley del canal".

## Regla 4 — Mide también el COSTE de aprender
Cada video registra no solo su resultado, también lo que costó producirlo (horas de investigación,
guion, edición, $ de IA, tiempo hasta publicar). Para una fábrica, el **rendimiento por unidad de
esfuerzo** importa tanto como el CTR. Comando: `record-cost`; se ve en `dna`.

## HITO ACTUAL (medible, no vago)
> **10 videos instrumentados** con ADN + resultado + coste.

No "mejorar el framework". Diez filas reales. A partir de ~10 empiezan a emerger patrones débiles
que ya se pueden tratar como hipótesis y decidir cuáles merecen un experimento controlado. Con 1
no se distingue señal de ruido. Progreso del proyecto = **filas del dataset**, no commits ni módulos.

## Bucle operativo (el único trabajo hasta llegar a 10)
```
decide  →  think  →  [PRODUCIR + PUBLICAR]  →  record-dna / record-cost / record-analytics
        →  record-outcome  →  dna  →  (repetir)
```
Todo lo de código para esto YA existe y está probado (86 tests). Lo que falta es humano: publicar.
