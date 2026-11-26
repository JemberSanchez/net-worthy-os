# QUÉ HACE DESPEGAR UN SHORT DE FINANZAS — evidencia, no opiniones

> **Fecha:** 2026-07-16 · **Muestra:** 543 Shorts EN de finanzas (API de YouTube) · **n útil: 39**
> **Estado: PROVISIONAL.** Es un estudio OBSERVACIONAL, no un experimento. Correlación, no causa.
> Se reproduce con `scratchpad/viral.py` + `viral2.py` (el método está abajo; la API es gratis).

Este documento existe porque el canal decidía por intuición y por un score que resultó estar roto.
Lo más valioso que hay aquí es la sección **"lo que NO se sostiene"**: son teorías que parecían
ciertas, que llegamos a creernos, y que el dato mató. Léela antes de proponer nada.

> **26-nov:** la **Parte II** (§8-§12, al final) añade lo VISUAL: gancho, ritmo, texto, giros, bucle,
> miniatura; fuentes externas comparadas con el motor y cambios priorizados con su métrica.

---

## 1. El método (y por qué el primer intento no valía)

**Intento 1 — INVÁLIDO (sesgo de supervivencia).** Mirar solo los Shorts que explotaron. No dice
nada: no ves a los miles que hicieron lo mismo y fracasaron.

**Intento 2 — INVÁLIDO (confounder).** Comparar "los que explotaron" contra "vídeos normales"
(`order=viewCount` vs `order=date`). Los grupos diferían en la variable dominante:

|                    | explotaron  | control  |
| ------------------ | ----------- | -------- |
| **subs del canal** | **166.000** | **27,5** |

Todo lo que "distinguía" a los ganadores podía ser simplemente _tener audiencia_. Cualquier
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

1. **Clip de una persona real hablando** — _"A billionaire dropped the realest money advice"_
   (7,5M / 3.790 subs / 40s / like 2,1%) · Dave Ramsey (1,4M / 1.370 subs / 130s / 1,8%) ·
   _"SHAQ REVEALS THE MONEY ADVICE…"_ (1,1M / 1.580 subs / 68s / 1,4%) ·
   _"He explained LEVERAGE better than college professors"_ (18,3M / 30.300 subs / 47s / 2,1%).
2. **Demo visual / challenge** — _"How to do the 100 envelope savings challenge"_
   (**25,5M / 26.800 subs / 17s** / 1,8%) · _"100-Day Savings Challenge"_ (9,8M / 3.890 subs / 6s).
3. **Explicador con la promesa desnuda en el título** — _"This Is How The Stock Market Works"_
   (11,7M / 53.900 subs / 112s / **like 3,7%**) · _"This is the actual power of passive income"_
   (6,2M / 13.700 subs / 32s).

Ninguno es _gancho → 3 bullets → stat → CTA_. **El formato del canal no aparece ni una vez entre
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

## 7. Calendario de alternancia noticia / personaje (propuesta 5-nov, PROVISIONAL)

Por qué: los 39 despegues de §3.1 son atemporales y el único formato con apoyo convergente es el de
personaje (§3.2), pero es un estudio correlacional y sin medir retención. El canal publicó **7 noticias
seguidas y 0 personajes**, así que no tiene datos propios para comparar. La alternancia es el
experimento: **una variable (formato), 8 vídeos, se compara retención con ≥30 vistas por plataforma**.
Sin ese corte, ni personaje ni noticia se declaran ganadores (POLITICA regla 2). `decide` sigue eligiendo
las noticias; los personajes los pone este calendario porque el escáner no ve lo atemporal (§3.1).

| Turno | Tipo      | Tema                | Estructura        | Gancho posible (idea, guion en inglés por escribir)                     |
| ----- | --------- | ------------------- | ----------------- | ----------------------------------------------------------------------- |
| 1     | Personaje | Ronald Wayne        | vida de personaje | vendió su 10 % de Apple por $800                                        |
| 2     | Noticia   | ganador de `decide` | error común       | según el tema                                                           |
| 3     | Personaje | Anne Scheiber       | misterio          | auditora del IRS, nunca ganó más de $4.000 al año, dejó $22 M           |
| 4     | Noticia   | ganador de `decide` | cuenta atrás      | según el tema                                                           |
| 5     | Personaje | Jesse Livermore     | cuenta atrás      | ganó unos $100 M en el crac de 1929 y quebró en 1934                    |
| 6     | Noticia   | ganador de `decide` | contradicción     | según el tema                                                           |
| 7     | Personaje | Oseola McCarty      | vida de personaje | lavandera, donó unos $150.000 a una universidad                         |
| 8     | Personaje | Isaac Newton        | contradicción     | el genio que perdió al menos £10.000 en la burbuja de los Mares del Sur |

**Cambio del 11-nov (decisión del usuario, PROVISIONAL, n=11):** de alternar 1 a 1 a **3 personajes por cada noticia**.
Score v3 ≥ 0,67: personaje 3 de 3 (ronald-wayne 0,84 · jesse-livermore 0,82 · buffett-deficit 0,67), noticia 2 de 8
(midterm-rally 1,0 · gdp-annualized 0,73). La noticia de cada cuatro mantiene la comparación.

En reserva: Grace Groner y Ronald Read (ya montados, **sin publicar**; sus guiones fallan G-COMODIN y G-TU:
reescribir antes de renderizar) y Hetty Green (faltan cifras por cotejar).

Fuentes leídas el 5-nov (cifras de la tabla presentes en el texto):
[Wayne](https://en.wikipedia.org/wiki/Ronald_Wayne) ·
[Scheiber](https://en.wikipedia.org/wiki/Anne_Scheiber) ·
[Livermore](https://en.wikipedia.org/wiki/Jesse_Livermore) ·
[McCarty](https://en.wikipedia.org/wiki/Oseola_McCarty) ·
[Newton, en South Sea Company](https://en.wikipedia.org/wiki/South_Sea_Company) ·
[Green](https://en.wikipedia.org/wiki/Hetty_Green).
⚠ Es Wikipedia, una fuente secundaria, y las páginas de Scheiber y McCarty llevan aviso de citas: al producir,
cada cifra de `cifras[]` se coteja contra la referencia primaria que esa página enlaza (BBC y CNN en
Wayne). Livermore murió por suicidio: el guion no lo usa como gancho ni como giro. Imágenes: solo Commons PD/CC0/CC BY.
***

# PARTE II — LO VISUAL Y LA PARTE VISUAL DEL GUION (26-nov-2026) · **PROVISIONAL**

Pregunta: qué hace que un Short faceless de finanzas (EN) **retenga** y **se comparta**, mirando solo lo
visual (gancho 0-3 s, ritmo, texto en pantalla, giros, bucle, miniatura/título), no la calidad técnica.
Método: 4 búsquedas en paralelo (plataformas, datos de retención/gancho, ritmo/texto, canales del nicho)
más los datos propios de `data/omega.sqlite`. Etiquetas: **[oficial]** YouTube/Meta · **[estudio]** con n y
método · **[anuncios]** estudio sobre anuncios (no orgánico) · **[blog]** sin método, orientativo ·
**[propio]** nuestra DB. No se vio ningún Short fotograma a fotograma (el navegador no cargó YouTube):
todo lo de estilo de canales es de segunda mano.

## 8. Hallazgos con su fuente

### 8.1 Cuándo se va la gente (lo más sólido)

- **[estudio]** Kuaishou, datos industriales: **30 % de las vistas termina antes de 3 s, 80 % antes de
  32 s** ([CREAD, arXiv 2401.07521](https://arxiv.org/pdf/2401.07521), 2024). La mayoría de saltos, en
  los primeros 5 s ([arXiv 2603.22663](https://arxiv.org/pdf/2603.22663), 2026; solo extractos leídos).
- **[estudio]** TikTok, donación de datos (n = 347 usuarios, 9,2 M vídeos): se ve de media **~45 %** de
  cada vídeo, estable en el tiempo ([arXiv 2301.04945](https://arxiv.org/abs/2301.04945), 2023).
- **[estudio, Meta 2016]** El contenido del feed móvil se recuerda tras **0,25 s**; tiempo medio por pieza
  1,7 s ([Facebook IQ](https://www.facebook.com/business/news/insights/capturing-attention-feed-video-creative)).
  Consecuencia: el primer cuadro ya trabaja, antes que la voz.
- **[anuncios]** TikTok/MediaScience (n = 343, eye-tracking): **50 % del impacto en los 2 primeros s, 90 %
  en 6 s** ([TikTok](https://ads.tiktok.com/business/vi/blog/mediascience-study-brands-memorable-tiktok), 2021,
  patrocinado). Facebook/Nielsen: 47 % del valor en 3 s ([MarTech](https://martech.org/even-brief-video-views-drive-brand-lift-facebook-nielsen-study-finds)).
- **[oficial]** "Viewed vs swiped away" = % de impresiones del feed vistas en vez de saltadas
  ([YouTube Help](https://support.google.com/youtube/answer/12220281)). **YouTube no publica objetivo**: el
  "70-85 % es bueno" es [blog]. Paddy Galloway (3.300 M vistas, vía vidIQ, no verificado): los virales se
  agrupan en ≥ ~60 % que pasan los primeros segundos.

### 8.2 Qué tipo de gancho (débil: casi todo es de anuncios)

- **[anuncios]** >63 % de los anuncios TikTok con más CTR muestran el mensaje clave en los **3 primeros s**
  (fuente original no encontrada). Meta: marca y mensaje en los 5 primeros s, 1,7× más probable estar en
  el 20 % superior de intención de compra.
- **[anuncios]** VidMob × TikTok (1.678 anuncios): gente corriente 1,7× más probable de enganchar; mirada a
  cámara +14 % de vista a 2 s ([PDF](https://www.vidmob.com/wp-content/uploads/2024/02/Vidmob-x-Tik-Tok-Hook-Analysis-.pdf)).
  Faceless: no aplica directo; sugiere **personas reales en pantalla** (fotos/metraje del personaje).
- **[blog, con casos]** Jenny Hoyos vía [vidIQ](https://vidiq.com/blog/post/how-jenny-hoyos-gets-10m-views-per-youtube-short):
  gancho ~3 s que **se entiende sin sonido**, primeras palabras = la promesa sobre la imagen que la muestra;
  ritmo rápido-medio-pico-medio-rápido.
- **[caso documentado]** Humphrey Yang despegó contando 10.000 granos de arroz = patrimonio de Bezos (2,2 M
  vistas en dos vídeos); él lo atribuye a la representación visual
  ([Fortune 2020](https://fortune.com/2020/03/21/tik-tok-influencers-personal-finance-advice/)). Patrón:
  **cifra abstracta convertida en objeto físico**.
- **No existe** estudio riguroso que compare pregunta abierta vs ruptura de patrón vs empezar en mitad de la
  acción vs enseñar el final primero. Quien dé un "% por tipo de gancho" cita un blog.

### 8.3 Ritmo de cortes

- **[estudio]** SHOT/AutoShot (CVPR-W 2023, 853 vídeos cortos, 11.606 planos anotados): **plano medio
  2,59 s (~23 cortes/min)**, vídeo medio 39,5 s ([arXiv 2304.06116](https://arxiv.org/abs/2304.06116)). Es la
  norma de la plataforma, no de los virales. Cine actual: ~2,5 s ([Cutting et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC3485803)).
- **[estudio, TV]** Cortes **dentro de la misma escena/idea** suben atención y memoria sin subir carga
  cognitiva (Lang et al. 2000, JBEM 44). Con **≥ 10 cambios de escena NO relacionados por 30 s** (uno cada
  ≤ 3 s) la memoria de la información cae (Lang et al. 1999, solo citas secundarias).
  Para finanzas: **cortar rápido dentro de una idea, no saltar de idea cada 3 s**.
- **[estudio]** Meta-análisis 2025 (reproducción acelerada): más velocidad de información sube la carga
  (g = 0,59) y baja la retención de lo aprendido (g = −0,41) ([Frontiers](https://www.frontiersin.org/articles/10.3389/fpsyg.2025.1427609)).
  La densidad tiene techo.
- **[blog]** "un corte cada 2-4 s, un beat nuevo cada 5-7 s" (OpusClip): sin método, coincide con SHOT.

### 8.4 Voz y texto en pantalla

- **[blog]** 130-160 palabras/min recomendadas; Biteable midió 169 de media (128-203) en sus vídeos. Nadie
  midió el ritmo de voz de Shorts virales.
- **[estudio]** Principio de redundancia (Mayer): texto que repite la narración perjudicó en 8 de 12 pruebas,
  efecto pequeño (d ≈ 0,10): **subtítulo de palabras clave** mejor que transcripción completa
  ([UNH/Mayer](https://www.unh.edu/teaching-learning-resource-hub/sites/default/files/media/2023-06/itow-research-based-principles-for-designing-multimedia-instruction-mayer.pdf)).
- **[oficial]** Instagram recomienda menos los Reels "mayoritariamente cubiertos de texto", silenciados,
  borrosos, con bordes/marcas de agua o no originales ([Instagram](https://creators.instagram.com/original-content-guidelines/)).
- "85 % ve sin sonido" y "+12 % de tiempo con subtítulos" son de 2016, anuncios de feed: **caducados** para
  Shorts/Reels (TikTok/Shorts se ven con sonido; encuesta TikTok: 88 % dice que el sonido es esencial).
- **[blog]** Zonas seguras: no hay especificación oficial de YouTube; terceros discrepan (abajo 300-672 px
  de 1920, derecha 48-150 px). Nuestro L1 (fuera de y > 84 % y de la columna derecha) cae dentro del rango.
- **[estudio]** Gráficas animadas: transiciones animadas **entre estados**, por etapas y **con escala fija**
  mejoran la percepción; reescalar el eje a mitad la empeora (Heer & Robertson 2007,
  [IEEE TVCG](https://idl.uw.edu/papers/animated-transitions)).

### 8.5 Giros, bucle, final

- **[oficial, 2022]** Facebook Reels: inicio-medio-final claros o gancho con recompensa (revelación/giro); una
  buena transición hace re-ver ([Meta](https://creators.facebook.com/blog/reels-best-practices-tips-tricks)).
- **Bucle: sin estudio controlado.** Solo una anécdota (vidIQ 2021: un creador pasó de ~100 % a ~200 % de
  porcentaje visto con bucles de 7-8 s). **Ojo con la métrica [oficial]:** desde el 31-mar-2025 cada
  reproducción repetida cuenta como vista, pero las **vistas comprometidas excluyen los bucles**. Nuestro
  `se_quedaron` = engaged/vistas: un bucle sube el denominador, así que **puede bajar el score v4 aunque
  guste**. Desde el 24-ago-2026 todos los formatos cuentan la vista desde el primer cuadro
  ([YouTube blog](https://blog.youtube/inside-youtube/engaged-views-youtube-explained/)).
- Re-ganchos "cada N s": **ningún dato riguroso**. Lo único medido es la forma de la curva (caída temprana).

### 8.6 Miniatura y título

- **[oficial vía TechCrunch 2023]** Todd Sherman (Shorts): casi todas las vistas vienen del feed deslizado,
  la miniatura importa poco. Concuerda con §2 (el título casi no distingue). **No invertir aquí.**

### 8.7 Plataformas: originalidad (riesgo directo para un canal faceless con voz IA)

- **[oficial]** YouTube "inauthentic content" (15-jul-2025, reescrito jul-2026): no monetizan "slideshows de
  imágenes, historias de plantilla o texto desplazándose con poca o ninguna narrativa", contenido IA de
  "plantillas genéricas" con aspecto de producción en masa, y **presentadores IA que dan consejo financiero**
  ([política](https://support.google.com/youtube/answer/1311392); [TechCrunch 20-jul-2026](https://techcrunch.com/2026/07/20/youtube-clarifies-policies-around-ai-slop-and-upsetting-videos/)).
  Permitido: misma intro/outro y series si cada vídeo tiene foco distinto; IA para visuales de fondo de una
  narrativa "única y bien investigada". Revisan tema principal, vídeos más vistos y recientes.
- **[oficial]** Meta: Mosseri (ene-2025) top 3 señales = tiempo visto, likes/alcance, **envíos/alcance**
  (los envíos pesan más para no seguidores). Facebook (14-jul-2025) baja la distribución a cuentas que
  reusan contenido ajeno.

### 8.8 Canales del nicho (de segunda mano, sin ver los vídeos)

Patrones que repiten las fuentes (Zack D. Films 29 M subs, 100 % Shorts; Casually Finance 433 K; Humphrey
Yang 2,1 M; Graham Stephan, ~80 % de vistas en Shorts según OutlierKit, estimado):

1. Promesa en el **primer cuadro**, entendible en mudo (cifra u objeto en pantalla).
2. **Dinero abstracto convertido en objeto** (arroz, fajos, objeto 3D, gráfica con eje real).
3. Historia por **mecanismo y puntos de giro**, no "5 hábitos de millonarios".
4. **Mostrar la prueba**: documentos, gráficas y capturas reales; el metraje de stock "que tapa que no hay
   prueba" es el fallo más citado (opinión editorial, alineada con la política de YouTube).
5. Final corto que vuelve al inicio (bucle): práctica común, sin dato en finanzas.
6. Un **formato reconocible** por canal, pero sustancia distinta en cada vídeo.

### 8.9 Datos propios [propio, n = 9, 24-553 vistas]

Retención relativa (`production_retention.relative`, leída hoy) a mitad: mejores gdp-annualized 0,65,
midterm-rally 0,59, huang-resigns 0,59; peores buffett-deficit 0,38, aws-profit 0,09, average-401k 0,05.
Rasgos del storyboard (escenas, % `foto`+`titulo`, nº de tipos, golpes, tipo de la 1.ª escena) **no separan**
mejores de peores: gdp-annualized (el mejor) tiene 94 % `foto`+`titulo` y 3 tipos. Con n = 9 y estas vistas
no se puede atribuir nada a lo visual.

⚠ **Validar el instrumento antes de usarlo:** los valores de hoy no cuadran con la tabla del 13-nov de
`docs/INVESTIGACION-VIRAL.md` §2.1 (allí gdp-annualized = 1,38 al 10 %; hoy 0,60). O cambió la definición de
`relative` en `analytics-sync`, o se re-sincronizó con otra escala. Aclararlo antes de fijar umbrales sobre él.

## 9. Lo que ya cubrimos

| Hallazgo                                    | Ya en el motor                                                                                                        | Dónde                                   |
| ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | --------------------------------------- |
| Atención decidida en 0-3 s                  | voz ≤ 0,6 s, texto antes de 0,8 s, gancho entendible sin contexto, clip del gancho no oscuro, luma/contraste en 0-2 s | G1, `gancho_clip_oscuro`, C1 `gancho_*` |
| Plano medio ~2,6 s                          | tramo más largo sin cambio visual ≤ 2,5 s                                                                             | R1 (`medir_ritmo.py`)                   |
| Re-ganchos                                  | hueco entre golpes ≤ 12 s; MITAD medida en el brief del guionista                                                     | G2, `guionista --reglas`                |
| Subtítulo de palabras clave                 | grupos ≤ 3 palabras; se omite lo que la escena ya escribe                                                             | `motor.js` (subtítulos)                 |
| Zona segura de Shorts                       | texto fuera de y > 84 % y de la columna derecha                                                                       | L1                                      |
| Voz 130-170 ppm (blog)                      | 150-200 ppm                                                                                                           | V1                                      |
| Anti-plantilla (política YouTube)           | parecido visual/guion/estructura/recursos; repetición de edición; variedad de escenas                                 | P1, P1.rep, `variedad_escenas`          |
| Mostrar la prueba                           | documento legible (entrada + 3 palabras/s); cada cifra con URL                                                        | E1 `prueba_breve`, D1                   |
| Gráfica con escala fija, un cambio a la vez | `curva`, `anios`, `puntos`, `contador3d`                                                                              | catálogo                                |
| Sin presentador IA que aconseje             | voz faceless sin persona; aviso YMYL                                                                                  | D1                                      |
| Miniatura/título                            | no se optimiza (§2)                                                                                                   | —                                       |

## 10. Huecos (lo que nadie mide hoy)

1. **El primer cuadro sin sonido.** G1 mira que haya texto y voz pronto, no que los cuadros de 0-1 s **digan
   la promesa** a quien aún no oye ni lee el subtítulo.
2. **Cifra convertida en objeto.** No hay regla ni medida de si la cifra clave tiene representación física.
3. **Ritmo por idea.** R1 pone un suelo de cambio (≤ 2,5 s quieto) pero no un **techo de saltos de idea**
   (≥ 10 cambios no relacionados por 30 s satura). Tampoco se guarda el plano medio de cada vídeo para
   cruzarlo con la retención.
4. **El giro de la mitad no tiene marca visual.** MITAD está en el guion; nada obliga a que el giro se _vea_
   distinto (cambio de tipo de escena, color, música `oscuro`).
5. **Cobertura de texto.** Instagram castiga "mayormente cubierto de texto"; no medimos el % del cuadro con texto.
6. **Distancia a referencias del nicho.** POLITICA la admite como métrica, pero no hay conjunto de referencia
   ni números sacados de él (plano medio, tiempo al primer texto, ppm, % de texto).
7. **Bucle**: sin probar, y con trampa de métrica (§8.5).

## 11. Cambios propuestos, priorizados (NO implementados: es propuesta)

Orden = evidencia × efecto esperado / coste. Cada uno es UNA variable: aislarla antes de concluir (POLITICA).

1. **Conjunto de referencia y medidores existentes sobre él.** 15-20 Shorts del nicho con ≥ 1 M vistas (los
   del §3.2 más Casually Finance) medidos con `medir_ritmo`, `analizar_video`, `medir_texto`, `medir_voz`:
   plano medio, cortes/min, tiempo al primer texto, ppm, % del cuadro con texto.
   _Por qué:_ sin esto los umbrales de R1/V1/G1 son a ojo; con esto la "distancia a referencias" es un número.
   _Medir:_ la propia distancia, cada métrica nuestra contra la mediana de referencia. _Coste:_ bajo.
   ⚠ Descargar vídeos ajenos requiere el OK del usuario (solo análisis local, nunca re-subir).
2. **Prueba "mudo" del gancho (J0).** Hoja de 4 cuadros (0 / 0,5 / 1 / 2 s) sin audio: ¿se entiende la
   promesa y hay un objeto, cifra o persona concretos, no un título sobre fondo tenue?
   _Por qué:_ 0,25 s ya cuenta (Meta), 30 % se va antes de 3 s (Kuaishou), patrón Hoyos/Galloway.
   _Medir:_ A/B a ciegas del usuario (gancho mudo-fuerte vs actual) y `se_quedaron` de Studio.
   _Coste:_ bajo, un juicio más en `critico.py`.
3. **Cifra clave convertida en objeto.** La cifra central tiene una escena que la vuelve contable o
   comparable (fajos, montón, puntos, años de salario); ya existen `puntos`, `contador3d`, `tarjetas`.
   _Por qué:_ caso Yang y patrón 2 del nicho; más que "número grande en pantalla".
   _Medir:_ retención relativa en el bloque de esa escena (`retention_by_block`) contra los vecinos; a ciegas.
   _Coste:_ bajo (guion + catálogo actual).
4. **Giro de la mitad con marca visual.** En la frase del giro (40-60 %): cambio de tipo de escena más
   `musica.oscuro` o paleta distinta, no solo un `golpe`.
   _Por qué:_ la mitad es donde se hunden 3 de 9; el giro se escribe pero no se _ve_.
   _Medir:_ retención relativa al 50 % ≥ 0,6 (objetivo de `INVESTIGACION-VIRAL` §4), tras validar el
   instrumento (§8.9). _Coste:_ bajo.
5. **Techo de saltos de idea**, además del suelo de R1: ≤ ~9 cambios de _escena_ por 30 s; los cortes
   rápidos _dentro_ de una escena (punch, `mov`) siguen libres.
   _Por qué:_ Lang 1999/2000, dentro de una idea ayuda y entre ideas satura; finanzas es información.
   _Medir:_ guardar plano medio y escenas/30 s en el ADN; cruzar con retención al 50 % cuando n ≥ 15.
   _Coste:_ bajo, `medir_ritmo` ya detecta cortes.
6. **Al menos una evidencia real por vídeo** (documento, gráfica con fuente, captura) en vez de stock
   genérico; contar el % de segundos con stock genérico.
   _Por qué:_ política de YouTube (plantilla/slideshow) y fallo nº 1 citado en el nicho; arriesga la
   monetización, que es el objetivo. _Medir:_ a ciegas ("¿se ve genérico?") y revisión YPP sin rechazo.
   _Coste:_ medio (buscar documentos).
7. **Cobertura de texto ≤ X % del cuadro**, con X sacado del #1.
   _Por qué:_ Instagram lo penaliza explícitamente; redundancia de Mayer.
   _Medir:_ `medir_texto` ya tiene cajas, falta el % de área por cuadro; comparar alcance en IG. _Coste:_ bajo.
8. **Último plano "para enviar"**: comparación que el espectador manda ("tu 401k vs el suyo") legible al final.
   _Por qué:_ envíos/alcance es señal top de Meta para no seguidores; hoy 2 compartidos en 3.817 vistas.
   _Medir:_ compartidos/alcance en `production_social`. _Coste:_ bajo.
9. **Bucle (experimento, no regla):** la última frase enlaza con la primera, aviso YMYL fuera del corte.
   _Por qué:_ práctica común, sin dato riguroso; puede inflar vistas y **bajar** `se_quedaron`.
   _Medir:_ porcentaje visto y retención al 100 %, NO el score v4; A/B en 2 vídeos del mismo formato.
   _Coste:_ bajo, pero choca con la tarjeta final del aviso.

**No hacer** (evidencia en contra o nula): optimizar miniatura/título de Shorts (§2, §8.6); voz por encima de
200 ppm; saltos de idea cada ≤ 3 s; subtítulo de transcripción completa; "+X % por tipo de gancho" de blogs.

## 12. Límites y fuentes sin verificar

- Lang 1999 y Robertson 2008: solo citas secundarias. TikTok "63 %": fuente original no hallada. Galloway:
  resumen de vidIQ. Citas de Mosseri, Sherman y Mohan: vía prensa.
- Casi todo lo de "tipo de gancho" viene de **anuncios**, no de Shorts orgánicos.
- Ningún Short del nicho se analizó fotograma a fotograma: el cambio #1 existe para cerrar justo eso.
