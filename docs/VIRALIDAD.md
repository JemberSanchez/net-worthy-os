# QUÉ HACE DESPEGAR UN SHORT DE FINANZAS — evidencia, no opiniones

> **Fecha:** 2026-07-16 · **Muestra:** 543 Shorts EN de finanzas (API de YouTube) · **n útil: 39**
> **Estado: PROVISIONAL.** Es un estudio OBSERVACIONAL, no un experimento. Correlación, no causa.
> Se reproduce con `scratchpad/viral.py` + `viral2.py` (el método está abajo; la API es gratis).

Este documento existe porque el canal decidía por intuición y por un score que resultó estar roto.
Lo más valioso que hay aquí es la sección **"lo que NO se sostiene"**: son teorías que parecían
ciertas, que llegamos a creernos, y que el dato mató. Léela antes de proponer nada.

---

## 1. El método (y por qué el primer intento no valía)

**Intento 1 — INVÁLIDO (sesgo de supervivencia).** Mirar solo los Shorts que explotaron. No dice
nada: no ves a los miles que hicieron lo mismo y fracasaron.

**Intento 2 — INVÁLIDO (confounder).** Comparar "los que explotaron" contra "vídeos normales"
(`order=viewCount` vs `order=date`). Los grupos diferían en la variable dominante:

| | explotaron | control |
|---|---|---|
| **subs del canal** | **166.000** | **27,5** |

Todo lo que "distinguía" a los ganadores podía ser simplemente *tener audiencia*. Cualquier
conclusión de aquí es basura.

**Intento 3 — el que vale.** Comparar **solo dentro de canales pequeños** (la situación real del
canal): entre canales pequeños, ¿qué separa a los que despegaron de los que no? Más un filtro
honesto para quitar ruido: canal real (1.000–100.000 subs, no fantasmas de 20 subs), engagement
real (≥1% likes/vista) y ≥7 días de vida (un vídeo de ayer no ha demostrado nada).

**Solo el 13% de la muestra sobrevive al filtro.** La mayoría de lo que parece viral es ruido:
anuncios, trailers de películas, manualidades, contenido en otros idiomas mal etiquetado.

---

## 2. ⛔ LO QUE **NO** SE SOSTIENE (lo más importante del documento)

### La duración NO predice nada
Parecía que sí: los que explotan duraban 57s de mediana y los nuestros 24-32s. **Era el
confounder del tamaño del canal** — los canales grandes hacen vídeos de ~57s. Dentro de canales
pequeños:

```
DESPEGARON: p25=17s  MEDIANA=36s  p75=60s
NO despeg.: p25=21s  MEDIANA=38s  p75=60s
```

Y los despegues reales van de **17s a 130s**. **No alargues ni acortes buscando un número mágico.**

### El título casi no distingue
Dentro de canales pequeños, despegaron vs no despegaron: `you/your` 0.17 vs 0.18 · pregunta 0.10
vs 0.09 · nombre propio 0.01 vs 0.01. **Prácticamente idénticos.** Único matiz débil: llevar un
número 0.33 vs 0.22.

### "Más escenas / más producción" NO aparece por ningún lado
El Short más brutal de la muestra —**9,8M de vistas con 3.890 subs**— dura **6 segundos** y es una
persona metiendo monedas en una caja. Cero escenas, cero producción, cero guion. Y el mejor de
todos (**25,5M con 26.800 subs**) es un challenge de sobres de **17 segundos**.
Corrobora el dato propio: el FED es el Short **más producido** del canal (música + sfx + fondo
vivo + 9 bloques) y es el **peor** (10 espectadores). S1 es el menos producido y el mejor (221).

### `vistas / suscriptores` es una métrica mala sin filtrar
Con canales de 23 subs, 230 vistas ya son "x10". El multiplicador solo significa algo con
canal real (≥1.000 subs) **y** engagement real.

---

## 3. ✅ LO QUE SÍ SE SOSTIENE

### 3.1. Ninguno de los 39 despegues es NOTICIA — todos son evergreen
Edades de los despegues: **231, 321, 314, 352, 338, 291, 302, 333, 159, 133 días**. Vídeos de casi
un año que **siguen acumulando vistas**. Cero temas noticiosos.

**Consecuencia dura:** el sistema solo puede proponer noticia. `youtube-scan` usa
`publishedAfter = hoy - 30 días` → **el catálogo evergreen es literalmente invisible** para él.
Un vídeo de hace dos años que hace 2.000 vistas/día no existe para `decide`.
Concuerda con el dato propio: S1/S2/S3 (evergreen) 221/199/67 vs FED (noticia) 10.
⚠ n=1 para la categoría noticia, y el FED tenía además 8s congelados. No está demostrado.

### 3.2. Tres formatos despegan. El boletín no es ninguno.
1. **Clip de una persona real hablando** — *"A billionaire dropped the realest money advice"*
   (7,5M / 3.790 subs / 40s / like 2,1%) · Dave Ramsey (1,4M / 1.370 subs / 130s / 1,8%) ·
   *"SHAQ REVEALS THE MONEY ADVICE…"* (1,1M / 1.580 subs / 68s / 1,4%) ·
   *"He explained LEVERAGE better than college professors"* (18,3M / 30.300 subs / 47s / 2,1%).
2. **Demo visual / challenge** — *"How to do the 100 envelope savings challenge"*
   (**25,5M / 26.800 subs / 17s** / 1,8%) · *"100-Day Savings Challenge"* (9,8M / 3.890 subs / 6s).
3. **Explicador con la promesa desnuda en el título** — *"This Is How The Stock Market Works"*
   (11,7M / 53.900 subs / 112s / **like 3,7%**) · *"This is the actual power of passive income"*
   (6,2M / 13.700 subs / 32s).

Ninguno es *gancho → 3 bullets → stat → CTA*. **El formato del canal no aparece ni una vez entre
los que despegan.** Convergen aquí cinco caminos independientes: el `decide` arreglado (gana
`warren buffett`, un personaje), el ADN propio (el único `story=character` es el mejor Short),
los outliers (clips de personas), y el marco del tribunal (roles + conflicto).

### 3.3. Benchmark de engagement: **likes/vista entre 1% y 3,7%**
Todos los despegues reales están en esa banda. Es un objetivo medible y comparable — mucho mejor
que las vistas, porque no depende de cuánto te distribuyan.

---

## 4. Lo que este estudio NO puede decir
- **No mide retención**, que es lo que decide la distribución en Shorts. La API no la da. Solo
  está en YouTube Studio / el panel de Facebook → hay que registrarla a mano.
- **Es correlacional.** Que los clips de personajes despeguen no prueba que un clip de personaje
  vaya a despegar: puede haber miles fracasando sin salir en la muestra.
- **No ve el vídeo.** Título, vistas, duración y engagement; nada de ritmo, edición ni gancho.
- **El filtro de idioma falla en origen:** `relevanceLanguage='en'` cuela tamil, telugu, coreano
  e indonesio. Se corrige con `_is_english` del proyecto (el título manda), pero después.

## 5. Qué hacer con esto
1. **No optimizar duración ni título.** No hay señal. Es tiempo tirado.
2. **No añadir producción.** El dato propio y el ajeno dicen lo mismo: no compra alcance.
3. **Evergreen, no noticia.** Y el sistema no puede ayudarte aquí: por `publishedAfter` solo ve
   noticia. Es criterio humano hasta que se arregle.
4. **Personaje o demo visual, no boletín.** Es la apuesta con más apoyo convergente.
5. **Medir retención y likes/vista.** Sin eso, todo esto se queda en teoría bonita.

## 6. Cómo reproducirlo
`scratchpad/viral.py` (recogida: tratamiento `order=viewCount` + control `order=date`, filtro
`_is_english`, calcula vistas/día, mult, like_rate) y `viral2.py` (comparación dentro de canales
pequeños). ~100 unidades de cuota por búsqueda, 8 búsquedas × 2 muestras = 1.600 de 10.000/día.
**Rehacerlo con más muestra y ≥90 días de vida mínima haría el n útil mucho más sólido.**
