# POLÍTICA DE INGENIERÍA — mejorar el motor, pero solo lo que se mide

> 21-oct-2026 (decisión del usuario): el motor **ya no está congelado**. La regla de julio ("ninguna
> feature sin un experimento publicado") frenaba la calidad: #7 y #8 v2 no se publican porque al
> usuario no le convencen, y publicar algo flojo solo para tener filas daña el canal.
> Lo que se mantiene es lo que la regla vieja protegía: nada de mejorar a ojo, en círculos.

## Regla 1 — Una mejora entra si sube una métrica MEDIDA
Cualquier cambio del motor creativo es bienvenido si mejora, medido antes y después, al menos una de estas:
- **(a) La calificación a ciegas del usuario** sobre las mismas piezas (sus quejas concretas, con
  segundo exacto, se convierten en reglas deterministas o en la rúbrica de un juez).
- **(b) La distancia a los Shorts de referencia** del nicho (datos públicos reales: segundo del
  gancho, ritmo de cortes, texto en pantalla, duración, voz).
- **(c) La retención real** una vez publicado.

```
❌  idea → cambio → "se ve mejor" → otro cambio (seis rondas del LEAD, jul-2026)
✅  queja o brecha medida → cambio → re-medir → entra solo si la métrica mejora
```
Meta: que un juez automático coincida con el usuario en piezas que no ha visto. Cuando lo haga de
forma consistente, se gana la autonomía (publicar sin aprobación); antes, no.

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
> **Un juez automático que coincida con el usuario** en piezas que no ha visto, y después
> **10 videos v2 publicados** con ADN + resultado + coste.

Progreso = métricas que se mueven (acuerdo juez↔usuario, distancia a la referencia, retención),
no commits ni módulos. A partir de ~10 publicados empiezan a emerger patrones débiles del canal.

## Bucle operativo
```
producir → medir (calificación a ciegas / referencia) → mejorar lo que falla → re-medir
        → publicar lo que convence → record-dna / analytics-sync → dna → (repetir)
```
