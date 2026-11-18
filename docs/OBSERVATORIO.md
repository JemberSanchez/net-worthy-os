# OBSERVATORIO — entender qué premia el algoritmo y qué disfruta la gente (diseño, 14-nov-2026)

> Estado: **DISEÑO, nada construido.** Cada pieza termina con una métrica MEDIDA (docs/POLITICA.md).
> Todo umbral sale de n pequeño y es **PROVISIONAL** hasta que se diga lo contrario con datos.

## 0. Por qué existe

El canal produce bien (el crítico caza los defectos técnicos), pero no sabe **por qué** un vídeo despega
y otro muere. Hoy miramos el total final de cada vídeo; el algoritmo decide en los primeros
espectadores. Necesitamos medir lo que él mide, en el momento en que lo mide, y compararlo con lo que
funciona en toda la plataforma, no solo en nuestros vídeos.

## 1. Evidencia de partida (medida el 14-nov, YouTube Analytics API, desglose completo de tráfico)

| Vídeo         | Vistas desde el feed | Vistas totales | % medio visto | Se quedaron (engaged/vistas) | Destino      |
| ------------- | -------------------: | -------------: | ------------: | ---------------------------: | ------------ |
| nvidia-weight |                    0 |              2 |           0 % |                          0/2 | muerto       |
| binance-heist |                    2 |              5 |           0 % |                          0/5 | muerto       |
| fed-vs-card   |                    1 |              4 |          11 % |                          1/4 | muerto       |
| holiday-debt  |                   26 |             29 |          19 % |                         3/29 | muerto (2.ª) |
| ronald-wayne  |                  237 |            241 |          70 % |                      126/241 | empujado     |
| midterm-rally |                  479 |            496 |          81 % |                      227/496 | empujado     |

Lecturas (n=6, PROVISIONAL):

- YouTube **sí prueba** cada Short en el feed, con una muestra diminuta (1-26 personas). Corrige la idea
  anterior de que "no los probó": los probó y la gente deslizó.
- Los empujados retienen 70-81 % de media; los muertos, < 20 %. La prueba inicial se gana o se pierde en
  los **primeros 1-2 segundos**.
- El metadato no explica nada: los 7 vídeos comparados son públicos, no "para niños", categoría 27,
  34-41 s, con título y etiquetas parecidas (Data API, 14-nov).
- El orden de publicación respecto a Meta no explica nada: ronald-wayne salió a la vez que Meta y despegó.

Lo que YouTube documenta en público: la métrica de Studio "Shown in feed" y "How many chose to view"
(visto vs. deslizado). **No** documenta que esa sea la señal de ranking ni ningún umbral; los "70-90 %"
que circulan son análisis de terceros. Nosotros medimos el nuestro.

## 2. Principios

1. **Medir lo que el algoritmo ve, cuando lo ve**: la primera muestra del feed, no el total a 30 días.
2. **Lo que la gente hace manda sobre lo que dice**: retención y deslizamiento por encima de comentarios.
3. **Toda la plataforma, no solo nosotros**: un patrón solo se adopta si aparece en lo que despega
   AHORA en el nicho y además mejora NUESTRA métrica en un experimento.
4. **Una variable por experimento**, con test de significancia (`omega/creative/experiments.py` ya lo
   hace y se niega a declarar ganador con ruido).
5. **Legal primero**: nada de descargar vídeos ajenos (Términos de YouTube/TikTok), música solo con
   licencia comercial verificada, publicar en vivo solo con aprobación en el chat.

## 3. Piezas

Orden por impacto/coste. Cada una: pregunta, fuentes, qué existe, qué falta, criterio de "listo".

### P0 — Datos completos y a tiempo (base de todo) · ~1 sesión

- **Pregunta:** ¿cuándo y por qué se encendió o se apagó el empuje de cada vídeo?
- **Problema actual:** `analytics_yt.consultar` ya trae el tráfico completo, pero `production_analytics`
  guarda solo la fuente dominante (`trafico_dominante`). Y Analytics llega con 48-72 h de retraso:
  imposible ver la primera hora con esa API.
- **Hacer:**
  - Guardar el desglose completo de tráfico (`SHORTS`, `YT_SEARCH`, `SUBSCRIBER`…) por vídeo.
  - Tabla nueva `production_snapshot(ref, plataforma, t_horas, vistas, likes, comentarios, compartidos)`
    con fotos a 1, 3, 24 y 72 h. Fuente: `viewCount`/`likeCount` de la **Data API** (casi en tiempo
    real) para YouTube; insights de Meta; TikTok cuando exista P5.
  - Lanzador: **nada corre en el PC del usuario** (decisión 14-nov). `fotos` se lanza a mano o dentro
    de `analytics-sync`/`/producir`; para fotos horarias, GitHub Actions con cron en el repo PRIVADO de
    estado (logs privados; secreto `YOUTUBE_TOKEN_JSON`), pendiente de aprobación.
  - **Autopsia automática** al llegar Analytics (72 h), una de tres causas, cada una con su arreglo:
    `no_probado` (0 vistas de feed: problema de publicación) · `deslizado` (feed > 0 y % visto < 30 %:
    gancho) · `visto_sin_empuje` (% visto alto, poco alcance: contenido o tema).
- **Listo:** los 16 vídeos publicados con tráfico completo y autopsia; cada vídeo nuevo con fotos a 1/3/24/72 h
  sin intervención manual. Test sobre la clasificación de la autopsia.

### P1 — Ganar los primeros 2 segundos · ~1-2 sesiones

- **Pregunta:** ¿qué hace que el primer espectador no deslice?
- **Qué existe:** puerta `gancho` del previo (luma del primer fotograma), `_puerta_gancho` del
  guionista (cifra/nombres en la 1.ª frase), retención por bloque en 7 vídeos.
- **Hacer:**
  - Ficha del **primer fotograma y los 2 primeros segundos** de cada vídeo propio: qué se ve (cara,
    objeto, texto, gráfico), cuántas palabras en pantalla, si hay movimiento en el fotograma 0, cuándo
    llega la primera palabra de voz, si el gancho se entiende sin sonido.
  - Cruzar la ficha con el % visto de la primera muestra del feed (P0). Mismo cruce con los Shorts del
    nicho que despegan (P2).
  - Convertir las diferencias en reglas de puerta (estáticas, antes de la voz) solo cuando un
    experimento las confirme.
- **Listo:** % medio visto de la primera muestra del feed > 50 % en 3 vídeos seguidos (hoy: mediana de
  los 6 medidos ≈ 15 %). Umbral PROVISIONAL.

### P2 — Radar de toda la plataforma (YouTube + TikTok + Reels) · ~2 sesiones + ~20 min/semana

- **Pregunta:** ¿qué formatos, ganchos y estilos despegan HOY en finanzas, en canales chicos?
- **Qué existe:** `research/viral_collect.py` + `viral_compare.py` (muestra fija desde 2025-07-01, solo
  metadatos), `docs/VIRALIDAD.md`.
- **Hacer:**
  - **YouTube:** ventana móvil (30-60 días), canales ≤ 10k subs, orden por vistas/día; filtro
    `_is_english`. Métricas: vistas/día, likes/vista, comentarios/vista.
  - **TikTok:** Creative Center (público): hashtags, canciones, creadores y vídeos en tendencia por
    región e industria (finanzas). Sin API de investigación (solo académicos).
  - **Reels:** observación manual en Chrome; Meta no expone búsqueda de Reels ajenos por API.
  - **Ficha visual** de los 15 mejores por plataforma, vista en el Chrome del usuario como cualquier
    espectador (sin descargar): fotograma 0, gancho de 2 s, texto en pantalla, ritmo, voz humana/IA,
    formato, final en bucle. Plantilla fija para que sea comparable semana a semana.
  - Informe `research/radar-<fecha>.md`: formatos en alza, ganchos repetidos, 3 huecos frente a
    nuestros vídeos (vía ADN + `medir_parecido`).
- **Listo:** 2 informes semanales seguidos con la misma plantilla y ≥ 1 hallazgo convertido en
  experimento (P4).

### P3 — Qué disfruta la gente (comentarios + engagement) · ~1 sesión

- **Pregunta:** ¿qué frase citan, qué preguntan, qué discuten, qué piden?
- **Fuentes:** `commentThreads.list` de la Data API (comentarios públicos; hoy solo la usamos para
  publicar), comentarios de nuestros vídeos en YouTube/FB/IG/TikTok.
- **Hacer:** ~100 comentarios top de los 15 mejores del radar + todos los nuestros. Clasificación con
  plantilla fija (cita, pregunta, desacuerdo, emoción, petición de tema). Salida: agregados con citas
  cortas, nunca volcados.
- **Usos:** temas pedidos van a `decide`; frases citadas y emociones van al brief del guionista.
- **Listo:** el brief del guionista recibe "lo que la audiencia pide/cita" y un vídeo hecho con eso se
  mide contra el anterior del mismo formato.

### P4 — Bucle de experimentos · continuo

- Cada hallazgo de P1-P3 entra como experimento de **una** variable en `experiments.py`.
- Métrica principal: % visto de la primera muestra del feed y "se quedaron"; secundaria: likes/vista
  (banda del nicho 1-3,7 %, VIRALIDAD §3.3) y compartidos.
- Con n por vídeo tan bajo, la unidad es el **vídeo**, no el espectador: se necesitan varios vídeos por
  variante. Se acepta "inconcluso" como resultado.
- **Listo:** un experimento resuelto (ganador significativo o inconcluso declarado) al mes.

### P5 — TikTok · decisión del usuario + ~1-2 sesiones

- **Publicar:** la Content Posting API exige una **auditoría** de la app; sin ella todo lo publicado
  queda en privado y como máximo 5 usuarios por 24 h (docs oficiales de TikTok for Developers). Plazo
  de la auditoría: no documentado oficialmente. Hasta pasarla: **subida manual** desde el móvil o la web
  con el MP4 que ya produce el motor.
- **Medir:** TikTok Studio (manual) al principio; vía API, solo tras la auditoría y con los scopes de
  lectura que haya que verificar.
- **Música:** la biblioteca general **no** está autorizada para contenido de marca; la Commercial Music
  Library sí, con sus términos y "Usable Placements". Hasta verificarlos, seguimos con nuestra lista
  cerrada de licencias.
- **Dinero:** Creator Rewards paga vídeos **de ≥ 1 min**, con ≥ 10k seguidores (fuentes de terceros
  citando los términos de EE. UU.; confirmarlo en TikTok Studio). Esto conecta con P6.
- **Adaptación:** mismo vídeo, distinto empaquetado (texto sobre el vídeo, descripción, hashtags del
  Creative Center); zonas seguras propias de TikTok a medir.
- **Listo:** cuenta creada por el usuario, 10 vídeos subidos, fotos de P0 con datos de TikTok.

### P6 — Motor para vídeos largos (≥ 1 min y hasta 10 min) · sesión propia

- **Por qué ahora:** TikTok paga ≥ 1 min; YouTube largo monetiza mejor. El motor actual no escala:
  render ≈ 3-7× la duración, OCR del crítico lineal en duración, 45 de 99 corridas fallidas (13-nov).
- **Palancas medibles** (HyperFrames 0.9.45 ya las soporta: `--start/--end`, `--workers`, `--gpu`,
  `--keyframe-interval`):
  - Render por **tramos** en paralelo, con caché por hash del tramo: un parche del crítico re-renderiza
    solo el tramo tocado. Concatenación sin recodificar (keyframe al inicio de cada tramo).
  - OCR del crítico solo en los instantes donde el plan pone o cambia texto (escala con el número de
    textos, no con la duración).
  - Voz por frase con caché (hash de texto + voz) y worker de Kokoro persistente.
  - Puertas estáticas específicas de vídeo largo: variedad visual por minuto, repetición de recursos,
    memoria.
- **Listo:** un vídeo de 3 min de prueba medido de punta a punta: render + crítico ≤ 2× la duración,
  0 fallos de corrida, mismo resultado del crítico que un render completo (SSIM y textos).

## 4. Orden propuesto

Prioridad fijada por el usuario el 14-nov: **motor, creatividad y entender el algoritmo; TikTok al final.**

`P0 → P1 → P2 → P3 → P4 (continuo)`, con **P6 en paralelo** (sesión propia, no toca los mismos archivos).
**P5 (TikTok) va el último.** P0 va primero porque sin la primera muestra del feed no se puede medir P1-P4.

## 5. Decisiones abiertas (del usuario)

1. **TikTok:** ¿cuenta de empresa o personal? (afecta a música y Creative Center). ¿Pedir la auditoría
   de la API o subir a mano?
2. **Vídeos largos:** ¿qué duración objetivo primero: 60-90 s (TikTok + Shorts) o 3-10 min (YouTube largo)?
3. **Radar en Chrome:** ¿tiempo semanal aceptable (~20 min de sesión) o quincenal?
4. ~~Tarea programada local~~: descartada por el usuario (14-nov). Alternativa: cron de GitHub Actions
   en el repo privado de estado.

## 6. Límites (lo que esto no puede saber)

- El ranking real es secreto: medimos sus efectos, no sus reglas.
- n por vídeo bajísimo (1-26 personas en la primera muestra): toda conclusión pide varios vídeos.
- Correlación ≠ causa en el radar; solo los experimentos (P4) dan causa.
- "Se quedaron" de Studio no está en la API: usamos engaged/vistas (validado ±5 pts en 7 vídeos).

## Fuentes (consultadas el 14-nov-2026)

- TikTok Content Posting API, Direct Post: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
- TikTok Content Sharing Guidelines: https://developers.tiktok.com/docs/en/content-sharing-guidelines
- TikTok Creative Center: https://ads.tiktok.com/help/article/creative-center
- TikTok Commercial Music Library (biblioteca general no autorizada para marcas): https://ads.tiktok.com/business/zh/blog/audio-library-royalty-free-music
- Creator Rewards (terceros, verificar en la app): https://ttcalculator.net/learn/creator-rewards-program/
- YouTube Shorts, métricas "Shown in feed"/"chose to view" (resumen de la ayuda de YouTube): https://outlierkit.com/resources/youtube-shorts-algorithm/
- Medición propia: YouTube Analytics API y Data API, 14-nov-2026 (sección 1).
